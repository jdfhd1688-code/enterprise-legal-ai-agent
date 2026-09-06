from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.schemas.risk import Finding, LegalBasis, RiskAnalysis


class RiskSchemaTests(unittest.TestCase):
    def test_valid_contract_parses(self) -> None:
        payload = {
            "task_id": "TASK-001",
            "risk_level": "high",
            "legal_domain": "contract",
            "confidence": 0.86,
            "summary": "发现高风险条款。",
            "findings": [
                {
                    "clause_id": "C-12",
                    "risk_type": "liability",
                    "severity": "high",
                    "issue": "责任范围过宽",
                    "contract_evidence": "合同原文片段",
                    "legal_basis": [
                        {
                            "title": "DEMO/SAMPLE",
                            "article_no": "样例条款",
                            "source": "DEMO/SAMPLE",
                            "effective_date": "2024-01-01",
                            "is_demo_sample": True,
                        }
                    ],
                    "recommendation": "建议修改。",
                }
            ],
            "requires_human_review": True,
            "review_reason": "高风险",
        }
        risk = RiskAnalysis.model_validate(payload)
        self.assertEqual(risk.task_id, "TASK-001")
        self.assertTrue(risk.findings[0].legal_basis[0].is_demo_sample)

    def test_finding_defaults_and_none_date(self) -> None:
        finding = Finding(
            clause_id="C1",
            risk_type="payment",
            severity="medium",
            issue="issue",
            legal_basis=[LegalBasis(title="t", article_no="a", source="s", effective_date="")],
        )
        self.assertIsNone(finding.legal_basis[0].effective_date)
        self.assertEqual(finding.contract_evidence, "")

    def test_invalid_risk_level_rejected(self) -> None:
        payload = {
            "task_id": "TASK-2",
            "risk_level": "severe",
            "legal_domain": "contract",
            "confidence": 0.9,
            "summary": "x",
            "findings": [],
        }
        with self.assertRaises(ValidationError):
            RiskAnalysis.model_validate(payload)


if __name__ == "__main__":
    unittest.main()

