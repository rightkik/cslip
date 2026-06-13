import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

import app.storage.sheets as sheets_module
from app.db.models import ReceiptRecord, ReceiptStatus
from app.storage.sheets import append_receipt_row


@pytest.fixture(autouse=True)
def _reset():
    sheets_module._sheets_service = None
    yield
    sheets_module._sheets_service = None


@pytest.fixture
def mock_service():
    svc = MagicMock()
    with patch("app.storage.sheets._get_service", return_value=svc):
        yield svc


_RECORD = ReceiptRecord(
    id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
    line_user_id="U123",
    line_message_id="msg-001",
    status=ReceiptStatus.confirmed,
    vendor_name="Starbucks",
    vendor_tax_id="1234567890123",
    document_type="receipt",
    category="ค่าอาหาร",
    issue_date="2025-01-15",
    subtotal=Decimal("172.90"),
    vat_amount=Decimal("12.10"),
    wht_amount=None,
    total_amount=Decimal("185.00"),
    currency="THB",
    drive_file_url="https://drive.google.com/file/d/abc/view",
)


async def test_append_receipt_row_calls_api(mock_service):
    mock_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {}

    await append_receipt_row(_RECORD)

    mock_service.spreadsheets.return_value.values.return_value.append.assert_called_once()
    call_kwargs = mock_service.spreadsheets.return_value.values.return_value.append.call_args[1]
    assert call_kwargs["spreadsheetId"] == "test-sheet-id"
    assert call_kwargs["valueInputOption"] == "USER_ENTERED"


async def test_append_receipt_row_correct_columns(mock_service):
    captured = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    mock_service.spreadsheets.return_value.values.return_value.append.side_effect = capture

    await append_receipt_row(_RECORD)

    row = captured["body"]["values"][0]
    assert row[0] == "2025-01-15"         # วันที่
    assert row[1] == str(_RECORD.id)      # ID
    assert row[2] == "Starbucks"           # ผู้ขาย
    assert row[3] == "1234567890123"       # เลขผู้เสียภาษี
    assert row[4] == "receipt"             # ประเภท
    assert row[5] == "ค่าอาหาร"           # หมวดหมู่
    assert "172.90" in row[6]              # ยอดก่อนภาษี
    assert "12.10" in row[7]              # VAT
    assert row[8] == ""                    # WHT (None → "")
    assert "185.00" in row[9]             # ยอดสุทธิ
    assert "drive.google.com" in row[10]  # ลิงก์ไฟล์


async def test_append_receipt_row_none_fields(mock_service):
    record = ReceiptRecord(
        id=uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
        line_user_id="U999",
        line_message_id="msg-002",
        status=ReceiptStatus.confirmed,
    )
    mock_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {}

    await append_receipt_row(record)  # should not raise

    row = mock_service.spreadsheets.return_value.values.return_value.append.call_args[1]["body"]["values"][0]
    assert row[0] == ""   # no issue_date
    assert row[10] == ""  # no drive_file_url
