from __future__ import annotations

from pathlib import Path


from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent / ".env"

class Settings(BaseSettings):
    model_config: str = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", env_file_encoding="utf-8")

    APP_NAME: str
    APP_ENV: str
    FACILITIES_CSV: str
    RAW_DISCHARGE_DATA: str
    WATER_TEMPERATURE_DATA: str
    CURTAILMENT_DATA: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
