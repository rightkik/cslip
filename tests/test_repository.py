from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import ReceiptRecord, ReceiptStatus
from app.db.repository import ReceiptRepository
from app.ocr.base import ReceiptData

_RECEIPT_ID = "550e8400-e29b-41d4-a716-446655440000"

_SAMPLE_ROW = {
    "id": _RECEIPT_ID,
    "line_user_id": "U123",
    "line_message_id": "msg-001",
    "status": "pending",
    "vendor_name": "Starbucks",
    "vendor_tax_id": None,
    "document_type": "receipt",
    "document_number": None,
    "issue_date": "2025-01-15",
    "category": "food",
    "subtotal": 172.90,
    "vat_amount": 12.10,
    "wht_amount": None,
    "total_amount": 185.00,
    "currency": "THB",
    "raw_text": None,
    "confidence": 0.95,
    "drive_file_id": None,
    "drive_file_url": None,
    "sheet_row_synced": False,
    "created_at": "2025-01-15T12:00:00+00:00",
    "confirmed_at": None,
    "company_id": None,
}

_SAMPLE_DATA = ReceiptData(
    vendor_name="Starbucks",
    total_amount=Decimal("185.00"),
    vat_amount=Decimal("12.10"),
    confidence=0.95,
)


def _make_repo() -> tuple[ReceiptRepository, MagicMock]:
    mock_client = MagicMock()
    return ReceiptRepository(mock_client), mock_client


async def test_get_latest_pending_by_user_returns_record():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = [_SAMPLE_ROW]
    chain = (
        client.table.return_value.select.return_value
        .eq.return_value.eq.return_value
        .order.return_value.limit.return_value
    )
    chain.execute = AsyncMock(return_value=mock_result)

    record = await repo.get_latest_pending_by_user("U123")

    assert isinstance(record, ReceiptRecord)
    assert str(record.id) == _RECEIPT_ID


async def test_get_latest_pending_by_user_returns_none_when_empty():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = []
    chain = (
        client.table.return_value.select.return_value
        .eq.return_value.eq.return_value
        .order.return_value.limit.return_value
    )
    chain.execute = AsyncMock(return_value=mock_result)

    record = await repo.get_latest_pending_by_user("U999")
    assert record is None


async def test_update_fields_serialises_decimal():
    repo, client = _make_repo()
    chain = client.table.return_value.update.return_value.eq.return_value
    chain.execute = AsyncMock(return_value=MagicMock())

    from decimal import Decimal
    await repo.update_fields(_RECEIPT_ID, {"total_amount": Decimal("999.99")})

    update_payload = client.table.return_value.update.call_args[0][0]
    assert update_payload["total_amount"] == 999.99
    assert isinstance(update_payload["total_amount"], float)


async def test_get_by_id_returns_record():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = _SAMPLE_ROW
    chain = client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
    chain.execute = AsyncMock(return_value=mock_result)

    record = await repo.get_by_id(_RECEIPT_ID)

    assert isinstance(record, ReceiptRecord)
    assert str(record.id) == _RECEIPT_ID
    client.table.return_value.select.return_value.eq.assert_called_with("id", _RECEIPT_ID)


async def test_get_by_id_returns_none_when_not_found():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = None
    chain = client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
    chain.execute = AsyncMock(return_value=mock_result)

    record = await repo.get_by_id("nonexistent-id")

    assert record is None


async def test_insert_pending_returns_id():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = [{"id": _RECEIPT_ID}]
    client.table.return_value.insert.return_value.execute = AsyncMock(return_value=mock_result)

    result_id = await repo.insert_pending(_SAMPLE_DATA, "U123", "msg-001")

    assert result_id == _RECEIPT_ID
    client.table.assert_called_with("receipts")
    inserted_row = client.table.return_value.insert.call_args[0][0]
    assert inserted_row["line_user_id"] == "U123"
    assert inserted_row["line_message_id"] == "msg-001"
    assert inserted_row["status"] == "pending"
    assert inserted_row["total_amount"] == 185.0


async def test_get_by_message_id_returns_none_when_not_found():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = None
    chain = client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
    chain.execute = AsyncMock(return_value=mock_result)

    record = await repo.get_by_message_id("nonexistent")

    assert record is None


async def test_get_by_message_id_returns_record():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = _SAMPLE_ROW
    chain = client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value
    chain.execute = AsyncMock(return_value=mock_result)

    record = await repo.get_by_message_id("msg-001")

    assert isinstance(record, ReceiptRecord)
    assert str(record.id) == _RECEIPT_ID
    assert record.vendor_name == "Starbucks"
    assert record.status == ReceiptStatus.pending


async def test_update_status_calls_update():
    repo, client = _make_repo()
    chain = client.table.return_value.update.return_value.eq.return_value
    chain.execute = AsyncMock(return_value=MagicMock())

    await repo.update_status(_RECEIPT_ID, ReceiptStatus.confirmed)

    update_payload = client.table.return_value.update.call_args[0][0]
    assert update_payload == {"status": "confirmed"}
    client.table.return_value.update.return_value.eq.assert_called_with("id", _RECEIPT_ID)


async def test_mark_synced_sets_flag():
    repo, client = _make_repo()
    chain = client.table.return_value.update.return_value.eq.return_value
    chain.execute = AsyncMock(return_value=MagicMock())

    await repo.mark_synced(_RECEIPT_ID)

    update_payload = client.table.return_value.update.call_args[0][0]
    assert update_payload == {"sheet_row_synced": True}


async def test_list_by_user_and_month_returns_records():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = [_SAMPLE_ROW]
    chain = (
        client.table.return_value
        .select.return_value
        .eq.return_value
        .gte.return_value
        .lt.return_value
    )
    chain.execute = AsyncMock(return_value=mock_result)

    records = await repo.list_by_user_and_month("U123", 2025, 1)

    assert len(records) == 1
    assert isinstance(records[0], ReceiptRecord)
    assert records[0].vendor_name == "Starbucks"


async def test_list_by_user_and_month_empty():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = []
    chain = (
        client.table.return_value
        .select.return_value
        .eq.return_value
        .gte.return_value
        .lt.return_value
    )
    chain.execute = AsyncMock(return_value=mock_result)

    records = await repo.list_by_user_and_month("U999", 2025, 6)

    assert records == []


async def test_update_drive_info_calls_update():
    repo, client = _make_repo()
    chain = client.table.return_value.update.return_value.eq.return_value
    chain.execute = AsyncMock(return_value=MagicMock())

    await repo.update_drive_info(_RECEIPT_ID, "file-xyz", "https://drive.google.com/...")

    update_payload = client.table.return_value.update.call_args[0][0]
    assert update_payload["drive_file_id"] == "file-xyz"
    assert update_payload["drive_file_url"] == "https://drive.google.com/..."


async def test_list_by_user_and_month_december_wraps_year():
    repo, client = _make_repo()
    mock_result = MagicMock()
    mock_result.data = []
    chain = (
        client.table.return_value
        .select.return_value
        .eq.return_value
        .gte.return_value
        .lt.return_value
    )
    chain.execute = AsyncMock(return_value=mock_result)

    await repo.list_by_user_and_month("U123", 2025, 12)

    lt_call = chain.execute  # just ensure it didn't raise
    gte_call_arg = client.table.return_value.select.return_value.eq.return_value.gte.call_args[0]
    lt_call_arg = client.table.return_value.select.return_value.eq.return_value.gte.return_value.lt.call_args[0]
    assert gte_call_arg == ("issue_date", "2025-12-01")
    assert lt_call_arg == ("issue_date", "2026-01-01")
