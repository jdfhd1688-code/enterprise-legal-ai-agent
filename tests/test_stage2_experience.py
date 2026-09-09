from __future__ import annotations

import base64
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from app.review_experience import STAGE_ORDER, VISUAL_STAGES, render_review_experience, visual_stage_for
from app.services.analysis_service import AnalysisService
from tests.helpers import TempSettings


class Stage2ExperienceTests(unittest.TestCase):
    def test_review_visual_contains_brand_story_and_accessible_progress(self) -> None:
        markup = render_review_experience("retrieving", "sample_contract.pdf")
        self.assertIn("循法而行", markup)
        self.assertIn("正在检索法律依据", markup)
        self.assertIn('data-stage-asset="stage2.png"', markup)
        image_match = re.search(r'src="data:image/png;base64,([^"]+)"', markup)
        self.assertIsNotNone(image_match)
        self.assertEqual(base64.b64decode(image_match.group(1))[:8], b"\x89PNG\r\n\x1a\n")
        self.assertIn("alt=", markup)
        self.assertIn("process-step active", markup)
        self.assertNotIn("78%", markup)

    def test_fine_grained_workflow_maps_to_four_visual_stages(self) -> None:
        self.assertEqual(visual_stage_for("received"), 1)
        self.assertEqual(visual_stage_for("parsing"), 1)
        self.assertEqual(visual_stage_for("planning"), 2)
        self.assertEqual(visual_stage_for("retrieving"), 2)
        self.assertEqual(visual_stage_for("analyzing"), 3)
        self.assertEqual(visual_stage_for("validating"), 3)
        self.assertEqual(visual_stage_for("review_required"), 3)
        self.assertEqual(visual_stage_for("reporting"), 4)
        self.assertEqual(visual_stage_for("completed"), 4)

    def test_approved_visual_assets_exist_unchanged_in_central_directory(self) -> None:
        for visual in VISUAL_STAGES.values():
            asset = ROOT / "app" / "static" / "review_stages" / visual["asset"]
            self.assertTrue(asset.is_file())
            self.assertEqual(asset.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

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
        self.assertNotIn("completed", observed)
        self.assertEqual(observed[-1], "review_required")
        markup = render_review_experience(observed[-1], sample.name)
        self.assertIn("visual-stage-3", markup)
        self.assertIn("需要人工复核", markup)
        self.assertNotIn("stage4.png", markup)


if __name__ == "__main__":
    unittest.main()
