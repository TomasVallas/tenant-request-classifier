import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FRONTEND_ORIGIN = "https://demo.example"


def make_settings(**overrides: object) -> Settings:
    """Build settings that ignore any local .env file."""
    values: dict[str, object] = {
        "llm_provider": "fake",
        "app_env": "production",
        "frontend_origin": FRONTEND_ORIGIN,
        "rate_limit_per_minute": 100,
        "llm_timeout_seconds": 1.0,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(settings=make_settings()))
