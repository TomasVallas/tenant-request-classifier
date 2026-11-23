"""FastAPI application, CORS and routes."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.classifier import ModelUnavailableError, classify_request
from app.config import Settings
from app.llm import RequestClassifier, get_classifier
from app.rate_limit import RateLimitMiddleware, SlidingWindowRateLimiter
from app.schemas import (
    MAX_REQUEST_LENGTH,
    ClassificationResult,
    ClassifyRequest,
    HealthResponse,
)

CLASSIFY_PATH = "/api/classify"

ERROR_EMPTY_TEXT = "Palvelupyyntö ei voi olla tyhjä."
ERROR_TEXT_TOO_LONG = f"Palvelupyyntö saa olla enintään {MAX_REQUEST_LENGTH:,} merkkiä.".replace(
    ",", " "
)
ERROR_INVALID_REQUEST = "Pyynnön muoto on virheellinen. Anna palvelupyyntö text-kentässä."
ERROR_MODEL_UNAVAILABLE = (
    "Kielimalli ei ole juuri nyt käytettävissä. Yritä hetken kuluttua uudelleen."
)


def _validation_message(exc: RequestValidationError) -> str:
    for error in exc.errors():
        if error["loc"][-1] != "text":
            continue
        if error["type"] == "string_too_short":
            return ERROR_EMPTY_TEXT
        if error["type"] == "string_too_long":
            return ERROR_TEXT_TOO_LONG
    return ERROR_INVALID_REQUEST


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    # A custom body also keeps the default handler from echoing the request text back.
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(status_code=422, content={"detail": _validation_message(exc)})


def create_app(
    settings: Settings | None = None,
    classifier: RequestClassifier | None = None,
) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    active_settings = settings or Settings()
    active_classifier = classifier or get_classifier(active_settings)
    limiter = SlidingWindowRateLimiter(limit=active_settings.rate_limit_per_minute)

    app = FastAPI(title="Tenant Request Classifier", version="0.1.0")
    app.add_exception_handler(RequestValidationError, _handle_validation_error)

    # The middleware added last runs first. CORS must wrap the rate limit so that
    # browsers can also read the 429 response.
    app.add_middleware(
        RateLimitMiddleware,
        limiter=limiter,
        path=CLASSIFY_PATH,
        trust_proxy=active_settings.trust_proxy_headers,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", provider=active_settings.llm_provider)

    @app.post(CLASSIFY_PATH, response_model=ClassificationResult)
    async def classify(request: ClassifyRequest) -> ClassificationResult:
        try:
            return await classify_request(
                text=request.text,
                model=active_classifier,
                provider=active_settings.llm_provider,
                timeout_seconds=active_settings.llm_timeout_seconds,
            )
        except ModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=ERROR_MODEL_UNAVAILABLE) from exc

    return app


app = create_app()
