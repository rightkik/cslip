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

    # Google OAuth2 credentials
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str

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
