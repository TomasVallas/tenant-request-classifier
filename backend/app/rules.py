"""Deterministic rules gate. It runs after the model and has the final say."""

import re
import unicodedata
from dataclasses import dataclass

from app.schemas import Category, LLMOutput, Urgency

LOW_CONFIDENCE_THRESHOLD = 0.6

RULE_LOW_CONFIDENCE = "low_confidence"
RULE_CATEGORY_OTHER = "category_muu"
RULE_URGENT_REVIEW = "urgent_requires_review"

_LOCKED_OUT_STEM = r"(?:lukittau[dt]|lukkiu[dt])"

# Patterns use word stems so that Finnish inflected forms match. A false alarm only costs
# a human review, while a missed emergency is worse, so the patterns lean towards matching.
EMERGENCY_PATTERNS: dict[str, re.Pattern[str]] = {
    "vesivuoto": re.compile(r"vesivuo[td]|\bvesi\s+vuota|\bvett[äa]\s+vuota|\bvuota\w*\s+vett"),
    "vesivahinko": re.compile(r"vesivahin[gk]"),
    "tulva": re.compile(r"tulv"),
    "tulipalo": re.compile(r"tulipalo"),
    # The lookahead excludes words such as "savuke" (cigarette).
    "savu": re.compile(r"\bsavu(?!k)"),
    "kaasu": re.compile(r"kaasu"),
    "sähköisku": re.compile(r"sähköisk"),
    # The lookahead excludes missing hot water ("ei lämmintä vettä"), which is not a heating loss.
    "ei lämpöä": re.compile(
        r"\bei(?:vät)?\s+(?:ole\s+|tule\s+)?läm[pm](?!\w*\s+vet)"
        r"|\blämmity\w*\s+(?:ei\s+toimi|(?:on\s+)?(?:poikki|rikki))"
    ),
    "ei sähköä": re.compile(
        r"\bei\s+(?:ole\s+|tule\s+)?sähköä\b"
        r"|\bsähköt\s+(?:(?:on|ovat)\s+)?(?:poikki|pois)\b"
        r"|\bsähköt\s+(?:ei|eivät)\s+toimi"
        r"|sähkökatk"
    ),
    "lukittautunut ulos": re.compile(
        rf"{_LOCKED_OUT_STEM}\w*\s+(?:\w+\s+){{0,2}}ulos\b"
        rf"|\bulos\s+(?:\w+\s+){{0,2}}{_LOCKED_OUT_STEM}"
        r"|\bavaim\w*\s+jäi\w*\s+sisä"
    ),
}


@dataclass(frozen=True)
class RuleDecision:
    urgency: Urgency
    needs_human: bool
    rule_hits: tuple[str, ...]


def normalize_text(text: str) -> str:
    """Normalize Unicode and case so that matching does not depend on how text was typed."""
    return unicodedata.normalize("NFC", text).casefold()


def find_emergency_keywords(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [
        f"emergency_keyword:{keyword}"
        for keyword, pattern in EMERGENCY_PATTERNS.items()
        if pattern.search(normalized)
    ]


def resolve_urgency(model_urgency: Urgency, emergency_hits: list[str]) -> Urgency:
    return "kiireellinen" if emergency_hits else model_urgency


def is_low_confidence(confidence: float) -> bool:
    return confidence < LOW_CONFIDENCE_THRESHOLD


def is_other_category(category: Category) -> bool:
    return category == "muu"


def is_urgent(urgency: Urgency) -> bool:
    return urgency == "kiireellinen"


def apply_rules(text: str, output: LLMOutput) -> RuleDecision:
    hits = find_emergency_keywords(text)
    urgency = resolve_urgency(output.urgency, hits)

    low_confidence = is_low_confidence(output.confidence)
    other_category = is_other_category(output.category)
    urgent = is_urgent(urgency)

    if low_confidence:
        hits.append(RULE_LOW_CONFIDENCE)
    if other_category:
        hits.append(RULE_CATEGORY_OTHER)
    if urgent:
        hits.append(RULE_URGENT_REVIEW)

    return RuleDecision(
        urgency=urgency,
        needs_human=low_confidence or other_category or urgent,
        rule_hits=tuple(hits),
    )
