import json
import logging
import re

from google import genai
from google.genai import types

from app.config import get_settings
from app.ocr.base import OCRProvider, ReceiptData

logger = logging.getLogger(__name__)

_TEXT_PROMPT = """
You are a Thai expense quick-entry parser. The user typed a short text describing an expense.
Parse it into the standard receipt JSON format.

Examples:
- "กาแฟ 65" -> {"vendor_name":"กาแฟ","total_amount":65,"category":"ค่าอาหาร","confidence":0.8}
- "ค่า Figma 590" -> {"vendor_name":"Figma","total_amount":590,"category":"ค่าซอฟต์แวร์","confidence":0.9}
- "ค่าอาหาร 120 บาท" -> {"category":"ค่าอาหาร","total_amount":120,"confidence":0.85}
- "Grab 95" -> {"vendor_name":"Grab","total_amount":95,"category":"ค่าเดินทาง","confidence":0.9}

Return ONLY a valid JSON object with the same fields as the receipt schema.
Unknown fields -> null. currency default "THB". No markdown, no code fences.
""".strip()

_SYSTEM_PROMPT = """
You are a Thai receipt and tax-document extraction engine. You will receive an image or PDF of
a receipt, tax invoice, bank transfer slip, handwritten cash bill, or an order screenshot
(Shopee/Lazada/TikTok). The document may be in Thai, English, or mixed.

Extract the following fields and return ONLY a single valid JSON object — no markdown, no code
fences, no commentary. If a field is unknown, use null.

{
  "vendor_name": string | null,
  "vendor_tax_id": string | null,
  "document_type": "tax_invoice" | "receipt" | "slip" | "cash_bill" | "order_screenshot" | "other" | null,
  "document_number": string | null,
  "issue_date": string | null,
  "category": string | null,
  "subtotal": number | null,
  "vat_amount": number | null,
  "wht_amount": number | null,
  "total_amount": number | null,
  "currency": string,
  "raw_text": string | null,
  "confidence": number
}

Rules:
- Amounts are numbers without separators or currency symbols (e.g. 1605.00).
- issue_date: ISO 8601 "YYYY-MM-DD". Convert Thai Buddhist year (พ.ศ.) by subtracting 543.
- Thai date "14 ม.ค. 2568" -> "2025-01-14".
- For bank slips: vendor_name = recipient/payee; document_type = "slip".
- For order screenshots: vendor_name = platform or shop; document_type = "order_screenshot".
- Never invent a tax ID — only include vendor_tax_id if clearly visible (13 digits).
- category in Thai: "ค่าซอฟต์แวร์","ค่าอาหาร","ค่าเดินทาง","ค่าโฆษณา","ค่าอุปกรณ์สำนักงาน","ค่าบริการ","อื่นๆ"
- If only total shown and VAT included: vat = total - total/1.07.
- Output must be parseable by json.loads on the first try.
""".strip()


class GeminiOCR(OCRProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    async def extract(self, file_bytes: bytes, mime_type: str) -> ReceiptData:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[types.Part.from_bytes(data=file_bytes, mime_type=mime_type)],
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text or ""
            data = _safe_parse(raw)
            return ReceiptData(**data)
        except Exception:
            logger.exception("Gemini OCR failed")
            raise


    async def extract_text(self, text: str) -> ReceiptData:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[text],
                config=types.GenerateContentConfig(
                    system_instruction=_TEXT_PROMPT,
                    response_mime_type="application/json",
                ),
            )
            data = _safe_parse(response.text or "")
            return ReceiptData(**data)
        except Exception:
            logger.exception("Gemini text parse failed")
            raise


def _safe_parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON: %.120s", raw)
        return {}
