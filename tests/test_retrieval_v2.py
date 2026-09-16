from __future__ import annotations

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.evaluation.dataset_loader import DatasetLoader
from app.evaluation.dataset_models import RetrievalEvalCase
from app.evaluation.report import render_json, render_markdown
from app.evaluation.retrieval_v2 import (
    RetrievalCaseOutcome,
    RetrievalV2Evaluator,
    calculate_metrics,
)
from app.evaluation.runner import EvaluationRunner
from app.rag.contract_retriever import ContractRetriever
from app.skills.chunker import ChunkerSkill
from app.skills.document_parser import DocumentParserSkill
from app.tools.knowledge_base_tool import KnowledgeBaseTool


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "eval" / "retrieval_v2.json"
LEGACY = ROOT / "data" / "eval" / "legal_retrieval_eval.json"
CONTRACT = ROOT / "data" / "demo_contracts" / "demo_phase4_contract.docx"


def case(
    case_id: str,
    expected: list[str],
    *,
    query_type: str = "legal",
    negative: bool = False,
    domain: str = "contract",
) -> RetrievalEvalCase:
    return RetrievalEvalCase(
        id=case_id,
        query=f"query {case_id}",
        query_type=query_type,
        expected_doc_ids=expected,
        expected_no_relevant_result=negative,
        legal_domain=domain,
    )


class RetrievalMetricTests(unittest.TestCase):
    def test_hit_at_k_correctness(self) -> None:
        outcomes = [
            RetrievalCaseOutcome(case("A", ["gold"]), ["gold", "x"]),
            RetrievalCaseOutcome(case("B", ["gold"]), ["x", "y", "gold"]),
            RetrievalCaseOutcome(case("C", ["gold"]), ["x", "y", "z", "q", "gold"]),
            RetrievalCaseOutcome(case("D", ["gold"]), ["x"]),
        ]
        metrics = calculate_metrics(outcomes)
        self.assertEqual(metrics["hit_at_1"], 0.25)
        self.assertEqual(metrics["hit_at_3"], 0.5)
        self.assertEqual(metrics["hit_at_5"], 0.75)

    def test_recall_at_5_uses_all_relevant_documents(self) -> None:
        outcomes = [
            RetrievalCaseOutcome(case("A", ["one", "two"]), ["one", "x"]),
            RetrievalCaseOutcome(case("B", ["three", "four"]), ["three", "four"]),
        ]
        self.assertEqual(calculate_metrics(outcomes)["recall_at_5"], 0.75)

    def test_mrr_uses_first_relevant_rank(self) -> None:
        outcomes = [
            RetrievalCaseOutcome(case("A", ["gold"]), ["gold"]),
            RetrievalCaseOutcome(case("B", ["gold"]), ["x", "gold"]),
            RetrievalCaseOutcome(case("C", ["gold"]), ["x"]),
        ]
        self.assertEqual(calculate_metrics(outcomes)["mrr"], 0.5)

    def test_no_hit_query_scores_zero(self) -> None:
        metrics = calculate_metrics([RetrievalCaseOutcome(case("A", ["gold"]), ["x"])])
        self.assertEqual(metrics["hit_at_5"], 0.0)
        self.assertEqual(metrics["recall_at_5"], 0.0)
        self.assertEqual(metrics["mrr"], 0.0)

    def test_negative_accuracy_requires_no_results(self) -> None:
        outcomes = [
            RetrievalCaseOutcome(case("A", [], negative=True), []),
            RetrievalCaseOutcome(case("B", [], negative=True), ["false-positive"]),
        ]
        metrics = calculate_metrics(outcomes)
        self.assertEqual(metrics["negative_case_count"], 2)
        self.assertEqual(metrics["negative_accuracy"], 0.5)


class ContractRetrieverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        parsed = DocumentParserSkill().parse(CONTRACT.name, CONTRACT.read_bytes())
        cls.chunks = ChunkerSkill().chunk(parsed)

    def test_contract_query_ranks_real_chunks(self) -> None:
        hits = ContractRetriever().retrieve(self.chunks, "违约责任与间接损失", top_k=5)
        self.assertEqual(hits[0].chunk_id, "P0007")

    def test_contract_hit_preserves_section_page_anchor_and_score(self) -> None:
        hit = ContractRetriever().retrieve(self.chunks, "付款条件", top_k=1)[0]
        self.assertTrue(hit.chunk_id)
        self.assertTrue(hit.section)
        self.assertEqual(hit.page_no, 1)
        self.assertIsNotNone(hit.anchor)
        self.assertGreater(hit.score, 0)


class RetrievalV2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = DatasetLoader().load(DATASET)
        cls.output = RetrievalV2Evaluator(project_root=ROOT).evaluate(cls.dataset)

    def test_dataset_has_legal_contract_negative_and_multi_relevant_cases(self) -> None:
        cases = self.dataset.cases
        self.assertEqual(len(cases), 42)
        self.assertEqual(sum(item.query_type.value == "legal" for item in cases), 30)
        self.assertEqual(sum(item.query_type.value == "contract" for item in cases), 12)
        self.assertEqual(sum(item.expected_no_relevant_result for item in cases), 6)
        self.assertGreaterEqual(sum(len(item.expected_doc_ids) > 1 for item in cases), 1)

    def test_legacy_queries_and_gold_targets_are_migrated_exactly(self) -> None:
        legacy = json.loads(LEGACY.read_text(encoding="utf-8"))["items"]
        chunks = KnowledgeBaseTool().chunks
        lookup = {(item.title, item.article_no): item.chunk_id for item in chunks}
        migrated = self.dataset.cases[:24]
        for old, new in zip(legacy, migrated):
            with self.subTest(case=old["id"]):
                expected = lookup[(old["expected_law_title"], old["expected_article_no"])]
                self.assertEqual(new.query, old["query"])
                self.assertEqual(new.expected_doc_ids, [expected])

    def test_per_type_metrics_are_present(self) -> None:
        self.assertIn("type.legal.hit_at_5", self.output.metrics)
        self.assertIn("type.contract.hit_at_5", self.output.metrics)

    def test_per_domain_metrics_are_present(self) -> None:
        self.assertIn("domain.data.recall_at_5", self.output.metrics)
        self.assertIn("domain.contract_document.recall_at_5", self.output.metrics)

    def test_original_hard_cases_remain_in_dataset(self) -> None:
        case_ids = {case.id for case in self.dataset.cases}
        self.assertTrue(
            {"RET-V2-030", "RET-V2-038", "RET-V2-040", "RET-V2-041"}.issubset(case_ids)
        )
        self.assertEqual(len(self.dataset.cases), 42)
        self.assertGreater(self.output.metrics["relevance_gate_rejection_count"], 0)

    def test_empty_expected_ids_require_explicit_negative(self) -> None:
        with self.assertRaises(ValidationError):
            case("invalid", [])

    def test_duplicate_expected_ids_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            case("invalid", ["same", "same"])

    def test_runner_integration(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(RetrievalV2Evaluator(project_root=ROOT))
        result = runner.run("retrieval_v2", DATASET)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.case_count, 42)
        self.assertEqual(result.metadata.dataset_version, "2.0.0")

    def test_json_report_contains_metrics_and_failures(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(RetrievalV2Evaluator(project_root=ROOT))
        result = runner.run("retrieval_v2", DATASET)
        payload = json.loads(render_json([result]))
        self.assertIn("recall_at_5", payload["results"][0]["metrics"])
        self.assertIn("false_positive_retrieval_count", payload["results"][0]["metrics"])
        self.assertIn("failures", payload["results"][0])

    def test_markdown_report_contains_rejection_metrics(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(RetrievalV2Evaluator(project_root=ROOT))
        result = runner.run("retrieval_v2", DATASET)
        report = render_markdown([result])
        self.assertIn("# Evaluation Summary", report)
        self.assertIn("relevance_gate_rejection_count", report)


if __name__ == "__main__":
    unittest.main()
