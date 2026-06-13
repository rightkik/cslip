from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ReceiptStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class ReceiptRecord(BaseModel):
    id: UUID
    line_user_id: str
    line_message_id: str
    status: ReceiptStatus
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    issue_date: date | None = None
    category: str | None = None
    subtotal: Decimal | None = None
    vat_amount: Decimal | None = None
    wht_amount: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str = "THB"
    raw_text: str | None = None
    confidence: float | None = None
    drive_file_id: str | None = None
    drive_file_url: str | None = None
    sheet_row_synced: bool = False
    created_at: datetime | None = None
    confirmed_at: datetime | None = None
    company_id: UUID | None = None
