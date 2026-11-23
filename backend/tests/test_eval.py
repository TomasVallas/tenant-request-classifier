import asyncio
from datetime import date
from pathlib import Path

import pytest
from conftest import make_settings

from app.llm import get_classifier
from app.schemas import MAX_REQUEST_LENGTH, LLMOutput
from eval import run_eval
from eval.run_eval import (
    CASE_TYPES,
    FAILED,
    CaseResult,
    EvalCase,
    load_cases,
    main,
    render_markdown,
    run_cases,
    summarize,
)


class FailingModel:
    async def ainvoke(self, text: str) -> LLMOutput:
        raise RuntimeError("Provider failed")


def make_case(
    case_id: str = "t1",
    category: str = "vika",
    urgency: str = "normaali",
    tags: tuple[str, ...] = ("basic",),
) -> EvalCase:
    return EvalCase(id=case_id, text="Teksti", category=category, urgency=urgency, tags=tags)


def make_result(
    case: EvalCase,
    category: str | None = None,
    urgency: str | None = None,
    needs_human: bool = False,
    latency_ms: int | None = 10,
) -> CaseResult:
    return CaseResult(
        case=case,
        category=category or case.category,
        urgency=urgency or case.urgency,
        needs_human=needs_human,
        latency_ms=latency_ms,
    )


def test_dataset_has_30_unique_valid_requests() -> None:
    cases = load_cases()
    assert len(cases) == 30
    assert len({case.id for case in cases}) == 30
    assert len({case.text for case in cases}) == 30
    assert all(0 < len(case.text) <= MAX_REQUEST_LENGTH for case in cases)


def test_dataset_covers_all_labels_and_case_types() -> None:
    cases = load_cases()
    assert {case.category for case in cases} == {"vika", "laskutus", "muutto", "muu"}
    assert {case.urgency for case in cases} == {"kiireellinen", "normaali"}
    assert {tag for case in cases for tag in case.tags} == set(CASE_TYPES)


def test_dataset_has_one_prompt_injection_on_a_real_emergency() -> None:
    injections = [case for case in load_cases() if "prompt_injection" in case.tags]
    assert len(injections) == 1
    assert "unohda" in injections[0].text.lower()
    assert injections[0].urgency == "kiireellinen"


def test_prompt_injection_does_not_change_pipeline_result() -> None:
    injection = next(case for case in load_cases() if "prompt_injection" in case.tags)
    results = asyncio.run(run_cases([injection], get_classifier(make_settings()), "fake", 1.0))
    assert results[0].correct
    assert results[0].needs_human is True


def test_summarize_calculates_metrics() -> None:
    results = [
        make_result(make_case("a")),
        make_result(make_case("b"), category="muu", needs_human=True, latency_ms=30),
        make_result(make_case("c", urgency="kiireellinen"), needs_human=True),
        make_result(make_case("d", urgency="kiireellinen"), urgency="normaali"),
    ]
    summary = summarize(results)

    assert summary.total == 4
    assert summary.category_accuracy == pytest.approx(0.75)
    assert summary.urgency_accuracy == pytest.approx(0.75)
    assert summary.urgent_recall == pytest.approx(0.5)
    assert summary.human_review_rate == pytest.approx(0.5)
    assert summary.mean_latency_ms == pytest.approx(15)
    assert summary.category_matrix["vika"]["vika"] == 3
    assert summary.category_matrix["vika"]["muu"] == 1
    assert summary.urgency_matrix["kiireellinen"]["normaali"] == 1
    assert summary.type_results["basic"] == (2, 4)
    assert [miss.case.id for miss in summary.misses] == ["b", "d"]


def test_failed_calls_count_as_wrong() -> None:
    case = make_case(urgency="kiireellinen")
    summary = summarize(
        [make_result(case, category=FAILED, urgency=FAILED, needs_human=True, latency_ms=None)]
    )
    assert summary.failed == 1
    assert summary.category_accuracy == 0
    assert summary.urgent_recall == 0
    assert summary.mean_latency_ms is None
    assert summary.category_matrix["vika"][FAILED] == 1


def test_summarize_rejects_empty_results() -> None:
    with pytest.raises(ValueError, match="empty"):
        summarize([])


def test_run_cases_records_model_failure() -> None:
    results = asyncio.run(run_cases([make_case()], FailingModel(), "stub", 1.0))
    assert results[0].failed
    assert results[0].needs_human is True


def test_render_markdown_contains_report_sections() -> None:
    summary = summarize([make_result(make_case("a")), make_result(make_case("b"), category="muu")])
    markdown = render_markdown(summary, "fake", "baseline", date(2026, 1, 2))

    assert "- **Provider:** `fake`" in markdown
    assert "- **Date:** 2026-01-02" in markdown
    assert "| Category accuracy | 50.0% |" in markdown
    assert "## Category confusion matrix" in markdown
    assert "| **vika** | 1 | 0 | 0 | 1 |" in markdown
    assert "| b | basic | vika / normaali | muu / normaali |" in markdown
    assert FAILED not in markdown


def test_render_markdown_shows_failed_column_only_when_needed() -> None:
    summary = summarize([make_result(make_case(), category=FAILED, urgency=FAILED)])
    assert "| vika | laskutus | muutto | muu | failed |" in render_markdown(
        summary, "stub", "model", date(2026, 1, 2)
    )


def test_main_writes_results_with_fake(tmp_path: Path) -> None:
    output = tmp_path / "results.md"
    assert main(["--provider", "fake", "--output", str(output)]) == 0
    content = output.read_text(encoding="utf-8")
    assert "keyword baseline (not a language model)" in content
    assert "30 fictional labelled requests" in content


def test_main_limit_writes_no_default_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_output = tmp_path / "results.md"
    monkeypatch.setattr(run_eval, "RESULTS_PATH", default_output)
    assert main(["--provider", "fake", "--limit", "3"]) == 0
    assert not default_output.exists()


def test_main_keeps_previous_results_when_all_calls_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "results.md"
    output.write_text("previous results", encoding="utf-8")
    monkeypatch.setattr(run_eval, "get_classifier", lambda settings: FailingModel())

    assert main(["--provider", "fake", "--output", str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "previous results"


def test_main_reports_missing_provider_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(settings: object) -> None:
        raise ValueError("LLM_PROVIDER=openai requires: OPENAI_API_KEY")

    monkeypatch.setattr(run_eval, "get_classifier", fail)
    assert main(["--provider", "openai"]) == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().err
