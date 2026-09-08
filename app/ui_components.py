"""Small, reusable HTML render helpers for the Streamlit UI."""

from __future__ import annotations

import html

import streamlit as st


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def badge(value: str, kind: str = "neutral") -> str:
    return f'<span class="badge {esc(kind)}">{esc(value)}</span>'


def page_header(title: str, subtitle: str, description: str, demo_mode: bool) -> None:
    mode = "DEMO MODE" if demo_mode else "REAL LLM"
    st.markdown(
        f"""
        <div class="page-head">
          <div class="page-head-copy">
            <div class="eyebrow"><span></span> LEGAL OPERATIONS WORKSPACE</div>
            <h1>{esc(title)}</h1>
            <div class="page-subtitle">{esc(subtitle)}</div>
            <div class="page-description">{esc(description)}</div>
          </div>
          <div class="mode-badge"><span class="mode-dot"></span>{esc(mode)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, note: str = "", demo: bool = False) -> None:
    demo_html = '<span class="demo-tag">演示数据</span>' if demo else ""
    st.markdown(
        f'<div class="section-row"><div class="section-title">{esc(title)}{demo_html}</div>'
        f'<div class="section-note">{esc(note)}</div></div>',
        unsafe_allow_html=True,
    )


def metric_cards(items: list[tuple[str, str, str]]) -> None:
    icons = {
        "本周审查": "↗",
        "高风险任务": "!",
        "待人工复核": "✓",
        "平均审查耗时": "◷",
    }
    cards = "".join(
        f'<div class="metric-card metric-{index}"><div class="metric-top"><div class="metric-label">{esc(label)}</div>'
        f'<div class="metric-icon">{esc(icons.get(label, "·"))}</div></div>'
        f'<div class="metric-value">{esc(value)}</div><div class="metric-foot">{esc(foot)}</div></div>'
        for index, (label, value, foot) in enumerate(items, 1)
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def step_header(number: int, title: str) -> None:
    st.markdown(
        f'<div class="step-head"><span class="step-no">{number}</span>'
        f'<span class="step-title">{esc(title)}</span></div>',
        unsafe_allow_html=True,
    )


def choice_copy(title: str, description: str) -> None:
    st.markdown(
        f'<div class="choice-copy"><div class="choice-title">{esc(title)}</div>'
        f'<div class="choice-desc">{esc(description)}</div></div>',
        unsafe_allow_html=True,
    )


def workflow_steps(active: int = 1) -> None:
    labels = ("合同来源", "审查方式", "审查确认")
    content = "".join(
        f'<div class="workflow-step {"active" if index == active else ""}">'
        f'<span>{index}</span><strong>{esc(label)}</strong></div>'
        for index, label in enumerate(labels, 1)
    )
    st.markdown(f'<div class="workflow-steps">{content}</div>', unsafe_allow_html=True)
