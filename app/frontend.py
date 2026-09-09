"""Enterprise Legal AI Agent - productised Streamlit workbench."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.agent.review_planner import DIMENSION_LABELS, REVIEW_DIMENSIONS
from app.schemas.risk import ReviewDecision, Severity
from app.review_experience import render_review_experience
from app.schemas.task import TaskRecord
from app.services.analysis_service import AnalysisService
from app.styles import APP_CSS
from app.ui_components import badge, choice_copy, esc, metric_cards, page_header, section, step_header, workflow_steps


@st.cache_resource(show_spinner=False)
def get_service() -> AnalysisService:
    return AnalysisService()


NAV_ITEMS = {
    "dashboard": "工作台",
    "review": "新建审查",
    "human_review": "待人工复核",
    "reports": "报告中心",
    "history": "审查记录",
}
STATUS_LABELS = {
    "submitted": "已提交", "parsing": "解析中", "chunking": "切分中", "retrieving": "检索中",
    "analyzing": "分析中", "validating": "校验中", "routing": "路由中", "awaiting_review": "待复核",
    "report_ready": "报告已生成", "reviewed": "已复核", "failed": "失败", "cancelled": "已取消",
}
RISK_LABELS = {"high": "高风险", "medium": "中风险", "low": "低风险", "-": "待分析"}
REVIEW_DIMENSIONS_UI = [item for item in REVIEW_DIMENSIONS if item != "general_contract"]


def go(page: str, task_id: str | None = None) -> None:
    st.session_state["page"] = page
    if task_id:
        st.session_state["selected_task_id"] = task_id


def format_time(value: datetime | None) -> str:
    if not value:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def risk_html(level: str) -> str:
    kind = level if level in {"high", "medium", "low"} else "neutral"
    return badge(RISK_LABELS.get(level, level), kind)


def status_html(status: str) -> str:
    kind = "review" if status == "awaiting_review" else "low" if status in {"reviewed", "report_ready"} else "neutral"
    return badge(STATUS_LABELS.get(status, status), kind)


def task_level(task: TaskRecord) -> str:
    return task.risk.risk_level.value if task.risk else "-"


def task_dimension(task: TaskRecord) -> str:
    return DIMENSION_LABELS.get(task.review_dimension, task.review_dimension)


def render_sidebar(service: AnalysisService) -> None:
    page = st.session_state.get("page", "dashboard")
    with st.sidebar:
        st.markdown(
            """<div class="sidebar-brand"><div class="sidebar-brand-row"><div class="sidebar-mark" aria-label="獬豸品牌标记">
            <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M11 31c2-9 9-14 18-13 7 1 12 5 14 12l-5 2-2 8H15zM18 19c1-8 5-13 12-14 6-1 10 2 12 7l-7 2-2 5M29 6l6-5-2 8"/></svg></div>
            <div><div class="sidebar-name">Enterprise Legal AI</div>
            <div class="sidebar-sub">企业法务智能工作台</div></div></div></div>
            <div class="nav-section-label">主工作区</div>""",
            unsafe_allow_html=True,
        )
        for key, label in NAV_ITEMS.items():
            if st.button(label, key=f"nav_{key}", type="primary" if page == key else "secondary", width="stretch"):
                go(key)
                st.rerun()
        mode = "DEMO MODE" if service.settings.demo_mode else "REAL LLM"
        st.markdown(
            f'<div class="sidebar-footer"><div class="sidebar-status"><span></span>{esc(mode)}</div>'
            '<div class="sidebar-footer-title">安全与合规提示</div><div>AI 辅助审查结果不构成正式法律意见。</div>'
            '<div class="sidebar-version">獬豸递卷 · 皋陶审契</div></div>',
            unsafe_allow_html=True,
        )


def dashboard_page(service: AnalysisService) -> None:
    tasks = service.list_tasks()
    live = bool(tasks)
    high_count = sum(task_level(task) == "high" for task in tasks)
    review_count = sum(task.status.value == "awaiting_review" for task in tasks)
    st.markdown('<div class="dashboard-page-marker"></div>', unsafe_allow_html=True)
    page_header(
        "工作台", "企业合同智能审查与风险复核工作台",
        "统一管理合同风险识别、法规依据、法务复核与报告交付。", service.settings.demo_mode,
    )
    hero_main, hero_action = st.columns([2.15, 1], gap="large", vertical_alignment="top")
    with hero_main:
        st.markdown(
            '<div class="dashboard-hero"><div class="hero-kicker">LEGAL RISK CONTROL CENTER</div>'
            '<div class="hero-title">让每一份合同风险<br/>都有依据、有结论、有追踪</div>'
            '<div class="hero-copy">从合同上传到风险分级、人工复核和报告归档，在一个工作台内闭环完成。</div>'
            '<div class="hero-flow"><span>合同解析</span><i>→</i><span>智能审查</span><i>→</i><span>法务复核</span><i>→</i><span>报告归档</span></div></div>',
            unsafe_allow_html=True,
        )
    with hero_action:
        with st.container(border=True):
            st.markdown(
                '<div class="quick-card-marker"></div><div class="quick-kicker">QUICK START</div>'
                '<div class="quick-title">发起新的合同审查</div>'
                '<div class="quick-copy">上传企业合同，或使用脱敏示例体验完整风险审查闭环。</div>',
                unsafe_allow_html=True,
            )
            if st.button("＋ 新建合同审查", type="primary", width="stretch", key="dashboard_new"):
                go("review")
                st.rerun()
            st.caption("预计用时 2 分钟 · 全程保留审计记录")
    section("运营概览", "基于本地任务记录" if live else "数据仅用于界面演示", demo=not live)
    metric_cards([
        ("本周审查", str(len(tasks) if live else 18), "本地任务记录" if live else "较上周 +12%"),
        ("高风险任务", str(high_count if live else 4), "需优先关注"),
        ("待人工复核", str(review_count if live else 3), "进入法务复核队列"),
        ("平均审查耗时", "< 2分钟" if live else "1分42秒", "端到端处理耗时"),
    ])
    if tasks:
        recent = [(t.original_filename, format_time(t.created_at), risk_html(task_level(t)), status_html(t.status.value)) for t in tasks[:6]]
    else:
        recent = [
            ("采购框架协议_华东区.pdf", "2026-09-08 09:32", risk_html("high"), status_html("awaiting_review")),
            ("软件服务合同_V3.docx", "2026-09-08 08:47", risk_html("medium"), status_html("report_ready")),
            ("保密协议_供应商版.pdf", "2026-09-07 17:18", risk_html("low"), status_html("report_ready")),
        ]
    recent_rows = "".join(f"<tr><td class='primary-cell'>{esc(n)}</td><td>{esc(c)}</td><td>{r}</td><td>{s}</td><td>查看</td></tr>" for n, c, r, s in recent)
    if tasks and any(t.risk and t.risk.findings for t in tasks):
        items = []
        for task in [t for t in tasks if t.risk and t.risk.findings][:4]:
            finding = task.risk.findings[0]
            items.append((task.original_filename, finding.risk_type, finding.severity.value, not finding.evidence_sufficient or task.status.value == "awaiting_review"))
    else:
        items = [("采购框架协议.pdf", "交付责任", "high", True), ("软件服务合同.docx", "数据合规", "medium", True), ("渠道合作协议.pdf", "争议解决", "medium", False)]
    risk_rows = "".join(f"<tr><td class='primary-cell'>{esc(n)}</td><td>{esc(k)}</td><td>{risk_html(l)}</td><td>{'是' if rv else '否'}</td></tr>" for n, k, l, rv in items)
    demo_marker = '<span class="demo-tag">演示数据</span>' if not live else ""
    st.markdown(
        f"<div class='dashboard-panels'><div><div class='dashboard-panel-head'><strong>最近审查任务 {demo_marker}</strong><span>最近 6 条</span></div>"
        f"<div class='panel'><table class='clean-table'><thead><tr><th>合同名称</th><th>审查时间</th><th>风险等级</th><th>当前状态</th><th></th></tr></thead><tbody>{recent_rows}</tbody></table></div></div>"
        f"<div><div class='dashboard-panel-head'><strong>待处理风险 {demo_marker}</strong><span>优先级排序</span></div>"
        f"<div class='panel'><table class='clean-table'><thead><tr><th>合同</th><th>风险类型</th><th>等级</th><th>人工复核</th></tr></thead><tbody>{risk_rows}</tbody></table></div></div></div>",
        unsafe_allow_html=True,
    )
    section("最近报告", "已生成的审查报告", demo=not live)
    reports = [t for t in tasks if t.report_markdown][:4]
    report_rows = [(t.original_filename, "报告已生成", format_time(t.updated_at)) for t in reports] or [("软件服务合同_V3.docx", "报告已生成", "2026-09-08 08:49"), ("保密协议_供应商版.pdf", "报告已生成", "2026-09-07 17:20")]
    rows = "".join(f"<tr><td class='primary-cell'>{esc(n)}</td><td>{badge(s, 'low')}</td><td>{esc(c)}</td><td>查看报告</td></tr>" for n, s, c in report_rows)
    st.markdown(f"<div class='panel'><table class='clean-table'><thead><tr><th>合同名称</th><th>报告状态</th><th>生成时间</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)


def review_page(service: AnalysisService) -> None:
    st.markdown('<div class="review-page-marker"></div>', unsafe_allow_html=True)
    page_header("新建合同审查", "用三步完成审查配置", "选择合同来源与审查方式，确认后启动智能风险识别。", service.settings.demo_mode)
    workflow_steps(1)
    st.session_state.setdefault("source_mode", None)
    st.session_state.setdefault("sample_kind", "high")
    st.session_state.setdefault("review_mode", "full")
    step_header(1, "选择合同来源")
    upload_col, demo_col = st.columns(2, gap="large")
    with upload_col:
        with st.container(border=True):
            selected = st.session_state.source_mode == "upload"
            st.markdown(f'<div class="choice-card-marker {"selected" if selected else ""}"></div><div class="choice-icon">↑</div>', unsafe_allow_html=True)
            choice_copy("上传合同", "支持 PDF / DOCX / TXT，上传企业合同进行智能审查。")
            st.caption("适合真实合同 · 文件仅在本地处理")
            if st.button("已选择上传合同" if selected else "选择上传合同", type="primary" if selected else "secondary", width="stretch"):
                st.session_state.source_mode = "upload"; st.rerun()
    with demo_col:
        with st.container(border=True):
            selected = st.session_state.source_mode == "demo"
            st.markdown(f'<div class="choice-card-marker {"selected" if selected else ""}"></div><div class="choice-icon">◇</div>', unsafe_allow_html=True)
            choice_copy("体验示例", "使用脱敏示例合同快速体验完整审查流程。")
            st.caption("无需上传 · 约 30 秒完成")
            if st.button("已选择体验示例" if selected else "选择体验示例", type="primary" if selected else "secondary", width="stretch"):
                st.session_state.source_mode = "demo"; st.rerun()
    uploaded = None
    if st.session_state.source_mode == "upload":
        st.markdown('<div class="selection-note">已选择“上传合同”。示例合同选择已隐藏。</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("拖放或选择合同文件", type=["pdf", "docx", "txt"], key="contract_uploader")
    elif st.session_state.source_mode == "demo":
        st.markdown('<div class="selection-note">已选择“体验示例”。上传区域已隐藏。</div>', unsafe_allow_html=True)
        high, low = st.columns(2, gap="large")
        with high:
            choice_copy("高风险示例合同", "包含交付、违约等风险，用于体验人工复核流程。")
            if st.button("使用高风险示例", type="primary" if st.session_state.sample_kind == "high" else "secondary", width="stretch"):
                st.session_state.sample_kind = "high"; st.rerun()
        with low:
            choice_copy("低风险示例合同", "风险条款相对完整，可直接体验报告生成流程。")
            if st.button("使用低风险示例", type="primary" if st.session_state.sample_kind == "low" else "secondary", width="stretch"):
                st.session_state.sample_kind = "low"; st.rerun()
    step_header(2, "选择审查方式")
    full_col, special_col = st.columns(2, gap="large")
    with full_col:
        with st.container(border=True):
            selected = st.session_state.review_mode == "full"
            st.markdown(f'<div class="choice-card-marker {"selected" if selected else ""}"></div><div class="choice-icon">✦</div>', unsafe_allow_html=True)
            choice_copy("智能全面审查", "自动识别付款、责任、解除、续期、知识产权等主要风险。")
            st.caption("推荐 · 自动匹配审查维度")
            if st.button("已选择智能全面审查" if selected else "选择智能全面审查", type="primary" if selected else "secondary", width="stretch"):
                st.session_state.review_mode = "full"; st.rerun()
    with special_col:
        with st.container(border=True):
            selected = st.session_state.review_mode == "special"
            st.markdown(f'<div class="choice-card-marker {"selected" if selected else ""}"></div><div class="choice-icon">◎</div>', unsafe_allow_html=True)
            choice_copy("专项审查", "聚焦指定法律风险，输出更有针对性的风险判断。")
            st.caption("适合重点条款与特定议题")
            if st.button("已选择专项审查" if selected else "选择专项审查", type="primary" if selected else "secondary", width="stretch"):
                st.session_state.review_mode = "special"; st.rerun()
    selected_dimensions: list[str] = []
    if st.session_state.review_mode == "special":
        selected_dimension = st.selectbox(
            "审查维度",
            REVIEW_DIMENSIONS_UI,
            index=None,
            format_func=lambda item: DIMENSION_LABELS[item],
            placeholder="请选择审查维度",
        )
        selected_dimensions = [selected_dimension] if selected_dimension else []
    question = st.text_area("特别关注的问题（可选）", placeholder="例如：请重点审查乙方延期交付时的责任承担。", height=90)
    step_header(3, "审查确认")
    if st.session_state.source_mode == "upload":
        contract_name = uploaded.name if uploaded else "等待上传合同"
    elif st.session_state.source_mode == "demo":
        contract_name = "示例高风险合同" if st.session_state.sample_kind == "high" else "示例低风险合同"
    else:
        contract_name = "尚未选择合同来源"
    method_name = "智能全面审查" if st.session_state.review_mode == "full" else "专项审查"
    dimension_name = "自动识别" if st.session_state.review_mode == "full" else "、".join(DIMENSION_LABELS[i] for i in selected_dimensions) or "等待选择"
    st.markdown(
        f"<div class='confirm-card'><div class='confirm-title'>审查任务确认</div><div class='confirm-grid'>"
        f"<div class='confirm-item'><span>合同</span><strong>{esc(contract_name)}</strong></div><div class='confirm-item'><span>审查方式</span><strong>{esc(method_name)}</strong></div>"
        f"<div class='confirm-item'><span>审查维度</span><strong>{esc(dimension_name)}</strong></div></div><div class='output-list'><strong>预计输出：</strong> 合同风险摘要 · 风险明细 · 合同证据 · 法规依据 · 处理建议 · 人工复核条件</div></div>",
        unsafe_allow_html=True,
    )
    source_ready = st.session_state.source_mode == "demo" or (st.session_state.source_mode == "upload" and uploaded is not None)
    method_ready = st.session_state.review_mode == "full" or bool(selected_dimensions)
    if st.button("开始智能审查", type="primary", width="stretch", disabled=not (source_ready and method_ready)):
        if st.session_state.source_mode == "demo":
            filename = f"sample_contract_{st.session_state.sample_kind}_risk.pdf"
            data = (service.settings.contract_dir / filename).read_bytes()
        else:
            filename, data = uploaded.name, uploaded.getvalue()
        st.session_state["review_request"] = {
            "filename": filename,
            "data": data,
            "question": question,
            "review_dimension": selected_dimensions[0] if selected_dimensions else None,
        }
        st.session_state.pop("process_error", None)
        st.session_state.pop("process_task_id", None)
        go("process")
        st.rerun()


def review_process_page(service: AnalysisService) -> None:
    """Render the dedicated process route; a fragment advances the real workflow."""
    request = st.session_state.get("review_request")
    if not request:
        go("review")
        st.rerun()

    st.markdown('<div class="process-page-marker"></div>', unsafe_allow_html=True)
    review_process_runner(service, request)


@st.fragment(run_every=0.8)
def review_process_runner(service: AnalysisService, request: dict) -> None:
    """Let intake paint once before synchronous workflow callbacks begin."""
    stage_slot = st.empty()
    error = st.session_state.get("process_error")
    if error:
        stage_slot.markdown(render_review_experience("failed", request["filename"]), unsafe_allow_html=True)
        action_a, action_b = st.columns(2)
        if action_a.button("重新开始审查", type="primary", width="stretch"):
            st.session_state.pop("process_error", None)
            st.session_state.pop("process_task_id", None)
            st.rerun()
        if action_b.button("返回工作台", width="stretch"):
            st.session_state.pop("review_request", None)
            st.session_state.pop("process_error", None)
            st.session_state.pop("process_task_id", None)
            go("dashboard")
            st.rerun()
        with st.expander("查看技术详情", expanded=False):
            st.code(str(error))
        return

    status_slot = st.empty()

    prepared_id = st.session_state.get("process_task_id")
    if not prepared_id:
        try:
            prepared = service.prepare_task(
                request["filename"],
                request["data"],
                request["question"],
                review_dimension=request["review_dimension"],
            )
            st.session_state["process_task_id"] = prepared.task_id
            stage_slot.markdown(render_review_experience("received", request["filename"]), unsafe_allow_html=True)
            status_slot.markdown(
                '<div class="process-current"><span></span><div><small>当前处理</small><strong>合同文件已接收。</strong></div></div>',
                unsafe_allow_html=True,
            )
            return
        except Exception as exc:  # noqa: BLE001
            st.session_state["process_error"] = str(exc)
            st.rerun()

    def update_stage(stage: str, message: str) -> None:
        stage_slot.markdown(render_review_experience(stage, request["filename"]), unsafe_allow_html=True)
        status_slot.markdown(
            f'<div class="process-current"><span></span><div><small>当前处理</small><strong>{esc(message)}</strong></div></div>',
            unsafe_allow_html=True,
        )
        time.sleep(0.8 if stage == "completed" else 0.55)

    try:
        task = service.execute_task(
            st.session_state["process_task_id"],
            request["data"],
            on_stage=update_stage,
        )
        if task.error:
            st.session_state["process_error"] = task.error
            st.rerun()
        st.session_state["last_task_id"] = task.task_id
        st.session_state.pop("review_request", None)
        st.session_state.pop("process_task_id", None)
        go("result", task.task_id)
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.session_state["process_error"] = str(exc)
        st.rerun()


def render_result_hero(task: TaskRecord) -> None:
    risk = task.risk
    if not risk:
        return
    manual = sum(not item.evidence_sufficient or item.severity.value == "high" for item in risk.findings)
    values = [("综合风险", RISK_LABELS[risk.risk_level.value]), ("风险发现数量", str(len(risk.findings))), ("建议人工复核数量", str(manual)), ("置信度", f"{risk.confidence:.0%}"), ("审查领域", task_dimension(task))]
    metrics = "".join(f'<div class="result-metric"><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k, v in values)
    st.markdown(
        f"<div class='result-hero'><div class='result-head'><div><div class='result-kicker'>EXECUTIVE SUMMARY</div>"
        f"<div class='result-title'>审查执行摘要</div></div><div class='result-complete'>✓ REVIEW COMPLETE</div></div>"
        f"<div class='result-summary'>{esc(risk.summary)}</div><div class='result-metrics'>{metrics}</div></div>",
        unsafe_allow_html=True,
    )


def render_finding(finding, index: int) -> None:
    basis = finding.legal_basis[0] if finding.legal_basis else None
    basis_text = f"{basis.title} · {basis.article_no} · {basis.source}" if basis else "未检索到可验证的法律依据"
    insufficient = "<div class='insufficient'>依据不足，需要人工复核</div>" if not finding.evidence_sufficient else ""
    st.markdown(
        f"<div class='finding-card {esc(finding.severity.value)}'><div class='finding-top'><div><div class='finding-index'>{index:02d}</div><div class='finding-title'>{esc(finding.issue)}</div></div>{risk_html(finding.severity.value)}</div>"
        f"<div>{badge(finding.risk_type, 'neutral')}</div>{insufficient}<div class='finding-grid'>"
        f"<div class='detail-block'><div class='detail-label'>合同证据 · {esc(finding.evidence_section or finding.clause_id)}</div><div class='detail-text'>{esc(finding.contract_evidence)}</div></div>"
        f"<div class='detail-block'><div class='detail-label'>风险说明</div><div class='detail-text'>{esc(finding.issue)}</div></div>"
        f"<div class='detail-block'><div class='detail-label'>法律依据</div><div class='detail-text'>{esc(basis_text)}</div></div>"
        f"<div class='detail-block'><div class='detail-label'>AI 建议</div><div class='detail-text'>{esc(finding.recommendation)}</div></div></div></div>", unsafe_allow_html=True,
    )
    a, b, _ = st.columns([1, 1.25, 4])
    a.button("查看证据", key=f"evidence_{index}_{finding.clause_id}", width="stretch")
    if b.button("加入人工复核", key=f"manual_{index}_{finding.clause_id}", width="stretch"):
        st.toast("已标记供法务关注；任务路由仍遵循现有工作流规则。")


def technical_details(task: TaskRecord) -> None:
    with st.expander("查看技术处理详情", expanded=False):
        overview_tab, metadata_tab, risk_tab, mcp_tab = st.tabs(
            ["处理概览", "Metadata", "Risk JSON", "MCP Mock Log"]
        )
        with overview_tab:
            st.markdown("#### Review Dimension")
            st.write({"dimension": task.review_dimension, "label": task_dimension(task), "question": task.question})
            st.markdown("#### Retrieval Hits")
            for hit in task.retrieval.hits[:4]:
                st.markdown(f"- **{hit.chunk.title}** · {hit.chunk.article_no} · score `{hit.score:.3f}` · {hit.match_reason}")
            if not task.retrieval.hits:
                st.caption("No retrieval hits")
            elif len(task.retrieval.hits) > 4:
                st.caption(f"另有 {len(task.retrieval.hits) - 4} 条命中记录，可在 Metadata 中核验。")
            st.markdown("#### Workflow Route")
            st.write({"route": task.route, "reason": task.route_reason})
            st.markdown("#### Agent Execution Trace")
            for event in task.events:
                st.markdown(f"- `{event.stage}` · {event.message}")
        with metadata_tab:
            st.json([hit.metadata for hit in task.retrieval.hits])
        with risk_tab:
            st.json(task.risk.model_dump(mode="json") if task.risk else {})
        with mcp_tab:
            st.json(task.retrieval.mcp_calls)


def result_page(service: AnalysisService) -> None:
    task_id = st.session_state.get("selected_task_id") or st.session_state.get("last_task_id")
    if not task_id:
        go("history"); st.rerun()
    try:
        task = service.get_task(task_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"任务不可用：{exc}"); return
    page_header("审查结果", task.original_filename, f"任务编号 {task.task_id}", service.settings.demo_mode)
    if task.error:
        st.error(task.error); return
    if not task.risk:
        st.warning("该任务尚未生成风险结果。"); return
    render_result_hero(task)
    if task.status.value == "awaiting_review" or task.risk.requires_human_review:
        st.markdown(
            '<div class="manual-review-notice"><div><span>LEGAL REVIEW ADVISED</span>'
            '<strong>建议人工复核</strong><p>该任务存在高风险、证据不足或置信度条件，已进入法务复核队列。</p></div></div>',
            unsafe_allow_html=True,
        )
    selected = st.radio("风险筛选", ["全部", "高风险", "中风险", "低风险"], horizontal=True, label_visibility="collapsed")
    level = {"高风险": "high", "中风险": "medium", "低风险": "low"}.get(selected)
    findings = [f for f in task.risk.findings if not level or f.severity.value == level]
    section("风险明细", f"显示 {len(findings)} 项")
    for index, finding in enumerate(findings, 1):
        render_finding(finding, index)
    if not findings:
        st.markdown('<div class="empty-panel">当前筛选条件下没有风险发现。</div>', unsafe_allow_html=True)
    if task.status.value == "awaiting_review" and st.button("进入人工复核", type="primary", key="result_to_review"):
        go("human_review", task.task_id); st.session_state["review_task_id"] = task.task_id; st.rerun()
    if task.report_markdown:
        st.download_button("下载审查报告", task.report_markdown, f"{task.task_id}_report.md", "text/markdown")
    section("技术详情", "默认折叠，仅供技术评审")
    technical_details(task)


def audit_trail(task: TaskRecord) -> None:
    section("审计轨迹", f"{len(task.audit_events)} 条事件")
    events = task.audit_events
    if events:
        for event in events:
            st.markdown(f'<div class="audit-item"><strong>{esc(event.event_type)}</strong> · {esc(event.actor)} · {format_time(event.timestamp)}<br/>{esc(event.detail)}</div>', unsafe_allow_html=True)
    else:
        for event in task.events:
            st.markdown(f'<div class="audit-item"><strong>{esc(event.stage)}</strong><br/>{esc(event.message)}</div>', unsafe_allow_html=True)


def human_review_page(service: AnalysisService) -> None:
    tasks = service.list_review_tasks()
    page_header("待人工复核", "法务复核任务队列", "集中处理高风险或证据不足的合同审查任务。", service.settings.demo_mode)
    section("复核任务", f"待处理 {len(tasks)} 项")
    if not tasks:
        st.markdown('<div class="empty-panel">当前没有待人工复核任务。运行高风险示例后，任务会进入此队列。</div>', unsafe_allow_html=True); return
    header = st.columns([2.2, .7, .7, .8, 1.15, .85, .75])
    for col, label in zip(header, ["合同名称", "风险等级", "置信度", "发现数量", "创建时间", "状态", "操作"]): col.caption(label)
    for task in tasks:
        cols = st.columns([2.2, .7, .7, .8, 1.15, .85, .75], vertical_alignment="center")
        cols[0].markdown(f"**{esc(task.original_filename)}**"); cols[1].markdown(risk_html(task_level(task)), unsafe_allow_html=True)
        cols[2].write(f"{task.risk.confidence:.0%}" if task.risk else "—"); cols[3].write(len(task.risk.findings) if task.risk else 0)
        cols[4].write(format_time(task.created_at)); cols[5].markdown(status_html(task.status.value), unsafe_allow_html=True)
        if cols[6].button("进入复核", key=f"open_review_{task.task_id}"):
            st.session_state["review_task_id"] = task.task_id; st.rerun()
    selected_id = st.session_state.get("review_task_id")
    if selected_id not in {task.task_id for task in tasks}: return
    task = service.get_task(selected_id)
    section("复核任务详情", task.task_id)
    ai_col, human_col = st.columns(2, gap="large")
    modifications: dict[str, dict[str, str]] = {}
    with ai_col:
        with st.container(border=True):
            st.markdown('<div class="review-panel-marker ai"></div><div class="review-panel-kicker">AI ANALYSIS</div><div class="column-title">AI 原始判断</div>', unsafe_allow_html=True)
            if task.risk:
                st.markdown(f"风险等级　{risk_html(task.risk.risk_level.value)}", unsafe_allow_html=True)
                for index, finding in enumerate(task.risk.findings, 1):
                    basis = finding.legal_basis[0] if finding.legal_basis else None
                    st.markdown(f"**{index:02d} · {finding.issue}**"); st.caption(f"合同证据：{finding.contract_evidence}")
                    st.write(f"AI 建议：{finding.recommendation}"); st.write(f"法律依据：{basis.title + ' · ' + basis.article_no if basis else '依据不足'}")
    with human_col:
        with st.container(border=True):
            st.markdown('<div class="review-panel-marker human"></div><div class="review-panel-kicker">LEGAL DECISION</div><div class="column-title">法务复核</div>', unsafe_allow_html=True)
            for finding in (task.risk.findings if task.risk else []):
                severity = st.selectbox(f"最终风险等级 · {finding.clause_id}", [i.value for i in Severity], index=[i.value for i in Severity].index(finding.severity.value), format_func=lambda value: RISK_LABELS[value], key=f"review_severity_{task.task_id}_{finding.clause_id}")
                recommendation = st.text_area("修改建议", value=finding.recommendation, key=f"review_rec_{task.task_id}_{finding.clause_id}")
                modifications[finding.clause_id] = {"issue": finding.issue, "recommendation": recommendation, "severity": severity}
            decision = st.radio("最终决策", [i.value for i in ReviewDecision], format_func=lambda value: {"approve": "通过", "request_changes": "要求修改", "reject": "不通过"}[value], horizontal=True, key=f"decision_{task.task_id}")
            comment = st.text_area("复核意见", placeholder="记录判断依据、修改要求或后续处理意见。", key=f"comment_{task.task_id}")
            if st.button("保存复核结果", type="primary", width="stretch", key=f"save_{task.task_id}"):
                try:
                    service.submit_review(task.task_id, ReviewDecision(decision), comment=comment, modifications=modifications, reviewer="demo-reviewer")
                    st.session_state.pop("review_task_id", None); st.toast("复核结果与审计记录已保存。"); st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
    audit_trail(task)


def reports_page(service: AnalysisService) -> None:
    tasks = [task for task in service.list_tasks() if task.report_markdown]
    page_header("报告中心", "合同审查报告", "查看、复核并下载已生成的正式审查报告。", service.settings.demo_mode)
    section("报告列表", f"共 {len(tasks)} 份")
    if not tasks:
        st.markdown('<div class="empty-panel">暂无可用报告。完成低风险审查或人工复核后，报告将在这里生成。</div>', unsafe_allow_html=True); return
    header = st.columns([2.1, .75, .85, 1.15, 1, .55, .65])
    for col, label in zip(header, ["合同名称", "风险等级", "报告状态", "生成时间", "人工复核", "查看", "下载"]): col.caption(label)
    for task in tasks:
        cols = st.columns([2.1, .75, .85, 1.15, 1, .55, .65], vertical_alignment="center")
        cols[0].markdown(f"**{esc(task.original_filename)}**"); cols[1].markdown(risk_html(task_level(task)), unsafe_allow_html=True)
        cols[2].markdown(badge("已生成", "low"), unsafe_allow_html=True); cols[3].write(format_time(task.updated_at)); cols[4].write("已复核" if task.review else "无需复核")
        if cols[5].button("查看", key=f"report_view_{task.task_id}"): st.session_state["report_task_id"] = task.task_id; st.rerun()
        cols[6].download_button("下载", task.report_markdown, f"{task.task_id}_report.md", "text/markdown", key=f"report_download_{task.task_id}")
    selected_id = st.session_state.get("report_task_id")
    if selected_id not in {task.task_id for task in tasks}: selected_id = tasks[0].task_id
    task = service.get_task(selected_id); risk = task.risk
    section("报告详情", task.task_id)
    st.markdown(f"<div class='confirm-card'><div class='confirm-grid'><div class='confirm-item'><span>合同信息</span><strong>{esc(task.original_filename)}</strong></div><div class='confirm-item'><span>审查范围</span><strong>{esc(task_dimension(task))}</strong></div><div class='confirm-item'><span>人工复核状态</span><strong>{'已复核' if task.review else '无需复核'}</strong></div></div></div>", unsafe_allow_html=True)
    if risk:
        st.markdown("### 风险摘要"); st.write(risk.summary); st.markdown("### 风险明细与处理建议")
        for index, finding in enumerate(risk.findings, 1):
            st.markdown(f"**{index}. {finding.issue}**　{risk_html(finding.severity.value)}", unsafe_allow_html=True)
            st.write(f"合同证据：{finding.contract_evidence}"); st.write(f"处理建议：{finding.recommendation}")
            if finding.legal_basis: st.caption("法律依据：" + "；".join(f"{item.title} {item.article_no}" for item in finding.legal_basis))
    st.markdown("### 免责声明")
    st.caption("本报告由 AI 辅助生成，仅用于企业内部风险初筛与法务工作支持，不构成正式法律意见。法规引用含 DEMO/SAMPLE 数据，请在正式决策前由专业人员核验。")


def history_page(service: AnalysisService) -> None:
    tasks = service.list_tasks()
    page_header("审查记录", "历史任务与处理状态", "查询本地保存的合同审查任务，并进入详情查看完整结果。", service.settings.demo_mode)
    section("历史任务", f"共 {len(tasks)} 条")
    if not tasks:
        st.markdown('<div class="empty-panel">暂无历史审查记录。</div>', unsafe_allow_html=True); return
    header = st.columns([1.55, 1.65, 1, 1.1, .7, .85, 1.15, .65])
    for col, label in zip(header, ["task_id", "合同名称", "审查方式", "审查维度", "风险等级", "状态", "创建时间", "详情"]): col.caption(label)
    for task in tasks:
        cols = st.columns([1.55, 1.65, 1, 1.1, .7, .85, 1.15, .65], vertical_alignment="center")
        mode = "智能全面审查" if task.review_dimension == "general_contract" else "专项审查"
        for col, value in zip(cols[:4], [task.task_id, task.original_filename, mode, task_dimension(task)]): col.write(value)
        cols[4].markdown(risk_html(task_level(task)), unsafe_allow_html=True); cols[5].markdown(status_html(task.status.value), unsafe_allow_html=True); cols[6].write(format_time(task.created_at))
        if cols[7].button("查看", key=f"history_{task.task_id}"): go("result", task.task_id); st.rerun()


def main() -> None:
    st.set_page_config(page_title="Enterprise Legal AI Agent", page_icon="§", layout="wide", initial_sidebar_state="expanded")
    st.markdown(APP_CSS, unsafe_allow_html=True)
    service = get_service(); render_sidebar(service)
    page = st.session_state.get("page", "dashboard")
    pages = {
        "dashboard": dashboard_page,
        "review": review_page,
        "process": review_process_page,
        "human_review": human_review_page,
        "reports": reports_page,
        "history": history_page,
        "result": result_page,
    }
    if page not in pages:
        go("dashboard"); st.rerun()
    pages[page](service)


if __name__ == "__main__":
    main()
