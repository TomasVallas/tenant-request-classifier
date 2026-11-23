import asyncio

import pytest
from conftest import FRONTEND_ORIGIN, make_settings
from fastapi.testclient import TestClient

from app.main import (
    ERROR_EMPTY_TEXT,
    ERROR_INVALID_REQUEST,
    ERROR_MODEL_UNAVAILABLE,
    ERROR_TEXT_TOO_LONG,
    create_app,
)
from app.rate_limit import RATE_LIMIT_MESSAGE
from app.schemas import MAX_REQUEST_LENGTH, LLMOutput


class FailingModel:
    async def ainvoke(self, text: str) -> LLMOutput:
        raise RuntimeError("Provider failed")


class SlowModel:
    async def ainvoke(self, text: str) -> LLMOutput:
        await asyncio.sleep(5)
        raise AssertionError("The timeout should cancel this call")


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "provider": "fake"}


def test_classify_returns_full_result(client: TestClient) -> None:
    response = client.post("/api/classify", json={"text": "Keittiön hana vuotaa, asunto B12"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "vika"
    assert body["urgency"] == "normaali"
    assert body["summary"].startswith("Vikailmoitus")
    assert body["reply_draft"]
    assert 0 <= body["confidence"] <= 1
    assert body["needs_human"] is False
    assert body["rule_hits"] == []
    assert body["provider"] == "fake"
    assert body["latency_ms"] >= 0


def test_classify_emergency_is_urgent_and_needs_human(client: TestClient) -> None:
    response = client.post("/api/classify", json={"text": "Kylpyhuoneessa on vesivuoto"})
    body = response.json()
    assert body["urgency"] == "kiireellinen"
    assert body["needs_human"] is True
    assert "emergency_keyword:vesivuoto" in body["rule_hits"]


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_classify_rejects_empty_text(client: TestClient, text: str) -> None:
    response = client.post("/api/classify", json={"text": text})
    assert response.status_code == 422
    assert response.json() == {"detail": ERROR_EMPTY_TEXT}


def test_classify_accepts_maximum_length(client: TestClient) -> None:
    response = client.post("/api/classify", json={"text": "a" * MAX_REQUEST_LENGTH})
    assert response.status_code == 200


def test_classify_rejects_too_long_text(client: TestClient) -> None:
    too_long = "a" * (MAX_REQUEST_LENGTH + 1)
    response = client.post("/api/classify", json={"text": too_long})
    assert response.status_code == 422
    assert response.json() == {"detail": ERROR_TEXT_TOO_LONG}
    assert too_long not in response.text


@pytest.mark.parametrize("payload", [{}, {"text": 123}, {"wrong": "kenttä"}])
def test_classify_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    response = client.post("/api/classify", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": ERROR_INVALID_REQUEST}


@pytest.mark.parametrize("model", [FailingModel(), SlowModel()])
def test_model_failure_and_timeout_return_503(model: object) -> None:
    settings = make_settings(llm_timeout_seconds=0.01)
    client = TestClient(create_app(settings=settings, classifier=model))
    response = client.post("/api/classify", json={"text": "Hana vuotaa"})
    assert response.status_code == 503
    assert response.json() == {"detail": ERROR_MODEL_UNAVAILABLE}


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:5173"])
def test_cors_rejects_other_origins_in_production(client: TestClient, origin: str) -> None:
    response = client.get("/api/health", headers={"Origin": origin})
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_localhost_in_development() -> None:
    client = TestClient(create_app(settings=make_settings(app_env="development")))
    origin = "http://localhost:5173"
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin


def test_rate_limit_returns_429_with_cors_headers() -> None:
    client = TestClient(create_app(settings=make_settings(rate_limit_per_minute=2)))
    headers = {"Origin": FRONTEND_ORIGIN}
    for _ in range(2):
        response = client.post("/api/classify", json={"text": "Hana vuotaa"}, headers=headers)
        assert response.status_code == 200

    response = client.post("/api/classify", json={"text": "Hana vuotaa"}, headers=headers)
    assert response.status_code == 429
    assert response.json() == {"detail": RATE_LIMIT_MESSAGE}
    assert response.headers["retry-after"] == "60"
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_spoofed_forwarded_header_does_not_bypass_rate_limit() -> None:
    settings = make_settings(rate_limit_per_minute=1, trust_proxy_headers=True)
    client = TestClient(create_app(settings=settings))
    body = {"text": "Hana vuotaa"}

    first = client.post("/api/classify", json=body, headers={"X-Forwarded-For": "1.1.1.1, 9.9.9.9"})
    second = client.post(
        "/api/classify", json=body, headers={"X-Forwarded-For": "2.2.2.2, 9.9.9.9"}
    )
    other_client = client.post(
        "/api/classify", json=body, headers={"X-Forwarded-For": "2.2.2.2, 8.8.8.8"}
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert other_client.status_code == 200


def test_rate_limit_does_not_apply_to_health() -> None:
    client = TestClient(create_app(settings=make_settings(rate_limit_per_minute=1)))
    for _ in range(3):
        assert client.get("/api/health").status_code == 200
