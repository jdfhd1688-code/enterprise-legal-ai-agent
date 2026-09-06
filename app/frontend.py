"""Enterprise Legal AI Agent - productised Streamlit workbench.

Run from the project root:
    streamlit run app/frontend.py
"""

from __future__ import annotations

import html
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app.agent.review_planner import DIMENSION_LABELS, REVIEW_DIMENSIONS
from app.schemas.risk import ReviewDecision, Severity
from app.schemas.task import TaskRecord
from app.services.analysis_service import AnalysisService


@st.cache_resource(show_spinner=False)
def get_service() -> AnalysisService:
    return AnalysisService()


PAGE_LABELS = {
    "dashboard": "工作台总览",
    "review": "合同审查",
    "human_review": "人工复核",
    "reports": "报告中心",
}

STATUS_LABELS = {
    "submitted": "已提交",
    "parsing": "解析中",
    "chunking": "切分中",
    "retrieving": "检索中",
    "analyzing": "分析中",
    "validating": "校验中",
    "routing": "路由中",
    "awaiting_review": "待复核",
    "report_ready": "报告已生成",
    "reviewed": "已复核",
    "failed": "失败",
}


def apply_theme() -> None:
    st.markdown(
        """<style>
        :root { color-scheme: light; }
        .stApp { background: #f6f8fb; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e5e9f0;
        }
        .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }
        .top-header {
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .top-header h1 {
            font-size: 1.7rem; font-weight: 700; letter-spacing: 0;
            color: #111827; margin: 0;
        }
        .top-header .subtitle { color: #64748b; font-size: 0.95rem; }
        .mode-pill {
            display: inline-block; background: #eef2ff; color: #3730a3;
            border: 1px solid #c7d2fe; border-radius: 999px;
            padding: 0.2rem 0.75rem; font-size: 0.78rem; font-weight: 600;
        }
        .capability-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; }
        .capability {
            background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
            padding: 0.9rem 1rem;
        }
        .capability .k { color: #2563eb; font-weight: 700; font-size: 0.9rem; }
        .capability .d { color: #64748b; font-size: 0.8rem; margin-top: 0.2rem; }
        .finding-card {
            border-radius: 8px; border: 1px solid #e2e8f0;
            border-left: 4px solid #94a3b8; background: #ffffff;
            padding: 1rem 1.1rem; margin: 0.7rem 0;
        }
        .finding-card.high { border-left-color: #dc2626; }
        .finding-card.medium { border-left-color: #f59e0b; }
        .finding-card.low { border-left-color: #16a34a; }
        .finding-title { font-size: 1rem; font-weight: 700; color: #0f172a; }
        .evidence-block {
            background: #f8fafc; border: 1px solid #eef2f7; border-radius: 6px;
            padding: 0.6rem 0.75rem; font-size: 0.85rem; color: #334155;
        }
        .meta-chip {
            display: inline-block; background: #f1f5f9; color: #475569;
            border-radius: 5px; padding: 0.1rem 0.45rem;
            margin-right: 0.3rem; font-size: 0.75rem;
        }
        .badge {
            display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
            font-size: 0.75rem; font-weight: 600;
        }
        .badge.high { background: #fee2e2; color: #b91c1c; }
        .badge.medium { background: #fef3c7; color: #b45309; }
        .badge.low { background: #dcfce7; color: #15803d; }
        .badge.neutral { background: #e2e8f0; color: #334155; }
        .badge.warn { background: #ede9fe; color: #6d28d9; }
        h2.section-title { font-size: 1.1rem; font-weight: 700; margin: 1.3rem 0 0.4rem; }
        .kpi-number { font-size: 1.55rem; font-weight: 800; color: #0f172a; }
        .kpi-label { color: #64748b; font-size: 0.82rem; }
        @media (max-width: 900px) {
            .capability-grid { grid-template-columns: 1fr 1fr; }
        }
        </style>""",
        unsafe_allow_html=True,
    )


