"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["fake", "azure_openai", "openai", "anthropic"]
AppEnv = Literal["development", "production"]

DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


class Settings(BaseSettings):
    # Empty values in .env count as unset, so the copied .env.example works as it is.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    llm_provider: Provider = "fake"
    llm_timeout_seconds: float = Field(default=20.0, gt=0)
    # Used for OpenAI and Azure. The current Anthropic API rejects this parameter.
    llm_temperature: float | None = Field(default=0.0, ge=0, le=2)

    azure_openai_endpoint: str | None = None
    azure_openai_api_key: SecretStr | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str | None = None

    openai_api_key: SecretStr | None = None
    openai_model: str | None = None

    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5-5"

    # Defaults to production so that localhost origins are only allowed when opted in.
    app_env: AppEnv = "production"
    frontend_origin: str = "http://localhost:5173"
    rate_limit_per_minute: int = Field(default=20, gt=0)
    # Enable only behind a proxy that appends the client IP to X-Forwarded-For.
    trust_proxy_headers: bool = False

    @field_validator("llm_temperature", mode="before")
    @classmethod
    def parse_disabled_temperature(cls, value: object) -> object:
        """Allow LLM_TEMPERATURE=none for models that do not accept a temperature."""
        if isinstance(value, str) and value.strip().lower() == "none":
            return None
        return value

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.frontend_origin.rstrip("/")]
        if self.app_env == "development":
            origins.extend(origin for origin in DEV_ORIGINS if origin not in origins)
        return origins
