import logging
import urllib.parse
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import (
    FileMessageContent,
    ImageMessageContent,
    MessageEvent,
    PostbackEvent,
)

from app.config import get_settings
from app.db.models import ReceiptStatus
from app.db.repository import get_repository
from app.line_client import download_content, reply_receipt_confirmation, reply_text
from app.ocr.gemini import GeminiOCR
from app.storage.drive import build_filename, ensure_folder_path, upload_file
from app.storage.sheets import append_receipt_row

logger = logging.getLogger(__name__)

app = FastAPI(title="Cslip", version="0.1.0")


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
            if isinstance(msg, (ImageMessageContent, FileMessageContent)):
                line_user_id = getattr(event.source, "user_id", None) or "unknown"
                background_tasks.add_task(
                    _process_receipt,
                    message_id=msg.id,
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

    # Drive upload runs after reply — failure here is non-fatal; receipt is already in DB
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
        await reply_text(reply_token, "✏️ ฟีเจอร์แก้ไขกำลังพัฒนา 🙏")
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
