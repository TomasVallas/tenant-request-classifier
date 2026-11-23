import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FRONTEND_ORIGIN = "https://demo.example"


def make_settings(**overrides: object) -> Settings:
    """Build settings that ignore any local .env file and provider keys in the environment."""
    values: dict[str, object] = {
        "llm_provider": "fake",
        "llm_temperature": 0.0,
        "app_env": "production",
        "frontend_origin": FRONTEND_ORIGIN,
        "rate_limit_per_minute": 100,
        "llm_timeout_seconds": 1.0,
        "azure_openai_endpoint": None,
        "azure_openai_api_key": None,
        "azure_openai_deployment": None,
        "azure_openai_api_version": None,
        "openai_api_key": None,
        "openai_model": None,
        "anthropic_api_key": None,
        "anthropic_model": "claude-opus-5-5",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(settings=make_settings()))
