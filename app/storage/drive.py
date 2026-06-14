import asyncio
import io
import logging
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.config import get_settings

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive"]
_folder_cache: dict[str, str] = {}
_drive_service = None


def _get_service():
    global _drive_service
    if _drive_service is None:
        settings = get_settings()
        creds = Credentials(
            token=None,
            refresh_token=settings.google_refresh_token,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive_service


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\-.]", "_", str(text).strip())
    return text[:50]


def _find_or_create_folder_sync(service, name: str, parent_id: str) -> str:
    escaped = name.replace("'", "\\'")
    q = (
        f"name='{escaped}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    res = service.files().list(q=q, fields="files(id)", pageSize=1, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return folder["id"]


def _upload_file_sync(
    service, file_bytes: bytes, filename: str, mime_type: str, folder_id: str
) -> tuple[str, str]:
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    meta = {"name": filename, "parents": [folder_id]}
    result = service.files().create(body=meta, media_body=media, fields="id,webViewLink", supportsAllDrives=True).execute()
    return result["id"], result.get("webViewLink", "")


def build_filename(
    issue_date: str | None,
    vendor_name: str | None,
    document_number: str | None,
    mime_type: str,
) -> str:
    """Construct a Drive filename: {date}_{vendor}[_{docnum}].{ext}"""
    _EXT = {
        "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
        "image/gif": "gif", "image/webp": "webp", "application/pdf": "pdf",
    }
    ext = _EXT.get(mime_type, "bin")
    date_part = _slugify(issue_date) if issue_date else "unknown_date"
    vendor_part = _slugify(vendor_name) if vendor_name else "unknown_vendor"
    parts = [date_part, vendor_part]
    if document_number:
        parts.append(_slugify(document_number))
    return "_".join(parts) + f".{ext}"


async def ensure_folder_path(company: str, year: int, month: int) -> str:
    """Return Drive folder_id for root/{company}/{YYYY}/{MM}, creating levels as needed."""
    root_id = get_settings().drive_root_folder_id

    def _sync() -> str:
        service = _get_service()
        parent = root_id
        for part in [company, str(year), f"{month:02d}"]:
            key = f"{parent}/{part}"
            if key in _folder_cache:
                parent = _folder_cache[key]
            else:
                fid = _find_or_create_folder_sync(service, part, parent)
                _folder_cache[key] = fid
                parent = fid
        return parent

    return await asyncio.to_thread(_sync)


async def upload_file(
    file_bytes: bytes, filename: str, mime_type: str, folder_id: str
) -> tuple[str, str]:
    """Upload bytes to Drive folder. Returns (file_id, web_view_url)."""
    def _sync() -> tuple[str, str]:
        service = _get_service()
        return _upload_file_sync(service, file_bytes, filename, mime_type, folder_id)

    return await asyncio.to_thread(_sync)
