from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LINE Messaging API
    line_channel_access_token: str
    line_channel_secret: str

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Google Service Account — provide exactly one
    # GOOGLE_SA_JSON_PATH: local file path (dev)
    # GOOGLE_SA_JSON_B64: base64-encoded JSON (Render deployment) — decoded in Task 7
    google_sa_json_path: str | None = None
    google_sa_json_b64: str | None = None

    # Google Drive + Sheets
    drive_root_folder_id: str
    sheets_spreadsheet_id: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
