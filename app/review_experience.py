"""Cinematic four-stage presentation for the real legal-review workflow."""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path


STAGE_ORDER = (
    "received", "parsing", "planning", "retrieving", "analyzing",
    "validating", "reporting", "completed",
)

STAGE_COPY = {
    "received": ("合同已接收", "正在确认文件完整性与审查范围。"),
    "parsing": ("正在解析合同", "读取合同内容、主体信息与关键条款结构。"),
    "planning": ("正在规划审查维度", "识别付款、履行、违约与争议解决等审查领域。"),
    "retrieving": ("正在检索法律依据", "查找与合同条款相关的法规与可验证证据。"),
    "analyzing": ("正在分析合同风险", "结合合同条款、法律依据与审查规则生成风险判断。"),
    "validating": ("正在校验审查结果", "核验风险结论的结构完整性与证据充分性。"),
    "review_required": ("需要人工复核", "AI 初审已完成，该任务已按真实路由规则进入法务复核。"),
    "reporting": ("正在生成报告", "正在将已校验的审查结果整理为正式报告。"),
    "completed": ("审查完成", "风险分析与结果校验完成，最终审查报告已生成。"),
    "failed": ("审查未完成", "分析过程中出现异常，请重新尝试。"),
}

VISUAL_STAGES = {
    1: {
        "title": "合同解析", "subtitle": "獬豸递卷 · 契约入审",
        "description": "正在读取合同内容、识别主体信息并解析关键条款结构。",
        "asset": "stage1.png", "alt": "合同初审场景：獬豸与皋陶共同查看进入系统的合同文件。",
    },
    2: {
        "title": "法规检索", "subtitle": "循法而行 · 有据可依",
        "description": "正在规划审查维度，并检索与合同条款相关的法律依据。",
        "asset": "stage2.png", "alt": "法规检索场景：合同条款与法律法规依据进行匹配。",
    },
    3: {
        "title": "风险分析", "subtitle": "獬豸辨曲直 · 皋陶断疑契",
        "description": "正在结合合同条款、法规依据与审查规则识别潜在风险。",
        "asset": "stage3.png", "alt": "风险分析场景：合同风险点被识别并分级，皋陶进行深度判断。",
    },
    4: {
        "title": "审查完成", "subtitle": "结论既定 · 审契成卷",
        "description": "风险分析与结果校验完成，最终审查报告已生成。",
        "asset": "stage4.png", "alt": "审查完成场景：审查报告已经生成并形成最终结论。",
    },
}

WORKFLOW_VISUAL_MAP = {
    "received": 1, "parsing": 1,
    "planning": 2, "retrieving": 2,
    "analyzing": 3, "validating": 3, "review_required": 3, "failed": 3,
    "reporting": 4, "completed": 4,
}

PROGRESS_STEPS = (
    ("parsing", "合同解析"), ("planning", "审查规划"),
    ("retrieving", "法规检索"), ("analyzing", "风险分析"),
    ("validating", "结果校验"), ("reporting", "报告生成"),
)

_STAGE_ASSET_DIR = Path(__file__).resolve().parent / "static" / "review_stages"


@lru_cache(maxsize=4)
def _asset_data_uri(filename: str) -> str:
    """Embed an approved stage PNG so Streamlit does not need a static route."""
    asset_path = _STAGE_ASSET_DIR / filename
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def visual_stage_for(workflow_stage: str) -> int:
    """Map a fine-grained workflow state to one of the four approved visuals."""
    return WORKFLOW_VISUAL_MAP.get(workflow_stage, 1)


def stage_index(stage: str) -> int:
    if stage == "review_required":
        return STAGE_ORDER.index("validating") + 1
    if stage == "failed":
        return -1
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 0


def _progress_markup(stage: str) -> str:
    current = stage_index(stage)
    progress = []
    for key, label in PROGRESS_STEPS:
        position = stage_index(key)
        if stage == "completed" or current > position:
            state, mark = "done", "✓"
        elif current == position or (stage == "received" and key == "parsing"):
            state, mark = "active", "●"
        else:
            state, mark = "pending", "○"
        progress.append(
            f'<div class="process-step {state}"><span>{mark}</span><strong>{html.escape(label)}</strong></div>'
        )
    return "".join(progress)


def render_review_experience(stage: str, filename: str) -> str:
    """Render one workflow-driven state using one approved source image."""
    safe_stage = stage if stage in STAGE_COPY else "received"
    visual_number = visual_stage_for(safe_stage)
    visual = VISUAL_STAGES[visual_number]
    status_title, status_description = STAGE_COPY[safe_stage]
    asset_url = _asset_data_uri(visual["asset"])
    review_notice = (
        '<div class="process-review-branch"><strong>HUMAN REVIEW REQUIRED</strong>'
        '<span>任务停留在风险分析阶段，未展示“审查完成”。</span></div>'
        if safe_stage == "review_required" else ""
    )
    return f"""
    <div class="review-process stage-{safe_stage} visual-stage-{visual_number}">
      <div class="process-heading">
        <div><div class="process-kicker">CINEMATIC LEGAL REVIEW · STAGE {visual_number:02d}</div>
        <h1>{html.escape(visual['title'])}</h1><div class="process-subtitle">{html.escape(visual['subtitle'])}</div></div>
        <p>{html.escape(visual['description'])}</p>
      </div>
      <div class="process-visual">
        <img src="{asset_url}" data-stage-asset="{visual['asset']}" alt="{html.escape(visual['alt'])}" loading="eager" decoding="async" fetchpriority="high">
        <div class="process-visual-shade"></div><div class="process-live-state"><span></span>REAL WORKFLOW</div>
      </div>
      <div class="process-status"><div class="status-mark"><span></span></div>
        <div><div class="process-stage-title">{html.escape(status_title)}</div><div class="process-stage-copy">{html.escape(status_description)}</div></div>
        <div class="process-file">当前卷宗<br><strong>{html.escape(filename)}</strong></div>
      </div>
      {review_notice}
      <div class="process-progress">{_progress_markup(safe_stage)}</div>
      <div class="process-footnote">视觉阶段由实际审查状态推导，不显示估算百分比。</div>
    </div>
    """
