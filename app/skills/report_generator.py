"""Final report generation skill."""

from __future__ import annotations

from datetime import datetime, timezone

from app.agent.prompts import DISCLAIMER, REPORT_INTRO
from app.schemas.risk import RiskAnalysis, ReviewOutcome


class ReportGenerator:
    """Builds an auditable Markdown report from validated risk data."""

    def generate(
        self,
        task_id: str,
        filename: str,
        question: str,
        risk: RiskAnalysis,
        review: ReviewOutcome | None = None,
        evidence_notes: list[str] | None = None,
    ) -> str:
        evidence_notes = evidence_notes or []
        lines: list[str] = [
            f"# {REPORT_INTRO}",
            "",
            f"**任务：** {task_id}",
            f"**合同文件：** {filename}",
            f"**用户问题：** {question or '通用风险初筛'}",
            f"**风险等级：** {risk.risk_level.upper()}",
            f"**审查维度：** {risk.review_dimension}",
            f"**法律领域：** {risk.legal_domain}",
            f"**置信度：** {risk.confidence:.2f}",
            f"**证据充分：** {str(risk.evidence_sufficient).lower()}",
            f"**检索摘要：** {risk.retrieval_summary or '未提供'}",
            f"**生成时间：** {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            f"**分析引擎：** {risk.analysis_mode} ({risk.model_version})",
            "",
            f"> {DISCLAIMER}",
            "",
            "## 风险摘要",
            "",
            risk.summary,
        ]
        if evidence_notes:
            lines.extend(["", "## 证据说明", ""])
            lines.extend(f"- {note}" for note in evidence_notes[:12])

        if risk.findings:
            lines.extend(["", "## 风险发现", ""])
            for index, finding in enumerate(risk.findings, 1):
                lines.extend(
                    [
                        f"### {index}. {finding.clause_id} - {finding.issue}",
                        "",
                        f"- 风险类型：`{finding.risk_type}`",
                        f"- 严重度：`{finding.severity.value}`",
                        "",
                        "**合同证据**",
                        "",
                        finding.contract_evidence,
                        "",
                        "**建议**",
                        "",
                        finding.recommendation,
                    ]
                )
                if finding.legal_basis:
                    lines.extend(["", "**知识库引用（DEMO/SAMPLE）**", ""])
                    for basis in finding.legal_basis:
                        lines.append(
                            f"- {basis.title}｜{basis.article_no}｜来源：{basis.source}"
                            f"｜状态：{basis.status}｜辖区：{basis.jurisdiction}"
                            f"｜匹配原因：{basis.match_reason}"
                            f"｜生效：{basis.effective_date or 'unknown'}"
                            f"｜失效：{basis.expiry_date or 'none'}"
                            f"{'（DEMO/SAMPLE）' if basis.is_demo_sample else ''}"
                        )
                lines.append("")
        else:
            lines.extend(["", "## 风险发现", "", "未检出符合规则的风险项。"])

        if review is not None:
            lines.extend(
                [
                    "",
                    "## 人工复核结果",
                    "",
                    f"- 复核决定：{review.decision.value}",
                    f"- 复核人：{review.reviewer}",
                    f"- 复核时间：{review.reviewed_at.isoformat(timespec='seconds')}",
                    f"- 复核意见：{review.comment or '无'}",
                ]
            )
            if review.final_summary:
                lines.extend(["", f"**最终摘要：** {review.final_summary}"])
        return "\n".join(lines).strip() + "\n"


def build_risk_summary(risk: RiskAnalysis) -> str:
    """Short human-readable overview used in the UI."""
    findings = len(risk.findings)
    return f"{risk.risk_level.upper()}｜置信度 {risk.confidence:.2f}｜发现 {findings} 个风险项"
