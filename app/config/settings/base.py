"""
settings/config.py — Application configuration.

All environment-driven settings live here. Read from .env via pydantic-settings.
This is the Django settings.py equivalent for FastAPI.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/network_route_optimizer"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    log_level: str = "info"

    # ── Pathfinding ───────────────────────────────────────────────────────────
    default_algorithm: str = "dijkstra"

    # ── Route Cache ───────────────────────────────────────────────────────────
    route_cache_enabled: bool = True
    route_cache_ttl_seconds: int = 60
    route_cache_max_size: int = 256


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — called once, reused everywhere."""
    return Settings()
