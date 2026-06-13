import logging
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookParser
from linebot.v3.webhooks import FileMessageContent, ImageMessageContent, MessageEvent

from app.config import get_settings
from app.line_client import download_content, format_receipt_summary, reply_text
from app.ocr.gemini import GeminiOCR

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
                # Dedup by messageId added in Task 3 via DB unique constraint
                background_tasks.add_task(
                    _process_receipt,
                    message_id=msg.id,
                    reply_token=event.reply_token,
                )

    return {"ok": True}


async def _process_receipt(message_id: str, reply_token: str) -> None:
    try:
        logger.info("Processing receipt messageId=%s", message_id)
        file_bytes, mime_type = await download_content(message_id)
        data = await GeminiOCR().extract(file_bytes, mime_type)
        await reply_text(reply_token, format_receipt_summary(data))
        logger.info("Replied OCR result for messageId=%s", message_id)
    except Exception:
        logger.exception("Failed to process messageId=%s", message_id)
        try:
            await reply_text(reply_token, "อ่านไม่ออก กรุณาถ่ายใหม่ให้ชัดขึ้น หรือลองอีกครั้ง 🙏")
        except Exception:
            logger.exception("Failed to send error reply for messageId=%s", message_id)
