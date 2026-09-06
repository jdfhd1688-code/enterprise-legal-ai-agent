"""Prompt templates for the optional real-LLM path."""

SYSTEM_PROMPT = """你是企业合同风险初筛助手。
你只输出一个 JSON 对象，不输出解释。
所有法律依据必须来自下方给定的“知识库片段”，禁止编造法条、案例或来源。
来源必须以 DEMO/SAMPLE 标识，且不能冒充正式法律意见。
风险输出必须是辅助分析，不是律师意见。
"""


def build_analysis_user_prompt(
    question: str,
    contract_sections: list[str],
    knowledge_hits: list[str],
    review_dimension: str = "general_contract",
) -> str:
    section_text = "\n\n".join(f"[{idx}] {text[:900]}" for idx, text in enumerate(contract_sections, 1))
    kb_text = "\n\n".join(f"来源片段 {idx}：{text[:1200]}" for idx, text in enumerate(knowledge_hits, 1))
    return f"""用户问题：{question}
审查维度：{review_dimension}

合同原文切分片段：
{section_text}

已检索知识库片段（只能引用这些）：
{kb_text or "无"}

请输出 RiskAnalysis JSON：
task_id, risk_level(low/medium/high), legal_domain, confidence(0~1), summary,
findings[]（每个包含 clause_id, risk_type, severity, issue, contract_evidence,
legal_basis[]，其中每项含 title, article_no, source, effective_date, is_demo_sample；
没有真实依据时 legal_basis 为空数组）, requires_human_review, review_reason, generated_at。
"""

REPAIR_PROMPT = """请修复以下 JSON，使其符合 schema，并只输出修复后的 JSON。
原因：{error}
输入：{payload}
"""

REPORT_INTRO = "AI 辅助合同风险初筛报告"
DISCLAIMER = (
    "重要提示：本报告由 AI/规则引擎自动生成，仅用于演示和初步筛查，"
    "不构成法律意见，也不能替代专业律师审查。报告中的知识库引用均为 "
    "DEMO/SAMPLE 演示数据，不代表真实法律依据。"
)
