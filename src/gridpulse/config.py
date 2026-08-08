"""Environment-based configuration with safe local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    demo_mode: bool = True
    log_level: str = "INFO"
    database_url: str = "sqlite:///./gridpulse.db"
    eia_api_key: str | None = None
    nasa_firms_map_key: str | None = None
    gemini_api_key: str | None = None
    hf_token: str | None = None
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "gridpulse-mvp"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("GRIDPULSE_ENV", "development"),
            demo_mode=_as_bool(os.getenv("GRIDPULSE_DEMO_MODE"), default=True),
            log_level=os.getenv("GRIDPULSE_LOG_LEVEL", "INFO").upper(),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./gridpulse.db"),
            eia_api_key=os.getenv("EIA_API_KEY") or None,
            nasa_firms_map_key=os.getenv("NASA_FIRMS_MAP_KEY") or None,
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            hf_token=os.getenv("HF_TOKEN") or None,
            langsmith_tracing=_as_bool(os.getenv("LANGSMITH_TRACING")),
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY") or None,
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "gridpulse-mvp"),
        )

