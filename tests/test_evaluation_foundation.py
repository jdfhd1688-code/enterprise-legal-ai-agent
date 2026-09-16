from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.evaluation.contracts import EvaluationFailure, EvaluatorOutput
from app.evaluation.dataset_loader import DatasetLoadError, DatasetLoader
from app.evaluation.report import render_json, render_markdown, write_reports
from app.evaluation.runner import (
    EvaluationRunner,
    EvaluatorNotRegisteredError,
    FoundationValidationEvaluator,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "eval" / "fixtures"
RETRIEVAL_FIXTURE = FIXTURES / "retrieval_foundation.json"


class SuccessEvaluator:
    name = "test_success"
    version = "test-v1"

    def evaluate(self, dataset):
        return EvaluatorOutput(
            case_count=len(dataset.cases),
            metrics={"observed_cases": len(dataset.cases)},
            failures=[EvaluationFailure(case_id=dataset.cases[0].id, reason="expected test failure")],
        )


class ExplodingEvaluator:
    name = "test_exploding"
    version = "test-v1"

    def evaluate(self, dataset):
        raise RuntimeError("synthetic evaluator failure")


class EvaluationDatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = DatasetLoader()

    def test_valid_datasets_load(self) -> None:
        expected = {
            "retrieval_foundation.json": "retrieval",
            "risk_foundation.json": "risk",
            "abstention_foundation.json": "abstention",
            "citation_foundation.json": "citation",
            "schema_foundation.json": "schema",
        }
        for name, dataset_type in expected.items():
            with self.subTest(name=name):
                loaded = self.loader.load(FIXTURES / name)
                self.assertEqual(loaded.metadata.dataset_type.value, dataset_type)
                self.assertEqual(len(loaded.cases), 2)

    def test_invalid_dataset_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(DatasetLoadError):
                self.loader.load(path)

    def test_missing_expected_doc_ids_fails(self) -> None:
        raw = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        del raw["cases"][0]["expected_doc_ids"]
        self._assert_invalid(raw)

    def test_invalid_risk_enum_fails(self) -> None:
        raw = json.loads((FIXTURES / "risk_foundation.json").read_text(encoding="utf-8"))
        raw["cases"][0]["expected_risk"] = "critical"
        self._assert_invalid(raw)

    def test_dataset_metadata_version_exists(self) -> None:
        loaded = self.loader.load(RETRIEVAL_FIXTURE)
        self.assertEqual(loaded.metadata.dataset_version, "1.0.0-fixture")

    def test_empty_dataset_is_rejected(self) -> None:
        raw = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        raw["cases"] = []
        self._assert_invalid(raw)

    def _assert_invalid(self, raw: dict) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(DatasetLoadError):
                self.loader.load(path)


class EvaluationRunnerTests(unittest.TestCase):
    def test_runner_handles_registered_evaluator(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(SuccessEvaluator())
        result = runner.run("test_success", RETRIEVAL_FIXTURE)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.case_count, 2)

    def test_runner_rejects_missing_evaluator(self) -> None:
        with self.assertRaises(EvaluatorNotRegisteredError):
            EvaluationRunner(project_root=ROOT).run("missing", RETRIEVAL_FIXTURE)

    def test_evaluator_exception_is_surfaced(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(ExplodingEvaluator())
        result = runner.run("test_exploding", RETRIEVAL_FIXTURE)
        self.assertEqual(result.status, "error")
        self.assertIn("synthetic evaluator failure", result.failures[0].reason)

    def test_run_metadata_contains_git_commit(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(FoundationValidationEvaluator())
        result = runner.run("foundation_validation", RETRIEVAL_FIXTURE)
        self.assertEqual(len(result.metadata.git_commit), 40)
        int(result.metadata.git_commit, 16)

    def test_secrets_are_redacted_from_reports(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(FoundationValidationEvaluator())
        result = runner.run(
            "foundation_validation",
            RETRIEVAL_FIXTURE,
            configuration={"api_key": "do-not-write-this", "nested": {"access_token": "also-secret"}},
        )
        report = render_json([result]) + render_markdown([result])
        self.assertNotIn("do-not-write-this", report)
        self.assertNotIn("also-secret", report)
        self.assertIn("[REDACTED]", report)


class EvaluationReportTests(unittest.TestCase):
    def setUp(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(SuccessEvaluator())
        self.result = runner.run("test_success", RETRIEVAL_FIXTURE)

    def test_json_report_is_valid(self) -> None:
        payload = json.loads(render_json([self.result]))
        self.assertEqual(payload["results"][0]["evaluator"], "test_success")

    def test_markdown_report_is_generated(self) -> None:
        report = render_markdown([self.result])
        self.assertIn("# Evaluation Summary", report)
        self.assertIn("## Known Limitations", report)

    def test_report_includes_failures(self) -> None:
        report = render_markdown([self.result])
        self.assertIn("expected test failure", report)
        self.assertIn("RET-FIX-001", report)

    def test_reports_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = write_reports([self.result], directory)
            self.assertTrue(json_path.is_file())
            self.assertTrue(markdown_path.is_file())
            json.loads(json_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
