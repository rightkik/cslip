import logging
import urllib.parse
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import (
    FileMessageContent,
    ImageMessageContent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)

from app.config import get_settings
from app.db.models import ReceiptRecord, ReceiptStatus
from app.ocr.base import ReceiptData
from app.db.repository import get_repository
from app.line_client import (
    download_content,
    format_receipt_summary,
    reply_receipt_confirmation,
    reply_text,
)
from app.ocr.gemini import GeminiOCR
from app.storage.drive import build_filename, ensure_folder_path, upload_file
from app.storage.sheets import append_receipt_row

logger = logging.getLogger(__name__)

app = FastAPI(title="Cslip", version="0.1.0")

# ---------------------------------------------------------------------------
# Field keyword → receipt column mapping for the edit-by-text flow
# ---------------------------------------------------------------------------
_EDIT_KEYWORDS: dict[str, str] = {
    "ยอด": "total_amount",
    "ยอดรวม": "total_amount",
    "ก่อนภาษี": "subtotal",
    "ยอดก่อน": "subtotal",
    "ภาษี": "vat_amount",
    "vat": "vat_amount",
    "wht": "wht_amount",
    "หมวด": "category",
    "หมวดหมู่": "category",
    "ร้าน": "vendor_name",
    "ชื่อร้าน": "vendor_name",
    "วันที่": "issue_date",
    "ประเภท": "document_type",
    "เลขที่": "document_number",
    "เลขผู้เสียภาษี": "vendor_tax_id",
}

_NUMERIC_FIELDS = {"total_amount", "vat_amount", "wht_amount", "subtotal"}


def parse_edit_command(text: str) -> tuple[str, str] | None:
    """Return (field_name, raw_value) if text starts with a known edit keyword."""
    text = text.strip()
    for keyword, field in _EDIT_KEYWORDS.items():
        if text.lower().startswith(keyword.lower()):
            value = text[len(keyword):].strip()
            if value:
                return field, value
    return None


def _coerce_field_value(field: str, raw: str):
    """Convert a raw string value to the correct Python type for a receipt field."""
    if field in _NUMERIC_FIELDS:
        cleaned = raw.replace("บาท", "").replace(",", "").replace("฿", "").strip()
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    if field == "issue_date":
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    return raw


