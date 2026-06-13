import os

# Set required env vars before any app module is imported by pytest
os.environ.update({
    "LINE_CHANNEL_ACCESS_TOKEN": "test-token",
    "LINE_CHANNEL_SECRET": "test-secret",
    "GEMINI_API_KEY": "test-key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "DRIVE_ROOT_FOLDER_ID": "test-folder-id",
    "SHEETS_SPREADSHEET_ID": "test-sheet-id",
})
