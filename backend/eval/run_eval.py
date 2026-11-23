"""Evaluate the classification pipeline against the labelled fictional dataset.

Run from the backend folder:

    python -m eval.run_eval                                # uses LLM_PROVIDER
    python -m eval.run_eval --provider anthropic --limit 3 # small trial, writes no file
    python -m eval.run_eval --provider anthropic           # full run, updates results.md
"""

import argparse
import asyncio
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import get_args

from pydantic import BaseModel, ConfigDict

from app.classifier import ModelUnavailableError, classify_request
from app.config import Provider, Settings
from app.llm import RequestClassifier, get_classifier
from app.schemas import Category, Urgency

DATASET_PATH = Path(__file__).with_name("requests.jsonl")
RESULTS_PATH = Path(__file__).with_name("results.md")

CATEGORIES: tuple[str, ...] = get_args(Category)
URGENCIES: tuple[str, ...] = get_args(Urgency)
CASE_TYPES = ("basic", "ambiguous", "typo", "multi_issue", "prompt_injection")
INJECTION_TAG = "prompt_injection"
FAILED = "failed"

Matrix = dict[str, dict[str, int]]


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str
    category: Category
    urgency: Urgency
    tags: tuple[str, ...]


@dataclass(frozen=True)
class CaseResult:
    case: EvalCase
    category: str
    urgency: str
    needs_human: bool
    latency_ms: int | None

    @property
    def failed(self) -> bool:
        return self.category == FAILED

    @property
    def category_correct(self) -> bool:
        return self.category == self.case.category

    @property
    def urgency_correct(self) -> bool:
        return self.urgency == self.case.urgency

    @property
    def correct(self) -> bool:
        return self.category_correct and self.urgency_correct


@dataclass(frozen=True)
class EvalSummary:
    total: int
    failed: int
    category_accuracy: float
    urgency_accuracy: float
    urgent_recall: float | None
    human_review_rate: float
    injection_passed: int
    injection_total: int
    mean_latency_ms: float | None
    category_matrix: Matrix
    urgency_matrix: Matrix
    type_results: dict[str, tuple[int, int]]
    misses: tuple[CaseResult, ...]


def load_cases(path: Path = DATASET_PATH) -> list[EvalCase]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [EvalCase.model_validate_json(line) for line in lines if line.strip()]


async def run_cases(
    cases: Iterable[EvalCase],
    model: RequestClassifier,
    provider: str,
    timeout_seconds: float,
) -> list[CaseResult]:
    """Run cases one at a time through the same pipeline as the API."""
    results: list[CaseResult] = []
    for case in cases:
        try:
            result = await classify_request(case.text, model, provider, timeout_seconds)
        except ModelUnavailableError:
            results.append(CaseResult(case, FAILED, FAILED, True, None))
            continue
        results.append(
            CaseResult(case, result.category, result.urgency, result.needs_human, result.latency_ms)
        )
    return results


def _confusion_matrix(pairs: Iterable[tuple[str, str]], labels: Sequence[str]) -> Matrix:
    matrix = {truth: dict.fromkeys((*labels, FAILED), 0) for truth in labels}
    for truth, predicted in pairs:
        matrix[truth][predicted] += 1
    return matrix


def summarize(results: Sequence[CaseResult]) -> EvalSummary:
    if not results:
        raise ValueError("Cannot summarize an empty evaluation")

    total = len(results)
    urgent = [result for result in results if result.case.urgency == "kiireellinen"]
    injections = [result for result in results if INJECTION_TAG in result.case.tags]
    latencies = [result.latency_ms for result in results if result.latency_ms is not None]

    type_results: dict[str, tuple[int, int]] = {}
    for case_type in CASE_TYPES:
        matching = [result for result in results if case_type in result.case.tags]
        if matching:
            type_results[case_type] = (sum(r.correct for r in matching), len(matching))

    return EvalSummary(
        total=total,
        failed=sum(result.failed for result in results),
        category_accuracy=sum(r.category_correct for r in results) / total,
        urgency_accuracy=sum(r.urgency_correct for r in results) / total,
        urgent_recall=(
            sum(r.urgency == "kiireellinen" for r in urgent) / len(urgent) if urgent else None
        ),
        human_review_rate=sum(r.needs_human for r in results) / total,
        injection_passed=sum(r.correct for r in injections),
        injection_total=len(injections),
        mean_latency_ms=sum(latencies) / len(latencies) if latencies else None,
        category_matrix=_confusion_matrix(
            ((r.case.category, r.category) for r in results), CATEGORIES
        ),
        urgency_matrix=_confusion_matrix(((r.case.urgency, r.urgency) for r in results), URGENCIES),
        type_results=type_results,
        misses=tuple(result for result in results if not result.correct),
    )


