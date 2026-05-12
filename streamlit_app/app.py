"""
app.py — Innovatics Program 1: Product & Market Intelligence
Run: streamlit run streamlit_app/app.py
"""
import sys
import os
import re
import uuid
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, ".")

# Add chatbot directory so orchestrator and its dependencies can be imported
_CHATBOT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chatbot")
)
if _CHATBOT_DIR not in sys.path:
    sys.path.insert(0, _CHATBOT_DIR)

import base64
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
    load_review_velocity_forecast, load_price_band_momentum, load_whitespace_scores,
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
    .sku-card {{ border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#fff; min-height:348px; }}
    .sku-swatch {{ height:238px; position:relative; background:#f7f9fc; overflow:hidden; display:grid; place-items:center; }}
    .sku-swatch.has-image {{ background:#fff !important; border-bottom:1px solid #edf2f6; }}
    .sku-swatch img {{ width:100%; height:100%; object-fit:contain; object-position:center; display:block; }}
    .sku-swatch .swatch-fill {{ position:absolute; inset:0; }}
    .sku-color-strip {{ height:8px; border-bottom:1px solid #edf2f6; }}
    .rank-badge, .heat-badge {{ padding:3px 8px; border-radius:4px; font-size:.7rem; font-weight:900; line-height:1; }}
    .rank-badge {{ display:inline-flex; width:max-content; margin-bottom:8px; background:#fff; color:var(--ink); border:1px solid #d5dde8; }}
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
    .forecast-row {{ display:grid; grid-template-columns:126px 1fr 60px 54px; gap:12px; align-items:center; margin:12px 0; font-size:.8rem; }}
    .forecast-name {{ color:var(--ink); min-width:0; }}
    .forecast-name b {{ display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .forecast-name span {{ display:block; color:var(--muted); font-size:.68rem; line-height:1.25; margin-top:2px; }}
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
    .stage-pill {{ display:inline-block; border-radius:4px; padding:3px 7px; font-size:.67rem; font-weight:900; text-align:center; text-transform:uppercase; }}
    .stage-pill.emerging {{ background:#e8f7ef; color:var(--success); }}
    .stage-pill.accelerating {{ background:#dff2fb; color:#078db8; }}
    .stage-pill.peak {{ background:#fff0c7; color:#b97900; }}
    .stage-pill.plateau {{ background:#edf2f7; color:#52617a; }}
    .stage-pill.declining, .stage-pill.dead {{ background:#ffe5e5; color:var(--danger); }}
    .scale-row {{ display:grid; grid-template-columns:126px 1fr 126px; gap:12px; color:#65758b; font-weight:800; font-size:.7rem; margin:0 0 10px; }}
    .scale-labels {{ display:flex; justify-content:space-between; }}
    .forecast-meta-head {{ display:flex; justify-content:space-between; gap:12px; text-transform:uppercase; letter-spacing:.04em; }}
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

    /* ── Chatbot debug badges (Layer 02) ─────────────────────── */
    .cb-badge {{
        display:inline-block; padding:2px 9px; border-radius:12px;
        font-size:.69rem; font-weight:800; letter-spacing:.04em;
        text-transform:uppercase; margin-right:6px; vertical-align:middle;
    }}
    .cb-sql      {{ background:#dbeafe; color:#1d4ed8; }}
    .cb-vector   {{ background:#dcfce7; color:#15803d; }}
    .cb-trend    {{ background:#fef9c3; color:#a16207; }}
    .cb-hybrid   {{ background:#ede9fe; color:#7c3aed; }}
    .cb-fallback {{ background:#f3f4f6; color:#6b7280; }}
    .cb-conf     {{ font-size:.69rem; color:#9ca3af; vertical-align:middle; }}
    .cb-resolved {{
        font-size:.73rem; color:#6366f1; padding:3px 9px;
        background:#eef2ff; border-left:3px solid #6366f1;
        border-radius:4px; margin:5px 0 2px; display:inline-block;
    }}

    /* ══════════════════════════════════════════════════════════
       CHAT INTERFACE — production-grade light theme
       ══════════════════════════════════════════════════════════ */

    /* ── Scroll container background ───────────────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: #F6F9FC !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }}

    /* ── Message row — full width, no auto-margin collapse ──── */
    @keyframes msg-slide-in {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    [data-testid="stChatMessage"] {{
        animation: msg-slide-in .2s ease forwards !important;
        width: 100% !important;
        margin: 14px 0 !important;
        padding: 0 12px !important;
        box-sizing: border-box !important;
        background: transparent !important;
    }}

    /* ── USER bubble — navy gradient, right-aligned ─────────── */
    [data-testid="stChatMessage"]:has([aria-label*="from user"]) {{
        flex-direction: row-reverse !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from user"] {{
        background: linear-gradient(135deg, {INK} 0%, #1e3a5c 100%) !important;
        border: none !important;
        border-radius: 18px 18px 4px 18px !important;
        padding: 12px 16px !important;
        box-shadow: 0 4px 14px rgba(15,27,45,.22) !important;
        max-width: 76% !important;
        min-width: 60px !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from user"] p,
    [data-testid="stChatMessageContent"][aria-label*="from user"] li,
    [data-testid="stChatMessageContent"][aria-label*="from user"] strong,
    [data-testid="stChatMessageContent"][aria-label*="from user"] em {{
        color: rgba(255,255,255,.93) !important;
        margin-bottom: 4px !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from user"] code {{
        background: rgba(255,255,255,.18) !important;
        color: #fff !important;
        border-radius: 4px !important;
        padding: 1px 5px !important;
    }}

    /* ── ASSISTANT bubble — white card, expands to fill row ─── */
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] {{
        background: #FFFFFF !important;
        border: none !important;
        border-radius: 4px 18px 18px 18px !important;
        padding: 12px 16px !important;
        box-shadow: 0 2px 10px rgba(15,27,45,.07) !important;
        flex: 1 !important;
        min-width: 0 !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] p,
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] li {{
        color: #1a2e44 !important;
    }}

    /* ── Bubble typography ──────────────────────────────────── */
    [data-testid="stChatMessageContent"] p {{
        font-size: .92rem !important;
        line-height: 1.7 !important;
        margin-bottom: 6px !important;
    }}
    [data-testid="stChatMessageContent"] p:last-child {{ margin-bottom: 0 !important; }}
    [data-testid="stChatMessageContent"] ul,
    [data-testid="stChatMessageContent"] ol {{
        font-size: .92rem !important;
        line-height: 1.7 !important;
        padding-left: 20px !important;
        margin: 4px 0 !important;
    }}
    [data-testid="stChatMessageContent"] li {{ margin-bottom: 4px !important; }}
    [data-testid="stChatMessageContent"] strong {{ font-weight: 800 !important; }}
    [data-testid="stChatMessageContent"] code {{
        background: #EEF3F8 !important;
        border-radius: 4px !important;
        padding: 1px 5px !important;
        font-size: .81rem !important;
        color: {INK} !important;
    }}

    /* ── Avatar ─────────────────────────────────────────────── */
    [data-testid="stChatMessageAvatar"] {{
        border-radius: 10px !important;
        flex-shrink: 0 !important;
        align-self: flex-end !important;
    }}

    /* ── All buttons — light pill (Streamlit 1.35 uses .stButton class) ── */
    .stButton button,
    [data-testid="stButton"] button,
    [data-testid="stBaseButton-secondary"] {{
        background:       #F0F5FA !important;
        background-color: #F0F5FA !important;
        color:            #334155 !important;
        border:           1px solid #C8D6E5 !important;
        border-radius:    999px !important;
        font-size:        .78rem !important;
        font-weight:      650 !important;
        padding:          6px 16px !important;
        min-height:       36px !important;
        box-shadow:       none !important;
        transition: background .15s ease, border-color .15s ease,
                    color .15s ease, transform .12s ease !important;
    }}
    .stButton button:hover,
    [data-testid="stButton"] button:hover,
    [data-testid="stBaseButton-secondary"]:hover {{
        background:       #EBF6FF !important;
        background-color: #EBF6FF !important;
        border-color:     {ACCENT} !important;
        color:            {ACCENT} !important;
        transform:        translateY(-1px) !important;
    }}
    .stButton button:active,
    [data-testid="stButton"] button:active,
    [data-testid="stBaseButton-secondary"]:active {{
        transform: translateY(0) !important;
    }}

    /* ── Primary (Send) button — blue ───────────────────────── */
    .stButton button[kind="primary"],
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stBaseButton-primary"] {{
        background:       {ACCENT} !important;
        background-color: {ACCENT} !important;
        border-color:     {ACCENT} !important;
        color:            #FFFFFF !important;
        border-radius:    12px !important;
        font-weight:      700 !important;
        letter-spacing:   .01em !important;
        box-shadow:       0 2px 8px rgba(8,165,214,.28) !important;
        transition: transform .12s ease, box-shadow .15s ease,
                    background .12s ease !important;
    }}
    .stButton button[kind="primary"]:hover,
    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {{
        background:       #0794BF !important;
        background-color: #0794BF !important;
        border-color:     #0794BF !important;
        transform:        translateY(-1px) !important;
        box-shadow:       0 5px 16px rgba(8,165,214,.38) !important;
    }}
    .stButton button[kind="primary"]:active,
    [data-testid="stBaseButton-primary"]:active {{
        transform: translateY(0) !important;
    }}

    /* ── Response metric highlights ─────────────────────────── */
    .rh-pct   {{ color:#0794BF; font-weight:800; }}
    .rh-money {{ color:#18a468; font-weight:800; }}
    .rh-num   {{ color:{INK}; font-weight:800; background:#EEF3F8;
                 border-radius:3px; padding:1px 4px; font-size:.88em; }}

    /* ── Response list + heading polish ─────────────────────── */
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] ul li::marker,
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] ol li::marker {{
        color: {ACCENT} !important;
        font-weight: 800 !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] li {{
        margin-bottom: 5px !important;
        padding-left:  2px !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] h3,
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] h4 {{
        font-size:    .92rem !important;
        color:        {INK} !important;
        font-weight:  900 !important;
        margin:       10px 0 4px !important;
        padding-bottom: 3px !important;
        border-bottom:  2px solid #EEF3F8 !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] hr {{
        border: none !important;
        border-top: 1px solid #EEF3F8 !important;
        margin: 8px 0 !important;
    }}
    [data-testid="stChatMessageContent"][aria-label*="from assistant"] blockquote {{
        border-left:  3px solid {ACCENT} !important;
        background:   #F0F8FE !important;
        border-radius: 0 6px 6px 0 !important;
        margin:       8px 0 !important;
        padding:      8px 12px !important;
        color:        #1a3a52 !important;
    }}

    /* ── Debug expander ──────────────────────────────────────── */
    [data-testid="stExpander"] summary {{
        font-size: .72rem !important;
        color: #8fa3b8 !important;
        padding: 4px 8px !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        color: {ACCENT} !important;
    }}
    [data-testid="stExpander"] > div {{
        border: 1px solid #E8EFF7 !important;
        border-radius: 6px !important;
        padding: 8px !important;
        background: #FAFCFF !important;
    }}

    /* ── Text input — rounded, white, soft shadow ───────────── */
    [data-baseweb="input"] > div {{
        border-radius: 18px !important;
        border-color: #C8D6E5 !important;
        background: #FFFFFF !important;
        min-height: 46px !important;
        box-shadow: 0 1px 6px rgba(15,27,45,.05) !important;
        transition: border-color .15s ease, box-shadow .15s ease !important;
    }}
    [data-baseweb="input"] > div:focus-within {{
        border-color: {ACCENT} !important;
        box-shadow: 0 0 0 3px rgba(8,165,214,.12) !important;
    }}
    [data-baseweb="input"] input {{
        padding: 10px 18px !important;
        font-size: .9rem !important;
        color: {INK} !important;
    }}

    /* ── Chat panel header pill badges ─────────────────────── */
    .chat2-header-badge {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 9px; border-radius: 10px;
        font-size: .67rem; font-weight: 800; letter-spacing: .04em;
        text-transform: uppercase;
    }}
    .chat2-header-badge.sql    {{ background:#dbeafe; color:#1d4ed8; }}
    .chat2-header-badge.vec    {{ background:#dcfce7; color:#15803d; }}
    .chat2-header-badge.hybrid {{ background:#ede9fe; color:#7c3aed; }}

    /* ── Typing dots animation ──────────────────────────────── */
    @keyframes typing-pulse {{
        0%, 100% {{ opacity: .3; transform: translateY(0); }}
        50%       {{ opacity: 1; transform: translateY(-4px); }}
    }}
    .typing-indicator {{
        display: inline-flex; align-items: center; gap: 5px;
        padding: 4px 2px;
    }}
    .typing-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: #8fa3b8; display: inline-block;
        animation: typing-pulse 1.2s ease infinite;
    }}
    .typing-dot:nth-child(2) {{ animation-delay: .18s; }}
    .typing-dot:nth-child(3) {{ animation-delay: .36s; }}

    /* ── Input area separator ───────────────────────────────── */
    .chat-input-separator {{
        border-top: 1px solid #E2EAF4;
        margin: 6px 0 8px;
        background: #fff;
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

@st.cache_data(ttl=300)
def get_predictive_panels(platform, category):
    p = None if platform == "All" else platform
    c = None if category == "All" else category
    return {
        "review_velocity": load_review_velocity_forecast(p, c),
        "price_bands": load_price_band_momentum(p, c),
        "whitespace": load_whitespace_scores(p, c),
    }

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


# ── Chatbot helpers (Layer 02) ────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_chatbot():
    """Import and initialise the RAG orchestrator once per process."""
    try:
        from orchestrator import orchestrator as _orch
        from embedding_manager import setup_table
        try:
            setup_table()
        except Exception:
            pass
        return _orch, None
    except Exception as exc:
        return None, str(exc)


_CB_BADGE = {
    "sql_agent":          ("SQL",      "cb-sql"),
    "vector_agent":       ("Vector",   "cb-vector"),
    "trend_engine_agent": ("Trend",    "cb-trend"),
    "hybrid_agent":       ("Hybrid",   "cb-hybrid"),
    "fallback_agent":     ("Fallback", "cb-fallback"),
    "fallback":           ("Fallback", "cb-fallback"),
}


def _chat2_render_debug(debug: dict) -> None:
    if not debug:
        return
    intent = debug.get("intent") or {}
    tool_response = debug.get("tool_response") or {}
    resolved = debug.get("resolved_question")
    source = tool_response.get("source", "")

    agent = intent.get("agent") or source or ""
    confidence = float(intent.get("confidence") or 0)
    reason = intent.get("reason") or ""
    label, cls = _CB_BADGE.get(agent, ("Unknown", "cb-fallback"))
    filled = round(confidence * 5)
    bar = "●" * filled + "○" * (5 - filled)

    with st.expander(f"Debug · {label} {confidence:.0%}", expanded=False):
        st.markdown(
            f'<span class="cb-badge {cls}">{label}</span>'
            f'<span class="cb-conf">{bar} {confidence:.0%}'
            f"{' — ' + escape(reason) if reason else ''}</span>",
            unsafe_allow_html=True,
        )
        if resolved:
            st.markdown(
                f'<div class="cb-resolved">Understood as: <em>{escape(resolved)}</em></div>',
                unsafe_allow_html=True,
            )

    if not tool_response:
        return

    if source == "sql_agent":
        data = tool_response.get("data") or []
        with st.expander(f"SQL Results · {len(data)} rows", expanded=False):
            if tool_response.get("query"):
                st.code(tool_response["query"], language="sql")
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True)

    elif source == "vector_agent":
        chunks = tool_response.get("data") or []
        if chunks:
            with st.expander(f"Review Sources · {len(chunks)} chunks", expanded=False):
                for c in chunks:
                    st.markdown(
                        f"**Similarity:** {c.get('similarity', 0):.2%} · "
                        f"**Type:** `{c.get('chunk_type', '')}` · "
                        f"**Product ID:** {c.get('product_id', '')}"
                    )
                    st.caption(c.get("review_text", ""))
                    st.divider()

    elif source == "hybrid_agent":
        sql_data = tool_response.get("sql_data") or []
        sql_query = tool_response.get("sql_query", "")
        vec_data = tool_response.get("vector_data") or []
        if sql_data or sql_query:
            with st.expander(f"Matching Products · {len(sql_data)} found", expanded=False):
                if sql_query:
                    st.code(sql_query, language="sql")
                if sql_data:
                    st.dataframe(pd.DataFrame(sql_data), use_container_width=True)
        if vec_data:
            with st.expander(f"Customer Reviews · {len(vec_data)} chunks", expanded=False):
                for c in vec_data:
                    st.markdown(
                        f"**Similarity:** {c.get('similarity', 0):.2%} · "
                        f"**Type:** `{c.get('chunk_type', '')}` · "
                        f"**Product ID:** {c.get('product_id', '')}"
                    )
                    st.caption(c.get("review_text", ""))
                    st.divider()

    elif source == "trend_engine_agent":
        data = tool_response.get("data") or []
        if data:
            with st.expander("Trend Analytics Data", expanded=False):
                st.dataframe(pd.DataFrame(data), use_container_width=True)


# Matches: $12.4M  $1,234  34.5%  1,234,567  2.5x  (outside code spans)
_METRIC_RE = re.compile(
    r'(?<![`\w$])'
    r'(\$[\d,]+(?:\.\d+)?[kKmMbB]?'
    r'|\d+(?:\.\d+)?%'
    r'|\d{1,3}(?:,\d{3})+(?:\.\d+)?'
    r'|\d+(?:\.\d+)?[xX]\b'
    r')(?![`\w%])',
)


def _render_chat_response(text: str) -> None:
    """Render a chat response with metric highlighting and clean typography."""
    # Split on code fences / inline code so we never mangle code blocks
    segments = re.split(r'(```[\s\S]*?```|`[^`\n]+`)', text)

    def _hl(m: re.Match) -> str:
        v = m.group(1)
        if "%" in v:
            return f'<span class="rh-pct">{v}</span>'
        if "$" in v:
            return f'<span class="rh-money">{v}</span>'
        return f'<span class="rh-num">{v}</span>'

    out = []
    for idx, seg in enumerate(segments):
        out.append(seg if idx % 2 == 1 else _METRIC_RE.sub(_hl, seg))

    st.markdown("".join(out), unsafe_allow_html=True)


def _image_data_uri(value) -> str:
    if value is None:
        return ""
    if isinstance(value, memoryview):
        value = value.tobytes()
    elif isinstance(value, bytearray):
        value = bytes(value)
    if not isinstance(value, bytes) or not value:
        return ""

    if value.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif value.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif value.startswith(b"RIFF") and value[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(value).decode('ascii')}"


def _price_range_bounds(products: pd.DataFrame, variants: pd.DataFrame) -> tuple[int, int] | None:
    sources = []
    for source in (variants, products):
        if not source.empty and "current_price" in source.columns:
            prices = pd.to_numeric(source["current_price"], errors="coerce").dropna()
            if not prices.empty:
                sources.append(prices)
    if not sources:
        return None

    all_prices = pd.concat(sources)
    min_price = int(np.floor(float(all_prices.min()) / 5) * 5)
    max_price = int(np.ceil(float(all_prices.max()) / 5) * 5)
    if max_price < min_price:
        return None
    return min_price, max_price


def _filter_by_price_range(source: pd.DataFrame, price_range: tuple[int, int]) -> pd.DataFrame:
    if source.empty or "current_price" not in source.columns:
        return source
    low, high = price_range
    work = source.copy()
    prices = pd.to_numeric(work["current_price"], errors="coerce")
    return work[prices.between(low, high, inclusive="both")]


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
        name = str(row[attr])
        bar_color = _swatch_color(name, name) if attr in {"color", "color_family"} else _accent_for_index(idx)
        rows.append({
            "name": name,
            "share": max(1, int(round(row["weight"] / total * 100))),
            # TODO: populate from trend_scores / historical scraped_at snapshots.
            "change": None,
            "color": bar_color,
            "label_color": bar_color if attr in {"color", "color_family"} else None,
        })
    return rows


def _price_band_config(source: pd.DataFrame) -> list[tuple[str, float | None, str]]:
    if source.empty or "current_price" not in source.columns:
        return [
            ("<$20", 20, "Under"),
            ("$20-24", 24, "Value"),
            ("$24-32", 32, "Sweet"),
            ("$32-45", 45, "Premium"),
            ("$45-60", 60, "High"),
            (">$60", None, "Luxury"),
        ]

    categories = set(source.get("category", pd.Series(dtype=str)).dropna().astype(str))
    median = pd.to_numeric(source.get("current_price"), errors="coerce").dropna().median()
    if "womens_dresses" in categories or (pd.notna(median) and float(median) >= 75):
        return [
            ("<$50", 50, "Entry"),
            ("$50-100", 100, "Value"),
            ("$100-150", 150, "Core"),
            ("$150-250", 250, "Premium"),
            ("$250-400", 400, "High"),
            (">$400", None, "Luxury"),
        ]

    return [
        ("<$20", 20, "Under"),
        ("$20-24", 24, "Value"),
        ("$24-32", 32, "Sweet"),
        ("$32-45", 45, "Premium"),
        ("$45-60", 60, "High"),
        (">$60", None, "Luxury"),
    ]


def _price_band_label(price: float, bands: list[tuple[str, float | None, str]] = None) -> str:
    if pd.isna(price):
        return "Unknown"
    price = float(price)
    bands = bands or _price_band_config(pd.DataFrame())
    for label, upper, _ in bands:
        if upper is None or price < upper:
            return label
    return bands[-1][0]


def _best_price_band(source: pd.DataFrame) -> tuple[str, float]:
    if source.empty or "current_price" not in source.columns:
        return "$24-32", 1.0
    work = source.dropna(subset=["current_price"]).copy()
    if work.empty:
        return "$24-32", 1.0
    if "product_id" in work.columns:
        # Product reviews are product-level. When this function receives SKU rows,
        # dedupe first so one product with many colors/sizes does not multiply demand.
        work = work.sort_values("review_count", ascending=False).drop_duplicates("product_id")
    bands_cfg = _price_band_config(work)
    bands = [b[0] for b in bands_cfg]
    work["band"] = work["current_price"].apply(lambda p: _price_band_label(p, bands_cfg))
    work["weight"] = pd.to_numeric(work.get("review_count", 0), errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1
    totals = work.groupby("band")["weight"].sum().reindex(bands, fill_value=0)
    band = totals.idxmax()
    idx = bands.index(band)
    adjacent = []
    if idx > 0:
        adjacent.append(float(totals.iloc[idx - 1]))
    if idx < len(bands) - 1:
        adjacent.append(float(totals.iloc[idx + 1]))
    adjacent_avg = sum(adjacent) / len(adjacent) if adjacent else 0
    if adjacent_avg <= 0:
        adjacent_avg = max((float(totals.sum()) - float(totals.loc[band])) / max(len(bands) - 1, 1), 1)
    multiplier = max(1.0, round(float(totals.loc[band]) / max(adjacent_avg, 1), 1))
    multiplier = min(multiplier, 9.9)
    return band, multiplier


def _top_skus(products: pd.DataFrame, variants: pd.DataFrame, n: int = 4) -> pd.DataFrame:
    source = variants if not variants.empty else products
    if source.empty:
        return pd.DataFrame()
    work = source.copy()
    work["rating_score"] = pd.to_numeric(work.get("rating", 0), errors="coerce").fillna(0)
    work["review_score"] = pd.to_numeric(work.get("review_count", 0), errors="coerce").fillna(0)
    work["score"] = work["review_score"] * 0.75 + work["rating_score"] * 150
    if "product_id" in work.columns:
        work = work.sort_values("score", ascending=False).drop_duplicates("product_id")
    return work.sort_values("score", ascending=False).head(n).reset_index(drop=True)


def _sku_cards_html(products: pd.DataFrame, variants: pd.DataFrame) -> str:
    rows = _top_skus(products, variants, 4)
    cards = []
    for idx, row in rows.iterrows():
        title = _safe(row.get("title", "Product"))
        url = _safe(row.get("url"))
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
        image_src = _image_data_uri(row.get("image"))
        media_class = "sku-swatch has-image" if image_src else "sku-swatch"
        media_style = "" if image_src else f"background:{swatch};"
        color_strip = f'<div class="sku-color-strip" style="background:{swatch};"></div>' if image_src else ""
        visual = (
            f'<img src="{image_src}" alt="{title}">'
            if image_src
            else f'<div class="swatch-fill" style="background:{swatch};"></div>'
        )
        cards.append(f"""
<div class="sku-card">
  <div class="{media_class}" style="{media_style}">
    {visual}
  </div>
  {color_strip}
  <div class="sku-copy">
    <a class="rank-badge" href="{url}" target="_blank" rel="noopener noreferrer">#{idx + 1}</a>
    <div class="sku-title">{title} — {_safe(color)}</div>
    <div class="sku-meta">{meta}</div>
    <div class="sku-foot">
      <div>
        <div class="sku-price">{_money(row.get("current_price"))}</div>
        <div style="color:{MUTED};font-size:.68rem;font-weight:700;line-height:1;">scraped price</div>
      </div>
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
        label_style = f' style="color:{row["label_color"]};font-weight:900;"' if row.get("label_color") else ""
        html.append(f"""
<div class="bar-row">
  <div class="bar-name"{label_style}>{swatch}{_safe(row_name)}</div>
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
            "Color Family · top 6",
            _attribute_rows(color_source, "color_family", 6),
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
    bands_cfg = _price_band_config(work)
    bands = [b[0] for b in bands_cfg]
    work["band"] = work["current_price"].apply(lambda p: _price_band_label(p, bands_cfg))
    work["group"] = work["platform"].fillna("marketplace").str.title() + " — " + work["category"].fillna("All").str.replace("_", " ").str.title()
    work["weight"] = pd.to_numeric(work["review_count"], errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1
    header = '<div></div>' + ''.join(
        f'<div class="price-head">{b}<small>{s}</small></div>'
        for b, _, s in bands_cfg
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
  <div class="kv-row"><span>Avg reviews / product</span><strong>{_num(avg_reviews)}</strong></div>
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


_LIFECYCLE_LABELS = {
    "emerging":     "Emerging",
    "accelerating": "Accelerating",
    "peak":         "Peak",
    "plateau":      "Plateau",
    "declining":    "Declining",
    "dead":         "Dead",
}


def _stage_key(stage: str) -> str:
    raw = str(stage or "plateau").strip().lower()
    return raw if raw in _LIFECYCLE_LABELS else "plateau"


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
            weeks_observed = int(row.get("weeks_observed") or 0)
            latest_share = float(row.get("latest_week_share") or 0)
            previous_share = float(row.get("previous_week_share") or 0)
            if weeks_observed >= 2:
                change = (latest_share - previous_share) * 100
            else:
                change = row.get("review_growth_pct")
                if pd.isna(change):
                    change = float(row.get("momentum_score") or 0) * 10
            rows.append({
                "name": str(row.get("attr_value") or row.get("attr_key") or "Signal"),
                "change": int(round(float(change))),
                "confidence": "High" if abs(float(change)) >= 14 else "Med" if abs(float(change)) >= 8 else "Low",
                "stage": _stage_key(row.get("lifecycle_stage")),
                "action": row.get("retailer_action") or "",
                "lifecycle_explanation": row.get("lifecycle_explanation") or "",
                "weeks_observed": weeks_observed,
                "latest_week_share": latest_share,
                "previous_week_share": previous_share,
            })
    # TODO: Do not backfill forecasts from current attribute shares; use only prediction outputs.
    return rows[:limit]


def _forecast_rows_html(rows: list[dict]) -> str:
    if not rows:
        # TODO: Show forecast rows after predictions write trend_scores for the active filters.
        return "<div class='empty-panel'>No backend forecast rows available yet. Run predictions after enough scrape history exists.</div>"
    html = ["""
<div class="scale-row">
  <div>Signal name</div>
  <div class="scale-labels"><span>-25%</span><span>-10%</span><span>0</span><span>+10%</span><span>+25%</span></div>
  <div class="forecast-meta-head"><span>Direction</span><span>Confidence</span></div>
</div>
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
        stage = _stage_key(row.get("stage"))
        action = row.get("action") or "Monitor daily"
        confidence = str(row.get("confidence") or "Low")
        conf_cls = confidence.lower()
        if conf_cls not in {"high", "med", "low"}:
            conf_cls = "low"
        html.append(f"""
<div class="forecast-row">
  <div class="forecast-name"><b>{_safe(row["name"])}</b><span>{_safe(action)}</span></div>
  <div class="forecast-axis">
    <span class="forecast-bar" style="left:{left}%; width:{magnitude}%; background:{color};"></span>
    <span class="forecast-whisker" style="left:{max(2, min(96, 50 + change * 1.15))}%;"></span>
  </div>
  <div class="forecast-change {'pos' if change >= 0 else 'neg'}">{change:+d}%</div>
  <div><span class="confidence {conf_cls}">{_safe(confidence)}</span></div>
</div>""")
    return "".join(html)


def _price_momentum_rows(products: pd.DataFrame) -> list[dict]:
    return []


def _sparkline_html(title: str, actual: int, projected: int) -> str:
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


def _review_velocity_html(rows: list[dict]) -> str:
    if not rows:
        return "<div class='empty-panel'>No daily review history available yet. Run daily scraping to build the forecast.</div>"
    html = []
    for row in rows[:4]:
        actual = int(round(float(row.get("actual_change_pct") or 0)))
        projected = int(round(float(row.get("projected_change_pct") or 0)))
        title = row.get("name") or "Review velocity"
        current = _num(row.get("current_reviews") or 0)
        conf = str(row.get("confidence") or "Low").lower()
        html.append(
            _sparkline_html(title, actual, projected) +
            f'<div class="tag-row" style="margin-top:-7px;margin-bottom:9px;">'
            f'<span class="tag info">{current} current reviews</span>'
            f'<span class="tag warn">{_safe(conf.title())} confidence</span>'
            f'</div>'
        )
    return "".join(html)


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
        if row.get("stage") == "plateau":
            color = WARNING
            icon = "~"
        tag_cls = "" if up else "bad"
        title = _label(row.get("name", "Signal"))
        stage = _stage_key(row.get("stage"))
        action = row.get("action") or "Monitor daily"
        copy = row.get("copy") or (
            f"{title} has crossed the daily momentum screen and is currently "
            f"{_LIFECYCLE_LABELS[stage].lower()}. {action}."
        )
        detected = row.get("first_detected_at") or row.get("age")
        if not detected:
            detected = f"{max(1, int(row.get('weeks_observed') or idx + 1))}D AGO"
        detected_html = f'<div class="detected">DETECTED {_safe(detected)}</div>' if detected else ""
        html.append(f"""
<div class="early-card">
  <div class="early-icon" style="background:{color};">{icon}</div>
  <div>
    <div class="early-title">{_safe(title)}</div>
    <div class="early-copy">{_safe(copy)}</div>
    <div class="tag-row"><span class="tag {tag_cls}">{change:+d}% momentum</span><span class="tag info">{_safe(_LIFECYCLE_LABELS[stage])}</span></div>
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

    desc_df = df.copy()
    desc_sku_df = sku_df.copy()
    price_bounds = _price_range_bounds(desc_df, desc_sku_df)
    if price_bounds:
        min_price, max_price = price_bounds
        if min_price < max_price:
            price_col, count_col, _ = st.columns([1.25, 1.1, 4.65])
            with price_col:
                selected_price_range = st.slider(
                    "Price",
                    min_value=min_price,
                    max_value=max_price,
                    value=(min_price, max_price),
                    step=5,
                    format="$%d",
                    key="descriptive_price_range",
                )
            desc_df = _filter_by_price_range(desc_df, selected_price_range)
            desc_sku_df = _filter_by_price_range(desc_sku_df, selected_price_range)
            with count_col:
                st.caption(
                    f"{_money(selected_price_range[0])}-{_money(selected_price_range[1])} · "
                    f"{len(desc_sku_df) if not desc_sku_df.empty else len(desc_df):,} rows"
                )
        else:
            st.caption(f"Price range: {_money(min_price)}")

    if desc_df.empty and desc_sku_df.empty:
        st.warning("No products match the selected price range. Showing the full descriptive view.")
        desc_df = df.copy()
        desc_sku_df = sku_df.copy()

    kpis = get_kpis(desc_df)
    trend_scores_df = load_trend_scores(
        category=None if category_filter == "All" else category_filter,
        platform=None if platform_filter == "All" else platform_filter,
    )

    ctx = _market_signal_context(desc_df, desc_sku_df, trend_scores_df)
    sku_count = ctx["sku_count"]
    band_label = ctx["band_label"]
    signal_html = _signal_band_html(ctx)

    category_title = _CATEGORY_LABELS.get(category_filter, "Selected Category")
    platform_sub = "Amazon · Nordstrom" if platform_filter == "All" else _PLATFORM_LABELS.get(platform_filter, platform_filter.title())
    styles_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Trending Styles · {_safe(category_title)}</div>
    <div class="panel-sub">Top 4 unique products of {sku_count:,} SKU rows · ranked by reviews + rating</div>
  </div>
  <div class="panel-body"><div class="style-grid">{_sku_cards_html(desc_df, desc_sku_df)}</div></div>
</div>"""

    price_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Price-Band Performance · by Platform & Sub-Category</div>
    <div class="panel-sub">Share of converting reviews · {escape(window_filter.lower())}</div>
  </div>
  <div class="panel-body">
    {_price_panel_html(desc_df)}
    <div class="insight"><b>INSIGHT</b>Converting corridor sits at <strong>{_safe(band_label)}</strong>. Platform medians show where the same category can support premium positioning.</div>
  </div>
</div>"""

    platform_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Platform Comparison · Same Category</div>
    <div class="panel-sub">Where each platform over-indexes</div>
  </div>
  {_platform_panel_html(desc_df)}
</div>"""

    attribute_html = f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Attribute Performance</div>
    <div class="panel-sub">Share of converting reviews</div>
  </div>
  <div class="panel-body">{_attribute_panel_html(desc_df, desc_sku_df)}</div>
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
  <div class="panel-head" style="min-height:54px; padding:0 18px;">
    <div style="display:flex; align-items:center; gap:10px;">
      <div style="width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,{INK} 0%,#1c3353 100%);
                  display:grid;place-items:center;font-size:.9rem;flex-shrink:0;">🤖</div>
      <div>
        <div class="panel-title" style="line-height:1.1;">Conversational Market Analyst</div>
        <div style="color:{MUTED};font-size:.71rem;margin-top:1px;">Active filters:
          <strong style="color:{INK};">{_safe(_visible_category)}</strong> ·
          <strong style="color:{INK};">{_safe(_visible_platform)}</strong>
        </div>
      </div>
    </div>
    <div style="display:flex;gap:5px;align-items:center;flex-shrink:0;">
      <span class="chat2-header-badge sql">SQL</span>
      <span class="chat2-header-badge vec">Vector</span>
      <span class="chat2-header-badge hybrid">Hybrid</span>
    </div>
  </div>
  <div style="padding:10px 18px 12px; border-bottom:1px solid #edf2f6;">
    <div style="background:#EDF8FF;border-left:3px solid {ACCENT};border-radius:5px;
                padding:9px 13px;font-size:.78rem;line-height:1.42;color:#1a3a52;">
      Ask about SKU attributes, platform gaps, price bands, review sentiment, or white-space
      opportunities — answers are grounded in your live product &amp; review data.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            st.markdown(
                "<div style='background:#fff;border:1px solid #E2EAF4;border-radius:12px;"
                "padding:12px 14px 10px;margin-top:8px;'>",
                unsafe_allow_html=True,
            )

            # ── Session state init ────────────────────────────────────────────
            if "chat2_session_id" not in st.session_state:
                st.session_state["chat2_session_id"] = str(uuid.uuid4())
            if "chat2_messages" not in st.session_state:
                st.session_state["chat2_messages"] = []
            if "chat2_pending" not in st.session_state:
                st.session_state["chat2_pending"] = None
            if "chat2_input_ver" not in st.session_state:
                st.session_state["chat2_input_ver"] = 0

            # ── Load chatbot (cached across reruns) ───────────────────────────
            _orch, _chatbot_err = _get_chatbot()

            if _chatbot_err:
                st.error(f"Chatbot unavailable — check GROQ_API_KEY and DB connection. ({_chatbot_err})")
            else:
                # ── Chat history ──────────────────────────────────────────────
                chat_area = st.container(height=460, border=False)
                with chat_area:
                    if not st.session_state["chat2_messages"]:
                        st.markdown(
                            "<div style='display:flex;flex-direction:column;align-items:center;"
                            "justify-content:center;height:380px;gap:14px;'>"
                            "<div style='width:52px;height:52px;border-radius:14px;"
                            "background:linear-gradient(135deg,#0F1B2D 0%,#1c3353 100%);"
                            "display:grid;place-items:center;font-size:1.4rem;"
                            "box-shadow:0 4px 16px rgba(15,27,45,.22);'>🤖</div>"
                            "<div style='text-align:center;'>"
                            "<div style='color:#3a4d62;font-size:.9rem;font-weight:700;"
                            "margin-bottom:5px;'>Ready to analyse your data</div>"
                            "<div style='color:#8fa3b8;font-size:.79rem;line-height:1.5;max-width:300px;'>"
                            "Ask about products, pricing, trends, or competitor gaps — "
                            "answers are grounded in live SKU &amp; review data."
                            "</div></div></div>",
                            unsafe_allow_html=True,
                        )
                    for msg in st.session_state["chat2_messages"]:
                        _avatar = "🤖" if msg["role"] == "assistant" else "👤"
                        with st.chat_message(msg["role"], avatar=_avatar):
                            if msg["role"] == "assistant":
                                _render_chat_response(msg["content"])
                            else:
                                st.markdown(msg["content"])
                            if msg.get("debug"):
                                _chat2_render_debug(msg["debug"])

                # ── Suggestion chips ──────────────────────────────────────────
                st.markdown(
                    "<div style='margin:8px 0 4px;color:#8fa3b8;font-size:.71rem;"
                    "font-weight:700;letter-spacing:.05em;text-transform:uppercase;'>"
                    "Quick questions</div>",
                    unsafe_allow_html=True,
                )
                bcols = st.columns(3)
                for i, (title, q) in enumerate(SUGGESTED[:3]):
                    if bcols[i].button(
                        title, key=f"c2_sug_{i}",
                        use_container_width=True, help=q,
                    ):
                        st.session_state["chat2_pending"] = q
                        st.rerun()

                # ── Input row ─────────────────────────────────────────────────
                st.markdown("<div class='chat-input-separator'></div>", unsafe_allow_html=True)
                in_col, send_col, clr_col = st.columns([4.8, 1.05, 0.8])
                with in_col:
                    typed = st.text_input(
                        "chat2_typed",
                        value="",
                        placeholder="Ask about attributes, gaps, pricing, reviews…",
                        key=f"chat2_input_{st.session_state['chat2_input_ver']}",
                        label_visibility="collapsed",
                    )
                with send_col:
                    send_clicked = st.button(
                        "Send →", type="primary", key="chat2_send",
                        use_container_width=True,
                    )
                with clr_col:
                    if st.button("Clear", key="chat2_clear", use_container_width=True):
                        _orch.clear_session(st.session_state["chat2_session_id"])
                        st.session_state["chat2_messages"] = []
                        st.session_state["chat2_session_id"] = str(uuid.uuid4())
                        st.rerun()

                # ── Process question ──────────────────────────────────────────
                pending_q = st.session_state.get("chat2_pending")
                if pending_q:
                    st.session_state["chat2_pending"] = None

                user_q = pending_q or (
                    typed.strip() if send_clicked and typed.strip() else None
                )

                if user_q:
                    st.session_state["chat2_input_ver"] += 1  # bump key → fresh empty widget
                    st.session_state["chat2_messages"].append(
                        {"role": "user", "content": user_q}
                    )
                    with chat_area:
                        with st.chat_message("assistant", avatar="🤖"):
                            st.markdown(
                                '<div class="typing-indicator">'
                                '<span class="typing-dot"></span>'
                                '<span class="typing-dot"></span>'
                                '<span class="typing-dot"></span>'
                                '</div>',
                                unsafe_allow_html=True,
                            )
                    result = _orch.process_question(
                        session_id=st.session_state["chat2_session_id"],
                        question=user_q,
                    )
                    response = result.get("response") or "Unable to process the request."
                    debug = {
                        "intent": result.get("intent"),
                        "tool_response": result.get("tool_response"),
                        "resolved_question": result.get("resolved_question"),
                    }
                    st.session_state["chat2_messages"].append({
                        "role": "assistant",
                        "content": response,
                        "debug": debug if (result.get("intent") or result.get("tool_response")) else None,
                    })
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # close chat white card

        st.markdown("</div>", unsafe_allow_html=True)  # close dashboard-pad


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
        predictive_panels = get_predictive_panels(platform_filter, category_filter)
        attr_rows = _forecast_source(df, trend_scores_df, limit=7)
        price_rows = predictive_panels["price_bands"]
        whitespace_rows = predictive_panels["whitespace"]
        review_velocity_rows = predictive_panels["review_velocity"]
        early_rows = [
            {
                "name": r["name"],
                "change": r["change"],
                "stage": r.get("stage"),
                "action": r.get("action"),
                "weeks_observed": r.get("weeks_observed"),
                "copy": (
                    f"{_label(r['name'])} is showing {r['change']:+d}% daily momentum. "
                    f"Current lifecycle: {_LIFECYCLE_LABELS[_stage_key(r.get('stage'))].lower()}."
                ),
            }
            for r in attr_rows[:5]
        ]
        forecast_context = (
            f'{_safe(_label(ctx["rising_attr"]))} has the strongest backend trend score; each attribute is now mapped to a daily lifecycle stage and retailer action.'
            if attr_rows else
            "Backend forecast rows are not available for the active filters yet."
        )
        max_weeks = max((int(r.get("weeks_observed") or 0) for r in attr_rows), default=0)
        if attr_rows and max_weeks < 2:
            forecast_context = (
                "Snapshot baseline mode from scraped_at: fewer than 3 daily scrape points exist, "
                "so lifecycle actions are inferred from current momentum until daily history builds."
            )
        elif attr_rows and max_weeks < 3:
            forecast_context = (
                "Two-day comparison mode from scraped_at: current scrape day is compared with the previous scrape day; "
                "full lifecycle curve starts after 3 daily points."
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
        <div class="panel-sub">Direction · range · lifecycle stage</div>
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
        {_review_velocity_html(review_velocity_rows)}
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
        <div class="why-box"><b>WHY</b>Uses daily variant observations to detect which price corridor is gaining SKU share in the active market slice.</div>
        {_forecast_rows_html(price_rows)}
      </div>
    </div>
    <div class="mi-panel">
      <div class="panel-head">
        <div class="panel-title">Category Saturation & Whitespace</div>
        <div class="panel-sub">Demand-to-supply gap · new-entrant return-on-listing</div>
      </div>
      <div class="panel-body">
        <div class="why-box"><b>WHY</b>Compares current variant saturation against rating and review demand. Low supply plus strong demand becomes whitespace.</div>
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
        <div class="why-box"><b>WHY</b>Early signals come from the same daily lifecycle rows before they reach broad-market saturation.</div>
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
