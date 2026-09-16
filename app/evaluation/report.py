"""Machine-readable and human-readable evaluation reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.contracts import EvaluationResult


DEFAULT_LIMITATIONS = [
    "Metrics apply only to the declared DEMO/SYNTHETIC dataset and retrieval target.",
    "Retrieval metrics do not measure legal conclusions, whole-system accuracy, production coverage, or hallucination rate.",
    "Legacy Recall@5 and corrected Retrieval v2 Recall@5 use different semantics and are not a trend.",
    "B2 implements Retrieval evaluation only; other evaluator families remain unavailable.",
]


def report_payload(
    results: list[EvaluationResult], limitations: list[str] | None = None
) -> dict[str, object]:
    return {
        "report_type": "evaluation_summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": [result.model_dump(mode="json") for result in results],
        "known_limitations": limitations or DEFAULT_LIMITATIONS,
    }


def render_json(results: list[EvaluationResult], limitations: list[str] | None = None) -> str:
    return json.dumps(report_payload(results, limitations), ensure_ascii=False, indent=2)


def render_markdown(results: list[EvaluationResult], limitations: list[str] | None = None) -> str:
    lines = ["# Evaluation Summary", ""]
    for result in results:
        metadata = result.metadata
        lines.extend(
            [
                f"## {result.evaluator}",
                "",
                "### Run Metadata",
                "",
                f"- Run ID: `{metadata.run_id}`",
                f"- Started: `{metadata.started_at.isoformat()}`",
                f"- Completed: `{metadata.completed_at.isoformat() if metadata.completed_at else 'not completed'}`",
                f"- Git commit: `{metadata.git_commit}`",
                f"- Evaluator version: `{metadata.evaluator_version}`",
                f"- Mode: `{metadata.mode}`",
                f"- Python: `{metadata.python_version}`",
                f"- Project: `{metadata.project_version}`",
                "",
                "### Dataset",
                "",
                f"- Name: `{metadata.dataset_name}`",
                f"- Version: `{metadata.dataset_version}`",
                f"- Cases: `{result.case_count}`",
                "",
                "### Evaluators Executed",
                "",
                f"- `{result.evaluator}` — `{result.status}`",
                "",
                "### Metrics",
                "",
            ]
        )
        if result.metrics:
            lines.extend(f"- {key}: `{value}`" for key, value in sorted(result.metrics.items()))
        else:
            lines.append("- None")
        lines.extend(["", "### Failures", ""])
        if result.failures:
            lines.extend(f"- `{failure.case_id}`: {failure.reason}" for failure in result.failures)
        else:
            lines.append("- None")
        lines.extend(["", "### Warnings", ""])
        if result.warnings:
            lines.extend(f"- {warning}" for warning in result.warnings)
        else:
            lines.append("- None")
        lines.append("")
    lines.extend(["## Known Limitations", ""])
    lines.extend(f"- {item}" for item in (limitations or DEFAULT_LIMITATIONS))
    lines.append("")
    return "\n".join(lines)


def write_reports(
    results: list[EvaluationResult],
    output_dir: str | Path,
    *,
    prefix: str = "evaluation-summary",
    limitations: list[str] | None = None,
) -> tuple[Path, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / f"{prefix}.json"
    markdown_path = target / f"{prefix}.md"
    json_path.write_text(render_json(results, limitations), encoding="utf-8")
    markdown_path.write_text(render_markdown(results, limitations), encoding="utf-8")
    return json_path, markdown_path
