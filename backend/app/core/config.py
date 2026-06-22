from functools import lru_cache
from typing import Self
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Website scrapper"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Option A: set DATABASE_URL directly (full connection string)
    # Option B: set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME below
    database_url: str | None = None
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "leadforge"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    scraper_headless: bool = True
    scraper_max_results: int = 120
    scraper_scroll_pause_ms: int = 1500
    scraper_scroll_stable_rounds: int = 5
    scraper_request_delay_ms: int = 500
    scraper_max_testimonials_per_business: int = 10
    scraper_testimonial_scroll_rounds: int = 4

    bulk_target_default: int = 10_000
    bulk_delay_between_searches_seconds: float = 3.0
    bulk_max_queries: int | None = None

    website_detection_timeout_seconds: int = 8
    website_detection_concurrency: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> str:
        if isinstance(value, list):
            return ",".join(value)
        return value

    @model_validator(mode="after")
    def resolve_database_url(self) -> Self:
        if self.database_url:
            return self

        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        object.__setattr__(
            self,
            "database_url",
            f"mysql+asyncmy://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}",
        )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
