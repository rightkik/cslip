import asyncio
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import get_settings
from app.db.models import ReceiptRecord

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_sheets_service = None


def _get_service():
    global _sheets_service
    if _sheets_service is None:
        settings = get_settings()
        creds = Credentials(
            token=None,
            refresh_token=settings.google_refresh_token,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        _sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return _sheets_service


def _append_row_sync(service, spreadsheet_id: str, row: list) -> None:
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A:L",
        valueInputOption="USER_ENTERED",
        body={"values": [row]},
    ).execute()


async def append_receipt_row(record: ReceiptRecord) -> None:
    """Append one confirmed receipt row to the configured Google Sheet.

    Columns: วันที่ | ID | ผู้ขาย | เลขผู้เสียภาษี | ประเภท | หมวดหมู่ |
             ยอดก่อนภาษี | VAT | WHT | ยอดสุทธิ | ลิงก์ไฟล์ | บันทึกเมื่อ
    """
    spreadsheet_id = get_settings().sheets_spreadsheet_id

    def _fmt(val) -> str:
        return f"{val:,.2f}" if val is not None else ""

    created_str = (
        record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else ""
    )

    row = [
        str(record.issue_date) if record.issue_date else "",
        str(record.id),
        record.vendor_name or "",
        record.vendor_tax_id or "",
        record.document_type or "",
        record.category or "",
        _fmt(record.subtotal),
        _fmt(record.vat_amount),
        _fmt(record.wht_amount),
        _fmt(record.total_amount),
        record.drive_file_url or "",
        created_str,
    ]

    def _sync() -> None:
        service = _get_service()
        _append_row_sync(service, spreadsheet_id, row)

    await asyncio.to_thread(_sync)
