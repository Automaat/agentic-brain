import sys

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class TelegramSettings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    brain_api_url: str = "http://localhost:8000"
    default_language: str = "en"
    allowed_user_ids: list[int] = []  # Empty = allow all


# Only instantiate if not in test environment
if "pytest" in sys.modules:
    # In test environment - create with dummy values
    settings = TelegramSettings(telegram_bot_token="test_token")
else:
    settings = TelegramSettings()
