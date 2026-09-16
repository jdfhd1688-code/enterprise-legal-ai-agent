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
from app.evaluation.retrieval_v2 import RetrievalV2Evaluator
from app.evaluation.runner import EvaluationRunner, FoundationValidationEvaluator


FOUNDATION_DATASET = ROOT / "data" / "eval" / "fixtures" / "retrieval_foundation.json"
RETRIEVAL_V2_DATASET = ROOT / "data" / "eval" / "retrieval_v2.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "evaluation" / "runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an offline evaluator")
    parser.add_argument(
        "--evaluator",
        default="foundation_validation",
        choices=["foundation_validation", "retrieval_v2"],
    )
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset = args.dataset or (
        RETRIEVAL_V2_DATASET if args.evaluator == "retrieval_v2" else FOUNDATION_DATASET
    )
    runner = EvaluationRunner(project_root=ROOT)
    runner.register(FoundationValidationEvaluator())
    runner.register(RetrievalV2Evaluator(project_root=ROOT))
    try:
        result = runner.run(
            args.evaluator,
            dataset,
            configuration={"network": "disabled", "evaluation_scope": args.evaluator},
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
                "metric_scope": "declared_dataset_only",
                "system_performance_claim": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
