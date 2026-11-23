"""Model providers. Phase 1 contains the deterministic fake provider."""

import re
from typing import Protocol

from app.config import Settings
from app.rules import normalize_text
from app.schemas import Category, LLMOutput


class RequestClassifier(Protocol):
    async def ainvoke(self, text: str) -> LLMOutput: ...


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern) for pattern in patterns)


# Dictionary order is the tie-break priority when two categories score equally.
_CATEGORY_PATTERNS: dict[Category, tuple[re.Pattern[str], ...]] = {
    "vika": _compile(
        r"vuot[ao]",
        r"vuodo",
        r"\brikki\b",
        r"rikkoutu",
        r"\bhajo",
        r"tukko",
        r"tukkeutu",
        r"tukos",
        r"\bei\s+toimi",
        r"\beivät\s+toimi",
        r"hana",
        r"\bwc\b",
        r"vessa",
        r"patteri",
        r"lämmit",
        r"ilmanvaihto",
        r"hissi",
        r"jääkaap",
        r"\bliesi",
        r"\blieden",
        r"\buuni",
        r"viemär",
        r"\bhome",
        r"kosteu",
        r"vaurio",
        r"vahin[gk]",
        r"tulv",
        r"\bsavu(?!k)",
        r"kaasu",
        r"sähköisk",
        r"sähkökatk",
        r"\bsähköt\b",
        r"\bvalot?\b",
        r"\blukko",
        r"\blukon",
        r"lukittau",
        r"ikkuna",
    ),
    "laskutus": _compile(
        r"lasku",
        r"\bvuokra(?!lai|sopimu|nant|talo|-|isän)",
        r"maksu",
        r"\bmaks[aeo]",
        r"vakuu",
        r"eräpäiv",
        r"perint",
        r"karhu",
        r"viitenumer",
        r"tilinumer",
        r"hyvity",
    ),
    "muutto": _compile(
        r"muutt[oa]",
        r"muuton",
        r"muutossa",
        r"\bmuutan\b",
        r"\bmuutamme\b",
        r"\bmuutin\b",
        r"\bmuutimme\b",
        r"irtisan",
        r"avai[mn]",
        r"vuokrasopimu",
        r"\bsopimu",
    ),
}

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


class FakeClassifier:
    """Keyword classifier for tests and for running the demo without an API key."""

    async def ainvoke(self, text: str) -> LLMOutput:
        return classify_with_keywords(text)


def get_classifier(settings: Settings) -> RequestClassifier:
    if settings.llm_provider == "fake":
        return FakeClassifier()
    raise ValueError(
        f"LLM provider '{settings.llm_provider}' is not implemented yet. Use LLM_PROVIDER=fake."
    )
