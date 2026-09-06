"""Review Dimension Planner: a lightweight, deterministic intent planner."""

from __future__ import annotations

import re

from pydantic import BaseModel


REVIEW_DIMENSIONS: tuple[str, ...] = (
    "delivery_liability",
    "payment_risk",
    "breach_liability",
    "confidentiality",
    "intellectual_property",
    "dispute_resolution",
    "data_compliance",
    "employment",
    "general_contract",
)

DIMENSION_LABELS: dict[str, str] = {
    "delivery_liability": "交付责任",
    "payment_risk": "付款风险",
    "breach_liability": "违约责任",
    "confidentiality": "保密条款",
    "intellectual_property": "知识产权",
    "dispute_resolution": "争议解决",
    "data_compliance": "数据合规",
    "employment": "劳动用工",
    "general_contract": "通用合同风险",
}

DIMENSION_DOMAIN: dict[str, str] = {
    "delivery_liability": "contract",
    "payment_risk": "contract",
    "breach_liability": "contract",
    "confidentiality": "ip",
    "intellectual_property": "ip",
    "dispute_resolution": "contract",
    "data_compliance": "data",
    "employment": "labor",
    "general_contract": "contract",
}

KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "delivery_liability": ("交付", "验收", "交期", "交货", "物流", "运输", "到货"),
    "payment_risk": ("付款", "价格", "付款条件", "预付款", "发票", "付款期限", "账期"),
    "breach_liability": ("违约", "赔偿", "责任", "违约金", "损失", "解除"),
    "confidentiality": ("保密", "商业秘密", "保密义务", "保密信息"),
    "intellectual_property": ("知识产权", "著作权", "商标", "专利", "许可", "所有权"),
    "dispute_resolution": ("管辖", "仲裁", "争议", "诉讼", "法院"),
    "data_compliance": ("数据", "个人信息", "隐私", "gdp", "网络安全", "个人信息保护", "数据合规"),
    "employment": ("劳动", "员工", "雇佣", "社保", "工资", "劳动合同", "竞业"),
}


class ReviewPlan(BaseModel):
    dimension: str = "general_contract"
    label: str = "通用合同风险"
    legal_domain: str = "contract"
    reason: str = "未识别到明确关键词，按通用合同风险处理。"
    matched_keywords: list[str] = []


class ReviewDimensionPlanner:
    """Selects a review dimension from the user question using keyword rules."""

    def plan(
        self,
        question: str,
        preferred_dimension: str | None = None,
    ) -> ReviewPlan:
        normalized = (question or "").lower()
        if preferred_dimension and preferred_dimension in REVIEW_DIMENSIONS:
            return self._build(
                preferred_dimension,
                f"用户在界面中指定了 {DIMENSION_LABELS[preferred_dimension]} 审查维度。",
            )

        best: tuple[int, str, list[str]] = (0, "general_contract", [])
        for dimension, keywords in KEYWORD_RULES.items():
            matched = [keyword for keyword in keywords if re.search(re.escape(keyword), normalized)]
            if len(matched) > best[0]:
                best = (len(matched), dimension, matched)
        if best[0] == 0:
            return ReviewPlan()
        dimension = best[1]
        return self._build(
            dimension,
            f"根据问题命中关键词：{', '.join(best[2])}。",
            matched=best[2],
        )

    @staticmethod
    def _build(dimension: str, reason: str, matched: list[str] | None = None) -> ReviewPlan:
        return ReviewPlan(
            dimension=dimension,
            label=DIMENSION_LABELS.get(dimension, dimension),
            legal_domain=DIMENSION_DOMAIN.get(dimension, "contract"),
            reason=reason,
            matched_keywords=matched or [],
        )
