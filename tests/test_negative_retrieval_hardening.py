from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.evaluation.dataset_loader import DatasetLoader
from app.evaluation.report import render_json
from app.evaluation.retrieval_v2 import RetrievalV2Evaluator
from app.evaluation.runner import EvaluationRunner
from app.rag.contract_retriever import ContractRetriever
from app.rag.relevance_gate import RelevanceGate
from app.skills.chunker import ChunkerSkill
from app.skills.document_parser import DocumentParserSkill
from app.tools.knowledge_base_tool import KnowledgeBaseTool


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "eval" / "retrieval_v2.json"
CONTRACT_PATH = ROOT / "data" / "demo_contracts" / "demo_phase4_contract.docx"


class NegativeRetrievalHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = DatasetLoader().load(DATASET_PATH)
        cls.cases = {case.id: case for case in cls.dataset.cases}
        parsed = DocumentParserSkill().parse(CONTRACT_PATH.name, CONTRACT_PATH.read_bytes())
        cls.contract_chunks = ChunkerSkill().chunk(parsed)
        cls.contract_retriever = ContractRetriever()
        cls.legal_retriever = KnowledgeBaseTool()
        cls.evaluator = RetrievalV2Evaluator(project_root=ROOT)
        cls.output = cls.evaluator.evaluate(cls.dataset)

    def test_negative_legal_query_can_return_no_usable_result(self) -> None:
        case = self.cases["RET-V2-030"]
        result = self.legal_retriever.search(
            case.query,
            top_k=5,
            domain=case.legal_domain,
            metadata_filter={
                "jurisdiction": case.jurisdiction,
                "status": ["current", "effective"],
                "source_type": "demo_sample",
            },
        )
        self.assertEqual(result.hits, [])
        self.assertGreater(result.relevance_gate_rejection_count, 0)

    def test_negative_contract_query_can_return_no_usable_result(self) -> None:
        result = self.contract_retriever.search(
            self.contract_chunks,
            self.cases["RET-V2-040"].query,
            top_k=5,
        )
        self.assertEqual(result.hits, [])
        self.assertGreater(len(result.candidates), 0)

    def test_relevant_legal_query_is_not_rejected(self) -> None:
        case = self.cases["RET-V2-001"]
        result = self.legal_retriever.search(
            case.query,
            top_k=5,
            domain=case.legal_domain,
            metadata_filter={
                "jurisdiction": case.jurisdiction,
                "status": ["current", "effective"],
                "source_type": "demo_sample",
            },
        )
        self.assertIn(case.expected_doc_ids[0], [hit.chunk.chunk_id for hit in result.hits])

    def test_relevant_contract_query_is_not_rejected(self) -> None:
        case = self.cases["RET-V2-033"]
        result = self.contract_retriever.search(self.contract_chunks, case.query, top_k=5)
        self.assertTrue(set(case.expected_doc_ids).issubset({hit.chunk_id for hit in result.hits}))

    def test_wrong_jurisdiction_is_rejected_by_metadata(self) -> None:
        case = self.cases["RET-V2-028"]
        result = self.legal_retriever.search(
            case.query,
            top_k=5,
            domain=case.legal_domain,
            metadata_filter={
                "jurisdiction": case.jurisdiction,
                "status": ["current", "effective"],
                "source_type": "demo_sample",
            },
        )
        self.assertEqual(result.hits, [])
        self.assertEqual(result.total_candidates, 0)

    def test_expired_only_source_is_not_usable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kb_dir = root / "kb"
            kb_dir.mkdir()
            (kb_dir / "expired.json").write_text(
                json.dumps({
                    "records": [{
                        "document_id": "EXPIRED-DEMO",
                        "title": "DEMO expired source",
                        "article_no": "demo-1",
                        "content": "付款期限规则",
                        "jurisdiction": "中国大陆",
                        "status": "expired",
                        "source_type": "demo_sample",
                    }]
                }),
                encoding="utf-8",
            )
            settings = Settings(
                legal_kb_dir=kb_dir,
                task_dir=root / "tasks",
                upload_dir=root / "uploads",
                output_dir=root / "outputs",
                contract_dir=root / "contracts",
                playbook_dir=root / "playbooks",
                eval_dir=root / "eval",
            )
            result = KnowledgeBaseTool(settings).search(
                "付款期限",
                metadata_filter={"status": ["current", "effective"]},
            )
            self.assertEqual(result.hits, [])

    def test_short_ambiguous_query_is_rejected(self) -> None:
        result = self.legal_retriever.search(
            "这个条款怎么样",
            top_k=5,
            metadata_filter={
                "jurisdiction": "中国大陆",
                "status": ["current", "effective"],
                "source_type": "demo_sample",
            },
        )
        self.assertEqual(result.hits, [])

    def test_partial_generic_overlap_does_not_guarantee_relevance(self) -> None:
        result = self.contract_retriever.search(self.contract_chunks, "不存在的保密期限", top_k=5)
        self.assertGreater(len(result.candidates), 0)
        self.assertEqual(result.hits, [])
        self.assertTrue(all(not hit.is_usable for hit in result.candidates))

    def test_relevance_gate_has_no_gold_label_input(self) -> None:
        parameters = set(inspect.signature(RelevanceGate.evaluate).parameters)
        self.assertEqual(parameters, {"self", "query", "candidate_text", "raw_score", "tokenizer"})
        self.assertFalse(parameters.intersection({"case_id", "expected_doc_ids", "gold_label"}))

    def test_positive_recall_does_not_regress(self) -> None:
        self.assertGreaterEqual(self.output.metrics["recall_at_5"], 0.9861)
        self.assertEqual(self.output.metrics["false_negative_retrieval_count"], 0)

    def test_multi_relevant_cases_remain_retrievable(self) -> None:
        multi_cases = [case for case in self.dataset.cases if len(case.expected_doc_ids) > 1]
        failures = {failure.case_id for failure in self.output.failures}
        self.assertGreater(len(multi_cases), 0)
        self.assertFalse(failures.intersection({case.id for case in multi_cases}))

    def test_report_includes_rejection_metrics(self) -> None:
        runner = EvaluationRunner(project_root=ROOT)
        runner.register(RetrievalV2Evaluator(project_root=ROOT))
        result = runner.run("retrieval_v2", DATASET_PATH)
        payload = json.loads(render_json([result]))["results"][0]
        for key in (
            "positive_query_recall",
            "false_positive_retrieval_count",
            "false_negative_retrieval_count",
            "no_result_rate",
            "relevance_gate_rejection_count",
        ):
            self.assertIn(key, payload["metrics"])


if __name__ == "__main__":
    unittest.main()
