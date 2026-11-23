"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["fake", "azure_openai", "openai", "anthropic"]
AppEnv = Literal["development", "production"]

DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Provider = "fake"
    llm_timeout_seconds: float = Field(default=20.0, gt=0)
    # Defaults to production so that localhost origins are only allowed when opted in.
    app_env: AppEnv = "production"
    frontend_origin: str = "http://localhost:5173"
    rate_limit_per_minute: int = Field(default=20, gt=0)

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_origin.rstrip("/")]
        if self.app_env == "development":
            origins.extend(origin for origin in DEV_ORIGINS if origin not in origins)
        return origins
