from __future__ import annotations

import unittest

from app.config import Settings
from app.schemas.kb import RetrievalResult
from app.schemas.risk import Finding, LegalBasis, RiskAnalysis
from app.tools.knowledge_base_tool import KnowledgeBaseTool
from app.workflow.router import WorkflowRoute, WorkflowRouter


def make_risk(task_id: str, level: str, findings: list | None = None) -> RiskAnalysis:
    return RiskAnalysis(
        task_id=task_id,
        risk_level=level,
        legal_domain="contract",
        confidence=0.9,
        summary="summary",
        findings=findings or [],
    )


class WorkflowRoutingTests(unittest.TestCase):
    def test_high_risk_goes_to_human_review(self) -> None:
        risk = make_risk("TASK-H", "high")
        route, routed = WorkflowRouter(Settings()).route(risk, RetrievalResult())
        self.assertEqual(route, WorkflowRoute.awaiting_review)
        self.assertTrue(routed.requires_human_review)

    def test_low_confidence_goes_to_human_review(self) -> None:
        settings = Settings(confidence_threshold=0.75)
        risk = RiskAnalysis(
            task_id="TASK-LC",
            risk_level="medium",
            legal_domain="contract",
            confidence=0.5,
            summary="low conf",
            findings=[],
        )
        route, _ = WorkflowRouter(settings).route(risk, RetrievalResult())
        self.assertEqual(route, WorkflowRoute.awaiting_review)

    def test_low_risk_with_evidence_goes_to_report(self) -> None:
        settings = Settings()
        kb = KnowledgeBaseTool(settings)
        hits = kb.search("违约金 合同 责任")
        self.assertFalse(hits.is_empty)
        risk = make_risk("TASK-LOW", "low")
        route, routed = WorkflowRouter(settings).route(risk, hits)
        self.assertEqual(route, WorkflowRoute.report)
        self.assertFalse(routed.requires_human_review)

    def test_finding_without_legal_basis_requires_review(self) -> None:
        settings = Settings()
        kb = KnowledgeBaseTool(settings)
        hits = kb.search("违约金")
        finding = Finding(
            clause_id="C1",
            risk_type="liability",
            severity="medium",
            issue="没有依据",
            contract_evidence="text",
            legal_basis=[],
        )
        risk = make_risk("TASK-NO", "low", [finding])
        route, routed = WorkflowRouter(settings).route(risk, hits)
        self.assertEqual(route, WorkflowRoute.awaiting_review)
        self.assertIn("证据不足", routed.review_reason or "")


if __name__ == "__main__":
    unittest.main()