def top_bar(service: AnalysisService, page_label: str) -> None:
    settings = service.settings
    mode_class = "neutral" if settings.demo_mode else "low"
    mode_text = "DEMO MODE" if settings.demo_mode else "REAL LLM"
    st.markdown(
        f"""
        <div class="top-header">
          <div>
            <h1>Enterprise Legal AI Agent</h1>
            <div class="subtitle">企业法务 AI 审查工作台 · {html.escape(page_label)}</div>
          </div>
          <div><span class="badge {mode_class}">{html.escape(mode_text)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("AI 仅提供辅助分析，不构成正式法律意见；本页展示的法规引用均为 DEMO/SAMPLE 演示数据。")


def status_badge(status: str) -> str:
    label = STATUS_LABELS.get(status, status)
    css = {"awaiting_review": "warn", "failed": "high", "reviewed": "low", "report_ready": "low"}.get(
        status, "neutral"
    )
    return f'<span class="badge {css}">{html.escape(label)}</span>'


def risk_badge(level: str) -> str:
    return f'<span class="badge {level}">{html.escape(level.upper())}</span>'


def escape_html(text: str) -> str:
    return html.escape(str(text or ""))


def task_meta(task: TaskRecord) -> dict:
    risk = task.risk
    return {
        "task_id": task.task_id,
        "file": task.original_filename,
        "status": STATUS_LABELS.get(task.status.value, task.status.value),
        "risk_level": risk.risk_level.value if risk else "-",
        "confidence": round(risk.confidence, 2) if risk else None,
        "findings": len(risk.findings) if risk else 0,
        "review_dimension": DIMENSION_LABELS.get(task.review_dimension, task.review_dimension),
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def capability_cards() -> None:
    cards = [
        ("合同解析", "PDF / TXT / DOCX"),
        ("法规检索", "Metadata filter + DEMO KB"),
        ("风险分级", "Structured Risk JSON"),
        ("人工复核", "Human-in-the-loop"),
    ]
    html_cards = "".join(
        f'<div class="capability"><div class="k">{escape_html(k)}</div>'
        f'<div class="d">{escape_html(d)}</div></div>'
        for k, d in cards
    )
    st.markdown(f'<div class="capability-grid">{html_cards}</div>', unsafe_allow_html=True)


def dashboard_page(service: AnalysisService) -> None:
    tasks = service.list_tasks()
    risks = [task.risk for task in tasks if task.risk]
    high_count = sum(1 for task in tasks if task.risk and task.risk.risk_level.value == "high")
    review_count = sum(1 for task in tasks if task.status.value == "awaiting_review")
    avg_confidence = round(sum(risk.confidence for risk in risks) / len(risks), 2) if risks else 0.0

    cols = st.columns(4)
    cols[0].metric("今日审查合同", len(tasks))
    cols[1].metric("高风险任务", high_count)
    cols[2].metric("待人工复核", review_count)
    cols[3].metric("平均置信度", avg_confidence)

    col_left, col_right = st.columns([2, 1], gap="large")
    with col_left:
        st.markdown('<h2 class="section-title">最近审查任务</h2>', unsafe_allow_html=True)
        if tasks:
            frame = pd.DataFrame([task_meta(task) for task in tasks[:10]])
            st.dataframe(frame, width="stretch", hide_index=True)
        else:
            st.info("还没有审查任务。进入“合同审查”上传合同或使用内置示例合同。")
    with col_right:
        st.markdown('<h2 class="section-title">风险类型分布</h2>', unsafe_allow_html=True)
        counter = Counter(finding.risk_type for task in tasks if task.risk for finding in task.risk.findings)
        if counter:
            st.bar_chart(pd.Series(counter, name="count"))
        else:
            st.caption("暂无风险类型数据")


def render_audit(task: TaskRecord) -> None:
    with st.expander("审计记录 / 处理轨迹", expanded=False):
        if task.audit_events:
            for event in task.audit_events:
                st.markdown(
                    f"`{event.event_type}` · {event.actor} · "
                    f"{event.timestamp.strftime('%H:%M:%S')} — {event.detail}"
                )
        else:
            for event in task.events:
                st.markdown(f"`{event.stage}` — {event.message}")


def render_technical_details(task: TaskRecord) -> None:
    with st.expander("高级信息 / 技术细节", expanded=False):
        st.markdown("**Workflow route**")
        st.write({"route": task.route, "route_reason": task.route_reason or task.risk.review_reason if task.risk else None})
        st.markdown("**Agent 执行轨迹**")
        for event in task.events:
            st.markdown(f"- `{event.stage}` {event.message}")
        if task.retrieval.hits:
            st.markdown("**Retrieval hits / 法规命中**")
            for hit in task.retrieval.hits:
                st.markdown(
                    f"- **{escape_html(hit.chunk.title)}** · {escape_html(hit.chunk.article_no)} · "
                    f"相似度 {hit.score:.3f} · 状态 {escape_html(hit.validity_status)} · "
                    f"匹配原因 {escape_html(hit.match_reason)}"
                )
                st.json(hit.metadata)
        else:
            st.markdown("**Retrieval hits / 法规命中**：无")
        if task.retrieval.mcp_calls:
            st.markdown("**MCP mock 调用记录**")
            st.json(task.retrieval.mcp_calls)
        if task.risk:
            st.markdown("**Risk JSON**")
            st.json(task.risk.model_dump(mode="json"))


def render_findings(task: TaskRecord) -> None:
    if not task.risk:
        return
    if not task.risk.findings:
        st.markdown("未检出符合规则的风险项。", unsafe_allow_html=True)
        return
    for finding in task.risk.findings:
        css = finding.severity.value
        basis_html = ""
        if finding.legal_basis:
            basis_html = "<div style='margin-top:0.5rem'><strong>法律依据（DEMO/SAMPLE）</strong></div>"
            for basis in finding.legal_basis:
                basis_html += (
                    f"<div class='meta-chip'>状态:{escape_html(basis.status)}</div>"
                    f"<div class='meta-chip'>辖区:{escape_html(basis.jurisdiction)}</div>"
                    f"<div class='meta-chip'>生效:{escape_html(basis.effective_date or 'unknown')}</div>"
                    f"<div class='meta-chip'>失效:{escape_html(basis.expiry_date or 'none')}</div>"
                    f"<div class='meta-chip'>原因:{escape_html(basis.match_reason)}</div>"
                    f"<div style='font-size:0.8rem;margin-top:0.2rem'>"
                    f"{escape_html(basis.title)}｜{escape_html(basis.article_no)}｜{escape_html(basis.source)}</div>"
                )
        evidence_html = f"<div class='evidence-block'>{escape_html(finding.contract_evidence)}</div>"
        st.markdown(
            f"""
            <div class="finding-card {css}">
              <div class="finding-title">{escape_html(finding.clause_id)} · {escape_html(finding.issue)}</div>
              <div style="margin:0.35rem 0">
                {risk_badge(finding.severity.value)} <span class="meta-chip">{escape_html(finding.risk_type)}</span>
                <span class="meta-chip">证据充分:{str(finding.evidence_sufficient).lower()}</span>
              </div>
              <div style="font-size:0.8rem;color:#64748b;margin-bottom:0.3rem">合同证据</div>
              {evidence_html}
              <div style="margin-top:0.55rem"><strong>处理建议</strong><br/>{escape_html(finding.recommendation)}</div>
              {basis_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_result(task: TaskRecord) -> None:
    risk = task.risk
    st.markdown("---")
    st.markdown('<h2 class="section-title">审查结果摘要</h2>', unsafe_allow_html=True)
    if task.error:
        st.error(task.error)
        return
    if risk:
        m = st.columns(6)
        m[0].metric("风险等级", risk.risk_level.value.upper())
        m[1].metric("置信度", f"{risk.confidence:.2f}")
        m[2].metric("法律领域", risk.legal_domain)
        m[3].metric("审查维度", DIMENSION_LABELS.get(risk.review_dimension, risk.review_dimension))
        m[4].metric("发现项", len(risk.findings))
        m[5].metric("证据充分", str(risk.evidence_sufficient).lower())
        st.markdown(f"**{escape_html(risk.summary)}**")
        if task.route == "human_review" or task.status.value == "awaiting_review":
            st.warning(task.route_reason or risk.review_reason or "该任务需要人工复核。")
        elif task.route:
            st.caption(f"Workflow route：{task.route} · {task.route_reason or ''}")

    render_findings(task)
    render_technical_details(task)
    render_audit(task)

    if task.report_markdown:
        st.download_button(
            "下载 Markdown 报告",
            data=task.report_markdown,
            file_name=f"{task.task_id}_report.md",
            mime="text/markdown",
            key=f"download_{task.task_id}",
        )
    if task.status.value == "awaiting_review":
        if st.button("进入人工复核", type="primary", key=f"goto_{task.task_id}"):
            st.session_state["page"] = "human_review"
            st.rerun()


def review_page(service: AnalysisService) -> None:
    st.markdown('<h2 class="section-title">合同智能审查</h2>', unsafe_allow_html=True)
    capability_cards()
    col_form, col_result = st.columns([1, 1], gap="large")
    with col_form:
        st.markdown('<h2 class="section-title">新建审查任务</h2>', unsafe_allow_html=True)
        use_sample = st.toggle("使用内置 DEMO/SAMPLE 示例合同", value=True)
        sample_kind = st.radio(
            "示例合同",
            ["高风险合同（进入人工复核）", "低风险合同（自动生成报告）"],
            horizontal=True,
        )
        uploaded = st.file_uploader(
            "上传合同（PDF / TXT / DOCX）",
            type=["pdf", "txt", "docx"],
            disabled=use_sample,
            key="contract_uploader",
        )
        dimension_options = ["auto"] + list(REVIEW_DIMENSIONS)
        dimension_labels = {"auto": "自动识别"} | {
            dim: DIMENSION_LABELS[dim] for dim in REVIEW_DIMENSIONS
        }
        dimension = st.selectbox(
            "审查维度",
            dimension_options,
            format_func=lambda item: dimension_labels[item],
            help="选择后系统将按该维度进行规则分析与知识库过滤。",
        )
        question = st.text_area(
            "审查问题",
            value="这份合同有哪些高风险条款？",
            height=92,
            help="用于 Review Dimension Planner 与风险分析上下文。",
        )
        if st.button("开始智能审查", type="primary", width="stretch"):
            try:
                if use_sample:
                    filename = (
                        "sample_contract_high_risk.pdf"
                        if sample_kind.startswith("高风险")
                        else "sample_contract_low_risk.pdf"
                    )
                    data = (service.settings.contract_dir / filename).read_bytes()
                elif uploaded:
                    filename, data = uploaded.name, uploaded.getvalue()
                else:
                    st.error("请上传合同或启用示例合同。")
                    return
                with st.spinner("Agent 正在执行解析、切分、检索与风险分析..."):
                    task = service.create_task(
                        filename,
                        data,
                        question,
                        review_dimension=None if dimension == "auto" else dimension,
                    )
                st.session_state["last_task_id"] = task.task_id
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    with col_result:
        task_id = st.session_state.get("last_task_id")
        if task_id:
            try:
                render_result(service.get_task(task_id))
            except Exception:  # noqa: BLE001
                st.info("选择任务后此处显示审查结果。")


def human_review_page(service: AnalysisService) -> None:
    st.markdown('<h2 class="section-title">待处理复核队列</h2>', unsafe_allow_html=True)
    tasks = service.list_review_tasks()
    if not tasks:
        st.success("当前没有待复核任务。")
        return
    for task in tasks:
        with st.container(border=True):
            meta = task_meta(task)
            st.markdown(
                f"**{escape_html(task.task_id)}** · {escape_html(task.original_filename)}"
                f" · {status_badge(task.status.value)} · {risk_badge(meta['risk_level'])}"
            )
            st.caption(
                f"创建 {task.created_at.strftime('%Y-%m-%d %H:%M')} · "
                f"置信度 {meta['confidence']} · 发现 {meta['findings']} 项 · "
                f"维度 {meta['review_dimension']}"
            )
            render_audit(task)
            modifications: dict[str, dict[str, str]] = {}
            for finding in (task.risk.findings if task.risk else []):
                st.markdown(f"**原始 AI 建议 · {finding.clause_id}**")
                st.write(finding.issue)
                st.write(f"合同证据：{finding.contract_evidence}")
                st.write(f"AI 建议：{finding.recommendation}")
                issue = st.text_area(
                    "人工修改：问题描述",
                    value=finding.issue,
                    key=f"rvi_{task.task_id}_{finding.clause_id}",
                )
                recommendation = st.text_area(
                    "人工修改：处理建议",
                    value=finding.recommendation,
                    key=f"rvr_{task.task_id}_{finding.clause_id}",
                )
                severity = st.selectbox(
                    "人工修改：严重度",
                    [item.value for item in Severity],
                    index=[item.value for item in Severity].index(finding.severity.value),
                    key=f"rvs_{task.task_id}_{finding.clause_id}",
                )
                modifications[finding.clause_id] = {
                    "issue": issue,
                    "recommendation": recommendation,
                    "severity": severity,
                }
            decision = st.radio(
                "最终决策",
                [item.value for item in ReviewDecision],
                format_func=lambda value: {
                    "approve": "通过",
                    "request_changes": "要求修改",
                    "reject": "不通过",
                }[value],
                key=f"decision_{task.task_id}",
                horizontal=True,
            )
            comment = st.text_area("复核意见", key=f"comment_{task.task_id}")
            if st.button("保存复核结果", type="primary", key=f"save_{task.task_id}"):
                try:
                    service.submit_review(
                        task.task_id,
                        ReviewDecision(decision),
                        comment=comment,
                        modifications=modifications,
                        reviewer="demo-reviewer",
                    )
                    st.success("复核结果与审计记录已保存。")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))


