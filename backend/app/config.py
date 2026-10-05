from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    rapidapi_key: str = ""
    rapidapi_host: str = "jsearch.p.rapidapi.com"
    database_url: str = "sqlite:///./data/stage1.db"
    config_path: str = "../config.yaml"
    google_service_account_json: str = "./credentials/google-service-account.json"
    google_sheet_id: str = ""
    google_sheet_title: str = "Job Pipeline"

    backend_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    path = Path(settings.config_path)
    if not path.is_absolute():
        path = settings.backend_root / path
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
