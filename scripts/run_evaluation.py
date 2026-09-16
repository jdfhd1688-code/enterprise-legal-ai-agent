"""Run the B1 offline evaluation foundation against a validated fixture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.report import write_reports
from app.evaluation.runner import EvaluationRunner, FoundationValidationEvaluator


DEFAULT_DATASET = ROOT / "data" / "eval" / "fixtures" / "retrieval_foundation.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "evaluation" / "runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the offline Evaluation Foundation")
    parser.add_argument(
        "--evaluator",
        default="foundation_validation",
        choices=["foundation_validation"],
        help="B1 registers infrastructure validation only; E1-E5 evaluators are not implemented here.",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = EvaluationRunner(project_root=ROOT)
    runner.register(FoundationValidationEvaluator())
    try:
        result = runner.run(
            args.evaluator,
            args.dataset,
            configuration={"network": "disabled", "purpose": "foundation_smoke_test"},
        )
        json_path, markdown_path = write_reports([result], args.output_dir)
    except Exception as exc:  # noqa: BLE001 - CLI must fail clearly
        print(f"Evaluation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "evaluator": result.evaluator,
                "status": result.status,
                "case_count": result.case_count,
                "json_report": str(json_path),
                "markdown_report": str(markdown_path),
                "performance_claim": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
