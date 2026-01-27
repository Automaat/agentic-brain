from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class TelegramSettings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    brain_api_url: str = "http://localhost:8000"
    default_language: str = "en"
    allowed_user_ids: list[int] = []  # Empty = allow all

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def parse_csv_user_ids(cls, v: str | list[int]) -> list[int]:
        """Parse comma-separated user IDs from .env"""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(uid.strip()) for uid in v.split(",")]
        return v


settings = TelegramSettings()  # type: ignore[call-arg]
