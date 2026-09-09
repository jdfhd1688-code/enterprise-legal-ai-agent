"""Explainable legal-search query construction."""

from __future__ import annotations

from dataclasses import dataclass, field


DIMENSION_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "delivery_liability": ("交付", "验收", "迟延履行"),
    "payment_risk": ("付款条件", "付款期限", "逾期付款"),
    "breach_liability": ("违约责任", "损害赔偿", "合同履行"),
    "confidentiality": ("保密义务", "商业秘密", "保密期限"),
    "intellectual_property": ("知识产权归属", "许可范围", "成果权利"),
    "dispute_resolution": ("争议解决", "管辖法院", "仲裁"),
    "data_compliance": ("个人信息", "数据处理", "安全义务"),
    "employment": ("劳动合同", "用工", "竞业限制"),
    "general_contract": ("合同履行", "违约责任", "风险分配"),
}


@dataclass(frozen=True)
class LegalQuery:
    query: str
    dimension: str
    jurisdiction: str
    metadata_filters: dict[str, object] = field(default_factory=dict)
    explanation: str = ""


class LegalRetrievalQueryBuilder:
    """Build a compact query from intent, dimension and contract evidence."""

    def build(
        self,
        question: str,
        contract_text: str,
        dimension: str,
        jurisdiction: str = "中国大陆",
    ) -> LegalQuery:
        expansions = DIMENSION_EXPANSIONS.get(dimension, DIMENSION_EXPANSIONS["general_contract"])
        excerpt = " ".join(contract_text.replace("\n", " ").split())[:260]
        parts = [question.strip(), *expansions, excerpt]
        query = " ".join(dict.fromkeys(part for part in parts if part))
        filters: dict[str, object] = {
            "jurisdiction": jurisdiction,
            "status": ["current", "effective"],
            "source_type": "demo_sample",
        }
        return LegalQuery(
            query=query,
            dimension=dimension,
            jurisdiction=jurisdiction,
            metadata_filters=filters,
            explanation=f"根据 {dimension} 审查维度扩展：{', '.join(expansions)}；辖区为 DEMO 默认值，需用户确认。",
        )
