"""Stage 2 review-process presentation helpers.

The module is intentionally UI-only: it maps real workflow callbacks to a
restrained Xiezhi / Gaotao visual without changing analysis decisions.
"""

from __future__ import annotations

import html


STAGE_ORDER = (
    "received",
    "parsing",
    "planning",
    "retrieving",
    "analyzing",
    "validating",
    "reporting",
    "completed",
)

STAGE_COPY = {
    "received": ("合同已接收", "正在确认文件完整性与审查范围。"),
    "parsing": ("正在解析合同", "识别合同结构、条款与核心审查对象。"),
    "planning": ("正在识别审查维度", "分析付款、履行、违约、争议解决等主要风险领域。"),
    "retrieving": ("正在检索法律依据", "查找与合同条款相关的法规与证据。"),
    "analyzing": ("正在分析合同风险", "结合合同证据与法律依据生成风险判断。"),
    "validating": ("正在校验审查结果", "核验风险结论的结构完整性与证据状态。"),
    "reporting": ("正在生成报告", "正在将已校验的审查结果整理为正式报告。"),
    "completed": ("审查完成", "审契已毕，正在进入现代法律审查结果页。"),
    "failed": ("审查未完成", "分析过程中出现异常，请重新尝试。"),
}

PROGRESS_STEPS = (
    ("parsing", "合同解析"),
    ("planning", "审查规划"),
    ("retrieving", "法规检索"),
    ("analyzing", "风险分析"),
    ("validating", "结果校验"),
    ("reporting", "报告生成"),
)


def stage_index(stage: str) -> int:
    """Return a stable stage index for UI progress and tests."""
    if stage == "failed":
        return -1
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 0


def render_review_experience(stage: str, filename: str) -> str:
    """Return the complete Stage 2 narrative panel for one real workflow stage."""
    safe_stage = stage if stage in STAGE_COPY else "received"
    title, description = STAGE_COPY[safe_stage]
    current = stage_index(safe_stage)
    progress = []
    for key, label in PROGRESS_STEPS:
        step_position = stage_index(key)
        if safe_stage == "completed" or current > step_position:
            state, mark = "done", "✓"
        elif current == step_position or (safe_stage == "received" and key == "parsing"):
            state, mark = "active", "●"
        else:
            state, mark = "pending", "○"
        progress.append(
            f'<div class="process-step {state}"><span>{mark}</span><strong>{html.escape(label)}</strong></div>'
        )

    return f"""
    <div class="review-process stage-{safe_stage}">
      <div class="process-heading">
        <div class="process-kicker">LEGAL REVIEW IN PROGRESS</div>
        <h1>獬豸递卷 <i>·</i> 皋陶审契</h1>
        <p>正在根据合同内容、法律依据与风险规则进行审查。</p>
      </div>
      <div class="process-scene" role="img" aria-label="獬豸递送合同卷宗至皋陶案前">
        <svg viewBox="0 0 1200 410" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <defs>
            <linearGradient id="paper" x1="0" x2="1"><stop stop-color="#fffdf7"/><stop offset="1" stop-color="#eee4d2"/></linearGradient>
            <filter id="soft"><feDropShadow dx="0" dy="9" stdDeviation="12" flood-color="#40372c" flood-opacity=".13"/></filter>
          </defs>
          <path class="horizon" d="M70 327 H1130"/>
          <g class="screen-lines"><path d="M890 62h205M890 82h205M890 102h205"/><path d="M1080 62v130"/></g>
          <g class="xiezhi-mark">
            <path d="M98 273c18-46 58-72 113-70 46 2 73 23 91 59l-21 12-13 48H137l-12-39z"/>
            <path d="M152 210c3-48 28-83 68-90 33-6 61 9 73 37l-28 9-9 36"/>
            <path class="horn" d="M215 122l38-70-8 76"/>
            <path d="M172 171c15 8 32 8 48 1M202 157h3M282 263c25-7 43-3 55 12"/>
            <path d="M151 322v33M205 322v33M262 319v36"/>
            <circle cx="205" cy="157" r="3"/>
          </g>
          <path class="delivery-path" d="M310 254 C450 224 560 239 703 248"/>
          <g class="scroll" filter="url(#soft)">
            <rect x="-75" y="-42" width="150" height="84" rx="5" fill="url(#paper)"/>
            <path d="M-58-18h94M-58-3h72M-58 12h88"/>
            <circle cx="52" cy="18" r="13" class="scroll-seal"/>
            <path d="M-80-47v94M80-47v94" class="scroll-rod"/>
          </g>
          <g class="law-pages">
            <rect x="690" y="133" width="91" height="112" rx="4"/><rect x="710" y="119" width="91" height="112" rx="4"/>
            <path d="M729 143h52M729 158h43M729 173h50M729 188h36"/>
          </g>
          <g class="gaotao-mark">
            <circle cx="931" cy="142" r="35"/>
            <path d="M900 133c8-39 58-51 73-10M895 180c28-18 75-14 91 13l18 82H877z"/>
            <path d="M918 190l25 32 58 8M943 222l-11 63"/>
            <path class="pen" d="M987 224l51-55M1038 169l5-13"/>
          </g>
          <g class="desk"><path d="M820 270h286v25H820zM846 295v61M1082 295v61"/></g>
          <g class="risk-marks"><path d="M723 259h58M735 271h37"/><circle cx="790" cy="259" r="5"/></g>
          <g class="completion-seal"><circle cx="776" cy="248" r="34"/><path d="M756 248h40M776 228v40"/></g>
        </svg>
        <div class="scene-label xiezhi-label"><strong>獬豸</strong><span>辨是非 · 识曲直</span></div>
        <div class="scene-label gaotao-label"><strong>皋陶</strong><span>审契理 · 定法度</span></div>
      </div>
      <div class="process-status">
        <div class="status-mark"><span></span></div>
        <div><div class="process-stage-title">{html.escape(title)}</div><div class="process-stage-copy">{html.escape(description)}</div></div>
        <div class="process-file">当前卷宗<br><strong>{html.escape(filename)}</strong></div>
      </div>
      <div class="process-progress">{''.join(progress)}</div>
      <div class="process-footnote">阶段状态来自实际审查工作流，不显示估算百分比。</div>
    </div>
    """
