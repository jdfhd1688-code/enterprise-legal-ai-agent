from __future__ import annotations

import unittest

from app.schemas.document import DocumentPage, ParsedDocument
from app.schemas.risk import RiskAnalysis
from app.skills.retrieval import RetrievalSkill
from app.tools.knowledge_base_tool import KnowledgeBaseTool
from app.workflow.router import WorkflowRoute, WorkflowRouter
from tests.helpers import TempSettings


class EmptyRetrievalTests(unittest.TestCase):
    def test_empty_kb_returns_no_hits_and_forces_review(self) -> None:
        with TempSettings() as settings:
            kb_tool = KnowledgeBaseTool(settings)
            self.assertEqual(kb_tool.chunks, [])
            skill = RetrievalSkill(kb_tool)
            parsed = ParsedDocument(
                source="contract.txt",
                title="contract",
                pages=[DocumentPage(source="contract.txt", page_no=1, text="采购合同")],
                file_size=10,
                content_type="txt",
                num_pages=1,
                text_length=4,
            )
            result = skill.retrieve(parsed, [], "有什么风险")
            self.assertTrue(result.is_empty)
            risk = RiskAnalysis(
                task_id="TASK-E",
                risk_level="low",
                legal_domain="contract",
                confidence=0.9,
                summary="no risk",
                findings=[],
            )
            route, routed = WorkflowRouter(settings).route(risk, result)
            self.assertEqual(route, WorkflowRoute.awaiting_review)
            self.assertIn("证据不足", routed.review_reason or "")


if __name__ == "__main__":
    unittest.main()

