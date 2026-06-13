from unittest.mock import MagicMock, patch

import pytest

import app.storage.drive as drive_module
from app.storage.drive import build_filename, ensure_folder_path, upload_file


@pytest.fixture(autouse=True)
def _reset():
    drive_module._folder_cache.clear()
    drive_module._drive_service = None
    yield
    drive_module._folder_cache.clear()
    drive_module._drive_service = None


@pytest.fixture
def mock_service():
    svc = MagicMock()
    with patch("app.storage.drive._get_service", return_value=svc):
        yield svc


# --- build_filename (pure) ---

def test_build_filename_all_fields():
    name = build_filename("2025-01-15", "Starbucks TH", "SB-001", "image/jpeg")
    assert name == "2025-01-15_Starbucks_TH_SB-001.jpg"


def test_build_filename_missing_fields():
    name = build_filename(None, None, None, "image/png")
    assert name == "unknown_date_unknown_vendor.png"


def test_build_filename_no_document_number():
    name = build_filename("2025-03-01", "Shop", None, "application/pdf")
    assert name == "2025-03-01_Shop.pdf"


def test_build_filename_unknown_mime():
    name = build_filename("2025-01-01", "X", None, "application/octet-stream")
    assert name.endswith(".bin")


# --- ensure_folder_path ---

async def test_ensure_folder_path_creates_all_levels(mock_service):
    files = mock_service.files.return_value
    files.list.return_value.execute.return_value = {"files": []}
    files.create.return_value.execute.return_value = {"id": "new-folder-id"}

    folder_id = await ensure_folder_path("default", 2025, 1)

    assert folder_id == "new-folder-id"
    assert files.list.call_count == 3
    assert files.create.call_count == 3


async def test_ensure_folder_path_uses_existing_folder(mock_service):
    files = mock_service.files.return_value
    files.list.return_value.execute.return_value = {"files": [{"id": "existing-id"}]}

    folder_id = await ensure_folder_path("default", 2025, 1)

    assert folder_id == "existing-id"
    assert files.list.call_count == 3
    files.create.assert_not_called()


async def test_ensure_folder_path_caches_lookups(mock_service):
    files = mock_service.files.return_value
    files.list.return_value.execute.return_value = {"files": []}
    files.create.return_value.execute.return_value = {"id": "folder-id"}

    await ensure_folder_path("default", 2025, 1)
    files.list.reset_mock()
    files.create.reset_mock()

    await ensure_folder_path("default", 2025, 1)

    files.list.assert_not_called()
    files.create.assert_not_called()


async def test_ensure_folder_path_month_zero_padded(mock_service):
    files = mock_service.files.return_value
    files.list.return_value.execute.return_value = {"files": []}
    files.create.return_value.execute.return_value = {"id": "fid"}

    await ensure_folder_path("default", 2025, 3)

    # third create call should use "03" not "3"
    calls = [str(c) for c in files.list.call_args_list]
    assert any("03" in c for c in calls)


# --- upload_file ---

async def test_upload_file_returns_ids(mock_service):
    files = mock_service.files.return_value
    files.create.return_value.execute.return_value = {
        "id": "file-abc",
        "webViewLink": "https://drive.google.com/file/d/file-abc/view",
    }

    file_id, url = await upload_file(b"data", "receipt.jpg", "image/jpeg", "folder-123")

    assert file_id == "file-abc"
    assert "file-abc" in url
