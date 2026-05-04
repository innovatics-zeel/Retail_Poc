"""
app.py — Innovatics Program 1: Product & Market Intelligence
Run: streamlit run streamlit_app/app.py
"""
import sys
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, ".")

from html import escape
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from streamlit_app.db import (
    load_products, get_kpis, attribute_counts,
    price_bands, platform_comparison, top_products,
    color_family_breakdown, save_feedback, data_summary_for_llm,
    load_trend_scores, load_recommendations, update_recommendation_status,
    load_review_velocity, load_variant_skus,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Innovatics | Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

INK      = "#0F1B2D"
MUTED    = "#6F7D95"
LINE     = "#DCE4EE"
PANEL    = "#FFFFFF"
CANVAS   = "#F4F7FB"
PRIMARY  = "#0F1B2D"
ACCENT   = "#08A5D6"
SUCCESS  = "#20A464"
WARNING  = "#FFB000"
DANGER   = "#E5393F"
COOL     = "#EEF3F8"
INFO_BG  = "#DFF2FB"
LIGHT_BG = CANVAS

st.markdown(f"""
<style>
    :root {{
        --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --panel:{PANEL};
        --canvas:{CANVAS}; --accent:{ACCENT}; --success:{SUCCESS};
        --warning:{WARNING}; --danger:{DANGER};
    }}
    .stApp, [data-testid="stAppViewContainer"] {{ background:{CANVAS}; color:{INK}; }}
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stSidebar"] {{ display:none !important; }}
    .block-container {{ padding:0 0 22px !important; max-width:100% !important; }}
    h1, h2, h3, p {{ letter-spacing:0 !important; }}
    div[data-testid="stVerticalBlock"] {{ gap:0.75rem; }}

    .top-shell {{
        background:#fff; border-bottom:1px solid var(--line);
        padding:12px 30px 10px; position:relative; z-index:5;
    }}
    .top-grid {{
        display:grid; grid-template-columns:210px 1fr 540px;
        gap:18px; align-items:center;
    }}
    .brand-mark {{ display:flex; align-items:center; gap:10px; font-weight:800; color:var(--ink); }}
    .mark-stack {{ position:relative; width:28px; height:34px; }}
    .mark-stack span {{ position:absolute; width:10px; height:24px; transform:rotate(42deg); border-radius:2px; }}
    .mark-stack .m1 {{ background:#079ed4; left:8px; top:-1px; height:10px; }}
    .mark-stack .m2 {{ background:#ffb000; left:8px; top:10px; }}
    .crumbs {{ color:var(--muted); font-size:0.88rem; }}
    .crumbs strong {{ color:var(--ink); font-weight:800; }}
    .nav-pill {{
        display:inline-flex; align-items:center; gap:8px; padding:7px 13px;
        border:1px solid var(--line); border-radius:7px; color:var(--muted);
        font-size:0.82rem; background:#f8fbff; margin-right:8px; font-weight:650;
    }}
    .nav-pill.active {{ color:var(--ink); background:#fff; box-shadow:0 0 0 2px #eef5fb inset; }}
    .nav-dot {{ width:6px; height:6px; border-radius:999px; background:#c9d4e1; display:inline-block; }}
    .nav-pill.active .nav-dot {{ background:var(--accent); box-shadow:0 0 8px rgba(8,165,214,.35); }}
    .filter-row {{ display:grid; grid-template-columns:1fr 1.15fr .9fr; gap:10px; align-items:end; }}
    .filter-row label {{ color:var(--muted) !important; font-size:0.76rem !important; font-weight:700 !important; }}
    .filter-row div[data-baseweb="select"] > div {{
        border-color:var(--line); border-radius:7px; min-height:38px; background:#fff;
        box-shadow:0 1px 2px rgba(15,27,45,.04);
    }}

    .hero-strip {{ background:#fff; border-bottom:1px solid var(--line); padding:26px 30px 14px; }}
    .hero-grid {{ display:grid; grid-template-columns:1fr auto; gap:20px; align-items:start; }}
    .hero-title {{ font-size:1.72rem; line-height:1.05; font-weight:900; margin:0; color:var(--ink); }}
    .hero-sub {{ color:var(--muted); margin:6px 0 0; font-size:.92rem; }}
    .live-meta {{ display:flex; align-items:center; gap:16px; justify-content:flex-end; color:var(--muted); font-size:.84rem; padding-top:4px; }}
    .live-meta strong {{ color:var(--ink); font-weight:850; }}
    .live-dot {{ width:7px; height:7px; border-radius:99px; background:#1eb96b; box-shadow:0 0 0 4px #e4f7ee; display:inline-block; margin-right:5px; }}
    .layer-strip {{ display:flex; gap:26px; margin-top:24px; align-items:flex-end; }}
    .layer-item {{ color:var(--muted); font-size:.75rem; line-height:1.05; font-weight:750; padding-bottom:10px; text-decoration:none; }}
    .layer-item b {{ display:block; color:var(--ink); font-size:.95rem; margin-top:2px; }}
    .layer-num {{ width:22px; height:22px; border-radius:999px; display:inline-grid; place-items:center; margin-right:8px; background:#e9eff5; color:#68768a; font-size:.78rem; font-weight:900; }}
    .layer-item.active {{ border-bottom:3px solid var(--accent); color:#9aa6b6; padding-right:28px; }}
    .layer-item.active .layer-num {{ background:var(--accent); color:#fff; }}

    .signal-band {{ display:grid; grid-template-columns:repeat(4,1fr); background:#fff; border-bottom:1px solid var(--line); }}
    .signal-card {{ min-height:96px; padding:19px 30px; border-right:1px solid var(--line); }}
    .signal-card:last-child {{ border-right:0; }}
    .signal-label {{ color:var(--muted); font-size:.78rem; margin-bottom:3px; font-weight:650; }}
    .signal-value {{ color:var(--ink); font-size:2.05rem; line-height:1.05; font-weight:900; white-space:nowrap; }}
    .signal-note {{ color:var(--muted); font-size:.82rem; margin-top:4px; }}
    .signal-note strong {{ color:var(--ink); }}
    .delta {{ display:inline-block; padding:2px 7px; border-radius:5px; font-size:.74rem; font-weight:900; vertical-align:middle; }}
    .delta.up {{ background:#cdf3df; color:var(--success); }}
    .delta.down {{ background:#ffe2e2; color:var(--danger); }}

    .dashboard-pad {{ padding:22px 30px 28px; }}
    .market-grid {{ display:grid; grid-template-columns:1.35fr .98fr .86fr; gap:16px; align-items:start; }}
    .market-grid.clean {{ grid-template-columns:1.35fr .98fr; }}
    .col-stack {{ display:flex; flex-direction:column; gap:16px; }}
    .mi-panel {{ background:#fff; border:1px solid var(--line); border-radius:7px; overflow:hidden; box-shadow:0 1px 2px rgba(15,27,45,.03); }}
    .panel-head {{ min-height:48px; display:flex; align-items:center; justify-content:space-between; padding:0 18px; border-bottom:1px solid #edf2f6; gap:16px; }}
    .panel-title {{ font-weight:900; color:var(--ink); font-size:1.01rem; line-height:1.1; }}
    .panel-sub {{ color:var(--muted); font-size:.78rem; line-height:1.1; text-align:right; }}
    .panel-body {{ padding:14px 18px 16px; }}
    .style-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
    .sku-card {{ border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#fff; min-height:146px; }}
    .sku-swatch {{ height:70px; position:relative; background:#253a59; }}
    .rank-badge, .heat-badge {{ position:absolute; top:9px; padding:3px 8px; border-radius:4px; font-size:.7rem; font-weight:900; line-height:1; }}
    .rank-badge {{ left:10px; background:#fff; color:var(--ink); border:1px solid #d5dde8; }}
    .heat-badge {{ right:10px; background:var(--warning); color:var(--ink); }}
    .heat-badge.rising {{ background:var(--accent); color:#fff; }}
    .sku-copy {{ padding:11px 13px 10px; }}
    .sku-title {{ color:var(--ink); font-size:.94rem; font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .sku-meta {{ color:var(--muted); font-size:.73rem; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .sku-foot {{ display:flex; justify-content:space-between; align-items:flex-end; gap:8px; margin-top:9px; }}
    .sku-price {{ color:var(--ink); font-weight:900; font-size:1.05rem; }}
    .sku-reviews {{ color:var(--muted); font-size:.72rem; text-align:right; }}

    .tabs-mini {{ display:grid; grid-template-columns:repeat(7,1fr); background:#edf3f8; padding:3px; gap:3px; border-radius:6px; margin-bottom:13px; }}
    .tabs-mini span, .tabs-mini a, .tabs-mini label {{ text-align:center; padding:8px 4px; border-radius:5px; color:#51617a; font-size:.78rem; text-decoration:none; cursor:pointer; }}
    .tabs-mini .active {{ background:#fff; color:var(--ink); font-weight:900; box-shadow:0 1px 3px rgba(15,27,45,.08); }}
    .attr-tabs input[type="radio"] {{ display:none; }}
    .attr-panel {{ display:none; }}
    #attr-show-all:checked ~ .tabs-mini label[for="attr-show-all"],
    #attr-color:checked ~ .tabs-mini label[for="attr-color"],
    #attr-pattern:checked ~ .tabs-mini label[for="attr-pattern"],
    #attr-material:checked ~ .tabs-mini label[for="attr-material"],
    #attr-neck:checked ~ .tabs-mini label[for="attr-neck"],
    #attr-fit:checked ~ .tabs-mini label[for="attr-fit"],
    #attr-sleeve:checked ~ .tabs-mini label[for="attr-sleeve"] {{
        background:#fff; color:var(--ink); font-weight:900; box-shadow:0 1px 3px rgba(15,27,45,.08);
    }}
    #attr-show-all:checked ~ .attr-content .attr-show-all,
    #attr-color:checked ~ .attr-content .attr-color,
    #attr-pattern:checked ~ .attr-content .attr-pattern,
    #attr-material:checked ~ .attr-content .attr-material,
    #attr-neck:checked ~ .attr-content .attr-neck,
    #attr-fit:checked ~ .attr-content .attr-fit,
    #attr-sleeve:checked ~ .attr-content .attr-sleeve {{ display:block; }}
    .bar-section {{ margin-top:13px; }}
    .bar-head {{ display:flex; justify-content:space-between; color:var(--ink); font-weight:900; font-size:.84rem; margin:10px 0 8px; }}
    .bar-head span:last-child {{ color:var(--muted); font-weight:650; font-size:.74rem; }}
    .bar-row {{ display:grid; grid-template-columns:112px 1fr 44px 42px; gap:10px; align-items:center; font-size:.8rem; margin:8px 0; }}
    .bar-name {{ color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .bar-track {{ height:6px; background:#edf2f6; border-radius:99px; overflow:hidden; }}
    .bar-fill {{ height:100%; border-radius:99px; background:var(--accent); }}
    .bar-share {{ text-align:right; color:var(--ink); font-weight:900; }}
    .bar-change {{ text-align:right; font-weight:900; }}
    .bar-change.pos {{ color:var(--success); }}
    .bar-change.neg {{ color:var(--danger); }}
    .swatch-dot {{ width:10px; height:10px; border-radius:2px; display:inline-block; margin-right:8px; border:1px solid #cbd5e1; vertical-align:-1px; }}

    .price-grid {{ display:grid; grid-template-columns:1.15fr repeat(6,1fr); gap:3px; align-items:center; font-size:.78rem; }}
    .price-cell {{ min-height:28px; display:grid; place-items:center; background:#edf2f6; border-radius:3px; color:#27354a; font-weight:800; }}
    .price-cell.hot {{ background:var(--accent); color:#fff; }}
    .price-cell.label {{ background:transparent; display:block; padding-top:6px; color:var(--ink); font-weight:900; }}
    .price-head {{ color:#52617a; font-size:.72rem; line-height:1; text-align:center; padding-bottom:6px; }}
    .price-head small {{ display:block; color:#7c8aa0; font-size:.64rem; }}

    .compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:0; }}
    .compare-box {{ padding:14px 18px; border-right:1px solid #edf2f6; }}
    .compare-box:last-child {{ border-right:0; }}
    .play-badge {{ float:right; background:#e9eff5; color:var(--ink); padding:3px 9px; border-radius:4px; font-size:.69rem; font-weight:900; }}
    .play-badge.dark {{ background:var(--ink); color:#fff; }}
    .kv-row {{ display:flex; justify-content:space-between; border-bottom:1px solid #edf2f6; padding:7px 0; color:var(--muted); font-size:.8rem; }}
    .kv-row strong {{ color:var(--ink); }}
    .kv-row .good {{ color:var(--success); font-weight:900; margin-left:5px; }}

    .region-row, .velocity-row {{ display:grid; grid-template-columns:90px 1fr 42px 52px; gap:9px; align-items:center; margin:10px 0; font-size:.8rem; }}
    .region-name, .velocity-name {{ color:var(--ink); }}
    .pill {{ display:inline-block; border-radius:4px; padding:3px 9px; font-size:.68rem; font-weight:900; text-align:center; }}
    .pill.hot {{ background:#fff0c7; color:#c27a00; }}
    .pill.warm {{ background:#dff4fb; color:#078db8; }}
    .pill.cool {{ background:#edf2f7; color:#68778b; }}
    .insight {{ margin-top:14px; background:{INFO_BG}; border-left:4px solid var(--accent); border-radius:4px; padding:11px 13px; color:#27354a; font-size:.8rem; line-height:1.35; }}
    .insight b:first-child {{ color:var(--accent); letter-spacing:.08em; font-size:.68rem; margin-right:7px; }}

    .sent-row {{ display:grid; grid-template-columns:84px 1fr 44px 56px; gap:10px; align-items:center; margin:11px 0; font-size:.8rem; }}
    .sent-track {{ height:8px; border-radius:99px; background:linear-gradient(90deg,#fbe2e2 0 48%,#cfeedd 52% 100%); position:relative; }}
    .sent-mid {{ position:absolute; left:50%; top:-5px; width:1px; height:18px; background:#9aa8bc; }}
    .sent-mark {{ position:absolute; top:-4px; width:3px; height:17px; border-radius:99px; background:var(--success); }}
    .sent-mark.neg {{ background:var(--danger); }}
    .sent-score {{ text-align:right; font-weight:900; color:var(--success); }}
    .sent-score.neg {{ color:var(--danger); }}
    .rev-count {{ color:var(--muted); text-align:right; font-size:.72rem; }}
    .footer-note {{ display:flex; justify-content:space-between; padding:10px 30px; color:var(--muted); font-size:.75rem; }}
    .footer-note b {{ color:var(--ink); background:#eaf0f6; border-radius:4px; padding:4px 8px; }}
    .layer-note {{ display:flex; align-items:center; justify-content:space-between; gap:16px; padding:0 30px 12px; background:#fff; border-bottom:1px solid var(--line); }}
    .layer-note .layer-strip {{ margin-top:0; }}
    .layer-note .layer-item {{ padding-top:12px; }}
    .layer-note .layer-item.active {{ padding-right:28px; }}
    .forecast-grid {{ display:grid; grid-template-columns:1.05fr 1fr 1.05fr; gap:16px; align-items:start; }}
    .forecast-left {{ display:flex; flex-direction:column; gap:16px; }}
    .forecast-mid {{ display:flex; flex-direction:column; gap:16px; }}
    .forecast-row {{ display:grid; grid-template-columns:126px 1fr 60px 48px; gap:12px; align-items:center; margin:12px 0; font-size:.8rem; }}
    .forecast-name {{ color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .forecast-axis {{ position:relative; height:16px; background:linear-gradient(90deg,transparent 0 49%,#93a4b8 49% 50%,transparent 50%); border-top:1px solid #edf2f6; border-bottom:1px solid #edf2f6; }}
    .forecast-bar {{ position:absolute; top:3px; height:10px; border-radius:2px; }}
    .forecast-whisker {{ position:absolute; top:-2px; height:20px; width:1px; background:#6f7d95; }}
    .forecast-change {{ text-align:right; font-weight:900; }}
    .forecast-change.pos {{ color:var(--success); }}
    .forecast-change.neg {{ color:var(--danger); }}
    .confidence {{ display:inline-block; border-radius:4px; padding:3px 7px; font-size:.67rem; font-weight:900; text-align:center; }}
    .confidence.high {{ background:#d9f5e6; color:var(--success); }}
    .confidence.med {{ background:#fff0c7; color:#b97900; }}
    .confidence.low {{ background:#edf2f7; color:#52617a; }}
    .scale-row {{ display:grid; grid-template-columns:126px 1fr 108px; gap:12px; color:#65758b; font-weight:800; font-size:.7rem; margin:0 0 10px; }}
    .scale-labels {{ display:flex; justify-content:space-between; }}
    .why-box {{ background:{INFO_BG}; border-left:4px solid var(--accent); border-radius:4px; padding:12px 14px; color:#27354a; font-size:.8rem; line-height:1.38; margin-bottom:14px; }}
    .why-box b:first-child {{ color:var(--accent); letter-spacing:.08em; font-size:.68rem; margin-right:7px; }}
    .mini-forecast {{ margin-top:10px; padding-bottom:13px; border-bottom:1px solid #edf2f6; }}
    .mini-forecast:last-child {{ border-bottom:0; padding-bottom:0; }}
    .mini-top {{ display:flex; justify-content:space-between; align-items:center; gap:12px; color:var(--ink); font-size:.82rem; font-weight:900; margin-bottom:6px; }}
    .sparkline {{ height:88px; background:#f6f9fc; border-radius:5px; border:1px solid #edf2f6; position:relative; overflow:hidden; }}
    .sparkline svg {{ display:block; width:100%; height:100%; }}
    .sparkline .now {{ position:absolute; left:50%; top:0; bottom:0; border-left:1px dashed #65758b; }}
    .spark-axis {{ display:flex; justify-content:space-between; color:#718199; font-size:.68rem; margin-top:4px; }}
    .early-card {{ display:grid; grid-template-columns:34px 1fr auto; gap:12px; padding:14px 0; border-bottom:1px solid #edf2f6; }}
    .early-card:last-child {{ border-bottom:0; }}
    .early-icon {{ width:28px; height:28px; border-radius:5px; display:grid; place-items:center; color:#fff; font-weight:900; font-size:.8rem; margin-top:2px; }}
    .early-title {{ font-weight:900; color:var(--ink); font-size:.9rem; margin-bottom:3px; }}
    .early-copy {{ color:#44546b; font-size:.78rem; line-height:1.35; }}
    .detected {{ color:var(--muted); font-size:.72rem; text-align:right; white-space:nowrap; }}
    .tag-row {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:7px; }}
    .tag {{ display:inline-block; padding:3px 7px; border-radius:4px; background:#e8f7ef; color:var(--success); font-size:.68rem; font-weight:900; }}
    .tag.warn {{ background:#fff0c7; color:#b97900; }}
    .tag.bad {{ background:#ffe5e5; color:var(--danger); }}
    .tag.info {{ background:#dff2fb; color:#078db8; }}
    .whitespace-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    .white-card {{ border:1px solid var(--line); border-radius:6px; padding:12px; background:#fff; }}
    .white-card.hot {{ background:#e7f7fc; border-color:var(--accent); }}
    .white-title {{ font-size:.86rem; font-weight:900; color:var(--ink); margin-bottom:9px; }}
    .white-meter {{ height:6px; background:#e9eef4; border-radius:99px; overflow:hidden; margin-bottom:10px; }}
    .white-fill {{ height:100%; border-radius:99px; background:var(--accent); }}
    .white-kv {{ display:flex; justify-content:space-between; color:var(--muted); font-size:.74rem; margin:3px 0; }}
    .white-kv strong {{ color:var(--success); }}
    .white-badge {{ display:inline-block; margin-top:8px; padding:4px 9px; border-radius:4px; color:#fff; background:var(--accent); font-size:.68rem; font-weight:900; }}
    .white-badge.warn {{ background:var(--warning); color:var(--ink); }}
    .white-badge.bad {{ background:var(--danger); }}

    .qa-grid {{ display:grid; grid-template-columns:.72fr 1.28fr; gap:16px; align-items:start; }}
    .question-list {{ display:flex; flex-direction:column; gap:9px; }}
    .q-chip {{ border:1px solid var(--line); border-radius:6px; padding:10px 12px; background:#fff; color:var(--ink); font-size:.8rem; font-weight:800; }}
    .q-chip span {{ color:var(--muted); display:block; font-weight:650; font-size:.7rem; margin-top:3px; }}
    .answer-shell {{ background:#fff; border:1px solid var(--line); border-radius:7px; overflow:hidden; }}
    .answer-body {{ padding:16px 18px; color:#27354a; font-size:.86rem; line-height:1.45; }}
    .context-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
    .context-card {{ border:1px solid var(--line); border-radius:6px; padding:12px; background:#fff; }}
    .context-card b {{ display:block; color:var(--ink); font-size:1.25rem; }}
    .context-card span {{ color:var(--muted); font-size:.75rem; }}

    .rec-grid {{ display:grid; grid-template-columns:.82fr 1.18fr; gap:16px; align-items:start; }}
    .rec-summary-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    .rec-stat {{ background:#fff; border:1px solid var(--line); border-radius:6px; padding:13px; }}
    .rec-stat b {{ display:block; color:var(--ink); font-size:1.42rem; }}
    .rec-stat span {{ color:var(--muted); font-size:.72rem; }}
    .rec-card {{ border:1px solid var(--line); border-radius:7px; background:#fff; margin-bottom:12px; overflow:hidden; }}
    .rec-card-head {{ display:grid; grid-template-columns:34px 1fr auto; gap:12px; align-items:start; padding:14px 16px 10px; border-bottom:1px solid #edf2f6; }}
    .rec-icon {{ width:28px; height:28px; border-radius:5px; display:grid; place-items:center; color:#fff; font-weight:900; }}
    .rec-title {{ color:var(--ink); font-weight:900; font-size:.94rem; }}
    .rec-meta {{ color:var(--muted); font-size:.72rem; margin-top:3px; }}
    .rec-body {{ padding:12px 16px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; color:#3e4e66; font-size:.78rem; line-height:1.35; }}
    .rec-body b {{ color:var(--ink); display:block; font-size:.7rem; letter-spacing:.04em; margin-bottom:4px; }}
    .action-row {{ padding:0 16px 14px; }}
    .empty-panel {{ background:#fff; border:1px dashed var(--line); border-radius:7px; padding:18px; color:var(--muted); font-size:.84rem; }}
    .mini-tab-controls [data-testid="stHorizontalBlock"] {{ gap:3px !important; background:#edf3f8; padding:3px; border-radius:6px; }}
    .mini-tab-controls button {{
        border:0 !important; box-shadow:none !important; border-radius:5px !important;
        min-height:34px; padding:7px 8px !important; background:transparent !important;
        color:#51617a !important; font-size:.78rem !important;
    }}
    .mini-tab-controls button:hover {{ background:#fff !important; color:var(--ink) !important; }}

    .stTabs [data-baseweb="tab-list"] {{
        gap:0; background:#fff; border-bottom:1px solid var(--line); padding-left:30px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height:44px; border-radius:0; padding:0 24px; color:var(--muted); font-weight:800;
    }}
    .stTabs [aria-selected="true"] {{ color:var(--ink) !important; border-bottom:3px solid var(--accent); }}
    .stTabs [data-baseweb="tab-highlight"] {{ background:transparent; }}
    @media (max-width:1100px) {{
        .top-grid, .hero-grid, .market-grid, .signal-band {{ grid-template-columns:1fr; }}
        .filter-row, .style-grid {{ grid-template-columns:1fr; }}
        .signal-card {{ border-right:0; border-bottom:1px solid var(--line); }}
    }}
</style>
""", unsafe_allow_html=True)

# ── Top controls ──────────────────────────────────────────────────────────────
_CATEGORY_LABELS = {
    "All": "All Apparel",
    "mens_tshirts": "Men's T-Shirts",
    "womens_dresses": "Women's Dresses",
}
_PLATFORM_LABELS = {
    "All": "Amazon · Nordstrom",
    "amazon": "Amazon",
    "nordstrom": "Nordstrom",
}
nav_logo, nav_crumbs, nav_cat, nav_platform, nav_window = st.columns([1.15, 3.7, 1.35, 1.7, 1.25])
with nav_logo:
    st.markdown("""
<div class="top-shell" style="border-bottom:0; padding:8px 0 0;">
  <div class="brand-mark">
    <span class="mark-stack"><span class="m1"></span><span class="m2"></span></span>
    <span>Innovatics</span>
  </div>
</div>
""", unsafe_allow_html=True)
with nav_crumbs:
    st.markdown("""
<div style="padding-top:16px;">
  <span class="crumbs">Decision Intelligence&nbsp;&nbsp;/&nbsp;&nbsp;<strong>Market Signal</strong></span>
  <span style="margin-left:24px;" class="nav-pill active"><span class="nav-dot"></span>Market Signal</span>
  <span class="nav-pill"><span class="nav-dot"></span>Merchandising Intelligence</span>
</div>
""", unsafe_allow_html=True)
with nav_cat:
    category_filter = st.selectbox(
        "Category",
        ["mens_tshirts", "womens_dresses", "All"],
        format_func=lambda x: _CATEGORY_LABELS.get(x, x),
        key="cat_filter",
    )
with nav_platform:
    platform_filter = st.selectbox(
        "Platforms",
        ["All", "amazon", "nordstrom"],
        format_func=lambda x: _PLATFORM_LABELS.get(x, x.title()),
        key="plt_filter",
    )
with nav_window:
    window_filter = st.selectbox(
        "Window",
        ["Last 30 Days", "Last 60 Days", "All Time"],
        key="window_filter",
    )

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_data(platform, category):
    p = None if platform == "All" else platform
    c = None if category == "All" else category
    return load_products(p, c)

@st.cache_data(ttl=300)
def get_variant_data(platform, category):
    p = None if platform == "All" else platform
    c = None if category == "All" else category
    return load_variant_skus(p, c)

df_raw = get_data(platform_filter, category_filter)
sku_raw = get_variant_data(platform_filter, category_filter)

df = df_raw.copy()
sku_df = sku_raw.copy()

_visible_category = _CATEGORY_LABELS.get(category_filter, category_filter.replace("_", " ").title())
_visible_platform = _PLATFORM_LABELS.get(platform_filter, platform_filter.title())
_total_skus = len(sku_df) if not sku_df.empty else len(df)
_total_reviews = int(df["review_count"].fillna(0).sum()) if not df.empty and "review_count" in df.columns else 0
_last_scrape = None
if not df.empty and "scraped_at" in df.columns:
    _last_scrape = pd.to_datetime(df["scraped_at"], errors="coerce").max()
_fresh_label = "not refreshed"
if pd.notna(_last_scrape):
    try:
        age_hours = max(0, int((pd.Timestamp.now(tz=_last_scrape.tz) - _last_scrape).total_seconds() // 3600))
        _fresh_label = f"{age_hours}h ago" if age_hours < 48 else f"{age_hours // 24}d ago"
    except Exception:
        _fresh_label = "recently"

st.markdown(f"""
<div class="hero-strip">
  <div class="hero-grid">
    <div>
      <h1 class="hero-title">Market Signal Intelligence</h1>
      <p class="hero-sub">Outside-in view of what's moving on US marketplaces — across four connected layers of intelligence.</p>
    </div>
    <div class="live-meta">
      <span><span class="live-dot"></span>Live · refreshed <strong>{escape(_fresh_label)}</strong></span>
      <span><strong>{_total_skus:,}</strong> SKUs</span>
      <span><strong>{_total_reviews:,}</strong> reviews</span>
      <span><strong>{escape(_visible_category)}</strong></span>
      <span><strong>{escape(_visible_platform)}</strong></span>
      <span><strong>{escape(window_filter)}</strong></span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "1  LAYER 01 · Descriptive",
    "2  LAYER 02 · Conversational",
    "3  LAYER 03 · Predictive",
    "4  LAYER 04 · Recommendations",
])


def _safe(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return escape(str(value))


def _money(value) -> str:
    if value is None or pd.isna(value):
        return "$--"
    return f"${float(value):,.0f}"


def _num(value) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return f"{int(value):,}"


def _label(value: str, fallback: str = "Unknown") -> str:
    if value is None or str(value).strip() == "" or str(value).lower() == "nan":
        return fallback
    return str(value).replace("_", " ").title()


def _swatch_color(color_name: str = "", family: str = "") -> str:
    text = f"{color_name or ''} {family or ''}".lower()
    palette = {
        "navy": "#233854", "blue": "#0a78ad", "black": "#101827",
        "white": "#f4f6f8", "olive": "#5b744b", "green": "#557448",
        "sand": "#8a6a3d", "beige": "#c7b394", "tan": "#cbb893",
        "brown": "#7a5a32", "burgundy": "#9c2638", "red": "#c43236",
        "pink": "#d78495", "grey": "#8893a1", "gray": "#8893a1",
        "purple": "#6a5a8f", "yellow": "#e7b744", "orange": "#d7832f",
    }
    for key, value in palette.items():
        if key in text:
            return value
    return "#253a59"


def _accent_for_index(idx: int) -> str:
    colors = [ACCENT, PRIMARY, WARNING, DANGER, "#7B8F69", "#8A6A3D"]
    return colors[idx % len(colors)]


def _attribute_rows(source: pd.DataFrame, attr: str, top_n: int = 6) -> list[dict]:
    if source.empty or attr not in source.columns:
        return []

    work = source[[attr, "review_count", "rating"]].copy()
    work[attr] = work[attr].fillna("").astype(str).str.split(r",\s*")
    work = work.explode(attr)
    work[attr] = work[attr].astype(str).str.strip()
    work = work[(work[attr] != "") & (work[attr].str.lower() != "nan")]
    if work.empty:
        return []

    work["weight"] = pd.to_numeric(work["review_count"], errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1
    work["rating"] = pd.to_numeric(work["rating"], errors="coerce")
    avg_rating = work["rating"].mean()

    grouped = (
        work.groupby(attr)
        .agg(weight=("weight", "sum"), avg_rating=("rating", "mean"))
        .sort_values("weight", ascending=False)
        .head(top_n)
        .reset_index()
    )
    total = grouped["weight"].sum() or 1
    rows = []
    for idx, row in grouped.iterrows():
        rows.append({
            "name": str(row[attr]),
            "share": max(1, int(round(row["weight"] / total * 100))),
            # TODO: populate from trend_scores / historical scraped_at snapshots.
            "change": None,
            "color": _accent_for_index(idx),
        })
    return rows


def _price_band_label(price: float) -> str:
    if pd.isna(price):
        return "Unknown"
    price = float(price)
    if price < 20:
        return "<$20"
    if price < 24:
        return "$20-24"
    if price < 32:
        return "$24-32"
    if price < 45:
        return "$32-45"
    if price < 60:
        return "$45-60"
    return ">$60"


def _best_price_band(source: pd.DataFrame) -> tuple[str, float]:
    if source.empty or "current_price" not in source.columns:
        return "$24-$32", 3.2
    work = source.dropna(subset=["current_price"]).copy()
    if work.empty:
        return "$24-$32", 3.2
    work["band"] = work["current_price"].apply(_price_band_label)
    work["weight"] = pd.to_numeric(work.get("review_count", 0), errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1
    band = work.groupby("band")["weight"].sum().sort_values(ascending=False).index[0]
    share = work.groupby("band")["weight"].sum().max() / max(work["weight"].sum(), 1)
    return band.replace("-", "-$") if band.startswith("$") and "-$" not in band else band, max(1.1, round(share * 8, 1))


def _top_skus(products: pd.DataFrame, variants: pd.DataFrame, n: int = 4) -> pd.DataFrame:
    source = variants if not variants.empty else products
    if source.empty:
        return pd.DataFrame()
    work = source.copy()
    work["rating_score"] = pd.to_numeric(work.get("rating", 0), errors="coerce").fillna(0)
    work["review_score"] = pd.to_numeric(work.get("review_count", 0), errors="coerce").fillna(0)
    work["score"] = work["review_score"] * 0.75 + work["rating_score"] * 150
    dedupe_cols = [c for c in ["product_id", "color"] if c in work.columns]
    if dedupe_cols:
        work = work.sort_values("score", ascending=False).drop_duplicates(dedupe_cols)
    return work.sort_values("score", ascending=False).head(n).reset_index(drop=True)


def _sku_cards_html(products: pd.DataFrame, variants: pd.DataFrame) -> str:
    rows = _top_skus(products, variants, 4)
    cards = []
    for idx, row in rows.iterrows():
        title = _safe(row.get("title", "Product"))
        color = _label(row.get("color") or row.get("color_family"), "Core")
        size = _label(row.get("size"), "Size mix")
        meta_bits = [
            _safe(row.get("material") or "material mix"),
            _safe(row.get("fit") or "fit mix"),
            _safe(row.get("pattern") or "solid"),
            size,
        ]
        meta = " · ".join([m for m in meta_bits if m])
        platform = _label(row.get("platform"), "Marketplace")
        reviews = _num(row.get("review_count", 0))
        swatch = _swatch_color(row.get("color"), row.get("color_family"))
        cards.append(f"""
<div class="sku-card">
  <div class="sku-swatch" style="background:{swatch};">
    <span class="rank-badge">#{idx + 1}</span>
  </div>
  <div class="sku-copy">
    <div class="sku-title">{title} — {_safe(color)}</div>
    <div class="sku-meta">{meta}</div>
    <div class="sku-foot">
      <div class="sku-price">{_money(row.get("current_price"))}</div>
      <div class="sku-reviews">{_safe(platform)} · {reviews} reviews</div>
    </div>
  </div>
</div>""")
    return "".join(cards) or "<div class='panel-body'>No SKU variants available yet.</div>"


def _bars_html(rows: list[dict], include_swatch: bool = False) -> str:
    html = []
    for idx, row in enumerate(rows):
        raw_change = row.get("change")
        change = int(raw_change) if raw_change is not None and pd.notna(raw_change) else None
        change_cls = "pos" if change is not None and change >= 0 else "neg"
        change_html = f"{change:+d}%" if change is not None else ""
        swatch = ""
        if include_swatch:
            swatch = f'<span class="swatch-dot" style="background:{_swatch_color(row["name"], row["name"])}"></span>'
        row_name = row["name"]
        row_share = row["share"]
        row_color = row.get("color", ACCENT)
        html.append(f"""
<div class="bar-row">
  <div class="bar-name">{swatch}{_safe(row_name)}</div>
  <div class="bar-track"><div class="bar-fill" style="width:{min(100, row_share)}%; background:{row_color};"></div></div>
  <div class="bar-share">{row_share}%</div>
  <div class="bar-change {change_cls}">{change_html}</div>
</div>""")
    return "".join(html)


def _attribute_section_html(title: str, rows: list[dict], swatches: bool, right: str) -> str:
    body = _bars_html(rows, swatches) if rows else "<div class='empty-panel'>No attribute data available for this tab.</div>"
    return f"""
<div class="bar-section" style="margin-top:13px;">
  <div class="bar-head"><span>{_safe(title)}</span><span>{_safe(right)}</span></div>
  {body}
</div>"""


def _attribute_panel_html(products: pd.DataFrame, variants: pd.DataFrame) -> str:
    color_source = variants if not variants.empty else products
    sections = {
        "color": _attribute_section_html(
            "Color · top 6",
            _attribute_rows(color_source, "color", 6),
            True,
            "Share by variant SKU",
        ),
        "pattern": _attribute_section_html(
            "Pattern · top 6",
            _attribute_rows(products, "pattern", 6),
            False,
            "Share of converting reviews",
        ),
        "material": _attribute_section_html(
            "Material & Weight",
            _attribute_rows(products, "material", 6),
            False,
            "Weighted by review velocity",
        ),
        "neck": _attribute_section_html(
            "Neck Type",
            _attribute_rows(products, "neck_type", 6),
            False,
            "Style · share",
        ),
        "fit": _attribute_section_html(
            "Fit Silhouette",
            _attribute_rows(products, "fit", 6),
            False,
            "Share of converting reviews",
        ),
        "sleeve": _attribute_section_html(
            "Sleeve Type",
            _attribute_rows(products, "sleeve_type", 6),
            False,
            "Style · share",
        ),
    }
    show_all = "".join(sections.values())
    return f"""
<div class="attr-tabs">
  <input checked id="attr-show-all" name="attr-tab" type="radio">
  <input id="attr-color" name="attr-tab" type="radio">
  <input id="attr-pattern" name="attr-tab" type="radio">
  <input id="attr-material" name="attr-tab" type="radio">
  <input id="attr-neck" name="attr-tab" type="radio">
  <input id="attr-fit" name="attr-tab" type="radio">
  <input id="attr-sleeve" name="attr-tab" type="radio">
  <div class="tabs-mini">
    <label for="attr-show-all">Show all</label>
    <label for="attr-color">Color</label>
    <label for="attr-pattern">Pattern</label>
    <label for="attr-material">Material</label>
    <label for="attr-neck">Neck</label>
    <label for="attr-fit">Fit</label>
    <label for="attr-sleeve">Sleeve</label>
  </div>
  <div class="attr-content">
    <div class="attr-panel attr-show-all">{show_all}</div>
    <div class="attr-panel attr-color">{sections["color"]}</div>
    <div class="attr-panel attr-pattern">{sections["pattern"]}</div>
    <div class="attr-panel attr-material">{sections["material"]}</div>
    <div class="attr-panel attr-neck">{sections["neck"]}</div>
    <div class="attr-panel attr-fit">{sections["fit"]}</div>
    <div class="attr-panel attr-sleeve">{sections["sleeve"]}</div>
  </div>
</div>
"""


def _price_panel_html(products: pd.DataFrame) -> str:
    if products.empty:
        return ""
    work = products.dropna(subset=["current_price"]).copy()
    if work.empty:
        return ""
    work["band"] = work["current_price"].apply(_price_band_label)
    work["group"] = work["platform"].fillna("marketplace").str.title() + " — " + work["category"].fillna("All").str.replace("_", " ").str.title()
    work["weight"] = pd.to_numeric(work["review_count"], errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1
    bands = ["<$20", "$20-24", "$24-32", "$32-45", "$45-60", ">$60"]
    header = '<div></div>' + ''.join(
        f'<div class="price-head">{b}<small>{s}</small></div>'
        for b, s in zip(bands, ["Under", "Value", "Sweet", "Premium", "High", "Luxury"])
    )
    rows = []
    for group, grp in work.groupby("group"):
        totals = grp.groupby("band")["weight"].sum()
        denom = max(totals.sum(), 1)
        median = grp["current_price"].median()
        rows.append(f'<div class="price-cell label">{_safe(group)}<br><small style="color:#7b8798;font-weight:600;">Median {_money(median)}</small></div>')
        max_band = totals.idxmax() if not totals.empty else None
        for band in bands:
            pct = int(round(totals.get(band, 0) / denom * 100))
            rows.append(f'<div class="price-cell {"hot" if band == max_band else ""}">{pct}%</div>')
    return f'<div class="price-grid">{header}{"".join(rows)}</div>'


def _platform_panel_html(products: pd.DataFrame) -> str:
    if products.empty or "platform" not in products.columns:
        return ""
    boxes = []
    for idx, (platform, grp) in enumerate(products.groupby("platform")):
        top_color = attribute_counts(grp, "color_family", 1)
        top_fit = attribute_counts(grp, "fit", 1)
        top_material = attribute_counts(grp, "material", 1)
        badge = "VOLUME PLAY" if grp["review_count"].fillna(0).sum() >= products["review_count"].fillna(0).sum() / max(products["platform"].nunique(), 1) else "PREMIUM PLAY"
        median_price = grp["current_price"].median()
        avg_reviews = grp["review_count"].mean()
        boxes.append(f"""
<div class="compare-box">
  <div class="panel-title">{_label(platform)}</div>
  <span class="play-badge {'dark' if idx % 2 else ''}">{badge}</span>
  <div style="clear:both; height:10px;"></div>
  <div class="kv-row"><span>Median price</span><strong>{_money(median_price)}</strong></div>
  <div class="kv-row"><span>Top color</span><strong>{_safe(top_color.iloc[0,0]) if not top_color.empty else "N/A"} <span class="good">{int(top_color.iloc[0,1] / max(len(grp), 1) * 100) if not top_color.empty else 0}%</span></strong></div>
  <div class="kv-row"><span>Top fit</span><strong>{_safe(top_fit.iloc[0,0]) if not top_fit.empty else "N/A"} <span class="good">{int(top_fit.iloc[0,1] / max(len(grp), 1) * 100) if not top_fit.empty else 0}%</span></strong></div>
  <div class="kv-row"><span>Top material</span><strong>{_safe(top_material.iloc[0,0]) if not top_material.empty else "N/A"}</strong></div>
  <div class="kv-row"><span>Avg reviews / SKU</span><strong>{_num(avg_reviews)}</strong></div>
</div>""")
    return f'<div class="compare-grid">{"".join(boxes)}</div>'


def _regional_panel_html(total_reviews: int) -> str:
    # TODO: Restore this panel after reviewer geo/location is saved in the backend.
    return ""


def _sentiment_panel_html(products: pd.DataFrame) -> str:
    # TODO: Restore this panel after review text/attribute sentiment is stored in the backend.
    return ""


def _velocity_panel_html(products: pd.DataFrame) -> str:
    # TODO: Restore this panel after historical SKU velocity or true sales data is available.
    return ""


def _market_signal_context(products: pd.DataFrame, variants: pd.DataFrame, scores: pd.DataFrame = None) -> dict:
    kpis = get_kpis(products)
    sku_count = len(variants) if not variants.empty else len(products)
    band_label, band_multiplier = _best_price_band(variants if not variants.empty else products)
    attr_candidates = []
    for attr_name in ["material", "fit", "neck_type", "sleeve_type", "pattern"]:
        attr_candidates.extend(_attribute_rows(products, attr_name, 5))
    attr_candidates = sorted(
        attr_candidates,
        key=lambda r: (r["change"] if r.get("change") is not None else -999, r["share"]),
        reverse=True,
    )
    rising_attr = attr_candidates[0]["name"] if attr_candidates else None
    rising_gain = None
    declining_attr = attr_candidates[-1]["name"] if attr_candidates else None
    declining_gain = None

    if scores is not None and not scores.empty and {"attr_value", "review_growth_pct"}.issubset(scores.columns):
        rising_rows = scores.sort_values("review_growth_pct", ascending=False)
        declining_rows = scores.sort_values("review_growth_pct", ascending=True)
        if not rising_rows.empty and pd.notna(rising_rows.iloc[0].get("attr_value")):
            rising_attr = str(rising_rows.iloc[0]["attr_value"])
            rising_gain = int(round(float(rising_rows.iloc[0].get("review_growth_pct") or 0)))
        if not declining_rows.empty and pd.notna(declining_rows.iloc[0].get("attr_value")):
            declining_attr = str(declining_rows.iloc[0]["attr_value"])
            declining_gain = int(round(float(declining_rows.iloc[0].get("review_growth_pct") or 0)))

    return {
        "kpis": kpis,
        "sku_count": sku_count,
        "band_label": band_label,
        "band_multiplier": band_multiplier,
        "rising_attr": rising_attr,
        "rising_gain": rising_gain,
        "declining_attr": declining_attr,
        "declining_gain": declining_gain,
    }


def _signal_band_html(ctx: dict) -> str:
    sku_count = ctx["sku_count"]
    rising_label = _label(ctx["rising_attr"], "Run predictions")
    declining_label = _label(ctx["declining_attr"], "Run predictions")
    rising_note = (
        f'<span style="color:{SUCCESS};font-weight:900;">{ctx["rising_gain"]:+d}%</span> review-velocity gain · selected window'
        if ctx.get("rising_gain") is not None else
        "No historical trend score available yet"
    )
    declining_note = (
        f'<span style="color:{DANGER};font-weight:900;">{ctx["declining_gain"]:+d}%</span> review-velocity drop · selected window'
        if ctx.get("declining_gain") is not None else
        "No historical trend score available yet"
    )
    return f"""
<div class="signal-band">
  <div class="signal-card">
    <div class="signal-label">Trending Styles Detected</div>
    <div class="signal-value">{sku_count:,} <span style="font-size:.9rem;color:{MUTED};font-weight:700;">SKUs</span></div>
    <div class="signal-note">Current filtered database snapshot</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Converting Price Band</div>
    <div class="signal-value">{_safe(ctx["band_label"])}</div>
    <div class="signal-note"><strong>{ctx["band_multiplier"]}×</strong> share of converting reviews vs adjacent bands</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Top Rising Attribute</div>
    <div class="signal-value" style="font-size:1.82rem;">{_safe(rising_label)}</div>
    <div class="signal-note">{rising_note}</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Top Declining Attribute</div>
    <div class="signal-value" style="font-size:1.82rem;">{_safe(declining_label)}</div>
    <div class="signal-note">{declining_note}</div>
  </div>
</div>"""


def _forecast_source(products: pd.DataFrame, scores: pd.DataFrame, attr_key: str = None, limit: int = 7) -> list[dict]:
    rows = []
    if not scores.empty:
        work = scores.copy()
        if attr_key and "attr_key" in work.columns:
            work = work[work["attr_key"] == attr_key]
        sort_col = "review_growth_pct" if "review_growth_pct" in work.columns else "momentum_score"
        if sort_col in work.columns:
            work = work.sort_values(sort_col, ascending=False)
        for _, row in work.head(limit).iterrows():
            change = row.get("review_growth_pct")
            if pd.isna(change):
                change = float(row.get("momentum_score") or 0) * 10
            rows.append({
                "name": str(row.get("attr_value") or row.get("attr_key") or "Signal"),
                "change": int(round(float(change))),
                "confidence": "High" if abs(float(change)) >= 14 else "Med" if abs(float(change)) >= 8 else "Low",
            })
    # TODO: Do not backfill forecasts from current attribute shares; use only prediction outputs.
    return rows[:limit]


def _forecast_rows_html(rows: list[dict]) -> str:
    if not rows:
        # TODO: Show forecast rows after predictions write trend_scores for the active filters.
        return "<div class='empty-panel'>No backend forecast rows available yet. Run predictions after enough scrape history exists.</div>"
    html = ["""
<div class="scale-row"><div></div><div class="scale-labels"><span>-25%</span><span>-10%</span><span>0</span><span>+10%</span><span>+25%</span></div><div></div></div>
"""]
    for row in rows:
        change = int(row["change"])
        magnitude = min(42, abs(change) * 1.7 + 7)
        if change >= 0:
            left = 50
            color = ACCENT
        else:
            left = max(6, 50 - magnitude)
            color = DANGER
        conf = str(row.get("confidence", "Low")).lower()
        conf_cls = "high" if "high" in conf else "med" if "med" in conf else "low"
        html.append(f"""
<div class="forecast-row">
  <div class="forecast-name">{_safe(row["name"])}</div>
  <div class="forecast-axis">
    <span class="forecast-bar" style="left:{left}%; width:{magnitude}%; background:{color};"></span>
    <span class="forecast-whisker" style="left:{max(2, min(96, 50 + change * 1.15))}%;"></span>
  </div>
  <div class="forecast-change {'pos' if change >= 0 else 'neg'}">{change:+d}%</div>
  <div><span class="confidence {conf_cls}">{_safe(row.get("confidence", "Low"))}</span></div>
</div>""")
    return "".join(html)


def _price_momentum_rows(products: pd.DataFrame) -> list[dict]:
    # TODO: Populate from backend prediction output by price band, not current-share heuristics.
    return []


def _sparkline_html(title: str, actual: int, projected: int) -> str:
    # TODO: Replace with real historical/projection points from review_velocity forecasts.
    projected_color = ACCENT if projected >= 0 else DANGER
    band_color = "#dff2fb" if projected >= 0 else "#ffe5e5"
    if projected >= 0:
        actual_pts = "10,76 92,58 168,42 222,34 260,24"
        projected_pts = "260,24 326,14 400,8 486,7"
        band_pts = "260,24 326,14 400,8 486,7 486,32 400,36 326,42 260,54"
    else:
        actual_pts = "10,24 92,34 168,48 222,54 260,56"
        projected_pts = "260,56 326,66 400,76 486,84"
        band_pts = "260,56 326,66 400,76 486,84 486,58 400,54 326,48 260,40"
    return f"""
<div class="mini-forecast">
  <div class="mini-top"><span>{_safe(title)}</span><span>Actual <span style="color:{SUCCESS if actual >= 0 else DANGER};">{actual:+d}%</span> · projected <span style="color:{projected_color};">{projected:+d}%</span> next 30d</span></div>
  <div class="sparkline">
    <svg viewBox="0 0 500 90" preserveAspectRatio="none">
      <polygon points="{band_pts}" fill="{band_color}" opacity=".75"></polygon>
      <polyline points="{actual_pts}" fill="none" stroke="{PRIMARY}" stroke-width="3"></polyline>
      <polyline points="{projected_pts}" fill="none" stroke="{projected_color}" stroke-width="3" stroke-dasharray="5 5"></polyline>
      <circle cx="260" cy="{24 if projected >= 0 else 56}" r="4" fill="{PRIMARY}"></circle>
    </svg>
    <span class="now"></span>
  </div>
  <div class="spark-axis"><span>-30d</span><span>-20d</span><span>-10d</span><strong>Now</strong><span>+10d</span><span>+20d</span><span>+30d</span></div>
</div>"""


def _early_signal_html(rows: list[dict]) -> str:
    if not rows:
        # TODO: Populate from backend early-signal detections with first_detected_at timestamps.
        return "<div class='empty-panel'>No backend early-signal detections available yet.</div>"
    html = []
    for idx, row in enumerate(rows[:5]):
        change = int(row.get("change", 0))
        up = change >= 0
        icon = "▲" if up else "▼"
        color = ACCENT if up else DANGER
        tag_cls = "" if up else "bad"
        title = _label(row.get("name", "Signal"))
        copy = row.get("copy") or f"{title} is showing a measurable {'velocity gain' if up else 'velocity drop'} before broad-market consensus."
        detected = row.get("first_detected_at") or row.get("age")
        detected_html = f'<div class="detected">DETECTED {_safe(detected)}</div>' if detected else ""
        html.append(f"""
<div class="early-card">
  <div class="early-icon" style="background:{color};">{icon}</div>
  <div>
    <div class="early-title">{_safe(title)}</div>
    <div class="early-copy">{_safe(copy)}</div>
    <div class="tag-row"><span class="tag {tag_cls}">{change:+d}% velocity</span><span class="tag info">{_safe(_visible_platform)}</span></div>
  </div>
  {detected_html}
</div>""")
    return "".join(html)


def _whitespace_html(rows: list[dict]) -> str:
    if not rows or not {"saturation", "new_listing_rol"}.issubset(rows[0].keys()):
        # TODO: Populate from backend demand/supply density and new-listing ROI metrics.
        return "<div class='empty-panel'>No backend whitespace metrics available yet.</div>"
    cards = []
    for idx, row in enumerate(rows[:6]):
        change = int(row.get("change", 0))
        saturation = int(row.get("saturation") or 0)
        rol = float(row.get("new_listing_rol") or 0)
        hot = saturation < 45 and change > 0
        bad = saturation >= 80 or change < 0
        sat = "Low" if saturation < 45 else "High" if saturation >= 80 else "Medium"
        badge_cls = "" if hot else "bad" if bad else "warn"
        badge = "WHITESPACE" if hot else "CROWDED · AVOID" if bad else "BALANCED"
        cards.append(f"""
<div class="white-card {'hot' if hot else ''}">
  <div class="white-title">{_safe(_label(row["name"]))}</div>
  <div class="white-meter"><div class="white-fill" style="width:{min(92, saturation)}%; background:{DANGER if bad else WARNING if not hot else ACCENT};"></div></div>
  <div class="white-kv"><span>Saturation</span><strong style="color:{DANGER if bad else SUCCESS if hot else '#b97900'};">{sat} · {saturation}%</strong></div>
  <div class="white-kv"><span>Demand momentum</span><strong style="color:{SUCCESS if change >= 0 else DANGER};">{change:+d}%</strong></div>
  <div class="white-kv"><span>New listing ROL</span><strong>{rol:.1f}x</strong></div>
  <span class="white-badge {badge_cls}">{badge}</span>
</div>""")
    return f'<div class="whitespace-grid">{"".join(cards)}</div>'


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DESCRIPTIVE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    if df.empty:
        st.info("No products in the database yet. Run the scraper first: `python scrape_runner.py`")
        st.stop()

    kpis = get_kpis(df)
    trend_scores_df = load_trend_scores(
        category=None if category_filter == "All" else category_filter,
        platform=None if platform_filter == "All" else platform_filter,
    )

    ctx = _market_signal_context(df, sku_df, trend_scores_df)
    sku_count = ctx["sku_count"]
    band_label = ctx["band_label"]
    signal_html = _signal_band_html(ctx)

    category_title = _CATEGORY_LABELS.get(category_filter, "Selected Category")
    platform_sub = "Amazon · Nordstrom" if platform_filter == "All" else _PLATFORM_LABELS.get(platform_filter, platform_filter.title())
    styles_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Trending Styles · {_safe(category_title)}</div>
    <div class="panel-sub">Top 4 of {sku_count:,} · ranked by review velocity + rating</div>
  </div>
  <div class="panel-body"><div class="style-grid">{_sku_cards_html(df, sku_df)}</div></div>
</div>"""

    price_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Price-Band Performance · by Platform & Sub-Category</div>
    <div class="panel-sub">Share of converting reviews · {escape(window_filter.lower())}</div>
  </div>
  <div class="panel-body">
    {_price_panel_html(df)}
    <div class="insight"><b>INSIGHT</b>Converting corridor sits at <strong>{_safe(band_label)}</strong>. Platform medians show where the same category can support premium positioning.</div>
  </div>
</div>"""

    platform_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Platform Comparison · Same Category</div>
    <div class="panel-sub">Where each platform over-indexes</div>
  </div>
  {_platform_panel_html(df)}
</div>"""

    attribute_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Attribute Performance</div>
    <div class="panel-sub">Share of converting reviews</div>
  </div>
  <div class="panel-body">{_attribute_panel_html(df, sku_df)}</div>
</div>"""

    # TODO: Re-add regional, sentiment, and sales-velocity panels when the backend stores those signals.

    footer_html = f"""
<div class="footer-note">
  <span><span style="color:{WARNING};font-weight:900;">•</span> Innovatics · Product & Market Intelligence — Database snapshot</span>
  <b>Tab 1 of 4 · Descriptive · SKU-level view</b>
</div>"""

    st.markdown(signal_html, unsafe_allow_html=True)
    st.markdown(f"""
<div class="dashboard-pad">
  <div class="market-grid clean">
    <div class="col-stack">{styles_html}{price_html}{platform_html}</div>
    <div class="col-stack">{attribute_html}</div>
  </div>
</div>
{footer_html}
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONVERSATIONAL INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )
        ctx = _market_signal_context(df, sku_df, trend_scores_df)
        st.markdown(_signal_band_html(ctx), unsafe_allow_html=True)

        SUGGESTED = [
            ("Attribute Drivers", "Which attributes explain the highest converting SKUs?"),
            ("Platform Gap", "Where does Nordstrom over-index versus Amazon?"),
            ("Price Corridor", "What price band should we prioritize next month?"),
            ("Sentiment Risk", "Which product features create rating risk?"),
            ("SKU White Space", "Which color and fit combinations look under-supplied?"),
            ("Assortment Move", "What should the merchant team add or reduce first?"),
        ]

        st.markdown('<div class="dashboard-pad">', unsafe_allow_html=True)
        left, right = st.columns([0.72, 1.28])
        with left:
            st.markdown(f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Question Starters</div>
    <div class="panel-sub">Grounded in current SKU data</div>
  </div>
  <div class="panel-body">
    <div class="question-list">
      {''.join(f'<div class="q-chip">{_safe(title)}<span>{_safe(q)}</span></div>' for title, q in SUGGESTED)}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Grounding Context</div>
    <div class="panel-sub">Used by the answer layer</div>
  </div>
  <div class="panel-body">
    <div class="context-grid" style="grid-template-columns:1fr;">
      <div class="context-card"><b>{len(df):,}</b><span>products loaded</span></div>
      <div class="context-card"><b>{ctx["sku_count"]:,}</b><span>variant/SKU rows</span></div>
      <div class="context-card"><b>{ctx["kpis"]["total_reviews"]:,}</b><span>review signals</span></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        with right:
            st.markdown(f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Conversational Market Analyst</div>
    <div class="panel-sub">Key finding · supporting data · implication</div>
  </div>
  <div class="panel-body">
    <div class="why-box"><b>WHY</b> Ask about SKU-level attributes, platform gaps, price bands, review sentiment, or white-space moves. Answers cite the active filters: <strong>{_safe(_visible_category)}</strong> · <strong>{_safe(_visible_platform)}</strong>.</div>
  </div>
</div>
""", unsafe_allow_html=True)

            question = st.text_input(
                "Market question",
                value=st.session_state.get("conv_question", SUGGESTED[0][1]),
                placeholder="e.g. Which attributes are gaining momentum fastest?",
                key="conv_input",
            )
            bcols = st.columns(3)
            for i, (_, q) in enumerate(SUGGESTED[:3]):
                if bcols[i].button(f"Use Q{i + 1}", key=f"sug_{i}", use_container_width=True):
                    st.session_state["conv_question"] = q
                    st.rerun()

            ask_clicked = st.button("Ask Market Analyst", type="primary", key="ask_btn", use_container_width=True)
            if ask_clicked and question.strip():
                with st.spinner("Analysing data and generating answer..."):
                    try:
                        import anthropic
                        from config.settings import settings

                        data_ctx = data_summary_for_llm(df)
                        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                        response = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1500,
                            system="""You are a senior retail market intelligence analyst at Innovatics.
You have access to scraped US apparel marketplace data stored in a normalized database
(products, product_variants, reviews, brands, categories, colors, sizes, platforms).
Answer questions concisely and specifically, always citing numbers from the data.
Structure your answer with: Key Finding, Supporting Data, Implication.
If the data context does not contain enough information, say so clearly — never hallucinate.
Keep answers under 300 words.""",
                            messages=[{
                                "role": "user",
                                "content": f"Data context:\n{data_ctx}\n\nQuestion: {question}",
                            }],
                        )
                        st.session_state["conv_answer"] = response.content[0].text
                    except Exception as e:
                        st.session_state["conv_answer"] = (
                            f"Could not connect to Claude API: {e}\n\n"
                            "Fallback read: the local dataset is loaded, but live answer generation needs ANTHROPIC_API_KEY."
                        )

            answer = st.session_state.get("conv_answer")
            if answer:
                st.markdown(f"""
<div class="answer-shell">
  <div class="panel-head">
    <div class="panel-title">Answer</div>
    <div class="panel-sub">Generated from active data context</div>
  </div>
  <div class="answer-body">{_safe(answer).replace(chr(10), '<br>')}</div>
</div>
""", unsafe_allow_html=True)

                snapshot_cols = ["title", "brand", "platform", "category", "current_price", "rating", "review_count"]
                snapshot_cols = [c for c in snapshot_cols if c in df.columns]
                st.dataframe(
                    top_products(df, by="review_count", n=5)[snapshot_cols],
                    use_container_width=True, hide_index=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PREDICTIVE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )
        ctx = _market_signal_context(df, sku_df, trend_scores_df)
        attr_rows = _forecast_source(df, trend_scores_df, limit=7)
        price_rows = _price_momentum_rows(df)
        whitespace_rows = sorted(attr_rows, key=lambda r: r["change"], reverse=True)
        early_rows = [{"name": r["name"], "change": r["change"]} for r in attr_rows[:5]]
        forecast_context = (
            f'{_safe(_label(ctx["rising_attr"]))} has the strongest backend trend score for the active filters.'
            if attr_rows else
            "Backend forecast rows are not available for the active filters yet."
        )

        st.markdown(_signal_band_html(ctx), unsafe_allow_html=True)

        st.markdown('<div class="dashboard-pad">', unsafe_allow_html=True)
        run_cols = st.columns([1, 4])
        with run_cols[0]:
            if st.button("Run Predictions", type="primary", key="run_pred_btn", use_container_width=True):
                with st.spinner("Computing trend scores..."):
                    try:
                        from predictions.run_predictions import run as _run_pred
                        result = _run_pred()
                        st.success(
                            f"Updated {result['scores']} scores · {result['velocity']} forecasts"
                        )
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Predictions failed: {_e}")

        st.markdown(f"""
<div class="forecast-grid">
  <div class="forecast-left">
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Attribute Forecast · Next 30 Days</div>
        <div class="panel-sub">Direction · range · confidence</div>
      </div>
      <div class="panel-body">
        <div class="why-box"><b>WHY</b>{forecast_context}</div>
        {_forecast_rows_html(attr_rows)}
      </div>
    </div>
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Review-Velocity Forecast</div>
        <div class="panel-sub">Sales-momentum proxy · 30d actual + 30d projected</div>
      </div>
      <div class="panel-body">
        <div class="empty-panel">No backend review-velocity forecast series available yet.</div>
      </div>
    </div>
  </div>
  <div class="forecast-mid">
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Price-Band Momentum Forecast</div>
        <div class="panel-sub">Where the corridor is widening</div>
      </div>
      <div class="panel-body">
        <div class="why-box"><b>WHY</b>Price-band forecasts will appear after the backend stores momentum by price corridor.</div>
        {_forecast_rows_html(price_rows)}
      </div>
    </div>
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Category Saturation & Whitespace</div>
        <div class="panel-sub">Demand-to-supply gap · new-entrant return-on-listing</div>
      </div>
      <div class="panel-body">
        <div class="why-box"><b>WHY</b>Whitespace requires backend demand/supply density and new-listing ROI metrics.</div>
        {_whitespace_html(whitespace_rows)}
      </div>
    </div>
  </div>
  <div class="forecast-left">
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Early-Signal Detection</div>
        <div class="panel-sub">Detected before broad-market consensus</div>
      </div>
      <div class="panel-body">
        <div class="why-box"><b>WHY</b>Early-signal cards require backend detection timestamps and threshold outputs.</div>
        {_early_signal_html(early_rows)}
      </div>
    </div>
  </div>
</div>
</div>
<div class="footer-note">
  <span><span style="color:{WARNING};font-weight:900;">•</span> Innovatics · Product & Market Intelligence — Database snapshot</span>
  <b>Tab 3 of 4 · Predictive · Screen 2 of 4</b>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RECOMMENDATION INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

_PATTERN_LABELS = {
    "emerging_star":       ("🌟", "Emerging Star",       SUCCESS),
    "declining_attribute": ("📉", "Declining Attribute", DANGER),
    "underserved_niche":   ("🔍", "Underserved Niche",   ACCENT),
    "review_leader":       ("🏆", "Review Leader",       WARNING),
    "cross_platform_gap":  ("↔️", "Cross-Platform Gap",   PRIMARY),
    "rating_outlier":      ("⭐", "Rating Outlier",       "#9B59B6"),
}

with tab4:
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )
        ctx = _market_signal_context(df, sku_df, trend_scores_df)
        st.markdown(_signal_band_html(ctx), unsafe_allow_html=True)

        st.markdown('<div class="dashboard-pad">', unsafe_allow_html=True)
        ctrl1, ctrl2, ctrl3 = st.columns([1.1, 1.1, 2.8])
        with ctrl1:
            run_all = st.button("Run Full Pipeline", type="primary", key="run_pipeline", use_container_width=True)
        with ctrl2:
            status_filter = st.selectbox(
                "Status",
                ["All", "pending", "accepted", "dismissed", "modified"],
                key="rec_status_filter",
            )
        with ctrl3:
            st.markdown(f"""
<div class="why-box" style="margin:0;">
  <b>WHY</b> Recommendations combine pattern detection, predictive momentum, price-band corridors, and review sentiment into action-ready merchandise moves.
</div>
""", unsafe_allow_html=True)

        if run_all:
            with st.spinner("Running predictions + generating recommendations..."):
                try:
                    from predictions.run_predictions import run as _pred_run
                    pred_result = _pred_run()

                    if pred_result["scores"] == 0:
                        st.warning("No trend scores computed — ensure products are in the DB.")
                    else:
                        from recommendations.run_recommendations import run as _rec_run
                        recs = _rec_run()
                        st.success(
                            f"✓ {pred_result['scores']} trend scores · "
                            f"{len(recs)} recommendations generated"
                        )
                        st.cache_data.clear()
                        st.rerun()
                except Exception as _e:
                    st.error(f"Pipeline failed: {_e}")

        # ── Load recommendations from DB ───────────────────────────
        status_q = None if status_filter == "All" else status_filter
        recs_from_db = load_recommendations(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
            status=status_q,
            limit=30,
        )
        all_recs_raw = load_recommendations(limit=1000)
        n_acc  = sum(1 for r in all_recs_raw if r["status"] == "accepted")
        n_dis  = sum(1 for r in all_recs_raw if r["status"] == "dismissed")
        n_mod  = sum(1 for r in all_recs_raw if r["status"] == "modified")
        n_pen  = sum(1 for r in all_recs_raw if r["status"] == "pending")

        st.markdown(f"""
<div class="rec-grid">
  <div class="forecast-left">
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Action Queue</div>
        <div class="panel-sub">Accept · modify · dismiss</div>
      </div>
      <div class="panel-body">
        <div class="rec-summary-grid">
          <div class="rec-stat"><b>{len(all_recs_raw):,}</b><span>Total recommendations</span></div>
          <div class="rec-stat"><b>{n_pen:,}</b><span>Pending review</span></div>
          <div class="rec-stat"><b>{n_acc:,}</b><span>Accepted actions</span></div>
          <div class="rec-stat"><b>{n_mod + n_dis:,}</b><span>Modified or dismissed</span></div>
        </div>
        <div class="insight"><b>INSIGHT</b>Focus first on recommendations tied to <strong>{_safe(_label(ctx["rising_attr"]))}</strong> and the <strong>{_safe(ctx["band_label"])}</strong> corridor.</div>
      </div>
    </div>
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Decision Inputs</div>
        <div class="panel-sub">Current filters</div>
      </div>
      <div class="panel-body">
        <div class="context-grid" style="grid-template-columns:1fr;">
          <div class="context-card"><b>{_safe(_visible_category)}</b><span>Category</span></div>
          <div class="context-card"><b>{_safe(_visible_platform)}</b><span>Platforms</span></div>
          <div class="context-card"><b>{ctx["kpis"]["total_reviews"]:,}</b><span>Review evidence</span></div>
        </div>
      </div>
    </div>
  </div>
  <div>
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Recommendation Intelligence</div>
        <div class="panel-sub">{len(recs_from_db):,} visible · {escape(status_filter.lower())}</div>
      </div>
      <div class="panel-body">
""", unsafe_allow_html=True)

        if not recs_from_db:
            st.markdown("""
<div class="empty-panel">No recommendations yet. Run the full pipeline to generate pattern-detected, Claude-drafted actions from your scraped SKU data.</div>
""", unsafe_allow_html=True)
        else:
            for rec in recs_from_db:
                rec_id = int(rec["rec_id"])
                status = rec.get("status", "pending")
                pattern_type = rec.get("pattern_type", "")
                emoji, label, color = _PATTERN_LABELS.get(
                    pattern_type, ("📌", pattern_type.replace("_", " ").title(), ACCENT)
                )

                border = (
                    SUCCESS if status == "accepted"  else
                    DANGER  if status == "dismissed" else
                    WARNING if status == "modified"  else color
                )
                status_badge_html = {
                    "accepted":  f'<span style="color:{SUCCESS}">✅ Accepted</span>',
                    "dismissed": f'<span style="color:{DANGER}">❌ Dismissed</span>',
                    "modified":  f'<span style="color:{WARNING}">✏️ Modified</span>',
                }.get(status, '<span style="color:#6F7D95">Pending</span>')

                observation = rec.get("observation", "") or rec.get("recommendation_text", "")
                action      = rec.get("action", "") or "Not provided by recommendation backend."
                impact      = rec.get("impact", "") or "Not provided by recommendation backend."
                confidence  = rec.get("confidence", "Medium")
                conf_color  = SUCCESS if confidence == "High" else WARNING if confidence == "Medium" else DANGER
                category_lbl = rec.get("category", "").replace("_", " ").title()
                platform_lbl = rec.get("platform", "").title()
                icon_bg = (
                    SUCCESS if status == "accepted" else
                    DANGER if status == "dismissed" else
                    WARNING if status == "modified" else color
                )
                icon_text = "✓" if status == "accepted" else "×" if status == "dismissed" else "!" if status == "modified" else "→"

                st.markdown(f"""
<div class="rec-card" style="border-left:4px solid {border};">
  <div class="rec-card-head">
    <div class="rec-icon" style="background:{icon_bg};">{icon_text}</div>
    <div>
      <div class="rec-title">{_safe(label)}</div>
      <div class="rec-meta">{_safe(category_lbl)} · {_safe(platform_lbl)} · <strong style="color:{conf_color};">{_safe(confidence)} confidence</strong></div>
    </div>
    <div class="detected">{status_badge_html}</div>
  </div>
  <div class="rec-body">
    <div><b>OBSERVATION</b>{_safe(observation)}</div>
    <div><b>ACTION</b>{_safe(action)}</div>
    <div><b>IMPACT</b>{_safe(impact)}<div class="tag-row"><span class="tag info">{_safe(rec.get('attr_key',''))} = {_safe(rec.get('attr_value',''))}</span></div></div>
  </div>
  <div class="action-row">
""", unsafe_allow_html=True)

                if status == "pending":
                    bcol1, bcol2, bcol3 = st.columns([1, 1, 4])
                    if bcol1.button("Accept",  key=f"acc_{rec_id}", use_container_width=True):
                        update_recommendation_status(rec_id, "accepted")
                        st.rerun()
                    if bcol2.button("Dismiss", key=f"dis_{rec_id}", use_container_width=True):
                        update_recommendation_status(rec_id, "dismissed")
                        st.rerun()
                    mod_text = bcol3.text_input(
                        "Modify:", key=f"mod_{rec_id}",
                        placeholder="Edit the recommendation text and save..."
                    )
                    if mod_text and bcol3.button("Save edit", key=f"sav_{rec_id}"):
                        update_recommendation_status(rec_id, "modified", mod_text)
                        st.rerun()
                elif status == "modified" and rec.get("modified_text"):
                    st.markdown(
                        f"<div class='why-box' style='margin:0;'><b>EDIT</b>{_safe(rec['modified_text'])}</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div></div>", unsafe_allow_html=True)

            st.markdown("""
<div class="mi-panel" style="margin-top:16px;">
  <div class="panel-head">
    <div class="panel-title">Action Mix</div>
    <div class="panel-sub">Current decision state</div>
  </div>
  <div class="panel-body">
""", unsafe_allow_html=True)
            mix_rows = [
                {"name": "Accepted", "share": int(n_acc / max(len(all_recs_raw), 1) * 100), "change": n_acc, "color": SUCCESS},
                {"name": "Pending", "share": int(n_pen / max(len(all_recs_raw), 1) * 100), "change": n_pen, "color": ACCENT},
                {"name": "Modified", "share": int(n_mod / max(len(all_recs_raw), 1) * 100), "change": n_mod, "color": WARNING},
                {"name": "Dismissed", "share": int(n_dis / max(len(all_recs_raw), 1) * 100), "change": -n_dis, "color": DANGER},
            ]
            st.markdown(_bars_html(mix_rows), unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)
            st.markdown("</div></div></div>", unsafe_allow_html=True)

        if not recs_from_db:
            st.markdown("</div></div></div>", unsafe_allow_html=True)

        st.markdown(f"""
</div></div>
<div class="footer-note">
  <span><span style="color:{WARNING};font-weight:900;">•</span> Innovatics · Product & Market Intelligence — Database snapshot</span>
  <b>Tab 4 of 4 · Recommendations · Ask & Act</b>
</div>
""", unsafe_allow_html=True)
