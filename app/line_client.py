import logging

import httpx

from app.config import get_settings
from app.ocr.base import ReceiptData

logger = logging.getLogger(__name__)

_LINE_API = "https://api.line.me"
_LINE_DATA_API = "https://api-data.line.me"


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {get_settings().line_channel_access_token}"}


async def download_content(message_id: str) -> tuple[bytes, str]:
    """Download image/file bytes from LINE content API."""
    url = f"{_LINE_DATA_API}/v2/bot/message/{message_id}/content"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_auth_headers())
        resp.raise_for_status()
    mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    return resp.content, mime


async def reply_text(reply_token: str, text: str) -> None:
    """Send a plain text reply (uses reply token — free, no quota)."""
    await _post_reply({
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    })


async def reply_receipt_confirmation(
    reply_token: str, data: ReceiptData, receipt_id: str
) -> None:
    """Send OCR summary with ยืนยัน / แก้ไข / ยกเลิก quick-reply buttons (Task 5+)."""
    payload = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": format_receipt_summary(data),
            "quickReply": {
                "items": [
                    {
                        "type": "action",
                        "action": {
                            "type": "postback",
                            "label": "✅ ยืนยัน",
                            "data": f"action=confirm&id={receipt_id}",
                            "displayText": "ยืนยัน",
                        },
                    },
                    {
                        "type": "action",
                        "action": {
                            "type": "postback",
                            "label": "✏️ แก้ไข",
                            "data": f"action=edit&id={receipt_id}",
                            "displayText": "แก้ไข",
                        },
                    },
                    {
                        "type": "action",
                        "action": {
                            "type": "postback",
                            "label": "❌ ยกเลิก",
                            "data": f"action=cancel&id={receipt_id}",
                            "displayText": "ยกเลิก",
                        },
                    },
                ]
            },
        }],
    }
    await _post_reply(payload)


def format_receipt_summary(data: ReceiptData) -> str:
    """Format ReceiptData into a human-readable Thai LINE message."""
    def _fmt(val) -> str:
        return f"{val:,.2f}" if val is not None else "-"

    lines = ["📄 ผลการอ่านใบเสร็จ", ""]
    lines.append(f"ร้าน: {data.vendor_name or '-'}")
    if data.vendor_tax_id:
        lines.append(f"เลขผู้เสียภาษี: {data.vendor_tax_id}")
    lines.append(f"วันที่: {data.issue_date or '-'}")
    lines.append(f"ประเภท: {data.document_type or '-'}")
    if data.document_number:
        lines.append(f"เลขที่: {data.document_number}")
    lines.append(f"หมวด: {data.category or '-'}")
    lines.append("")
    if data.subtotal is not None:
        lines.append(f"ก่อนภาษี: {_fmt(data.subtotal)} {data.currency}")
    if data.vat_amount is not None:
        lines.append(f"VAT: {_fmt(data.vat_amount)} {data.currency}")
    if data.wht_amount is not None:
        lines.append(f"WHT: {_fmt(data.wht_amount)} {data.currency}")
    lines.append(f"ยอดรวม: {_fmt(data.total_amount)} {data.currency}")
    if data.confidence is not None:
        lines.append(f"ความแม่นยำ: {int(data.confidence * 100)}%")
    return "\n".join(lines)


async def _post_reply(payload: dict) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_LINE_API}/v2/bot/message/reply",
            json=payload,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