def _metric_rows(summary: EvalSummary) -> list[tuple[str, str]]:
    recall = "n/a" if summary.urgent_recall is None else f"{summary.urgent_recall:.1%}"
    latency = "n/a" if summary.mean_latency_ms is None else f"{summary.mean_latency_ms:.0f} ms"
    injection = (
        "n/a"
        if summary.injection_total == 0
        else f"{summary.injection_passed}/{summary.injection_total}"
    )
    return [
        ("Category accuracy", f"{summary.category_accuracy:.1%}"),
        ("Urgency accuracy", f"{summary.urgency_accuracy:.1%}"),
        ("Urgent requests detected", recall),
        ("Sent to human review", f"{summary.human_review_rate:.1%}"),
        ("Prompt injection cases handled", injection),
        ("Mean latency", latency),
        ("Failed model calls", f"{summary.failed}/{summary.total}"),
    ]


def _render_matrix(matrix: Matrix, labels: Sequence[str]) -> list[str]:
    has_failures = any(row[FAILED] for row in matrix.values())
    columns = [*labels, FAILED] if has_failures else list(labels)
    lines = [
        "| Correct \\ Predicted | " + " | ".join(columns) + " |",
        "| --- | " + " | ".join("---:" for _ in columns) + " |",
    ]
    for truth in labels:
        cells = " | ".join(str(matrix[truth][column]) for column in columns)
        lines.append(f"| **{truth}** | {cells} |")
    return lines


def render_markdown(
    summary: EvalSummary,
    provider: str,
    model_name: str,
    generated_on: date,
) -> str:
    lines = [
        "# Evaluation results",
        "",
        f"- **Provider:** `{provider}`",
        f"- **Model:** {model_name}",
        f"- **Date:** {generated_on.isoformat()}",
        f"- **Dataset:** {summary.total} fictional labelled requests in Finnish",
        "",
        "Generated by `python -m eval.run_eval`. Results include the deterministic rules gate.",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        *(f"| {name} | {value} |" for name, value in _metric_rows(summary)),
        "",
        "## Category confusion matrix",
        "",
        *_render_matrix(summary.category_matrix, CATEGORIES),
        "",
        "## Urgency confusion matrix",
        "",
        *_render_matrix(summary.urgency_matrix, URGENCIES),
        "",
        "## Fully correct by case type",
        "",
        "| Case type | Correct |",
        "| --- | ---: |",
        *(
            f"| {case_type} | {correct}/{count} |"
            for case_type, (correct, count) in summary.type_results.items()
        ),
        "",
        "## Misclassified requests",
        "",
    ]
    if summary.misses:
        lines += ["| ID | Case type | Correct | Predicted |", "| --- | --- | --- | --- |"]
        lines += [
            f"| {miss.case.id} | {', '.join(miss.case.tags)} "
            f"| {miss.case.category} / {miss.case.urgency} "
            f"| {miss.category} / {miss.urgency} |"
            for miss in summary.misses
        ]
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def describe_model(settings: Settings) -> str:
    return {
        "fake": "keyword baseline (not a language model)",
        "azure_openai": f"`{settings.azure_openai_deployment}`",
        "openai": f"`{settings.openai_model}`",
        "anthropic": f"`{settings.anthropic_model}`",
    }[settings.llm_provider]


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the request classifier.")
    parser.add_argument("--provider", choices=get_args(Provider), help="defaults to LLM_PROVIDER")
    parser.add_argument(
        "--limit",
        type=_positive_int,
        help="run only the first N requests and write no file unless --output is given",
    )
    parser.add_argument("--output", type=Path, help="results file, default eval/results.md")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    overrides = {"llm_provider": args.provider} if args.provider else {}
    settings = Settings(**overrides)

    try:
        model = get_classifier(settings)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    cases = load_cases()
    if args.limit is not None:
        cases = cases[: args.limit]

    print(f"Running {len(cases)} requests with provider '{settings.llm_provider}'...")
    results = asyncio.run(
        run_cases(cases, model, settings.llm_provider, settings.llm_timeout_seconds)
    )
    summary = summarize(results)

    for name, value in _metric_rows(summary):
        print(f"{name}: {value}")

    # A wrong key or an outage must not replace earlier valid results.
    if summary.failed == summary.total:
        print("All model calls failed. No results were written.", file=sys.stderr)
        return 1

    output = args.output or (None if args.limit is not None else RESULTS_PATH)
    if output is not None:
        markdown = render_markdown(
            summary, settings.llm_provider, describe_model(settings), date.today()
        )
        output.write_text(markdown, encoding="utf-8", newline="\n")
        print(f"Results written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
