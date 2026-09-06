from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.agent.review_planner import ReviewDimensionPlanner
from app.config import Settings
from app.mcp.adapters import MockLegalRegistryAdapter
from app.schemas.kb import RetrievalResult
from app.schemas.risk import Finding, LegalBasis, ReviewDecision, RiskAnalysis
from app.services.analysis_service import AnalysisService
from app.tools.knowledge_base_tool import KnowledgeBaseTool
from app.workflow.router import WorkflowRoute, WorkflowRouter
from tests.helpers import TempSettings


class ReviewDimensionPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = ReviewDimensionPlanner()

    def test_detects_payment_risk(self) -> None:
        plan = self.planner.plan("请重点检查付款条款和逾期付款风险")
        self.assertEqual(plan.dimension, "payment_risk")
        self.assertEqual(plan.legal_domain, "contract")
        self.assertIn("付款", plan.matched_keywords)

    def test_falls_back_to_general(self) -> None:
        plan = self.planner.plan("帮我看看")
        self.assertEqual(plan.dimension, "general_contract")
        self.assertEqual(plan.reason, "未识别到明确关键词，按通用合同风险处理。")

    def test_preferred_dimension_wins(self) -> None:
        plan = self.planner.plan("任意问题", preferred_dimension="data_compliance")
        self.assertEqual(plan.dimension, "data_compliance")
        self.assertEqual(plan.legal_domain, "data")


class RAGMetadataFilterTests(unittest.TestCase):
    def test_expired_and_unknown_documents_are_filtered(self) -> None:
        with TempSettings() as settings:
            settings.legal_kb_dir.mkdir(parents=True, exist_ok=True)
            fixture = settings.legal_kb_dir / "fixture.json"
            fixture.write_text(
                json.dumps(
                    [
                        {
                            "document_id": "VALID-001",
                            "title": "DEMO valid rule",
                            "article_no": "article-1",
                            "content": "违约金应当与实际损失大体相当。",
                            "source": "DEMO/SAMPLE",
                            "source_url": "https://example.invalid/1",
                            "issuing_authority": "DEMO",
                            "effective_date": "2024-01-01",
                            "expiry_date": None,
                            "domain": "contract",
                            "jurisdiction": "中国大陆",
                            "source_type": "demo_sample",
                            "status": "effective",
                        },
                        {
                            "document_id": "EXPIRED-001",
                            "title": "DEMO expired rule",
                            "article_no": "article-2",
                            "content": "违约金按十倍支付。",
                            "source": "DEMO/SAMPLE",
                            "source_url": "https://example.invalid/2",
                            "issuing_authority": "DEMO",
                            "effective_date": "2010-01-01",
                            "expiry_date": "2020-01-01",
                            "domain": "contract",
                            "jurisdiction": "unknown",
                            "source_type": "demo_sample",
                            "status": "expired",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            tool = KnowledgeBaseTool(settings)
            result = tool.search(
                "违约金",
                top_k=5,
                domain="contract",
                metadata_filter={"status": ["current", "effective"]},
            )
            self.assertGreater(len(result.hits), 0)
            self.assertTrue(all(hit.chunk.status == "effective" for hit in result.hits))
            self.assertTrue(all(hit.metadata["jurisdiction"] for hit in result.hits))
            self.assertIn("domain=contract", result.filters_applied)


class WorkflowEvidenceTests(unittest.TestCase):
    def test_expired_legal_basis_forces_human_review(self) -> None:
        settings = Settings()
        risk = RiskAnalysis(
            task_id="TASK-EXP",
            risk_level="low",
            legal_domain="contract",
            confidence=0.9,
            summary="low",
            findings=[
                Finding(
                    clause_id="C1",
                    risk_type="liability",
                    severity="low",
                    issue="minor",
                    legal_basis=[
                        LegalBasis(
                            title="expired",
                            article_no="x",
                            source="demo",
                            status="expired",
                            jurisdiction="中国大陆",
                        )
                    ],
                )
            ],
        )
        route, routed = WorkflowRouter(settings).route(risk, RetrievalResult(hits=[]))
        self.assertEqual(route, WorkflowRoute.awaiting_review)
        self.assertIn("证据不足", routed.review_reason or "")
        self.assertFalse(routed.evidence_sufficient)


class HumanReviewAuditTests(unittest.TestCase):
    def test_audit_events_cover_review_loop(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            service = AnalysisService(settings)
            sample = ROOT / "data" / "contracts" / "sample_contract_high_risk.pdf"
            task = service.create_task(
                sample.name,
                sample.read_bytes(),
                "这份合同有哪些高风险条款？",
            )
            types = {event.event_type for event in task.audit_events}
            self.assertIn("task_created", types)
            self.assertIn("document_parsed", types)
            self.assertIn("retrieval_completed", types)
            self.assertIn("risk_analysis_completed", types)
            self.assertIn("human_review_started", types)

            reviewed = service.submit_review(
                task.task_id,
                ReviewDecision.approve,
                comment="approved",
                reviewer="tester",
            )
            review_types = {event.event_type for event in reviewed.audit_events}
            self.assertIn("human_review_completed", review_types)
            self.assertIn("report_generated", review_types)
            completed = next(
                event for event in reviewed.audit_events if event.event_type == "human_review_completed"
            )
            self.assertEqual(completed.actor, "reviewer")
            self.assertIsNotNone(reviewed.original_ai_result)
            self.assertIsNotNone(reviewed.reviewed_result)


class MCPAdapterTests(unittest.TestCase):
    def test_mock_adapter_exposes_integration_surface(self) -> None:
        adapter = MockLegalRegistryAdapter()
        self.assertEqual(len(adapter.list_resources()), 3)
        self.assertEqual(adapter.search_external_registry("劳动法", {"status": "effective"}), [])
        self.assertIn("pending_verification", adapter.get_legal_update("MOCK-EXT-001").status)
        self.assertIn("mock_synced", adapter.sync_verified_resource("MOCK-EXT-002").status)
        log = adapter.get_tool_call_log()
        self.assertGreaterEqual(len(log), 4)
        self.assertTrue(all(item["mock"] for item in log))


if __name__ == "__main__":
    unittest.main()
