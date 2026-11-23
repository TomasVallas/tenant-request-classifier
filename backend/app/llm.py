"""Model providers and the structured classification call."""

import re
from typing import Any, Protocol

from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable, RunnableLambda

from app.config import Settings
from app.prompts import build_messages, unwrap_request
from app.rules import normalize_text
from app.schemas import Category, LLMOutput

MAX_OUTPUT_TOKENS = 2000
MAX_PROVIDER_RETRIES = 1


class ChatModel(Protocol):
    def with_structured_output(
        self, schema: type[LLMOutput], **kwargs: Any
    ) -> Runnable[Any, Any]: ...


class RequestClassifier(Protocol):
    async def ainvoke(self, text: str) -> LLMOutput: ...


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern) for pattern in patterns)


# Dictionary order is the tie-break priority when two categories score equally.
# fmt: off
_CATEGORY_PATTERNS: dict[Category, tuple[re.Pattern[str], ...]] = {
    "vika": _compile(
        r"vuot[ao]", r"vuodo", r"\brikki\b", r"rikkoutu", r"\bhajo", r"tukko", r"tukkeutu",
        r"tukos", r"\bei\s+toimi", r"\beivät\s+toimi", r"hana", r"\bwc\b", r"vessa", r"patteri",
        r"lämmit", r"ilmanvaihto", r"hissi", r"jääkaap", r"\bliesi", r"\blieden", r"\buuni",
        r"viemär", r"\bhome", r"kosteu", r"vaurio", r"vahin[gk]", r"tulv", r"\bsavu(?!k)",
        r"kaasu", r"sähköisk", r"sähkökatk", r"\bsähköt\b", r"\bvalot?\b", r"\blukko", r"\blukon",
        r"lukittau", r"ikkuna",
    ),
    "laskutus": _compile(
        r"lasku", r"\bvuokra(?!lai|sopimu|nant|talo|-|isän)", r"maksu", r"\bmaks[aeo]", r"vakuu",
        r"eräpäiv", r"perint", r"karhu", r"viitenumer", r"tilinumer", r"hyvity",
    ),
    "muutto": _compile(
        r"muutt[oa]", r"muuton", r"muutossa", r"\bmuutan\b", r"\bmuutamme\b", r"\bmuutin\b",
        r"\bmuutimme\b", r"irtisan", r"avai[mn]", r"vuokrasopimu", r"\bsopimu",
    ),
}
# fmt: on

_SUMMARY_PREFIXES: dict[Category, str] = {
    "vika": "Vikailmoitus",
    "laskutus": "Laskutusasia",
    "muutto": "Muuttoasia",
    "muu": "Muu asia",
}

_REPLY_TEMPLATES: dict[Category, str] = {
    "vika": (
        "Kiitos ilmoituksestasi. Olemme vastaanottaneet vikailmoituksen, ja asiakaspalvelumme "
        "käsittelee sen. Kerrothan tarvittaessa tarkemman sijainnin asunnossa ja sen, milloin "
        "vika alkoi."
    ),
    "laskutus": (
        "Kiitos viestistäsi. Asiakaspalvelumme tarkistaa laskutusasiasi. Lähetäthän tarvittaessa "
        "laskun numeron tai muut asiaan liittyvät tiedot."
    ),
    "muutto": (
        "Kiitos viestistäsi. Asiakaspalvelumme käsittelee muuttoon liittyvän asiasi. Kerrothan "
        "tarvittaessa asunnon numeron ja suunnitellun muuttopäivän."
    ),
    "muu": (
        "Kiitos viestistäsi. Asiakaspalvelumme tutustuu asiaan. Voisitko vielä kertoa tarkemmin, "
        "mistä asiassa on kyse?"
    ),
}

_CONFIDENCE_NO_MATCH = 0.4
_CONFIDENCE_MIXED = 0.5
_CONFIDENCE_SINGLE_HIT = 0.75
_CONFIDENCE_MULTIPLE_HITS = 0.9


def _score_categories(normalized_text: str) -> dict[Category, int]:
    return {
        category: sum(1 for pattern in patterns if pattern.search(normalized_text))
        for category, patterns in _CATEGORY_PATTERNS.items()
    }


def classify_with_keywords(text: str) -> LLMOutput:
    """Classify by keywords. Urgency stays normal so that the rules gate alone escalates it."""
    scores = _score_categories(normalize_text(text))
    matched = {category: score for category, score in scores.items() if score > 0}

    category: Category
    if not matched:
        category = "muu"
        confidence = _CONFIDENCE_NO_MATCH
    else:
        category = max(matched, key=lambda name: matched[name])
        if len(matched) > 1:
            confidence = _CONFIDENCE_MIXED
        elif matched[category] > 1:
            confidence = _CONFIDENCE_MULTIPLE_HITS
        else:
            confidence = _CONFIDENCE_SINGLE_HIT

    return LLMOutput(
        category=category,
        urgency="normaali",
        summary=f"{_SUMMARY_PREFIXES[category]}: {' '.join(text.split())}",
        reply_draft=_REPLY_TEMPLATES[category],
        confidence=confidence,
    )


def _classify_messages(messages: list[BaseMessage]) -> LLMOutput:
    return classify_with_keywords(unwrap_request(str(messages[-1].content)))


class FakeChatModel:
    """Keyword classifier with the chat model interface. Needs no API key or network."""

    def with_structured_output(self, schema: type[LLMOutput], **kwargs: Any) -> Runnable[Any, Any]:
        return RunnableLambda(_classify_messages)


class StructuredClassifier:
    """Sends a request to a chat model and returns validated structured output."""

    def __init__(self, model: ChatModel) -> None:
        # JSON schema output works on all providers. Anthropic's default, forced tool
        # calling, is rejected by current Claude models.
        self._structured_model = model.with_structured_output(LLMOutput, method="json_schema")

    async def ainvoke(self, text: str) -> LLMOutput:
        output = await self._structured_model.ainvoke(build_messages(text))
        if not isinstance(output, LLMOutput):
            raise ValueError("Model did not return a valid structured response")
        return output


def _require_settings(settings: Settings, *names: str) -> None:
    missing = [name.upper() for name in names if getattr(settings, name) is None]
    if missing:
        raise ValueError(f"LLM_PROVIDER={settings.llm_provider} requires: {', '.join(missing)}")


def get_chat_model(settings: Settings) -> ChatModel:
    """Build the chat model. Provider packages are imported only when they are selected."""
    provider = settings.llm_provider
    if provider == "fake":
        return FakeChatModel()

    common: dict[str, Any] = {
        "timeout": settings.llm_timeout_seconds,
        "max_retries": MAX_PROVIDER_RETRIES,
        "max_tokens": MAX_OUTPUT_TOKENS,
    }

    if provider == "anthropic":
        _require_settings(settings, "anthropic_api_key")
        from langchain_anthropic import ChatAnthropic

        # The current API rejects temperature, so effort is the control here.
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            output_config={"effort": "low"},
            **common,
        )

    if settings.llm_temperature is not None:
        common["temperature"] = settings.llm_temperature

    if provider == "azure_openai":
        _require_settings(
            settings,
            "azure_openai_endpoint",
            "azure_openai_api_key",
            "azure_openai_deployment",
            "azure_openai_api_version",
        )
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            **common,
        )

    _require_settings(settings, "openai_api_key", "openai_model")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, **common)


def get_classifier(settings: Settings) -> RequestClassifier:
    return StructuredClassifier(get_chat_model(settings))