def reports_page(service: AnalysisService) -> None:
    st.markdown('<h2 class="section-title">报告中心</h2>', unsafe_allow_html=True)
    tasks = [task for task in service.list_tasks() if task.report_markdown]
    if not tasks:
        st.info("尚未生成报告。请先运行一次低风险审查或完成一次人工复核。")
        return
    options = {
        task.task_id: f"{task.task_id}｜{task.original_filename}｜{STATUS_LABELS.get(task.status.value, task.status.value)}"
        for task in tasks
    }
    selected = st.selectbox("选择报告", list(options.keys()), format_func=options.get)
    task = service.get_task(selected)
    meta = task_meta(task)
    st.markdown(
        f"**{escape_html(task.task_id)}** · {risk_badge(meta['risk_level'])} · "
        f"置信度 {meta['confidence']} · 审查维度 {meta['review_dimension']}"
    )
    if task.risk and task.risk.retrieval_summary:
        st.caption(task.risk.retrieval_summary)
    st.markdown(task.report_markdown)
    st.download_button(
        "下载 Markdown 报告",
        data=task.report_markdown,
        file_name=f"{task.task_id}_report.md",
        mime="text/markdown",
        key=f"download_report_{task.task_id}",
    )
    if task.review:
        st.markdown("**人工复核结果**")
        st.json(task.review.model_dump(mode="json"))
        if task.original_ai_result and task.reviewed_result:
            st.markdown("**AI 原始建议 vs 复核结果对比**")
            st.json(
                {
                    "original_risk_level": task.original_ai_result.risk_level.value,
                    "final_risk_level": task.reviewed_result.risk_level.value,
                    "original_summary": task.original_ai_result.summary,
                    "final_summary": task.reviewed_result.summary,
                }
            )


def main() -> None:
    st.set_page_config(page_title="Enterprise Legal AI Agent", layout="wide")
    apply_theme()
    service = get_service()
    page = st.session_state.get("page", "dashboard")
    if page not in PAGE_LABELS:
        page = "dashboard"
    with st.sidebar:
        st.markdown("### Legal Workbench")
        selected = st.radio(
            "导航",
            list(PAGE_LABELS.keys()),
            format_func=PAGE_LABELS.get,
            index=list(PAGE_LABELS.keys()).index(page),
            label_visibility="collapsed",
        )
        st.session_state["page"] = selected
        st.markdown("---")
        st.caption("MVP v0.2 · Streamlit + Pydantic + RAG + Workflow + HITL")

    top_bar(service, PAGE_LABELS[selected])
    if selected == "dashboard":
        dashboard_page(service)
    elif selected == "human_review":
        human_review_page(service)
    elif selected == "reports":
        reports_page(service)
    else:
        review_page(service)


if __name__ == "__main__":
    main()
