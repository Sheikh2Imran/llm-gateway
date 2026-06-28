"""
config.py — App configuration via environment variables.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to project root (one level up from app/)
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    log_level: str = "INFO"
    app_name: str = "LLM Gateway"
    app_version: str = "1.0.0"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    # Startup debug log — remove after confirming keys load
    import logging
    log = logging.getLogger(__name__)
    log.info(f"ENV file path: {ENV_FILE} (exists={ENV_FILE.exists()})")
    log.info(f"OpenAI key loaded: {'YES' if settings.openai_api_key else 'NO'}")
    log.info(f"Anthropic key loaded: {'YES' if settings.anthropic_api_key else 'NO'}")
    return settings