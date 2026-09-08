"""Visual system for the Streamlit legal workbench."""

APP_CSS = r"""
<style>
:root {
  --ink: #17202e;
  --muted: #687386;
  --brand: #243a5a;
  --brand-strong: #182a44;
  --brand-soft: #edf2f7;
  --canvas: #f7f7f5;
  --panel: #ffffff;
  --line: #e5e7eb;
  --high: #a83232;
  --high-soft: #f9eaea;
  --medium: #a65f20;
  --medium-soft: #fbf0e4;
  --low: #47715a;
  --low-soft: #eaf2ed;
  --radius: 10px;
}

html, body, [class*="css"] { font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif; }
.stApp { background: var(--canvas); color: var(--ink); }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; height: 2rem; }
[data-testid="stToolbar"] { visibility: hidden; }
.block-container { max-width: 1320px; padding: 2rem 2.4rem 4rem; }

[data-testid="stSidebar"] { background: #f1f2f1; border-right: 1px solid #dfe2e6; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.35rem; }
.sidebar-brand { padding: .35rem .35rem 1.15rem; border-bottom: 1px solid #dde1e6; margin-bottom: .75rem; }
.sidebar-mark { width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 9px; background: var(--brand); color: #fff; font-weight: 800; margin-bottom: .65rem; }
.sidebar-name { font-size: .96rem; font-weight: 750; color: #1f2937; letter-spacing: -.01em; }
.sidebar-sub { color: #7a8492; font-size: .72rem; margin-top: .2rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: .2rem; }
[data-testid="stSidebar"] label[data-baseweb="radio"] { padding: .58rem .7rem; border-radius: 8px; }
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) { background: #fff; box-shadow: 0 1px 2px rgba(25,35,50,.05); }
[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child { display: none; }
[data-testid="stSidebar"] label[data-baseweb="radio"] p { font-size: .88rem; color: #394556; }
.sidebar-footer { margin-top: 1.3rem; padding: .85rem .35rem; border-top: 1px solid #dde1e6; color: #7a8492; font-size: .71rem; line-height: 1.65; }

.page-head { display: flex; justify-content: space-between; gap: 1.5rem; align-items: flex-start; margin-bottom: 1.65rem; }
.eyebrow { color: #738096; font-size: .72rem; font-weight: 750; text-transform: uppercase; letter-spacing: .11em; margin-bottom: .45rem; }
.page-head h1 { color: var(--ink); font-size: 1.95rem; line-height: 1.2; letter-spacing: -.035em; margin: 0; font-weight: 760; }
.page-subtitle { color: #4b586b; font-size: 1rem; font-weight: 600; margin-top: .4rem; }
.page-description { color: var(--muted); max-width: 720px; font-size: .87rem; margin-top: .45rem; line-height: 1.6; }
.mode-badge { display: inline-flex; align-items: center; gap: .35rem; background: #fff; border: 1px solid var(--line);
  border-radius: 999px; padding: .34rem .65rem; color: #556174; font-size: .7rem; font-weight: 700; white-space: nowrap; }
.mode-dot { width: 6px; height: 6px; border-radius: 50%; background: #70839e; display: inline-block; }

.section-row { display: flex; align-items: baseline; justify-content: space-between; margin: 1.7rem 0 .75rem; }
.section-title { font-size: 1.08rem; font-weight: 730; color: #202a38; letter-spacing: -.015em; }
.section-note { color: #818a98; font-size: .75rem; }
.demo-tag { display: inline-block; margin-left: .45rem; color: #735b28; background: #f6f0df; border: 1px solid #eadfbf;
  border-radius: 999px; padding: .12rem .45rem; font-size: .65rem; font-weight: 700; vertical-align: 2px; }

.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: .85rem; }
.metric-card { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.05rem; box-shadow: 0 1px 2px rgba(20,30,45,.025); }
.metric-label { color: #747f8f; font-size: .75rem; font-weight: 620; }
.metric-value { color: #1d2735; font-size: 1.65rem; line-height: 1.25; font-weight: 760; margin-top: .45rem; letter-spacing: -.035em; }
.metric-foot { color: #9299a5; font-size: .67rem; margin-top: .25rem; }

.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: 0 1px 2px rgba(20,30,45,.025); }
.empty-panel { background: #fff; border: 1px dashed #d9dde3; border-radius: var(--radius); padding: 2rem; color: #7b8491; text-align: center; font-size: .83rem; }
.clean-table { width: 100%; border-collapse: collapse; font-size: .78rem; }
.clean-table th { text-align: left; color: #7b8492; font-weight: 650; padding: .62rem .55rem; border-bottom: 1px solid #e8eaed; white-space: nowrap; }
.clean-table td { color: #394455; padding: .72rem .55rem; border-bottom: 1px solid #eff0f2; vertical-align: middle; }
.clean-table tr:last-child td { border-bottom: 0; }
.clean-table .primary-cell { color: #202a38; font-weight: 650; }
.dashboard-panels { display:grid; grid-template-columns:minmax(0,1.7fr) minmax(0,1fr); gap:1.5rem; align-items:start; }
.dashboard-panel-head { display:flex; align-items:baseline; justify-content:space-between; margin:1.7rem 0 .75rem; }
.dashboard-panel-head strong { font-size:1.08rem; color:#202a38; }
.dashboard-panel-head span { color:#818a98; font-size:.75rem; }

.badge { display: inline-flex; align-items: center; border-radius: 999px; padding: .16rem .5rem; font-size: .66rem; font-weight: 730; white-space: nowrap; }
.badge.high { color: var(--high); background: var(--high-soft); }
.badge.medium { color: var(--medium); background: var(--medium-soft); }
.badge.low { color: var(--low); background: var(--low-soft); }
.badge.neutral { color: #566273; background: #edf0f3; }
.badge.review { color: #6d4f86; background: #f1eaf6; }

.step-head { display:flex; align-items:center; gap:.7rem; margin: 1.5rem 0 .75rem; }
.step-no { width: 28px; height: 28px; display:inline-flex; align-items:center; justify-content:center; border-radius: 50%; background:var(--brand); color:#fff; font-size:.72rem; font-weight:750; }
.step-title { font-size: 1.02rem; font-weight: 720; color:#202a38; }
.choice-copy { min-height: 74px; padding: .2rem .15rem .15rem; }
.choice-title { font-size: .93rem; font-weight: 720; color:#243040; }
.choice-desc { color:#758091; font-size:.76rem; line-height:1.55; margin-top:.3rem; }
.selection-note { border-left: 3px solid #8293aa; background:#f2f5f8; padding:.65rem .8rem; border-radius:0 7px 7px 0; color:#556174; font-size:.77rem; margin:.55rem 0; }
.confirm-card { background:#fff; border:1px solid #dce1e6; border-radius:12px; padding:1.1rem 1.2rem; margin:.7rem 0 1rem; box-shadow:0 2px 7px rgba(22,34,51,.035); }
.confirm-title { font-size:.92rem; font-weight:730; color:#202a38; margin-bottom:.7rem; }
.confirm-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem; }
.confirm-item span { display:block; color:#87909d; font-size:.67rem; margin-bottom:.2rem; }
.confirm-item strong { color:#344052; font-size:.78rem; font-weight:650; }
.output-list { color:#5f6b7b; font-size:.75rem; line-height:1.75; margin-top:.75rem; padding-top:.7rem; border-top:1px solid #eceef0; }

.result-hero { background:#fff; border:1px solid #dfe3e8; border-radius:12px; padding:1.15rem 1.25rem; margin-bottom:1rem; }
.result-kicker { color:var(--low); font-size:.7rem; font-weight:750; letter-spacing:.08em; }
.result-title { color:#202a38; font-size:1.45rem; font-weight:760; margin:.25rem 0; }
.result-summary { color:#687386; font-size:.82rem; line-height:1.6; max-width:920px; }
.result-metrics { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.65rem; margin-top:.85rem; }
.result-metric { background:#f7f8f8; border:1px solid #eaeced; border-radius:8px; padding:.7rem .75rem; }
.result-metric span { display:block; color:#838c98; font-size:.65rem; }
.result-metric strong { display:block; color:#293546; font-size:.9rem; margin-top:.2rem; }

.finding-card { background:#fff; border:1px solid var(--line); border-left:3px solid #8391a3; border-radius:10px; padding:1rem 1.15rem; margin:.75rem 0; }
.finding-card.high { border-left-color:var(--high); }.finding-card.medium { border-left-color:var(--medium); }.finding-card.low { border-left-color:var(--low); }
.finding-top { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
.finding-index { color:#9aa1ab; font-size:.7rem; font-weight:740; letter-spacing:.08em; }
.finding-title { color:#202a38; font-size:1rem; font-weight:730; margin:.14rem 0 .5rem; }
.finding-grid { display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin-top:.8rem; }
.detail-block { background:#f8f9f9; border:1px solid #eceeef; border-radius:8px; padding:.72rem .8rem; }
.detail-label { color:#808996; font-size:.66rem; font-weight:700; margin-bottom:.3rem; }
.detail-text { color:#465264; font-size:.76rem; line-height:1.6; }
.insufficient { color:#8f3030; background:#faeeee; border:1px solid #f0d3d3; border-radius:7px; padding:.55rem .7rem; font-size:.74rem; font-weight:650; margin-top:.7rem; }

.review-ai { border-top:3px solid #70839e; }.review-human { border-top:3px solid #8f7055; }
.column-title { font-size:.95rem; font-weight:730; color:#263243; margin-bottom:.75rem; }
.audit-item { border-left:2px solid #d8dde3; padding:.15rem 0 .65rem .75rem; color:#5f6b7b; font-size:.74rem; }

div.stButton > button, div.stDownloadButton > button { border-radius:8px; min-height:2.45rem; font-weight:680; border-color:#d7dce2; box-shadow:none; }
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] { background:var(--brand); border-color:var(--brand); color:#fff; }
div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover { background:var(--brand-strong); border-color:var(--brand-strong); }
[data-testid="stFileUploader"] { background:#fff; border:1px dashed #cdd4dc; border-radius:10px; padding:.65rem; }
[data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div { border-radius:8px; }
[data-testid="stExpander"] { background:#fff; border:1px solid var(--line); border-radius:9px; }
[data-testid="stAlert"] { border-radius:8px; }

.block-container:has(.review-page-marker) { padding-top:1.1rem; }
.block-container:has(.review-page-marker) .page-head { margin-bottom:.6rem; }
.block-container:has(.review-page-marker) .page-head h1 { font-size:1.75rem; }
.block-container:has(.review-page-marker) .page-description { margin-top:.2rem; }
.block-container:has(.review-page-marker) .step-head { margin:.75rem 0 .32rem; }
.block-container:has(.review-page-marker) .choice-copy { min-height:48px; padding:0 .1rem; }
.block-container:has(.review-page-marker) .choice-desc { margin-top:.12rem; line-height:1.35; }
.block-container:has(.review-page-marker) .selection-note { margin:.35rem 0; padding:.45rem .7rem; }
.block-container:has(.review-page-marker) [data-testid="stFileUploader"] { padding:.3rem .55rem; }
.block-container:has(.review-page-marker) [data-testid="stTextArea"] textarea { min-height:58px; height:58px; }
.block-container:has(.review-page-marker) .confirm-card { padding:.75rem 1rem; margin:.4rem 0 .65rem; }
.block-container:has(.review-page-marker) .output-list { margin-top:.45rem; padding-top:.4rem; }

@media (max-width: 1050px) {
  .metric-grid { grid-template-columns:repeat(2,1fr); }
  .result-metrics { grid-template-columns:repeat(3,1fr); }
  .dashboard-panels { grid-template-columns:1fr; gap:0; }
  .block-container { padding-left:1.5rem; padding-right:1.5rem; }
}
@media (max-width: 720px) {
  .page-head { flex-direction:column; }
  .metric-grid,.confirm-grid,.result-metrics,.finding-grid { grid-template-columns:1fr; }
  .block-container { padding-left:1rem; padding-right:1rem; }
}
</style>
"""
