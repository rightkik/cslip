import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.main as main_module
from app.db.models import ReceiptRecord, ReceiptStatus
from app.main import _handle_cancel, _handle_confirm, _handle_postback

_RECEIPT_ID = "550e8400-e29b-41d4-a716-446655440000"

_PENDING_RECORD = ReceiptRecord(
    id=uuid.UUID(_RECEIPT_ID),
    line_user_id="U123",
    line_message_id="msg-001",
    status=ReceiptStatus.pending,
    vendor_name="Starbucks",
    total_amount=Decimal("185.00"),
    drive_file_url="https://drive.google.com/file/d/abc/view",
)


def _mock_repo(**overrides):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=_PENDING_RECORD)
    repo.update_status = AsyncMock()
    repo.mark_synced = AsyncMock()
    for k, v in overrides.items():
        setattr(repo, k, v)
    return repo


# --- _handle_postback routing ---

async def test_handle_postback_routes_confirm():
    with patch("app.main._handle_confirm", new_callable=AsyncMock) as mock_confirm:
        await _handle_postback(f"action=confirm&id={_RECEIPT_ID}", "token")
    mock_confirm.assert_awaited_once_with(_RECEIPT_ID, "token")


async def test_handle_postback_routes_cancel():
    with patch("app.main._handle_cancel", new_callable=AsyncMock) as mock_cancel:
        await _handle_postback(f"action=cancel&id={_RECEIPT_ID}", "token")
    mock_cancel.assert_awaited_once_with(_RECEIPT_ID, "token")


async def test_handle_postback_missing_id_returns_early():
    with patch("app.main._handle_confirm", new_callable=AsyncMock) as mock_confirm:
        await _handle_postback("action=confirm", "token")
    mock_confirm.assert_not_awaited()


async def test_handle_postback_edit_shows_summary_and_instructions():
    repo = _mock_repo()
    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=repo),
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
    ):
        await _handle_postback(f"action=edit&id={_RECEIPT_ID}", "token")
    mock_reply.assert_awaited_once()
    msg = mock_reply.call_args[0][1]
    assert "พิมพ์แก้ไข" in msg


# --- _handle_confirm ---

async def test_handle_confirm_updates_status_and_replies():
    repo = _mock_repo()
    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=repo),
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
        patch("app.main.append_receipt_row", new_callable=AsyncMock),
    ):
        await _handle_confirm(_RECEIPT_ID, "token")

    repo.update_status.assert_awaited_once_with(_RECEIPT_ID, ReceiptStatus.confirmed)
    mock_reply.assert_awaited_once()
    assert "บันทึก" in mock_reply.call_args[0][1]


async def test_handle_confirm_syncs_sheets_and_marks_synced():
    repo = _mock_repo()
    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=repo),
        patch("app.main.reply_text", new_callable=AsyncMock),
        patch("app.main.append_receipt_row", new_callable=AsyncMock) as mock_sheets,
    ):
        await _handle_confirm(_RECEIPT_ID, "token")

    mock_sheets.assert_awaited_once()
    synced_record = mock_sheets.call_args[0][0]
    assert synced_record.status == ReceiptStatus.confirmed
    repo.mark_synced.assert_awaited_once_with(_RECEIPT_ID)


async def test_handle_confirm_sheets_failure_is_nonfatal():
    repo = _mock_repo()
    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=repo),
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
        patch("app.main.append_receipt_row", new_callable=AsyncMock, side_effect=Exception("sheets down")),
    ):
        await _handle_confirm(_RECEIPT_ID, "token")  # must not raise

    repo.update_status.assert_awaited_once()
    mock_reply.assert_awaited_once()
    repo.mark_synced.assert_not_awaited()


async def test_handle_confirm_receipt_not_found():
    repo = _mock_repo(get_by_id=AsyncMock(return_value=None))
    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=repo),
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
    ):
        await _handle_confirm(_RECEIPT_ID, "token")

    repo.update_status.assert_not_awaited()
    mock_reply.assert_awaited_once()
    assert "ไม่พบ" in mock_reply.call_args[0][1]


# --- _handle_cancel ---

async def test_handle_cancel_rejects_and_replies():
    repo = _mock_repo()
    with (
        patch("app.main.get_repository", new_callable=AsyncMock, return_value=repo),
        patch("app.main.reply_text", new_callable=AsyncMock) as mock_reply,
    ):
        await _handle_cancel(_RECEIPT_ID, "token")

    repo.update_status.assert_awaited_once_with(_RECEIPT_ID, ReceiptStatus.rejected)
    mock_reply.assert_awaited_once()
    assert "ยกเลิก" in mock_reply.call_args[0][1]
