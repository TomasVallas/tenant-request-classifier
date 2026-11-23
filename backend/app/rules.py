"""Deterministic rules gate. It runs after the model and has the final say."""

import re
import unicodedata
from dataclasses import dataclass

from app.schemas import Category, LLMOutput, Urgency

LOW_CONFIDENCE_THRESHOLD = 0.6

RULE_LOW_CONFIDENCE = "low_confidence"
RULE_CATEGORY_OTHER = "category_muu"
RULE_URGENT_REVIEW = "urgent_requires_review"

_FINNISH_LETTER_FOLD = str.maketrans({"ä": "a", "ö": "o", "å": "a"})

_WATER = r"ve(?:si|tta)\b"
_SURFACE = r"\b(?:lattia|katto|katos(?:ta|sa)|seina)\w*"
# Matches lämpö, lämpene and lämmin, but not lamppu (a lamp) after folding.
_HEAT_STEM = r"(?:lamp[oe]|lamm[io])"
_LOCKED_OUT_STEM = r"(?:lukittau[dt]|lukkiu[dt])"
# Words that may stand between a negation and the missing thing: "ei ole enää lämpöä".
_NEGATION_FILLER = r"(?:ole|ollut|oo|tule|tullut|enaa|yhtaan|lainkaan|ollenkaan|mitaan|juuri)"

# Patterns run on folded text (ä -> a, ö -> o), so they also match text typed without
# Finnish letters. A false alarm only costs a human review, while a missed emergency is
# worse, so the patterns lean towards matching. Punctuation ends a match on purpose.
EMERGENCY_PATTERNS: dict[str, re.Pattern[str]] = {
    "vesivuoto": re.compile(
        r"vesivuo[td]|\bvesi\s+vuota|\bvetta\s+vuota|\bvuota\w*\s+vett"
        rf"|\b{_WATER}(?:\s+\w+){{0,3}}?\s+valu"
        rf"|\bvalu\w*\s+(?:\w+\s+){{0,2}}{_WATER}"
        rf"|{_SURFACE}\s+(?:\w+\s+){{0,2}}{_WATER}"
        rf"|\b{_WATER}\s+(?:\w+\s+){{0,2}}{_SURFACE}"
    ),
    "vesivahinko": re.compile(r"vesivahin[gk]"),
    "tulva": re.compile(r"tulv"),
    "tulipalo": re.compile(r"tulipalo"),
    # The lookahead excludes words such as "savuke" (cigarette).
    "savu": re.compile(r"\bsavu(?!k)"),
    "kaasu": re.compile(r"kaasu"),
    "sähköisku": re.compile(r"sahkoisk"),
    # The lookahead excludes missing hot water ("ei lämmintä vettä"), which is not a heating loss.
    "ei lämpöä": re.compile(
        rf"\bei(?:vat)?\s+(?:{_NEGATION_FILLER}\s+){{0,3}}{_HEAT_STEM}(?!\w*\s+vet)"
        r"|\blammity\w*\s+(?:ei|eivat)\s+(?:(?:ole|ollut|enaa)\s+){0,2}toimi"
        r"|\blammity\w*\s+(?:(?:on|meni|mennyt|aivan|ihan)\s+){0,2}(?:poikki|rikki)"
        r"|\bpatteri\w*\s+(?:(?:on|ovat|aivan|ihan|edelleen|taysin)\s+){0,2}kylm"
    ),
    "ei sähköä": re.compile(
        rf"\bei\s+(?:{_NEGATION_FILLER}\s+){{0,3}}sahkoa\b"
        r"|\bsahkot\s+(?:(?:on|ovat|juuri|taas|nyt|kokonaan)\s+){0,2}"
        r"(?:poikki|pois|meni|mennyt|mennee|katke|lopp|havi)"
        r"|\bsahkot\s+(?:ei|eivat)\s+(?:(?:enaa|ole|ollut)\s+){0,2}toimi"
        r"|sahkokatk"
    ),
    "lukittautunut ulos": re.compile(
        rf"{_LOCKED_OUT_STEM}\w*\s+(?:\w+\s+){{0,2}}ulos\b"
        rf"|\bulos\s+(?:\w+\s+){{0,2}}{_LOCKED_OUT_STEM}"
        r"|\bavaim\w*\s+jai\w*\s+sisa"
        r"|\bjain\s+ulos\b"
        r"|\ben\s+paase\s+(?:sisaan\s+)?(?:asuntoon|kotiin)"
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


def fold_finnish_letters(text: str) -> str:
    """Normalize text and replace ä, ö and å so that "lampoa" matches "lämpöä"."""
    return normalize_text(text).translate(_FINNISH_LETTER_FOLD)


def find_emergency_keywords(text: str) -> list[str]:
    folded = fold_finnish_letters(text)
    return [
        f"emergency_keyword:{keyword}"
        for keyword, pattern in EMERGENCY_PATTERNS.items()
        if pattern.search(folded)
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
