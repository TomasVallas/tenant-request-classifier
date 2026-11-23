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
    """What the language model must return."""

    category: Category
    urgency: Urgency
    summary: str = Field(min_length=1, description="Short summary in Finnish, max 200 characters.")
    reply_draft: str = Field(
        min_length=1,
        description="Polite reply draft in Finnish with no promises.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0 and 1.")

    @field_validator("summary")
    @classmethod
    def limit_summary_length(cls, value: str) -> str:
        value = value.strip()
        if len(value) <= SUMMARY_MAX_LENGTH:
            return value
        return value[: SUMMARY_MAX_LENGTH - 1].rstrip() + "…"


class ClassificationResult(LLMOutput):
    """Model output after the rules gate has made the final decisions."""

    needs_human: bool
    rule_hits: list[str]
    provider: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: Literal["ok"]
    provider: str