def _record_to_data(record: ReceiptRecord) -> ReceiptData:
    return ReceiptData(
        vendor_name=record.vendor_name,
        vendor_tax_id=record.vendor_tax_id,
        document_type=record.document_type,
        document_number=record.document_number,
        issue_date=record.issue_date,
        category=record.category,
        subtotal=record.subtotal,
        vat_amount=record.vat_amount,
        wht_amount=record.wht_amount,
        total_amount=record.total_amount,
        currency=record.currency,
        raw_text=record.raw_text,
        confidence=record.confidence,
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")
    settings = get_settings()

    parser = WebhookParser(settings.line_channel_secret)
    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if isinstance(event, MessageEvent):
            msg = event.message
            line_user_id = getattr(event.source, "user_id", None) or "unknown"
            if isinstance(msg, (ImageMessageContent, FileMessageContent)):
                background_tasks.add_task(
                    _process_receipt,
                    message_id=msg.id,
                    reply_token=event.reply_token,
                    line_user_id=line_user_id,
                )
            elif isinstance(msg, TextMessageContent):
                background_tasks.add_task(
                    _handle_text_message,
                    text=msg.text,
                    reply_token=event.reply_token,
                    line_user_id=line_user_id,
                )
        elif isinstance(event, PostbackEvent):
            background_tasks.add_task(
                _handle_postback,
                data=event.postback.data,
                reply_token=event.reply_token,
            )

    return {"ok": True}


# ---------------------------------------------------------------------------
# Background task: image/file receipt
# ---------------------------------------------------------------------------

async def _process_receipt(message_id: str, reply_token: str, line_user_id: str) -> None:
    repo = await get_repository()

    existing = await repo.get_by_message_id(message_id)
    if existing is not None:
        logger.info("Duplicate messageId=%s, skipping", message_id)
        return

    file_bytes: bytes | None = None
    mime_type: str | None = None

    try:
        logger.info("Processing receipt messageId=%s user=%s", message_id, line_user_id)
        file_bytes, mime_type = await download_content(message_id)
        data = await GeminiOCR().extract(file_bytes, mime_type)
        receipt_id = await repo.insert_pending(data, line_user_id, message_id)
        # Reply BEFORE Drive upload — LINE reply token expires in 30 s
        await reply_receipt_confirmation(reply_token, data, receipt_id)
        logger.info("Receipt saved id=%s messageId=%s", receipt_id, message_id)
    except Exception:
        logger.exception("Failed to process messageId=%s", message_id)
        try:
            await reply_text(reply_token, "อ่านไม่ออก กรุณาถ่ายใหม่ให้ชัดขึ้น หรือลองอีกครั้ง 🙏")
        except Exception:
            logger.exception("Failed to send error reply for messageId=%s", message_id)
        return

    # Drive upload runs after reply — failure here is non-fatal
    try:
        file_date = data.issue_date or datetime.now(timezone.utc).date()
        folder_id = await ensure_folder_path("default", file_date.year, file_date.month)
        filename = build_filename(
            str(data.issue_date) if data.issue_date else None,
            data.vendor_name,
            data.document_number,
            mime_type,
        )
        drive_file_id, drive_file_url = await upload_file(file_bytes, filename, mime_type, folder_id)
        await repo.update_drive_info(receipt_id, drive_file_id, drive_file_url)
        logger.info("Drive upload done file_id=%s receipt_id=%s", drive_file_id, receipt_id)
    except Exception:
        logger.exception("Drive upload failed receipt_id=%s (receipt still saved in DB)", receipt_id)


# ---------------------------------------------------------------------------
# Background task: text message (edit or quick-entry)
# ---------------------------------------------------------------------------

async def _handle_text_message(text: str, reply_token: str, line_user_id: str) -> None:
    edit_cmd = parse_edit_command(text)

    if edit_cmd:
        repo = await get_repository()
        pending = await repo.get_latest_pending_by_user(line_user_id)
        if pending:
            field, raw_value = edit_cmd
            await _apply_edit(str(pending.id), field, raw_value, reply_token, repo)
            return

    # No edit match, or no pending receipt → natural language quick-entry
    await _handle_text_entry(text, reply_token, line_user_id)


async def _apply_edit(receipt_id: str, field: str, raw_value: str, reply_token: str, repo) -> None:
    coerced = _coerce_field_value(field, raw_value)
    if coerced is None:
        await reply_text(reply_token, f"ค่าไม่ถูกต้อง: '{raw_value}' ลองใหม่อีกครั้ง")
        return
    await repo.update_fields(receipt_id, {field: coerced})
    record = await repo.get_by_id(receipt_id)
    if record:
        data = _record_to_data(record)
        await reply_receipt_confirmation(reply_token, data, receipt_id)
        logger.info("Edit applied field=%s receipt_id=%s", field, receipt_id)


async def _handle_text_entry(text: str, reply_token: str, line_user_id: str) -> None:
    try:
        data = await GeminiOCR().extract_text(text)
        if data.total_amount is None and data.vendor_name is None:
            await reply_text(reply_token, "ไม่เข้าใจคำสั่ง ลองพิมพ์ เช่น 'กาแฟ 65 บาท' หรือ 'ค่า Figma 590' 🙏")
            return
        repo = await get_repository()
        message_id = f"text:{uuid.uuid4()}"
        receipt_id = await repo.insert_pending(data, line_user_id, message_id)
        await reply_receipt_confirmation(reply_token, data, receipt_id)
        logger.info("Text entry receipt saved id=%s user=%s", receipt_id, line_user_id)
    except Exception:
        logger.exception("Text entry failed user=%s", line_user_id)
        await reply_text(reply_token, "ไม่เข้าใจคำสั่ง ลองพิมพ์ เช่น 'กาแฟ 65 บาท' 🙏")


# ---------------------------------------------------------------------------
# Background task: postback (confirm / cancel / edit)
# ---------------------------------------------------------------------------

async def _handle_postback(data: str, reply_token: str) -> None:
    params = dict(urllib.parse.parse_qsl(data))
    action = params.get("action")
    receipt_id = params.get("id")

    if not receipt_id:
        logger.warning("Postback missing id: %s", data)
        return

    if action == "confirm":
        await _handle_confirm(receipt_id, reply_token)
    elif action == "cancel":
        await _handle_cancel(receipt_id, reply_token)
    elif action == "edit":
        await _handle_edit_prompt(receipt_id, reply_token)
    else:
        logger.warning("Unknown postback action=%s id=%s", action, receipt_id)


async def _handle_confirm(receipt_id: str, reply_token: str) -> None:
    repo = await get_repository()
    record = await repo.get_by_id(receipt_id)
    if record is None:
        await reply_text(reply_token, "ไม่พบรายการนี้")
        return

    await repo.update_status(receipt_id, ReceiptStatus.confirmed)
    # Reply before Sheets sync — token expires in 30 s
    await reply_text(reply_token, "✅ บันทึกเรียบร้อยแล้ว")

    # Sheets sync after reply — non-fatal
    try:
        confirmed_record = record.model_copy(update={"status": ReceiptStatus.confirmed})
        await append_receipt_row(confirmed_record)
        await repo.mark_synced(receipt_id)
        logger.info("Sheets synced receipt_id=%s", receipt_id)
    except Exception:
        logger.exception("Sheets sync failed receipt_id=%s (status still confirmed)", receipt_id)


async def _handle_cancel(receipt_id: str, reply_token: str) -> None:
    repo = await get_repository()
    await repo.update_status(receipt_id, ReceiptStatus.rejected)
    await reply_text(reply_token, "❌ ยกเลิกรายการแล้ว")


async def _handle_edit_prompt(receipt_id: str, reply_token: str) -> None:
    """Show current summary + edit instructions when user taps ✏️ แก้ไข."""
    repo = await get_repository()
    record = await repo.get_by_id(receipt_id)
    if record is None:
        await reply_text(reply_token, "ไม่พบรายการนี้")
        return
    data = _record_to_data(record)
    hint = (
        format_receipt_summary(data)
        + "\n\n✏️ พิมพ์แก้ไข เช่น:\n'ยอด 1250'\n'หมวด ค่าเดินทาง'\n'ร้าน Starbucks'"
    )
    await reply_text(reply_token, hint)
