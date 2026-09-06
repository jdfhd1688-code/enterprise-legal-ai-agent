"""Workflow router that turns structured risk JSON into a deterministic route."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas.kb import RetrievalResult
from app.schemas.risk import RiskAnalysis, RiskLevel


class WorkflowRoute:
    awaiting_review = "human_review"
    report = "report_generation"
    failed = "failed"


class WorkflowRouter:
    """Applies the documented business rules, not another LLM call."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evidence_sufficient(self, risk: RiskAnalysis, retrieval: RetrievalResult) -> bool:
        if not retrieval.hits:
            return False
        if any(not finding.legal_basis for finding in risk.findings):
            return False
        if any(
            basis.status not in {"current", "effective"}
            for finding in risk.findings
            for basis in finding.legal_basis
        ):
            return False
        return True

    def route(self, risk: RiskAnalysis, retrieval: RetrievalResult) -> tuple[str, RiskAnalysis]:
        reasons: list[str] = []
        low_confidence = risk.confidence < self.settings.confidence_threshold
        evidence_ok = self.evidence_sufficient(risk, retrieval)
        risk.evidence_sufficient = evidence_ok
        domain_specialist = self.settings.domain_requires_specialist_review(risk.legal_domain)
        specialist_dimension = risk.review_dimension in {
            "data_compliance",
            "employment",
            "intellectual_property",
        }

        if risk.risk_level == RiskLevel.high:
            reasons.append("高风险法律事项")
        if low_confidence:
            reasons.append(f"置信度 {risk.confidence:.2f} 低于阈值 {self.settings.confidence_threshold:.2f}")
        if domain_specialist and risk.risk_level in {RiskLevel.high, RiskLevel.medium}:
            reasons.append("高专业性法律领域")
        if specialist_dimension and risk.risk_level in {RiskLevel.medium, RiskLevel.high}:
            reasons.append("高风险管理维度需要人工复核")
        if not evidence_ok:
            reasons.append("法律知识库证据不足，不允许自动生成确定性报告")
        if not risk.evidence_sufficient:
            reasons.append("evidence_sufficient=false")
        if risk.requires_human_review:
            reasons.append("分析结果要求人工复核")

        if reasons:
            risk.requires_human_review = True
            risk.review_reason = "；".join(dict.fromkeys(reasons))
            return WorkflowRoute.awaiting_review, risk

        risk.requires_human_review = False
        risk.review_reason = None
        risk.evidence_sufficient = True
        return WorkflowRoute.report, risk


def route_risk_json(
    risk: RiskAnalysis,
    retrieval: RetrievalResult,
    settings: Settings | None = None,
) -> tuple[str, RiskAnalysis]:
    return WorkflowRouter(settings).route(risk, retrieval)
