import asyncio
import logging

import pytest

from app.classifier import ModelUnavailableError, classify_request
from app.schemas import LLMOutput

SECRET_TEXT = "Salainen palvelupyyntö: Matti Meikäläinen, asunto Z99, vesivuoto"


class StubModel:
    def __init__(self, urgency: str = "normaali") -> None:
        self._urgency = urgency

    async def ainvoke(self, text: str) -> LLMOutput:
        return LLMOutput(
            category="vika",
            urgency=self._urgency,
            summary="Vesivuoto asunnossa",
            reply_draft="Kiitos ilmoituksestasi.",
            confidence=0.95,
        )


class SlowModel:
    async def ainvoke(self, text: str) -> LLMOutput:
        await asyncio.sleep(5)
        raise AssertionError("The timeout should cancel this call")


class FailingModel:
    async def ainvoke(self, text: str) -> LLMOutput:
        raise RuntimeError(f"Provider failed for: {text}")


def run(text: str, model: object, timeout_seconds: float = 1.0):
    return asyncio.run(
        classify_request(
            text=text,
            model=model,
            provider="stub",
            timeout_seconds=timeout_seconds,
        )
    )


def test_emergency_keyword_overrides_model_urgency() -> None:
    result = run("Keittiössä on vesivuoto", StubModel(urgency="normaali"))
    assert result.urgency == "kiireellinen"
    assert result.needs_human is True
    assert "emergency_keyword:vesivuoto" in result.rule_hits


def test_result_contains_pipeline_metadata() -> None:
    result = run("Hana tippuu", StubModel())
    assert result.provider == "stub"
    assert result.latency_ms >= 0
    assert result.needs_human is False
    assert result.rule_hits == []


def test_timeout_raises_model_unavailable() -> None:
    with pytest.raises(ModelUnavailableError):
        run("Hana tippuu", SlowModel(), timeout_seconds=0.01)


def test_model_failure_raises_model_unavailable() -> None:
    with pytest.raises(ModelUnavailableError):
        run("Hana tippuu", FailingModel())


def test_success_log_excludes_request_text(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.classifier"):
        run(SECRET_TEXT, StubModel())
    assert "category=vika" in caplog.text
    assert "urgency=kiireellinen" in caplog.text
    assert "latency_ms=" in caplog.text
    assert "Meikäläinen" not in caplog.text


def test_failure_log_excludes_request_text(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.classifier"):
        with pytest.raises(ModelUnavailableError):
            run(SECRET_TEXT, FailingModel())
    assert "error_type=RuntimeError" in caplog.text
    assert "Meikäläinen" not in caplog.text
