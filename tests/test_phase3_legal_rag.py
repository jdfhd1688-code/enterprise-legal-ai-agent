from __future__ import annotations

import unittest
from pathlib import Path

from app.evaluation.retrieval_eval import RetrievalEvaluator
from app.guards.citation_guard import CitationGuard
from app.playbook.engine import PlaybookEngine
from app.rag.query_builder import LegalRetrievalQueryBuilder
from app.schemas.document import DocumentChunk
from app.schemas.risk import Finding, LegalBasis, RiskAnalysis
from app.services.analysis_service import AnalysisService
from app.tools.knowledge_base_tool import KnowledgeBaseTool
from tests.helpers import TempSettings


ROOT = Path(__file__).resolve().parents[1]


class LegalKnowledgeBaseTests(unittest.TestCase):
    def test_demo_kb_loads_governed_records(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            kb = KnowledgeBaseTool(settings)
            self.assertGreaterEqual(len(kb.chunks), 60)
            self.assertTrue(all(c.jurisdiction and c.domain and c.status and c.version for c in kb.chunks))
            self.assertTrue(all(c.source_type == "demo_sample" and c.is_demo_sample for c in kb.chunks))

    def test_metadata_filter_limits_jurisdiction_domain_and_status(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            result = KnowledgeBaseTool(settings).search(
                "违约责任 损害赔偿", domain="contract",
                metadata_filter={"jurisdiction": "中国大陆", "status": ["current"], "source_type": "demo_sample"},
            )
            self.assertTrue(result.hits)
            self.assertTrue(all(h.chunk.domain == "contract" and h.chunk.jurisdiction == "中国大陆" for h in result.hits))

    def test_hybrid_result_exposes_keyword_dense_and_rrf_scores(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            result = KnowledgeBaseTool(settings).search("违约责任 第577条", top_k=5)
            self.assertEqual(result.fusion_method, "rrf-k60")
            self.assertTrue(result.keyword_hits and result.dense_hits)
            self.assertTrue(all(h.rank > 0 and h.fusion_score > 0 for h in result.hits))
            self.assertTrue(any(h.keyword_score > 0 for h in result.hits))

    def test_exact_article_match_is_explainable(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            result = KnowledgeBaseTool(settings).search("违约金 样例条款 03", top_k=5, domain="contract")
            self.assertTrue(any("精确命中条款编号" in h.match_reason for h in result.hits))

    def test_query_builder_records_default_jurisdiction_uncertainty(self) -> None:
        built = LegalRetrievalQueryBuilder().build("长期拖延履行怎么办", "服务合同", "breach_liability")
        self.assertEqual(built.jurisdiction, "中国大陆")
        self.assertIn("DEMO", built.explanation)
        self.assertIn("违约责任", built.query)


class PlaybookAndEvidenceTests(unittest.TestCase):
    def test_playbook_loads_versioned_rules(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            engine = PlaybookEngine(settings)
            self.assertGreaterEqual(len(engine.rules), 10)
            self.assertTrue(all(rule.version == "demo-v1" for rule in engine.rules))

    def test_payment_deviation_generates_redline(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            chunks = [DocumentChunk(chunk_id="C1", source="demo.txt", section="付款", text="甲方应在收到合法发票后90日内付款。")]
            result = PlaybookEngine(settings).evaluate(chunks)
            payment = next(item for item in result.deviations if item.rule_id == "PAYMENT_TERM_001")
            self.assertIn("90", payment.evidence.actual)
            self.assertIsNotNone(payment.redline)
            self.assertIn("30", payment.redline.suggested_clause)

    def test_citation_guard_verifies_retrieved_citation(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            retrieval = KnowledgeBaseTool(settings).search("违约责任 第577条", top_k=5)
            hit = retrieval.hits[0]
            basis = LegalBasis(title=hit.chunk.title, article_no=hit.chunk.article_no, source=hit.chunk.source)
            finding = Finding(clause_id="C1", risk_type="breach", severity="medium", issue="违约", contract_evidence="未履行义务", legal_basis=[basis])
            risk = RiskAnalysis(task_id="T1", risk_level="medium", legal_domain="breach", confidence=.8, summary="test", findings=[finding])
            guarded = CitationGuard().validate(risk, retrieval)
            self.assertEqual(guarded.findings[0].legal_basis[0].citation_status.value, "verified")
            self.assertEqual(guarded.evidence_status.value, "sufficient")

    def test_unverified_citation_is_not_treated_as_evidence(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            retrieval = KnowledgeBaseTool(settings).search("违约责任", top_k=3)
            basis = LegalBasis(title="不存在的法律", article_no="第9999条", source="hallucinated")
            finding = Finding(clause_id="C1", risk_type="breach", severity="medium", issue="风险", contract_evidence="原文", legal_basis=[basis])
            risk = RiskAnalysis(task_id="T2", risk_level="medium", legal_domain="breach", confidence=.9, summary="test", findings=[finding])
            guarded = CitationGuard().validate(risk, retrieval)
            self.assertEqual(guarded.findings[0].legal_basis[0].citation_status.value, "unverified")
            self.assertTrue(guarded.requires_human_review)
            self.assertNotEqual(guarded.evidence_status.value, "sufficient")


class EvaluationAndWorkflowTests(unittest.TestCase):
    def test_eval_dataset_and_metrics_are_runnable(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            evaluator = RetrievalEvaluator(settings)
            self.assertGreaterEqual(len(evaluator.load_items()), 24)
            metrics = evaluator.evaluate()
            self.assertGreaterEqual(metrics["hit_at_3"], .9)
            self.assertGreaterEqual(metrics["recall_at_5"], .9)

    def test_high_risk_demo_has_three_part_evidence_and_redline(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            service = AnalysisService(settings)
            source = ROOT / "data" / "contracts" / "sample_contract_high_risk.pdf"
            task = service.create_task(source.name, source.read_bytes(), "审查高风险条款")
            self.assertTrue(task.risk.findings)
            self.assertTrue(any(f.contract_evidence and f.legal_evidence and f.playbook_evidence for f in task.risk.findings))
            self.assertTrue(any(f.redline is not None for f in task.risk.findings))
            self.assertEqual(task.route, "human_review")

    def test_report_contains_evidence_chain_sections(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            service = AnalysisService(settings)
            source = ROOT / "data" / "contracts" / "sample_contract_low_risk.pdf"
            task = service.create_task(source.name, source.read_bytes(), "审查合同")
            report = task.report_markdown or ""
            self.assertIn("证据状态", report)
            self.assertIn("引用校验", report)
            self.assertIn("企业 Playbook", report)


if __name__ == "__main__":
    unittest.main()
