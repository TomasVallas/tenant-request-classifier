"""Classification pipeline: input -> model -> rules gate -> result."""

import asyncio
import logging
import time

from app.llm import RequestClassifier
from app.rules import apply_rules
from app.schemas import ClassificationResult

logger = logging.getLogger(__name__)


class ModelUnavailableError(Exception):
    """The model failed or did not answer in time."""


async def classify_request(
    text: str,
    model: RequestClassifier,
    provider: str,
    timeout_seconds: float,
) -> ClassificationResult:
    started = time.perf_counter()
    try:
        async with asyncio.timeout(timeout_seconds):
            output = await model.ainvoke(text)
    except TimeoutError as exc:
        logger.warning("model_timeout provider=%s", provider)
        raise ModelUnavailableError("Model call timed out") from exc
    except Exception as exc:
        # Log only the error type, because error messages can contain the request text.
        logger.warning("model_error provider=%s error_type=%s", provider, type(exc).__name__)
        raise ModelUnavailableError("Model call failed") from exc

    decision = apply_rules(text, output)
    latency_ms = round((time.perf_counter() - started) * 1000)

    logger.info(
        "classified category=%s urgency=%s needs_human=%s latency_ms=%d",
        output.category,
        decision.urgency,
        decision.needs_human,
        latency_ms,
    )

    return ClassificationResult(
        **{**output.model_dump(), "urgency": decision.urgency},
        needs_human=decision.needs_human,
        rule_hits=list(decision.rule_hits),
        provider=provider,
        latency_ms=latency_ms,
    )
