from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.review_experience import STAGE_ORDER, render_review_experience
from app.services.analysis_service import AnalysisService
from tests.helpers import TempSettings


class Stage2ExperienceTests(unittest.TestCase):
    def test_review_visual_contains_brand_story_and_accessible_progress(self) -> None:
        markup = render_review_experience("retrieving", "sample_contract.pdf")
        self.assertIn("獬豸递卷", markup)
        self.assertIn("皋陶审契", markup)
        self.assertIn("正在检索法律依据", markup)
        self.assertIn("process-step active", markup)
        self.assertNotIn("78%", markup)

    def test_low_risk_workflow_emits_real_stage_sequence(self) -> None:
        observed: list[str] = []
        with TempSettings(use_real_kb=True) as settings:
            service = AnalysisService(settings)
            sample = ROOT / "data" / "contracts" / "sample_contract_low_risk.pdf"
            result = service.create_task(
                sample.name,
                sample.read_bytes(),
                "这份合同有哪些需要关注的问题？",
                on_stage=lambda stage, _message: observed.append(stage),
            )
        self.assertEqual(result.status.value, "report_ready")
        self.assertEqual(observed, list(STAGE_ORDER))

    def test_high_risk_branch_does_not_claim_report_generation(self) -> None:
        observed: list[str] = []
        with TempSettings(use_real_kb=True) as settings:
            service = AnalysisService(settings)
            sample = ROOT / "data" / "contracts" / "sample_contract_high_risk.pdf"
            result = service.create_task(
                sample.name,
                sample.read_bytes(),
                "这份合同有哪些高风险条款？",
                on_stage=lambda stage, _message: observed.append(stage),
            )
        self.assertEqual(result.status.value, "awaiting_review")
        self.assertNotIn("reporting", observed)
        self.assertEqual(observed[-1], "completed")


if __name__ == "__main__":
    unittest.main()
