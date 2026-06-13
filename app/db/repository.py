import logging
from datetime import date

from supabase import AsyncClient, acreate_client

from app.config import get_settings
from app.db.models import ReceiptRecord, ReceiptStatus
from app.ocr.base import ReceiptData

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None


async def _get_client() -> AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    return _client


class ReceiptRepository:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def insert_pending(
        self,
        receipt_data: ReceiptData,
        line_user_id: str,
        line_message_id: str,
    ) -> str:
        """Insert a new pending receipt and return its UUID."""
        row = {
            "line_user_id": line_user_id,
            "line_message_id": line_message_id,
            "status": ReceiptStatus.pending.value,
            "vendor_name": receipt_data.vendor_name,
            "vendor_tax_id": receipt_data.vendor_tax_id,
            "document_type": receipt_data.document_type,
            "document_number": receipt_data.document_number,
            "issue_date": receipt_data.issue_date.isoformat() if receipt_data.issue_date else None,
            "category": receipt_data.category,
            "subtotal": float(receipt_data.subtotal) if receipt_data.subtotal is not None else None,
            "vat_amount": float(receipt_data.vat_amount) if receipt_data.vat_amount is not None else None,
            "wht_amount": float(receipt_data.wht_amount) if receipt_data.wht_amount is not None else None,
            "total_amount": float(receipt_data.total_amount) if receipt_data.total_amount is not None else None,
            "currency": receipt_data.currency,
            "raw_text": receipt_data.raw_text,
            "confidence": receipt_data.confidence,
        }
        result = await self._client.table("receipts").insert(row).execute()
        return result.data[0]["id"]

    async def get_by_id(self, receipt_id: str) -> ReceiptRecord | None:
        result = (
            await self._client.table("receipts")
            .select("*")
            .eq("id", receipt_id)
            .maybe_single()
            .execute()
        )
        if result.data is None:
            return None
        return ReceiptRecord.model_validate(result.data)

    async def get_by_message_id(self, line_message_id: str) -> ReceiptRecord | None:
        result = (
            await self._client.table("receipts")
            .select("*")
            .eq("line_message_id", line_message_id)
            .maybe_single()
            .execute()
        )
        if result.data is None:
            return None
        return ReceiptRecord.model_validate(result.data)

    async def update_status(self, receipt_id: str, status: ReceiptStatus) -> None:
        await (
            self._client.table("receipts")
            .update({"status": status.value})
            .eq("id", receipt_id)
            .execute()
        )

    async def update_drive_info(
        self, receipt_id: str, drive_file_id: str, drive_file_url: str
    ) -> None:
        await (
            self._client.table("receipts")
            .update({"drive_file_id": drive_file_id, "drive_file_url": drive_file_url})
            .eq("id", receipt_id)
            .execute()
        )

    async def mark_synced(self, receipt_id: str) -> None:
        await (
            self._client.table("receipts")
            .update({"sheet_row_synced": True})
            .eq("id", receipt_id)
            .execute()
        )

    async def list_by_user_and_month(
        self, line_user_id: str, year: int, month: int
    ) -> list[ReceiptRecord]:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        result = (
            await self._client.table("receipts")
            .select("*")
            .eq("line_user_id", line_user_id)
            .gte("issue_date", start.isoformat())
            .lt("issue_date", end.isoformat())
            .execute()
        )
        return [ReceiptRecord.model_validate(r) for r in (result.data or [])]


async def get_repository() -> ReceiptRepository:
    return ReceiptRepository(await _get_client())
