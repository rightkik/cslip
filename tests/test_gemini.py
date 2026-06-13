import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ocr.base import ReceiptData
from app.ocr.gemini import GeminiOCR, _safe_parse


# --- unit tests for _safe_parse (no I/O) ---

def test_safe_parse_clean_json():
    raw = '{"vendor_name": "ร้านกาแฟ", "total_amount": 65.0, "currency": "THB"}'
    result = _safe_parse(raw)
    assert result["vendor_name"] == "ร้านกาแฟ"
    assert result["total_amount"] == 65.0


def test_safe_parse_strips_code_fences():
    raw = '```json\n{"total_amount": 100.0}\n```'
    assert _safe_parse(raw) == {"total_amount": 100.0}


def test_safe_parse_strips_plain_fences():
    raw = '```\n{"total_amount": 50.0}\n```'
    assert _safe_parse(raw) == {"total_amount": 50.0}


def test_safe_parse_invalid_returns_empty():
    assert _safe_parse("not json at all") == {}


def test_safe_parse_non_dict_returns_empty():
    assert _safe_parse("[1, 2, 3]") == {}


# --- integration-style test with mocked Gemini client ---

MOCK_PAYLOAD = {
    "vendor_name": "Starbucks Thailand",
    "vendor_tax_id": None,
    "document_type": "receipt",
    "document_number": "SB-001",
    "issue_date": "2025-03-15",
    "category": "ค่าอาหาร",
    "subtotal": None,
    "vat_amount": None,
    "wht_amount": None,
    "total_amount": 185.0,
    "currency": "THB",
    "raw_text": "Starbucks Latte 185 THB",
    "confidence": 0.92,
}


@pytest.mark.asyncio
async def test_extract_returns_receipt_data():
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(MOCK_PAYLOAD)

    with patch("app.ocr.gemini.genai.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        ocr = GeminiOCR()
        result = await ocr.extract(b"fake image bytes", "image/jpeg")

    assert isinstance(result, ReceiptData)
    assert result.vendor_name == "Starbucks Thailand"
    assert result.total_amount == Decimal("185.0")
    assert str(result.issue_date) == "2025-03-15"
    assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_extract_with_code_fence_response():
    mock_resp = MagicMock()
    mock_resp.text = f"```json\n{json.dumps(MOCK_PAYLOAD)}\n```"

    with patch("app.ocr.gemini.genai.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        ocr = GeminiOCR()
        result = await ocr.extract(b"fake bytes", "image/png")

    assert result.vendor_name == "Starbucks Thailand"


@pytest.mark.asyncio
async def test_extract_text_returns_receipt_data():
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"vendor_name": "กาแฟ", "total_amount": 65.0, "confidence": 0.8})

    with patch("app.ocr.gemini.genai.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.aio.models.generate_content = AsyncMock(return_value=mock_resp)

        ocr = GeminiOCR()
        result = await ocr.extract_text("กาแฟ 65")

    assert result.vendor_name == "กาแฟ"
    assert result.total_amount == Decimal("65.0")


@pytest.mark.asyncio
async def test_extract_propagates_gemini_error():
    with patch("app.ocr.gemini.genai.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.aio.models.generate_content = AsyncMock(
            side_effect=Exception("API quota exceeded")
        )

        ocr = GeminiOCR()
        with pytest.raises(Exception, match="API quota exceeded"):
            await ocr.extract(b"fake bytes", "image/jpeg")
