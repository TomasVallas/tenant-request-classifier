"""Request and response models shared by the API and the model layer."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

MAX_REQUEST_LENGTH = 2000
SUMMARY_MAX_LENGTH = 200

Category = Literal["vika", "laskutus", "muutto", "muu"]
Urgency = Literal["kiireellinen", "normaali"]


class ClassifyRequest(BaseModel):
    text: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_REQUEST_LENGTH),
    ]


class LLMOutput(BaseModel):
    """What the language model must return.

    Limits live in validators instead of JSON Schema keywords, because providers
    support different keywords in their structured output schemas.
    """

    category: Category
    urgency: Urgency
    summary: str = Field(description="Short summary in Finnish, max 200 characters.")
    reply_draft: str = Field(description="Polite reply draft in Finnish with no promises.")
    confidence: float = Field(description="Confidence between 0 and 1.")

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Summary must not be empty")
        if len(value) <= SUMMARY_MAX_LENGTH:
            return value
        return value[: SUMMARY_MAX_LENGTH - 1].rstrip() + "…"

    @field_validator("reply_draft")
    @classmethod
    def clean_reply_draft(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reply draft must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def check_confidence_range(cls, value: float) -> float:
        # Written this way so that NaN is rejected too.
        if not 0.0 <= value <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return value


class ClassificationResult(LLMOutput):
    """Model output after the rules gate has made the final decisions."""

    needs_human: bool
    rule_hits: list[str]
    provider: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: Literal["ok"]
    provider: str
