import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import ReceiptRecord, ReceiptStatus
from app.main import (
    _apply_edit,
    _handle_text_entry,
    _handle_text_message,
    _coerce_field_value,
    parse_edit_command,
)
from app.ocr.base import ReceiptData

_RECEIPT_ID = "550e8400-e29b-41d4-a716-446655440000"

_PENDING_RECORD = ReceiptRecord(
    id=uuid.UUID(_RECEIPT_ID),
    line_user_id="U123",
    line_message_id="msg-001",
    status=ReceiptStatus.pending,
    vendor_name="Starbucks",
    total_amount=Decimal("185.00"),
)


# ---------------------------------------------------------------------------
# parse_edit_command (pure)
# ---------------------------------------------------------------------------

def test_parse_edit_command_total_amount():
    assert parse_edit_command("ยอด 1250") == ("total_amount", "1250")


def test_parse_edit_command_category():
    assert parse_edit_command("หมวด ค่าอาหาร") == ("category", "ค่าอาหาร")


def test_parse_edit_command_vendor_name():
    assert parse_edit_command("ร้าน Amazon") == ("vendor_name", "Amazon")


def test_parse_edit_command_case_insensitive():
    assert parse_edit_command("VAT 12.10") == ("vat_amount", "12.10")


def test_parse_edit_command_no_match():
    assert parse_edit_command("กาแฟ 65 บาท") is None


def test_parse_edit_command_empty_value():
    assert parse_edit_command("ยอด") is None


def test_parse_edit_command_leading_spaces():
    assert parse_edit_command("  หมวด ค่าเดินทาง  ") == ("category", "ค่าเดินทาง")


# ---------------------------------------------------------------------------
# _coerce_field_value (pure)
# ---------------------------------------------------------------------------

def test_coerce_numeric_strips_baht():
    assert _coerce_field_value("total_amount", "1,250.50 บาท") == Decimal("1250.50")


def test_coerce_numeric_plain():
    assert _coerce_field_value("total_amount", "590") == Decimal("590")


def test_coerce_numeric_invalid_returns_none():
    assert _coerce_field_value("total_amount", "abc") is None


def test_coerce_date_valid():
    from datetime import date
    assert _coerce_field_value("issue_date", "2025-01-15") == date(2025, 1, 15)


def test_coerce_date_invalid_returns_none():
    assert _coerce_field_value("issue_date", "15/01/2025") is None


def test_coerce_text_field():
    assert _coerce_field_value("category", "ค่าอาหาร") == "ค่าอาหาร"


# ---------------------------------------------------------------------------
# _handle_text_message
# ---------------------------------------------------------------------------

async def test_handle_text_message_edit_applies_when_pending():
    mock_repo = MagicMock()
    mock_repo.get_latest_pending_by_user = AsyncMock(return_value=_PENDING_RECORD)

    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=mock_repo),
        patch("app.main._apply_edit", new_callable=AsyncMock) as mock_apply,
    ):
        await _handle_text_message("ยอด 1250", "token", "U123")

    mock_apply.assert_awaited_once_with(_RECEIPT_ID, "total_amount", "1250", "token", mock_repo)


async def test_handle_text_message_edit_fallback_when_no_pending():
    mock_repo = MagicMock()
    mock_repo.get_latest_pending_by_user = AsyncMock(return_value=None)

    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=mock_repo),
        patch("app.main._handle_text_entry", new_callable=AsyncMock) as mock_entry,
    ):
        await _handle_text_message("ยอด 1250", "token", "U123")

    mock_entry.assert_awaited_once_with("ยอด 1250", "token", "U123")


async def test_handle_text_message_no_edit_pattern_goes_to_quick_entry():
    with patch("app.main._handle_text_entry", new_callable=AsyncMock) as mock_entry:
        await _handle_text_message("กาแฟ 65 บาท", "token", "U123")

    mock_entry.assert_awaited_once_with("กาแฟ 65 บาท", "token", "U123")


# ---------------------------------------------------------------------------
# _apply_edit
# ---------------------------------------------------------------------------

async def test_apply_edit_updates_and_shows_summary():
    mock_repo = MagicMock()
    mock_repo.update_fields = AsyncMock()
    mock_repo.get_by_id = AsyncMock(return_value=_PENDING_RECORD)

    with patch("app.main.reply_receipt_confirmation", new_callable=AsyncMock) as mock_reply:
        await _apply_edit(_RECEIPT_ID, "total_amount", "1250", "token", mock_repo)

    mock_repo.update_fields.assert_awaited_once_with(
        _RECEIPT_ID, {"total_amount": Decimal("1250")}
    )
    mock_reply.assert_awaited_once()


async def test_apply_edit_invalid_value_replies_error():
    mock_repo = MagicMock()

    with patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply:
        await _apply_edit(_RECEIPT_ID, "total_amount", "abc", "token", mock_repo)

    mock_reply.assert_awaited_once()
    assert "ไม่ถูกต้อง" in mock_reply.call_args[0][1]
    mock_repo.update_fields.assert_not_called()


# ---------------------------------------------------------------------------
# _handle_text_entry
# ---------------------------------------------------------------------------

async def test_handle_text_entry_creates_pending_receipt():
    mock_data = ReceiptData(vendor_name="กาแฟ", total_amount=Decimal("65"))
    mock_repo = MagicMock()
    mock_repo.insert_pending = AsyncMock(return_value=_RECEIPT_ID)

    with (
        patch("app.main.GeminiOCR") as MockOCR,
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=mock_repo),
        patch("app.main.reply_receipt_confirmation", new_callable=AsyncMock) as mock_reply,
    ):
        MockOCR.return_value.extract_text = AsyncMock(return_value=mock_data)
        await _handle_text_entry("กาแฟ 65", "token", "U123")

    mock_repo.insert_pending.assert_awaited_once()
    mock_reply.assert_awaited_once()


async def test_handle_text_entry_empty_data_replies_error():
    mock_data = ReceiptData()  # no vendor_name, no total_amount

    with (
        patch("app.main.GeminiOCR") as MockOCR,
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
    ):
        MockOCR.return_value.extract_text = AsyncMock(return_value=mock_data)
        await _handle_text_entry("ขอบคุณ", "token", "U123")

    mock_reply.assert_awaited_once()
    assert "ไม่เข้าใจ" in mock_reply.call_args[0][1]


async def test_handle_text_entry_gemini_error_replies_error():
    with (
        patch("app.main.GeminiOCR") as MockOCR,
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
    ):
        MockOCR.return_value.extract_text = AsyncMock(side_effect=Exception("quota"))
        await _handle_text_entry("กาแฟ 65", "token", "U123")

    mock_reply.assert_awaited_once()
