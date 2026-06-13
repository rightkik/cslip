from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ReceiptData(BaseModel):
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


class OCRProvider(ABC):
    @abstractmethod
    async def extract(self, file_bytes: bytes, mime_type: str) -> ReceiptData: ...
