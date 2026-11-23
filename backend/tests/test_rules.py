import unicodedata

import pytest

from app.rules import (
    RULE_CATEGORY_OTHER,
    RULE_LOW_CONFIDENCE,
    RULE_URGENT_REVIEW,
    apply_rules,
    find_emergency_keywords,
    is_low_confidence,
    is_other_category,
    is_urgent,
    resolve_urgency,
)
from app.schemas import LLMOutput


def make_output(**overrides: object) -> LLMOutput:
    values: dict[str, object] = {
        "category": "vika",
        "urgency": "normaali",
        "summary": "Tiivistelmä",
        "reply_draft": "Kiitos viestistäsi.",
        "confidence": 0.9,
    }
    values.update(overrides)
    return LLMOutput(**values)


@pytest.mark.parametrize(
    ("text", "keyword"),
    [
        ("Keittiössä on vesivuoto", "vesivuoto"),
        ("Ilmoitan vesivuodosta", "vesivuoto"),
        ("Vesi vuotaa lattialle", "vesivuoto"),
        ("Katosta vuotaa vettä", "vesivuoto"),
        ("Epäilen vesivahinkoa", "vesivahinko"),
        ("Kylpyhuoneessa on vesivahingon jälkiä", "vesivahinko"),
        ("Kellarissa on tulva", "tulva"),
        ("Pesuhuone tulvii", "tulva"),
        ("Naapurissa on tulipalo", "tulipalo"),
        ("Pelkään tulipaloa", "tulipalo"),
        ("Rappukäytävässä on savua", "savu"),
        ("Haistan savun", "savu"),
        ("Asunnossa haisee kaasu", "kaasu"),
        ("Tuntuu kaasun haju", "kaasu"),
        ("Sain sähköiskun pistorasiasta", "sähköisku"),
        ("Asunnossa ei ole lämpöä", "ei lämpöä"),
        ("Patterit eivät lämpene", "ei lämpöä"),
        ("Lämmitys ei toimi", "ei lämpöä"),
        ("Asunnossa ei ole sähköä", "ei sähköä"),
        ("Sähköt ovat poikki", "ei sähköä"),
        ("Talossa on sähkökatko", "ei sähköä"),
        ("Olen lukittautunut ulos asunnosta", "lukittautunut ulos"),
        ("Lukittauduin ulos", "lukittautunut ulos"),
        ("Avaimet jäivät sisälle", "lukittautunut ulos"),
        ("Lattialla on vettä", "vesivuoto"),
        ("Vettä valuu katosta", "vesivuoto"),
        ("Seinästä tulee vettä", "vesivuoto"),
        ("vetta tulee lattialle", "vesivuoto"),
        ("Asunnossa ei ole ollut lämpöä kahteen päivään", "ei lämpöä"),
        ("Patterit eivät enää lämpene", "ei lämpöä"),
        ("Lämmitys ei ole toiminut eilisen jälkeen", "ei lämpöä"),
        ("Patterit ovat kylmät", "ei lämpöä"),
        ("asunnossa ei ole lampoa", "ei lämpöä"),
        ("Sähköt menivät koko asunnosta", "ei sähköä"),
        ("Sähköt katkesivat äsken", "ei sähköä"),
        ("Sähköt eivät enää toimi", "ei sähköä"),
        ("sahkot on poikki", "ei sähköä"),
        ("Jäin ulos asunnosta", "lukittautunut ulos"),
        ("En pääse sisään asuntoon", "lukittautunut ulos"),
    ],
)
def test_emergency_keywords_match_inflected_forms(text: str, keyword: str) -> None:
    assert f"emergency_keyword:{keyword}" in find_emergency_keywords(text)


@pytest.mark.parametrize(
    "text",
    [
        "Keittiön hana vuotaa, asunto B12",
        "Sähkölasku on liian suuri",
        "Asunnossa ei tule lämmintä vettä",
        "Rapussa on savukkeiden tumppeja",
        "Haluan irtisanoa vuokrasopimuksen",
        "Vuokra on maksettu kaksi vuotta sitten",
        "Eteisessä ei lamppu toimi",
        "Vaihdoin lampun, mutta valo ei syty",
        "Lämmitys on toiminut hyvin",
        "Sähköt toimivat taas normaalisti",
        "Astianpesukoneen pohjalle jää vettä",
        "Katto on kunnossa, vesi toimii",
        "Lattia on naarmuuntunut",
        "Haluan tietää sähkösopimuksesta",
        "En pääse sisään verkkopalveluun",
    ],
)
def test_ordinary_requests_are_not_emergencies(text: str) -> None:
    assert find_emergency_keywords(text) == []


def test_emergency_match_ignores_case() -> None:
    assert find_emergency_keywords("VESIVUOTO KEITTIÖSSÄ") == ["emergency_keyword:vesivuoto"]


def test_emergency_match_handles_decomposed_unicode() -> None:
    decomposed = unicodedata.normalize("NFD", "Asunnossa ei ole lämpöä")
    assert find_emergency_keywords(decomposed) == ["emergency_keyword:ei lämpöä"]


def test_resolve_urgency_overrides_model_on_emergency() -> None:
    assert resolve_urgency("normaali", ["emergency_keyword:tulva"]) == "kiireellinen"


@pytest.mark.parametrize("urgency", ["normaali", "kiireellinen"])
def test_resolve_urgency_keeps_model_value_without_emergency(urgency: str) -> None:
    assert resolve_urgency(urgency, []) == urgency


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [(0.0, True), (0.59, True), (0.6, False), (1.0, False)],
)
def test_is_low_confidence_threshold(confidence: float, expected: bool) -> None:
    assert is_low_confidence(confidence) is expected


@pytest.mark.parametrize(
    ("category", "expected"),
    [("muu", True), ("vika", False), ("laskutus", False), ("muutto", False)],
)
def test_is_other_category(category: str, expected: bool) -> None:
    assert is_other_category(category) is expected


@pytest.mark.parametrize(("urgency", "expected"), [("kiireellinen", True), ("normaali", False)])
def test_is_urgent(urgency: str, expected: bool) -> None:
    assert is_urgent(urgency) is expected


def test_apply_rules_clear_request_needs_no_human() -> None:
    decision = apply_rules("Keittiön hana vuotaa", make_output())
    assert decision.urgency == "normaali"
    assert decision.needs_human is False
    assert decision.rule_hits == ()


def test_apply_rules_emergency_beats_model_and_requires_human() -> None:
    decision = apply_rules("Kellarissa on vesivuoto", make_output(urgency="normaali"))
    assert decision.urgency == "kiireellinen"
    assert decision.needs_human is True
    assert decision.rule_hits == ("emergency_keyword:vesivuoto", RULE_URGENT_REVIEW)


def test_apply_rules_low_confidence_requires_human() -> None:
    decision = apply_rules("Hana", make_output(confidence=0.59))
    assert decision.needs_human is True
    assert decision.rule_hits == (RULE_LOW_CONFIDENCE,)


def test_apply_rules_other_category_requires_human() -> None:
    decision = apply_rules("Kysymys pihasta", make_output(category="muu"))
    assert decision.needs_human is True
    assert decision.rule_hits == (RULE_CATEGORY_OTHER,)


def test_apply_rules_model_urgency_requires_human() -> None:
    decision = apply_rules("Tilanne on vaarallinen", make_output(urgency="kiireellinen"))
    assert decision.urgency == "kiireellinen"
    assert decision.needs_human is True
    assert decision.rule_hits == (RULE_URGENT_REVIEW,)
