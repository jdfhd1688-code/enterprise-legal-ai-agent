from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.schemas.risk import ReviewDecision
from app.services.analysis_service import AnalysisService
from tests.helpers import TempSettings


class DemoEndToEndTests(unittest.TestCase):
    def test_high_risk_review_flow_and_low_risk_report_flow(self) -> None:
        with TempSettings(use_real_kb=True) as settings:
            service = AnalysisService(settings)
            high_file = ROOT / "data" / "contracts" / "sample_contract_high_risk.pdf"
            high = service.create_task(
                high_file.name,
                high_file.read_bytes(),
                "这份合同有哪些高风险条款？",
            )
            self.assertEqual(high.status.value, "awaiting_review")
            self.assertEqual(high.route, "human_review")
            self.assertEqual(high.risk.risk_level.value, "high")
            self.assertGreater(len(high.retrieval.hits), 0)

            reviewed = service.submit_review(
                high.task_id,
                ReviewDecision.approve,
                comment="法务确认通过。",
                reviewer="demo-legal-counsel",
            )
            self.assertEqual(reviewed.status.value, "reviewed")
            self.assertIn("人工复核结果", reviewed.report_markdown or "")

            low_file = ROOT / "data" / "contracts" / "sample_contract_low_risk.pdf"
            low = service.create_task(
                low_file.name,
                low_file.read_bytes(),
                "这份合同有哪些需要关注的问题？",
            )
            self.assertEqual(low.status.value, "report_ready")
            self.assertEqual(low.route, "report_generation")
            self.assertEqual(low.risk.risk_level.value, "low")
            self.assertIsNotNone(low.report_markdown)


if __name__ == "__main__":
    unittest.main()
