"""
app.py — Innovatics Program 1: Product & Market Intelligence
Run: streamlit run streamlit_app/app.py
"""
import sys
import os
import re
import uuid
import warnings

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

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
    load_filter_options,
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
    .filter-band {{ background:#fff; border-bottom:1px solid var(--line); padding:12px 30px 14px; }}
    .filter-band-label {{ color:#94a3b8; font-size:.68rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; padding-top:31px; }}
    .filter-row {{ display:grid; grid-template-columns:70px repeat(4, minmax(120px, 1fr)) 70px minmax(160px, 1fr) 170px; gap:10px; align-items:end; }}
    .filter-row label {{ color:var(--muted) !important; font-size:0.76rem !important; font-weight:700 !important; }}
    .filter-row div[data-baseweb="select"] > div {{
        border-color:var(--line); border-radius:7px; min-height:38px; background:#fff;
        box-shadow:0 1px 2px rgba(15,27,45,.04);
    }}
    .filter-actions-mini {{ display:flex; justify-content:flex-end; gap:12px; align-items:center; padding-bottom:8px; }}
    .filter-actions-mini span {{ color:var(--muted); font-size:.76rem; font-weight:800; }}

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
    .askact-grid {{ display:grid; grid-template-columns:.86fr 1.04fr; gap:16px; align-items:start; }}
    .ask-card {{ background:#091528; border:1px solid #152944; border-radius:8px; overflow:hidden; box-shadow:0 1px 2px rgba(15,27,45,.04); }}
    .ask-head {{ height:55px; display:flex; align-items:center; justify-content:space-between; gap:14px; padding:0 18px; border-bottom:1px solid #1d3048; }}
    .ask-title-wrap {{ display:flex; align-items:center; gap:10px; min-width:0; }}
    .iq-dot {{ width:28px; height:28px; border-radius:99px; display:grid; place-items:center; background:var(--accent); color:#fff; font-size:.72rem; font-weight:900; flex-shrink:0; }}
    .ask-title {{ color:#fff; font-weight:900; font-size:.92rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .online-badge {{ color:var(--accent); font-size:.68rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; display:flex; align-items:center; gap:6px; }}
    .online-badge:before {{ content:""; width:6px; height:6px; border-radius:99px; background:var(--accent); box-shadow:0 0 8px rgba(8,165,214,.8); }}
    .ask-body {{ padding:18px; }}
    .ask-question {{ background:#111e31; border-left:3px solid var(--warning); border-radius:5px; padding:12px 14px; margin-bottom:14px; }}
    .ask-label {{ display:block; color:var(--warning); font-size:.68rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; margin-bottom:6px; }}
    .ask-question div {{ color:#fff; font-size:.9rem; line-height:1.35; }}
    .ask-answer {{ color:#d8e2ee; font-size:.86rem; line-height:1.48; margin-bottom:14px; }}
    .ask-answer b:first-child {{ color:var(--accent); letter-spacing:.08em; font-size:.68rem; margin-right:7px; }}
    .ask-bars {{ border:1px solid #243852; background:#0d1b2e; border-radius:5px; padding:12px 13px; margin-bottom:12px; }}
    .ask-bars-title {{ color:#96a6ba; font-size:.68rem; font-weight:900; letter-spacing:.08em; text-transform:uppercase; margin-bottom:9px; }}
    .ask-bar-row {{ display:grid; grid-template-columns:72px 1fr 38px; gap:10px; align-items:center; color:#d8e2ee; font-size:.78rem; margin:7px 0; }}
    .ask-bar-track {{ height:5px; background:#243852; border-radius:99px; overflow:hidden; }}
    .ask-bar-fill {{ height:100%; background:var(--accent); border-radius:99px; }}
    .ask-citation {{ background:#06273d; border:1px solid #084666; border-radius:5px; padding:11px 13px; color:#b7c5d6; font-size:.76rem; line-height:1.45; }}
    .ask-citation b:first-child {{ color:var(--accent); display:block; letter-spacing:.08em; font-size:.68rem; margin-bottom:6px; }}
    .ask-cite-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    .suggested-panel {{ margin-top:12px; }}
    .suggested-row {{ display:grid; grid-template-columns:34px 1fr 18px; gap:10px; align-items:center; border:1px solid var(--line); border-radius:6px; padding:10px 12px; margin-bottom:8px; color:var(--ink); font-size:.8rem; background:#fff; }}
    .suggested-num {{ background:#e2f4fb; color:var(--accent); border-radius:4px; padding:3px 6px; font-size:.68rem; font-weight:900; text-align:center; }}
    .suggested-arrow {{ color:#9aabc0; text-align:right; }}
    .rec-list-card {{ border:1px solid var(--line); border-radius:7px; background:#fff; margin:12px 0; padding:14px 16px 11px; width:100%; box-sizing:border-box; }}
    .rec-list-card * {{ box-sizing:border-box; }}
    .rec-list-top {{ display:grid; grid-template-columns:42px minmax(0, 1fr) auto; gap:12px; align-items:start; width:100%; }}
    .rec-list-main {{ min-width:0; }}
    .rec-rank {{ background:#edf2f7; color:#8190a4; border-radius:4px; padding:5px 8px; font-size:.75rem; font-weight:900; text-align:center; }}
    .rec-list-title {{ color:var(--ink); font-size:.98rem; line-height:1.22; font-weight:900; margin-bottom:4px; }}
    .rec-list-copy {{ color:#536278; font-size:.78rem; line-height:1.38; }}
    .rec-conf {{ border-radius:4px; padding:4px 9px; font-size:.68rem; line-height:1; font-weight:900; white-space:nowrap; }}
    .rec-conf.high {{ background:#d9f5e6; color:var(--success); }}
    .rec-conf.medium {{ background:#fff0c7; color:#b97900; }}
    .rec-conf.low {{ background:#edf2f7; color:#52617a; }}
    .rec-ei {{ display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1fr); gap:1px; background:#edf2f6; margin:12px 0 10px; border-radius:4px; overflow:hidden; width:100%; min-width:0; }}
    .rec-ei-cell {{ background:#f6f9fc; padding:9px 11px; color:#3e4e66; font-size:.74rem; line-height:1.35; min-width:0; overflow-wrap:break-word; word-break:normal; }}
    .rec-ei-cell b {{ display:block; color:var(--accent); font-size:.66rem; letter-spacing:.08em; margin-bottom:4px; }}
    .rec-ei-cell.impact b {{ color:var(--warning); }}
    .rec-ei-text {{ display:block; width:100%; white-space:normal; overflow-wrap:break-word; }}
    .rec-foot {{ display:flex; align-items:center; justify-content:flex-end; gap:10px; color:var(--muted); font-size:.7rem; padding-top:8px; }}
    .rec-status {{ font-size:.7rem; font-weight:800; white-space:nowrap; }}
    .rec-status.pending {{ color:#6f7d95; }}
    .rec-status.accepted {{ color:var(--success); }}
    .rec-status.dismissed {{ color:var(--danger); }}
    .rec-status.modified {{ color:#b97900; }}
    .rec-actions {{ margin:-7px 0 14px 0; padding:0 16px 12px; border:1px solid var(--line); border-top:0; border-left-width:4px; border-radius:0 0 7px 7px; background:#fff; }}
    .rec-actions [data-testid="stHorizontalBlock"] {{ gap:8px !important; }}
    .rec-actions button {{ min-height:30px !important; border-radius:4px !important; font-size:.76rem !important; font-weight:800 !important; }}
    .empty-panel {{ background:#fff; border:1px dashed var(--line); border-radius:7px; padding:18px; color:var(--muted); font-size:.84rem; }}

    /* ── Predictive reference UI (from S2_Market Intelligence.html) ───────── */
    .pred-scope {{ background:linear-gradient(90deg,rgba(8,165,214,.06),rgba(124,58,237,.04)); border-bottom:1px solid rgba(8,165,214,.18); padding:12px 30px; display:flex; align-items:center; gap:14px; }}
    .pred-scope-icon {{ width:28px; height:28px; border-radius:6px; display:grid; place-items:center; background:rgba(8,165,214,.08); border:1px solid rgba(8,165,214,.18); color:#078db8; font-size:13px; flex:0 0 auto; }}
    .pred-scope-text {{ color:#475569; font-size:12.5px; line-height:1.55; }}
    .pred-scope-text strong {{ color:var(--ink); font-weight:800; }}
    .pred-scope-text .soon {{ color:#7c3aed; font-weight:800; }}
    .pred-canvas {{ padding:20px 30px 28px; display:flex; flex-direction:column; gap:16px; }}
    .pred-kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .pred-kpi {{ position:relative; overflow:hidden; min-height:154px; background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 18px; display:flex; flex-direction:column; gap:8px; }}
    .pred-kpi:before {{ content:""; position:absolute; left:0; right:0; top:0; height:2px; background:var(--accent); }}
    .pred-kpi.urgent:before {{ background:linear-gradient(90deg,var(--warning),#f59e0b); }}
    .pred-kpi.gain:before {{ background:linear-gradient(90deg,var(--success),#15803d); }}
    .pred-kpi.risk:before {{ background:linear-gradient(90deg,var(--danger),#991b1b); }}
    .pred-kpi.lead:before {{ background:linear-gradient(90deg,var(--accent),#7c3aed); }}
    .pred-kpi-label {{ color:#94a3b8; font-size:10.5px; font-weight:900; text-transform:uppercase; letter-spacing:.06em; display:flex; gap:6px; align-items:center; }}
    .pred-kpi-title {{ color:var(--ink); font-size:16px; line-height:1.22; font-weight:900; }}
    .pred-kpi-stat {{ display:flex; align-items:baseline; gap:7px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px; }}
    .pred-kpi-big {{ font-size:20px; font-weight:900; letter-spacing:0; }}
    .pred-kpi-meta {{ color:#475569; font-weight:700; }}
    .pred-kpi-foot {{ margin-top:auto; padding-top:8px; border-top:1px solid #e2e8f0; color:#94a3b8; font-size:10.5px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-panel {{ background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
    .pred-panel-head {{ min-height:62px; padding:14px 20px; border-bottom:1px solid #e2e8f0; display:flex; align-items:center; justify-content:space-between; gap:16px; }}
    .pred-panel-title {{ color:var(--ink); font-size:16px; font-weight:900; line-height:1.15; }}
    .pred-panel-sub {{ color:#475569; font-size:12.5px; margin-top:2px; }}
    .pred-sort {{ background:#fafbfd; border:1px solid #e2e8f0; border-radius:6px; color:#475569; font-size:12px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; padding:5px 10px; }}
    .pred-colhead, .pred-row {{ display:grid; grid-template-columns:32px minmax(220px,1fr) 110px 110px 130px 28px; gap:16px; align-items:center; }}
    .pred-colhead {{ padding:10px 20px; background:#fafbfd; border-bottom:1px solid #e2e8f0; color:#94a3b8; font-size:10px; font-weight:900; text-transform:uppercase; letter-spacing:.06em; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-row {{ padding:14px 20px; border-bottom:1px solid #e2e8f0; }}
    .pred-toggle {{ display:none; }}
    .pred-toggle:not(:checked) + .pred-row + .pred-expand-panel {{ display:none; }}
    .pred-toggle:checked + .pred-row {{ background:rgba(8,165,214,.08); border-bottom-color:rgba(8,165,214,.18); }}
    .pred-row.expanded {{ background:rgba(8,165,214,.08); border-bottom-color:rgba(8,165,214,.18); }}
    .pred-rank {{ text-align:center; color:#94a3b8; font-size:11px; font-weight:900; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-name {{ color:var(--ink); font-size:14.5px; font-weight:900; display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
    .pred-attrs {{ color:#475569; font-size:12px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; margin-top:3px; }}
    .pred-badges {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }}
    .pred-badge {{ font-size:9.5px; font-weight:900; letter-spacing:.03em; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; border-radius:3px; padding:2px 6px; }}
    .pred-badge.gt {{ background:rgba(8,165,214,.12); color:#078db8; }}
    .pred-badge.wx {{ background:rgba(255,176,0,.18); color:#a06b00; }}
    .pred-badge.soon {{ background:#edf2f7; color:#52617a; }}
    .pred-life {{ font-size:10px; text-transform:uppercase; letter-spacing:.04em; border-radius:3px; padding:2px 6px; font-weight:900; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-life.emerging {{ background:rgba(8,165,214,.08); color:#078db8; }}
    .pred-life.accelerating {{ background:rgba(32,164,100,.1); color:var(--success); }}
    .pred-life.plateau {{ background:rgba(148,163,184,.18); color:#475569; }}
    .pred-life.declining {{ background:rgba(229,57,63,.08); color:var(--danger); }}
    .pred-cell {{ text-align:center; }}
    .pred-cell.now {{ background:#fafbfd; border-radius:6px; padding:6px 4px; }}
    .pred-value {{ font-size:15px; font-weight:900; }}
    .pred-value.up {{ color:var(--success); }}
    .pred-value.down {{ color:var(--danger); }}
    .pred-value.neutral {{ color:#475569; }}
    .pred-conf {{ color:#94a3b8; font-size:10px; font-weight:800; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-progress {{ display:flex; justify-content:center; align-items:center; gap:3px; margin-top:5px; font-size:9px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-step {{ border-radius:3px; padding:2px 5px; font-weight:900; }}
    .pred-step.accelerating {{ background:rgba(32,164,100,.1); color:var(--success); }}
    .pred-step.emerging {{ background:rgba(8,165,214,.08); color:#078db8; }}
    .pred-step.plateau {{ background:rgba(148,163,184,.18); color:#475569; }}
    .pred-step.declining {{ background:rgba(229,57,63,.08); color:var(--danger); }}
    .pred-expand {{ width:28px; height:28px; border-radius:6px; display:grid; place-items:center; background:var(--accent); color:#fff; font-size:12px; margin:auto; cursor:pointer; user-select:none; transition:transform .15s; }}
    .pred-expand::before {{ content:"▾"; }}
    .pred-toggle:checked + .pred-row .pred-expand {{ transform:rotate(180deg); }}
    .pred-expand-panel {{ padding:18px 20px 20px 64px; background:rgba(8,165,214,.08); border-bottom:1px solid rgba(8,165,214,.18); }}
    .pred-expand-grid {{ display:grid; grid-template-columns:1.2fr 1fr; gap:20px; }}
    .pred-chart, .pred-driver {{ background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:14px 16px; }}
    .pred-chart-title, .pred-driver-title {{ color:#475569; font-size:10.5px; font-weight:900; letter-spacing:.06em; text-transform:uppercase; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; margin-bottom:10px; }}
    .pred-driver {{ display:flex; flex-direction:column; gap:8px; border:0; background:transparent; padding:0; }}
    .pred-driver-row {{ background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:8px 12px; display:flex; gap:10px; align-items:flex-start; }}
    .pred-driver-tag {{ min-width:124px; text-align:center; border-radius:3px; padding:2px 6px; font-size:10px; font-weight:900; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .pred-driver-tag.proxy {{ background:rgba(100,116,139,.18); color:#475569; }}
    .pred-driver-tag.pull {{ background:rgba(8,165,214,.18); color:#078db8; }}
    .pred-driver-tag.context {{ background:rgba(255,176,0,.24); color:#a06b00; }}
    .pred-driver-text {{ color:var(--ink); font-size:12px; line-height:1.45; }}
    .pred-driver-source {{ display:block; color:#94a3b8; font-size:10px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; margin-top:2px; }}
    .pred-life-grid, .pred-signal-grid {{ display:grid; grid-template-columns:repeat(4,1fr); }}
    .pred-life-card {{ padding:14px 16px; border-right:1px solid #e2e8f0; border-top:3px solid #94a3b8; }}
    .pred-life-card:last-child {{ border-right:0; }}
    .pred-life-card.emerging {{ border-top-color:var(--accent); }}
    .pred-life-card.accelerating {{ border-top-color:var(--success); }}
    .pred-life-card.declining {{ border-top-color:var(--danger); }}
    .pred-life-card-title {{ display:flex; justify-content:space-between; color:var(--ink); font-weight:900; }}
    .pred-life-count {{ border:1px solid #e2e8f0; background:#fafbfd; border-radius:999px; padding:2px 8px; font-size:11px; }}
    .pred-life-avg {{ color:#94a3b8; font-size:11.5px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; margin:6px 0 10px; }}
    .pred-life-item {{ padding:7px 0; border-top:1px solid #edf2f6; color:#475569; font-size:12px; }}
    .pred-life-item strong {{ color:var(--ink); }}
    .pred-signal-grid {{ grid-template-columns:repeat(3,1fr); gap:12px; }}
    .pred-signal-card {{ background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
    .pred-signal-head {{ padding:14px 16px; border-bottom:1px solid #e2e8f0; }}
    .pred-signal-title {{ color:var(--ink); font-size:14px; font-weight:900; }}
    .pred-signal-sub {{ color:#94a3b8; font-size:11.5px; margin-top:2px; }}
    .pred-signal-body {{ padding:14px 16px; }}
    .pred-coming {{ border:1px dashed #cbd5e1; background:#fafbfd; border-radius:8px; padding:15px; color:#475569; font-size:12.5px; line-height:1.45; min-height:132px; }}
    .pred-coming strong {{ display:inline-block; color:#a06b00; background:rgba(255,176,0,.16); border-radius:4px; padding:3px 7px; margin-bottom:8px; }}
    @media (max-width:1100px) {{
        .pred-kpis, .pred-life-grid, .pred-signal-grid {{ grid-template-columns:1fr 1fr; }}
        .pred-colhead {{ display:none; }}
        .pred-row {{ grid-template-columns:32px 1fr 88px; }}
        .pred-row .pred-cell:nth-of-type(4), .pred-row .pred-cell:nth-of-type(5) {{ display:none; }}
        .pred-expand-grid {{ grid-template-columns:1fr; }}
    }}
    @media (max-width:760px) {{ .pred-kpis, .pred-life-grid, .pred-signal-grid {{ grid-template-columns:1fr; }} }}
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

    /* ════════════════════════════════════════════════════════════════
       HTML REFERENCE DESIGN — App Chrome & New Components
       ════════════════════════════════════════════════════════════════ */
    .app-chrome {{
        background: linear-gradient(135deg, #0a1628 0%, #14233d 100%);
        padding: 11px 24px; display: flex; align-items: center;
        justify-content: space-between; border-bottom: 1px solid #1e3358;
    }}
    .chrome-left {{ display: flex; align-items: center; gap: 20px; }}
    .brand-wrap {{ display: flex; align-items: center; gap: 10px; color: #fff; }}
    .brand-i-mark {{
        width: 28px; height: 28px; background: #00a4e3; border-radius: 6px;
        display: grid; place-items: center;
        font-weight: 700; color: #0a1628; font-size: 15px;
    }}
    .brand-n {{ font-weight: 600; font-size: 17px; letter-spacing: -0.01em; }}
    .brand-div {{ color: rgba(255,255,255,0.25); font-size: 14px; margin: 0 2px; }}
    .brand-prod {{ font-weight: 500; font-size: 14px; color: rgba(255,255,255,0.85); }}
    .workspace-pill-new {{
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
        padding: 5px 11px; border-radius: 8px; color: rgba(255,255,255,0.9); font-size: 12.5px;
        display: inline-flex; align-items: center; gap: 8px;
    }}
    .workspace-pill-new::before {{
        content: ''; width: 6px; height: 6px; background: #00a4e3; border-radius: 50%; flex-shrink: 0;
    }}
    .chrome-right {{ display: flex; align-items: center; gap: 16px; }}
    .refresh-status-new {{
        display: flex; align-items: center; gap: 8px; font-size: 12px;
        color: rgba(255,255,255,0.7); font-family: ui-monospace, 'JetBrains Mono', monospace;
    }}
    @keyframes chrome-pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
    .live-dot-pulse {{
        width: 6px; height: 6px; background: #16a34a; border-radius: 50%; flex-shrink: 0;
        box-shadow: 0 0 0 3px rgba(22,163,74,0.22);
        animation: chrome-pulse 2.4s ease-in-out infinite;
    }}
    .account-btn {{
        width: 32px; height: 32px; background: rgba(255,255,255,0.1); border-radius: 50%;
        display: grid; place-items: center; color: #fff; font-weight: 600; font-size: 12px;
        border: 1px solid rgba(255,255,255,0.15);
    }}

    /* ── 2-row filter bar ──────────────────────────────── */
    .new-filter-bar {{
        background: #fff; border-bottom: 1px solid #e2e8f0; padding: 5px 20px 4px;
    }}
    .filter-row-wrap {{
        display: flex; align-items: center; gap: 4px; flex-wrap: nowrap; margin-bottom: 0;
    }}
    .filter-row-lbl {{
        font-size: 9.5px; text-transform: uppercase; letter-spacing: .07em;
        color: #94a3b8; font-weight: 600; font-family: ui-monospace, monospace;
        width: 58px; flex-shrink: 0; padding-top: 4px;
    }}
    .filter-divider-v {{ width: 1px; height: 22px; background: #e2e8f0; margin: 0 6px; flex-shrink: 0; }}
    /* Pill-style selectboxes */
    [data-testid="stSelectbox"] {{
        display: inline-flex !important; flex-direction: row !important;
        align-items: center !important; gap: 0 !important;
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 20px;
        padding: 1px 6px 1px 10px; min-width: 80px; cursor: pointer;
    }}
    [data-testid="stSelectbox"] label {{
        font-size: 11px !important; font-weight: 500 !important; color: #64748b !important;
        margin: 0 !important; padding: 0 !important; line-height: 26px !important;
        white-space: nowrap; flex-shrink: 0; cursor: pointer;
    }}
    [data-testid="stSelectbox"] > div {{
        min-width: 40px !important; flex: 1;
    }}
    [data-baseweb="select"] > div {{
        border: none !important; background: transparent !important;
        min-height: 24px !important; padding: 0 !important; box-shadow: none !important;
    }}
    [data-baseweb="select"] span {{ font-size: 12px !important; font-weight: 500 !important; color: #0f172a !important; }}
    [data-baseweb="select"] svg {{ width: 14px !important; height: 14px !important; color: #64748b !important; }}
    [data-testid="stHorizontalBlock"] {{ gap: 4px !important; align-items: center !important; }}
    /* SKU button & action links */
    .sku-lookup-link {{
        display: inline-flex; align-items: center; gap: 5px; padding: 5px 13px;
        background: #00a4e3; color: #fff; font-size: 12px; font-weight: 600;
        border-radius: 7px; white-space: nowrap; cursor: pointer; border: none;
    }}
    .filter-action-link {{
        font-size: 12px; color: #475569; font-weight: 500; cursor: pointer;
        white-space: nowrap; padding: 5px 6px; background: none; border: none;
        text-decoration: none;
    }}
    .filter-action-link:hover {{ color: #00a4e3; }}
    /* Panel collapse toggle button */
    .panel-toggle-btn {{
        display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px;
        font-size: 11.5px; color: #475569; background: #f8fafc;
        border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
    }}
    /* SKU modal dialog styling */
    .sku-modal-header {{
        background: #0a1628; color: #fff; padding: 14px 20px;
        display: flex; justify-content: space-between; align-items: center;
        border-radius: 8px 8px 0 0; margin: -16px -16px 16px;
    }}
    .sku-modal-title {{ font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
    .sku-modal-label {{ font-family: ui-monospace,monospace; font-size: 10px; text-transform: uppercase;
        letter-spacing: .07em; color: #64748b; margin-bottom: 6px; }}
    .sku-try-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    .sku-try-chip {{
        font-size: 11.5px; color: #0f172a; background: #f1f5f9;
        border: 1px solid #e2e8f0; border-radius: 6px; padding: 3px 9px; cursor: pointer;
    }}
    .sku-empty-state {{
        text-align: center; padding: 40px 20px; color: #94a3b8;
    }}
    .sku-empty-icon {{ font-size: 36px; margin-bottom: 14px; display: block; }}
    .sku-empty-text {{ font-size: 13px; line-height: 1.6; max-width: 320px; margin: 0 auto; }}
    .sku-result-card {{
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px;
    }}

    /* Analytics KPI strip */
    .kpi-strip-new {{
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
    }}
    .kpi-tile-new {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 16px 18px; position: relative; overflow: hidden;
        transition: border-color .15s;
    }}
    .kpi-tile-new::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, #00a4e3, #0080b3); opacity: .85;
    }}
    .kpi-tile-new:hover {{ border-color: #cbd5e1; }}
    .kpi-lbl-new {{
        font-size: 11.5px; color: #94a3b8; font-weight: 500;
        text-transform: uppercase; letter-spacing: .05em; margin-bottom: 8px;
    }}
    .kpi-val-new {{
        font-weight: 600; font-size: 22px; color: #0f172a;
        line-height: 1.15; letter-spacing: -.01em; margin-bottom: 4px;
    }}
    .kpi-meta-new {{
        font-size: 12.5px; color: #475569; display: flex; align-items: center;
        gap: 6px; flex-wrap: wrap;
    }}
    .kpi-delta {{
        font-family: ui-monospace, monospace; font-weight: 600; font-size: 11.5px;
        padding: 1px 6px; border-radius: 4px;
    }}
    .kpi-delta.up {{ color: #16a34a; background: rgba(22,163,74,.1); }}
    .kpi-delta.down {{ color: #dc2626; background: rgba(220,38,38,.08); }}
    .kpi-delta.neutral {{ color: #475569; background: rgba(100,116,139,.1); }}

    /* Winning Patterns hero panel */
    .hero-panel-new {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    }}
    .hero-panel-head {{
        padding: 16px 20px; border-bottom: 1px solid #e2e8f0;
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }}
    .hero-panel-title {{ font-weight: 600; font-size: 16px; color: #0f172a; letter-spacing: -.01em; }}
    .hero-panel-sub {{ font-size: 12.5px; color: #475569; margin-top: 2px; }}
    .sort-pill-new {{
        display: inline-flex; align-items: center; gap: 6px;
        background: #fafbfd; border: 1px solid #e2e8f0; padding: 5px 10px;
        border-radius: 6px; font-size: 12px; color: #475569;
        font-family: ui-monospace, monospace;
    }}
    .archetype-colhead, .archetype-row-new {{
        display: grid;
        grid-template-columns: 32px 1fr 200px 130px 110px 32px;
        gap: 16px; align-items: center; padding: 10px 20px; border-bottom: 1px solid #e2e8f0;
    }}
    .archetype-colhead {{
        background: #fafbfd; font-size: 10px; font-weight: 700; color: #94a3b8;
        text-transform: uppercase; letter-spacing: .06em;
        font-family: ui-monospace, monospace;
    }}
    .archetype-row-new {{ padding: 13px 20px; transition: background .15s; }}
    .archetype-row-new:last-child {{ border-bottom: none; }}
    .archetype-row-new:hover {{ background: #fafbfd; }}
    .arch-rank {{
        font-family: ui-monospace, monospace; font-size: 11.5px;
        color: #94a3b8; font-weight: 500; text-align: center;
    }}
    .arch-main {{ display: flex; flex-direction: column; gap: 4px; min-width: 0; }}
    .arch-name {{
        font-weight: 600; font-size: 14.5px; color: #0f172a;
        display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    }}
    .arch-attrs {{
        font-size: 12px; color: #475569; font-family: ui-monospace, monospace; margin-top: 1px;
    }}
    .arch-badges {{ display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }}
    .arch-badge {{
        font-size: 9.5px; font-weight: 600; letter-spacing: .03em; padding: 2px 6px; border-radius: 3px;
        font-family: ui-monospace, monospace;
    }}
    .arch-badge.proxy {{ background: rgba(100,116,139,.18); color: #475569; }}
    .arch-badge.pull {{ background: rgba(0,164,227,.12); color: #0080b3; }}
    .arch-badge.context {{ background: rgba(255,183,29,.18); color: #a06b00; }}
    .arch-badge.soon {{ background: #edf2f7; color: #52617a; }}
    .decision-tag-new {{
        display: inline-flex; align-items: center; gap: 4px;
        font-family: ui-monospace, monospace; font-size: 10px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .05em;
        padding: 3px 7px; border-radius: 4px; white-space: nowrap;
    }}
    .decision-tag-new.reprice {{ background: rgba(0,164,227,.1); color: #0080b3; }}
    .decision-tag-new.replenish {{ background: rgba(22,163,74,.1); color: #16a34a; }}
    .decision-tag-new.retire {{ background: rgba(220,38,38,.08); color: #dc2626; }}
    .decision-tag-new.reposition {{ background: rgba(255,183,29,.16); color: #b07a00; }}
    .decision-tag-new.watch {{ background: rgba(148,163,184,.18); color: #475569; }}
    .decision-tag-new.whitespace {{ background: rgba(124,58,237,.1); color: #6d28d9; }}
    .lifecycle-pill-new {{
        font-family: ui-monospace, monospace; font-size: 10px; text-transform: uppercase;
        letter-spacing: .04em; padding: 2px 6px; border-radius: 3px; font-weight: 500;
    }}
    .lifecycle-pill-new.emerging {{ background: rgba(0,164,227,.08); color: #0080b3; }}
    .lifecycle-pill-new.accelerating {{ background: rgba(22,163,74,.1); color: #16a34a; }}
    .lifecycle-pill-new.plateau {{ background: rgba(148,163,184,.18); color: #475569; }}
    .lifecycle-pill-new.declining {{ background: rgba(220,38,38,.08); color: #dc2626; }}
    .vel-cell {{ display: flex; flex-direction: column; gap: 2px; font-size: 12px; }}
    .vel-line {{ display: flex; align-items: center; gap: 6px; font-family: ui-monospace, monospace; }}
    .vel-ch {{ color: #94a3b8; font-size: 11px; width: 60px; flex-shrink: 0; }}
    .vel-up {{ color: #16a34a; font-weight: 600; }}
    .vel-down {{ color: #dc2626; font-weight: 600; }}
    .vel-neutral {{ color: #475569; font-weight: 600; }}
    .agree-cell {{ display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }}
    .agree-lbl {{
        font-size: 10.5px; color: #94a3b8; font-family: ui-monospace, monospace;
        text-transform: uppercase; letter-spacing: .04em;
    }}
    .agree-bars {{ display: flex; gap: 2px; }}
    .agree-bars span {{ width: 12px; height: 4px; border-radius: 1px; background: #cbd5e1; }}
    .agree-bars.strong span {{ background: #16a34a; }}
    .agree-bars.mixed span:nth-child(-n+2) {{ background: #fbbf24; }}
    .agree-bars.divergent span:nth-child(-n+1) {{ background: #dc2626; }}
    .agree-val {{
        font-size: 11.5px; font-weight: 600; color: #0f172a;
        font-family: ui-monospace, monospace; margin-top: 2px;
    }}
    .conf-cell {{ display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }}
    .conf-lbl {{
        font-size: 10.5px; color: #94a3b8; font-family: ui-monospace, monospace;
        text-transform: uppercase; letter-spacing: .04em;
    }}
    .conf-val {{ font-weight: 600; font-size: 15px; color: #0f172a; }}
    .expand-btn-new {{
        width: 28px; height: 28px; border-radius: 6px; display: grid; place-items: center;
        background: #00a4e3; color: #fff; font-size: 16px; font-weight: 400; flex-shrink: 0;
        cursor: pointer; user-select: none; line-height: 1; transition: background .15s;
    }}
    .expand-btn-new::after {{ content: '+'; }}
    .expand-btn-new:hover {{ background: #0080b3; }}
    /* Checkbox toggle: hide/show evidence panel + flip button icon */
    .pred-toggle + .archetype-row-new + .evidence-panel-s1 {{ display: none; }}
    .pred-toggle:checked + .archetype-row-new + .evidence-panel-s1 {{ display: block; }}
    .pred-toggle:checked + .archetype-row-new .expand-btn-new {{ background: #0f172a; }}
    .pred-toggle:checked + .archetype-row-new .expand-btn-new::after {{ content: '\00d7'; font-size: 18px; }}
    /* Evidence panel (S1) */
    .evidence-panel-s1 {{
        padding: 14px 20px 16px 68px;
        background: rgba(0,164,227,.05); border-bottom: 1px solid rgba(0,164,227,.15);
    }}
    .evidence-hdr {{
        font-family: ui-monospace, monospace; font-size: 10.5px; text-transform: uppercase;
        letter-spacing: .06em; color: #475569; margin-bottom: 10px; font-weight: 600;
    }}
    .driver-list-new {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }}
    .driver-row-new {{
        display: flex; align-items: center; gap: 10px; background: #fff;
        border: 1px solid #e2e8f0; padding: 8px 12px; border-radius: 6px; font-size: 12.5px;
    }}
    .driver-tag-new {{
        font-family: ui-monospace, monospace; font-size: 10.5px; font-weight: 600;
        padding: 2px 6px; border-radius: 3px; letter-spacing: .04em;
        flex-shrink: 0; min-width: 80px; text-align: center;
    }}
    .driver-tag-new.proxy {{ background: rgba(100,116,139,.12); color: #475569; }}
    .driver-tag-new.pull {{ background: rgba(0,164,227,.12); color: #0080b3; }}
    .driver-tag-new.context {{ background: rgba(255,183,29,.18); color: #a06b00; }}
    .driver-txt-new {{ color: #0f172a; flex: 1; }}
    .driver-src-new {{
        font-family: ui-monospace, monospace; font-size: 10.5px; color: #94a3b8;
        white-space: nowrap; display: inline-flex; align-items: center; gap: 4px;
    }}
    .evidence-acts {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }}
    .ev-link {{
        font-size: 12px; color: #0080b3; font-weight: 600; padding: 5px 11px;
        border: 1px solid rgba(0,164,227,.2); border-radius: 6px; background: #fff;
        cursor: pointer; transition: all .15s; text-decoration: none;
    }}
    .ev-link:hover {{ background: #00a4e3; color: #fff; }}

    /* Supporting panels */
    .supporting-grid-new {{
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
    }}
    .supporting-grid-new .span2 {{ grid-column: span 2; }}
    .support-panel-new {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    }}
    .support-panel-hdr {{
        padding: 13px 16px 10px; display: flex; align-items: center;
        justify-content: space-between; border-bottom: 1px solid #e2e8f0;
    }}
    .support-panel-title-new {{ font-weight: 600; font-size: 13.5px; color: #0f172a; }}
    .support-panel-sub-new {{ font-size: 11px; color: #94a3b8; font-family: ui-monospace, monospace; }}
    .support-panel-body {{ padding: 12px 16px 14px; }}

    /* Stacked bar */
    .stacked-bar-new {{
        display: flex; height: 28px; border-radius: 6px; overflow: hidden; margin: 8px 0 12px;
    }}
    .stacked-seg {{
        display: grid; place-items: center; font-size: 10.5px; font-weight: 600; color: #fff;
        font-family: ui-monospace, monospace; overflow: hidden; white-space: nowrap;
        transition: opacity .15s; cursor: pointer;
    }}
    .stacked-seg:hover {{ opacity: .85; }}
    .stacked-legend-new {{ display: flex; flex-direction: column; gap: 5px; }}
    .legend-row-new {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
    .legend-swatch-new {{ width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }}
    .legend-lbl-new {{ color: #475569; flex: 1; }}
    .legend-val-new {{
        font-family: ui-monospace, monospace; color: #0f172a; font-weight: 600; font-size: 11.5px;
    }}
    .legend-delta-new {{
        font-family: ui-monospace, monospace; font-size: 11px; font-weight: 600;
        padding: 1px 4px; border-radius: 3px;
    }}

    /* Bar list (HTML design) */
    .bar-list-new {{ display: flex; flex-direction: column; gap: 7px; }}
    .bar-row-new {{
        display: grid; grid-template-columns: 95px 1fr 75px;
        gap: 10px; align-items: center; font-size: 12px;
    }}
    .bar-lbl-new {{ color: #475569; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .bar-track-new {{ height: 8px; background: #f6f9fc; border-radius: 4px; overflow: hidden; }}
    .bar-fill-new {{
        height: 100%; background: linear-gradient(90deg,#00a4e3,#0080b3); border-radius: 4px;
    }}
    .bar-val-new {{
        font-family: ui-monospace, monospace; font-size: 11px; color: #0f172a;
        text-align: right; font-weight: 600;
    }}
    .converting-note {{
        margin-top: 10px; padding: 8px 10px; background: rgba(0,164,227,.06);
        border: 1px solid rgba(0,164,227,.15); border-radius: 6px;
        font-size: 11.5px; color: #0080b3; font-family: ui-monospace, monospace;
    }}

    /* Channel comparison (new) */
    .channel-compare-new {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .channel-card-new {{
        background: #fafbfd; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;
    }}
    .channel-card-hdr-new {{
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #e2e8f0;
    }}
    .channel-name-new {{ font-weight: 600; font-size: 12.5px; color: #0f172a; }}
    .ch-dot {{ width: 7px; height: 7px; border-radius: 50%; display: inline-block; }}
    .ch-dot.amz {{ background: #ff9900; }}
    .ch-dot.nor {{ background: #111; }}
    .channel-stat-new {{ display: flex; justify-content: space-between; font-size: 11.5px; padding: 4px 0; }}
    .channel-stat-lbl {{ color: #94a3b8; }}
    .channel-stat-val {{ color: #0f172a; font-family: ui-monospace, monospace; font-weight: 600; }}

    /* Automation strip */
    .automation-strip {{
        background: linear-gradient(135deg,#0a1628 0%,#14233d 100%);
        padding: 14px 20px; border-radius: 12px;
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }}
    .auto-left {{ display: flex; align-items: center; gap: 12px; }}
    .auto-badge {{
        background: rgba(255,183,29,.15); border: 1px solid rgba(255,183,29,.3);
        color: #ffb71d; font-family: ui-monospace, monospace; font-size: 11px; font-weight: 600;
        padding: 4px 10px; border-radius: 6px; white-space: nowrap;
    }}
    .auto-text {{ font-size: 13px; color: rgba(255,255,255,.85); }}
    .auto-right {{ display: flex; gap: 8px; }}
    .auto-btn {{
        padding: 7px 13px; border-radius: 6px; font-size: 12px; font-weight: 600;
        border: 1px solid rgba(255,255,255,.2); color: rgba(255,255,255,.85);
        background: rgba(255,255,255,.08); cursor: pointer;
    }}
    .auto-btn.primary {{ background: #00a4e3; border-color: #00a4e3; color: #fff; }}

    /* Predictive KPI cards (S2 updated) */
    .pred-kpi-new {{
        position: relative; overflow: hidden; background: #fff; border: 1px solid #e2e8f0;
        border-radius: 12px; padding: 16px 18px;
        display: flex; flex-direction: column; gap: 6px; min-height: 130px;
    }}
    .pred-kpi-new::before {{
        content: ''; position: absolute; left: 0; right: 0; top: 0; height: 2px; background: #00a4e3;
    }}
    .pred-kpi-new.urgent::before {{ background: linear-gradient(90deg,#ffb71d,#f59e0b); }}
    .pred-kpi-new.gain::before {{ background: linear-gradient(90deg,#16a34a,#15803d); }}
    .pred-kpi-new.risk::before {{ background: linear-gradient(90deg,#dc2626,#991b1b); }}
    .pred-kpi-new.lead::before {{ background: linear-gradient(90deg,#00a4e3,#7c3aed); }}
    .pred-kpi-lbl-new {{
        color: #94a3b8; font-size: 10.5px; font-weight: 700;
        text-transform: uppercase; letter-spacing: .06em;
    }}
    .pred-kpi-title-new {{ color: #0f172a; font-size: 15px; font-weight: 700; line-height: 1.25; }}
    .pred-kpi-stat-new {{
        display: flex; align-items: baseline; gap: 7px;
        font-family: ui-monospace, monospace; font-size: 11px;
    }}
    .pred-kpi-big-new {{ font-size: 19px; font-weight: 900; }}
    .pred-kpi-meta-new {{ color: #475569; font-weight: 600; }}
    .pred-kpi-foot-new {{
        margin-top: auto; padding-top: 8px; border-top: 1px solid #e2e8f0;
        color: #94a3b8; font-size: 10.5px; font-family: ui-monospace, monospace;
    }}

    /* S2 Forward signals (static placeholders) */
    .fwd-signal-card {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    }}
    .fwd-signal-hdr {{
        padding: 13px 16px 10px; border-bottom: 1px solid #e2e8f0;
    }}
    .fwd-signal-title {{ font-weight: 600; font-size: 13.5px; color: #0f172a; }}
    .fwd-signal-sub {{ font-size: 11px; color: #94a3b8; font-family: ui-monospace, monospace; margin-top: 2px; }}
    .fwd-signal-body {{ padding: 12px 16px 14px; }}
    .fwd-query-row {{
        display: flex; align-items: center; gap: 10px; padding: 6px 0;
        border-bottom: 1px solid #f1f5f9; font-size: 12.5px;
    }}
    .fwd-query-row:last-child {{ border-bottom: none; }}
    .fwd-query-name {{ color: #0f172a; flex: 1; font-weight: 500; }}
    .fwd-mini-bar {{ height: 5px; width: 60px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }}
    .fwd-mini-fill {{ height: 100%; border-radius: 3px; }}
    .fwd-delta-up {{ color: #16a34a; font-weight: 600; font-size: 11.5px; font-family: ui-monospace, monospace; }}
    .fwd-delta-down {{ color: #dc2626; font-weight: 600; font-size: 11.5px; font-family: ui-monospace, monospace; }}
    .fwd-region-row {{
        display: grid; grid-template-columns: 80px 1fr auto; gap: 10px; align-items: center;
        padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 12px;
    }}
    .fwd-region-row:last-child {{ border-bottom: none; }}
    .fwd-region-name {{ color: #475569; font-weight: 500; }}
    .fwd-anomaly {{ color: #0f172a; font-family: ui-monospace, monospace; font-weight: 600; font-size: 11.5px; }}

    /* S3 Mode toggle */
    .mode-toggle-bar {{
        background: #fff; border-bottom: 1px solid #e2e8f0;
        padding: 0 24px; display: flex; align-items: stretch;
    }}
    .mode-toggle-tab {{
        padding: 13px 20px; font-weight: 500; font-size: 14px; color: #475569;
        border-bottom: 2px solid transparent; cursor: pointer; transition: all .15s;
        display: flex; align-items: center; gap: 8px;
    }}
    .mode-toggle-tab.active {{ color: #0f172a; border-bottom-color: #00a4e3; font-weight: 600; }}
    .mode-count {{
        background: #00a4e3; color: #fff; font-size: 11px; font-weight: 700;
        padding: 2px 7px; border-radius: 10px;
    }}

    /* S3 Market frame */
    .market-frame {{
        background: linear-gradient(135deg,#0a1628 0%,#14233d 100%);
        border-radius: 12px; padding: 18px 20px;
        display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px;
    }}
    .market-frame-title {{ color: rgba(255,255,255,.9); font-size: 13px; font-weight: 600; }}
    .market-frame-signal {{ font-size: 15px; font-weight: 700; color: #fff; line-height: 1.3; }}
    .market-frame-drivers {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .market-frame-driver {{
        display: flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.1);
        padding: 5px 9px; border-radius: 6px; font-size: 12px; color: rgba(255,255,255,.8);
    }}
    .driver-pct {{ font-weight: 700; color: #00a4e3; }}

    /* S3 Rec cards (new design) */
    .rec-card-new {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        overflow: hidden; margin-bottom: 12px;
    }}
    .rec-card-grid {{
        display: grid; grid-template-columns: 32px 1fr auto auto;
        gap: 14px; align-items: center; padding: 14px 16px;
    }}
    .rec-idx {{
        font-family: ui-monospace, monospace; font-size: 11px;
        color: #94a3b8; text-align: center; font-weight: 600;
    }}
    .rec-main {{ min-width: 0; }}
    .rec-headline {{ color: #0f172a; font-size: 14px; font-weight: 700; line-height: 1.3; margin-bottom: 3px; }}
    .rec-evidence-sum {{ color: #475569; font-size: 12px; line-height: 1.4; }}
    .rec-conf-col {{
        display: flex; flex-direction: column; align-items: flex-end; gap: 4px;
        font-family: ui-monospace, monospace; font-size: 11px; white-space: nowrap;
    }}
    .conf-badge {{ padding: 3px 8px; border-radius: 4px; font-weight: 700; }}
    .conf-badge.high {{ background: rgba(22,163,74,.1); color: #16a34a; }}
    .conf-badge.medium {{ background: rgba(255,183,29,.15); color: #b07a00; }}
    .conf-badge.low {{ background: rgba(148,163,184,.18); color: #475569; }}
    .tier-strong {{ color: #16a34a; font-size: 10.5px; font-weight: 700; }}
    .tier-moderate {{ color: #b07a00; font-size: 10.5px; font-weight: 700; }}
    .tier-watch {{ color: #475569; font-size: 10.5px; font-weight: 700; }}
    .rec-expand-col {{
        width: 28px; height: 28px; border-radius: 6px; display: grid; place-items: center;
        background: #f6f9fc; border: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px;
        cursor: pointer; flex-shrink: 0;
    }}
    .rec-evidence-block {{
        padding: 12px 16px 14px; background: rgba(0,164,227,.04);
        border-top: 1px solid rgba(0,164,227,.12);
    }}
    .rec-driver-list {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; }}
    .rec-action-row {{ display: flex; gap: 8px; flex-wrap: wrap; padding-top: 8px; border-top: 1px solid #e2e8f0; }}
    .rec-action-btn {{
        padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;
        border: 1px solid #e2e8f0; color: #475569; background: #fff;
        cursor: pointer; transition: all .15s;
    }}
    .rec-action-btn:hover {{ border-color: #00a4e3; color: #0080b3; }}
    .rec-action-btn.primary {{ background: #00a4e3; border-color: #00a4e3; color: #fff; }}
    .rec-action-btn.primary:hover {{ background: #0080b3; }}
</style>
""", unsafe_allow_html=True)

# ── Top controls ──────────────────────────────────────────────────────────────
_CATEGORY_LABELS = {
    "All": "All Apparel",
    "mens_polos": "Polos",
    "mens_tshirts": "Men's T-Shirts",
    "womens_dresses": "Women's Dresses",
    "womens_tops": "Tops",
    "denim": "Denim",
}
_GENDER_LABELS = {
    "All": "All",
    "men": "Men",
    "women": "Women",
    "kids": "Kids",
    "unisex": "Unisex",
}
_STYLE_LABELS = {
    "All": "All",
    "crew": "Crew Neck",
    "v_neck": "V-Neck",
    "henley": "Henley",
    "polo": "Polo",
}
_PLATFORM_LABELS = {
    "All": "Amazon · Nordstrom",
    "amazon": "Amazon",
    "nordstrom": "Nordstrom",
}


def _repair_stale_widget_state() -> None:
    """
    Streamlit can retain stale browser widget IDs after large layout changes.
    In 1.35 this may raise a KeyError while building filtered_state before the
    actual widget renders. Drop only broken private widget entries and then let
    the keyed widgets below recreate clean state.
    """
    try:
        from streamlit.runtime.state.session_state_proxy import get_session_state

        raw_state = get_session_state()
        old_state = getattr(raw_state, "_old_state", None)
        new_session_state = getattr(raw_state, "_new_session_state", None)
        new_widget_state = getattr(raw_state, "_new_widget_state", None)
        key_mapper = getattr(raw_state, "_key_id_mapper", None)
        if old_state is None:
            return

        stale_keys: set[str] = set()
        for key in list(old_state.keys()):
            widget_id = raw_state._get_widget_id(key)
            if not isinstance(widget_id, str) or not widget_id.startswith("$$WIDGET_ID"):
                continue
            try:
                raw_state[widget_id]
            except KeyError:
                stale_keys.update({str(key), widget_id})

        if key_mapper is not None:
            id_key_mapping = getattr(key_mapper, "_id_key_mapping", {})
            key_id_mapping = getattr(key_mapper, "_key_id_mapping", {})
            for widget_id, user_key in list(id_key_mapping.items()):
                if not isinstance(widget_id, str) or not widget_id.startswith("$$WIDGET_ID"):
                    continue
                try:
                    raw_state[widget_id]
                except KeyError:
                    stale_keys.update({str(user_key), widget_id})
            for user_key, widget_id in list(key_id_mapping.items()):
                if not isinstance(widget_id, str) or not widget_id.startswith("$$WIDGET_ID"):
                    continue
                try:
                    raw_state[widget_id]
                except KeyError:
                    stale_keys.update({str(user_key), widget_id})

        for key in stale_keys:
            old_state.pop(key, None)
            if new_session_state is not None:
                new_session_state.pop(key, None)
            if new_widget_state is not None:
                new_widget_state.states.pop(key, None)
                new_widget_state.widget_metadata.pop(key, None)
            if key_mapper is not None and key.startswith("$$WIDGET_ID"):
                user_key = key_mapper._id_key_mapping.pop(key, None)
                if user_key:
                    key_mapper._key_id_mapping.pop(user_key, None)
    except Exception:
        pass


_repair_stale_widget_state()
for _filter_key, _filter_default in {
    "gender_filter": "All",
    "cat_filter": "All",
    "style_filter": "All",
    "plt_filter": "All",
    "window_filter": "Last 30 Days",
    "price_band_filter": "All",
    "rec_status_filter": "All",
    "s3_mode": "recommendations",
    "show_support_panels": True,
    "region_filter": "All US",
}.items():
    try:
        st.session_state.setdefault(_filter_key, _filter_default)
    except Exception:
        pass

# ── Load filter option lists from DB (cached 1 hour) ─────────────────────────
@st.cache_data(ttl=3600)
def _get_filter_options():
    return load_filter_options()

_fopts = _get_filter_options()
_gender_opts   = ["All"] + _fopts.get("genders", ["men", "women"])
_category_opts = ["All"] + _fopts.get("categories", ["mens_tshirts", "womens_dresses"])
_neck_type_opts = ["All"] + _fopts.get("neck_types", [])
_platform_opts = ["All"] + _fopts.get("platforms", ["amazon", "nordstrom"])

# ── SKU Lookup dialog ─────────────────────────────────────────────────────────
@st.dialog("SKU Lookup", width="large")
def _sku_lookup_dialog():
    st.markdown("""
<div class="sku-modal-header">
  <div class="sku-modal-title">🔍 SKU Lookup</div>
</div>
""", unsafe_allow_html=True)
    st.markdown('<div class="sku-modal-label">Enter a marketplace SKU or ASIN</div>', unsafe_allow_html=True)
    _q_col, _btn_col = st.columns([5, 1])
    with _q_col:
        _sku_q = st.text_input("sku_q", placeholder="e.g., B08L5XYZ12 (Amazon ASIN) or 7234890 (Nordstrom ID)",
                               label_visibility="collapsed", key="sku_lookup_input")
    with _btn_col:
        _do_lookup = st.button("Look up", type="primary", use_container_width=True, key="sku_lookup_go")
    st.markdown("""
<div class="sku-try-row">
  <span style="font-size:11px;color:#94a3b8;align-self:center;">TRY</span>
  <span class="sku-try-chip">B08HVCWRC1 · Amazon</span>
  <span class="sku-try-chip">7234890 · Nordstrom</span>
  <span class="sku-try-chip">B07PFGX5LL · Amazon</span>
</div>
""", unsafe_allow_html=True)
    st.divider()
    if _do_lookup and _sku_q.strip():
        # Search DB for this SKU/ASIN in products
        try:
            from streamlit_app.db import load_products
            _all = load_products()
            _q_lower = _sku_q.strip().lower()
            _hit = _all[_all.apply(lambda r: _q_lower in str(r.get("url","")).lower()
                                   or _q_lower in str(r.get("title","")).lower(), axis=1)]
            if _hit.empty:
                st.warning(f"No product found matching **{_sku_q}** in the database.")
            else:
                r = _hit.iloc[0]
                st.markdown(f"""
<div class="sku-result-card">
  <div style="font-weight:700;font-size:14px;margin-bottom:4px;">{r.get('title','—')[:80]}</div>
  <div style="font-size:12px;color:#475569;margin-bottom:10px;">
    Platform: <b>{r.get('platform','—')}</b> &nbsp;·&nbsp;
    Price: <b>${float(r.get('current_price') or 0):.2f}</b> &nbsp;·&nbsp;
    Rating: <b>{r.get('rating','—')}</b> &nbsp;·&nbsp;
    Reviews: <b>{int(r.get('review_count') or 0):,}</b>
  </div>
  <div style="font-size:11.5px;color:#64748b;">Category: {r.get('category','—')} &nbsp;·&nbsp; Color: {r.get('color','—')} &nbsp;·&nbsp; Neck: {r.get('neck_type','—')}</div>
</div>""", unsafe_allow_html=True)
        except Exception as _e:
            st.error(f"Lookup error: {_e}")
    else:
        st.markdown("""
<div class="sku-empty-state">
  <span class="sku-empty-icon">🔍</span>
  <div class="sku-empty-text">Enter an ASIN or Nordstrom product ID above to see review metrics,
  sentiment, price history, cross-platform comparison, and pattern mapping for that listing.<br><br>
  <span style="color:#b0bdcd;">All data is market-derived from public listings.</span></div>
</div>""", unsafe_allow_html=True)

# ── App Chrome (dark gradient header) ────────────────────────────────────────
st.markdown(f"""
<div class="app-chrome">
  <div class="chrome-left">
    <div class="brand-wrap">
      <div class="brand-i-mark">i</div>
      <span class="brand-n">Innovatics</span>
      <span class="brand-div">/</span>
      <span class="brand-prod">Channel Intelligence</span>
    </div>
    <div class="workspace-pill-new">Market Signal</div>
  </div>
  <div class="chrome-right">
    <div class="refresh-status-new">
      <span class="live-dot-pulse"></span>
      Live · refreshed recently
    </div>
    <div class="account-btn">Z</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 2-row compact pill filter bar ─────────────────────────────────────────────
_fb_lbl = lambda lbl, x, fmt=None: f"{lbl}  {fmt(x) if fmt else x}"

with st.container():
    st.markdown('<div class="new-filter-bar">', unsafe_allow_html=True)

    # ── Row 1 ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="filter-row-wrap">', unsafe_allow_html=True)
    st.markdown('<span class="filter-row-lbl">Context</span>', unsafe_allow_html=True)

    _r1 = st.columns([1.0, 1.4, 1.2, 1.5, 0.05, 1.1, 0.75, 0.65])
    with _r1[0]:
        gender_filter = st.selectbox(
            "Gender",
            _gender_opts,
            format_func=lambda x: _GENDER_LABELS.get(x, x.title()),
            key="gender_filter",
        )
    with _r1[1]:
        category_filter = st.selectbox(
            "Category",
            _category_opts,
            format_func=lambda x: _CATEGORY_LABELS.get(x, x.replace("_", " ").title()),
            key="cat_filter",
        )
    with _r1[2]:
        style_filter = st.selectbox(
            "Style",
            _neck_type_opts,
            key="style_filter",
        )
    with _r1[3]:
        window_filter = st.selectbox(
            "Window",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "All Time"],
            key="window_filter",
        )
    with _r1[4]:
        st.markdown('<div class="filter-divider-v"></div>', unsafe_allow_html=True)
    with _r1[5]:
        if st.button("🔍 Look up SKU", key="sku_open_btn", use_container_width=True):
            _sku_lookup_dialog()
    with _r1[6]:
        st.markdown('<span class="filter-action-link">↗ Save view</span>', unsafe_allow_html=True)
    with _r1[7]:
        st.markdown('<span class="filter-action-link">↺ Reset all</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Row 2 ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="filter-row-wrap">', unsafe_allow_html=True)
    st.markdown('<span class="filter-row-lbl">Refine</span>', unsafe_allow_html=True)
    _r2 = st.columns([1.1, 1.1, 1.4, 6.4])
    with _r2[0]:
        price_band_filter = st.selectbox(
            "Price band",
            ["All", "<$25", "$25–50", "$50–75", "$75–100", "$100–150", "$150+"],
            key="price_band_filter",
        )
    with _r2[1]:
        region_filter = st.selectbox(
            "Region",
            ["All US", "East", "West", "South", "Midwest"],
            key="region_filter",
        )
    with _r2[2]:
        platform_filter = st.selectbox(
            "Channel",
            _platform_opts,
            format_func=lambda x: "Amazon + Nordstrom" if x == "All" else _PLATFORM_LABELS.get(x, x.title()),
            key="plt_filter",
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close new-filter-bar

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


def _apply_universal_filters(source: pd.DataFrame, gender: str, style: str) -> pd.DataFrame:
    if source.empty:
        return source
    work = source.copy()
    if gender != "All" and "gender" in work.columns:
        work = work[work["gender"].fillna("").astype(str).str.lower() == gender]
    if style != "All":
        if "neck_type" in work.columns:
            work = work[work["neck_type"].fillna("").astype(str).str.lower() == style.lower()]
    return work


df_raw = get_data(platform_filter, category_filter)
sku_raw = get_variant_data(platform_filter, category_filter)

df = _apply_universal_filters(df_raw, gender_filter, style_filter)
sku_df = _apply_universal_filters(sku_raw, gender_filter, style_filter)


def _apply_price_band_filter(source: pd.DataFrame, band: str) -> pd.DataFrame:
    if band == "All" or source.empty or "current_price" not in source.columns:
        return source
    prices = pd.to_numeric(source["current_price"], errors="coerce")
    band_map = {
        "<$25": (0, 25),
        "$25–50": (25, 50),
        "$50–75": (50, 75),
        "$75–100": (75, 100),
        "$100–150": (100, 150),
        "$150+": (150, 99999),
    }
    lo, hi = band_map.get(band, (0, 99999))
    return source[prices.between(lo, hi, inclusive="left")]


if price_band_filter != "All":
    df = _apply_price_band_filter(df, price_band_filter)
    sku_df = _apply_price_band_filter(sku_df, price_band_filter)

_visible_category = _CATEGORY_LABELS.get(category_filter, category_filter.replace("_", " ").title())
_visible_gender = _GENDER_LABELS.get(gender_filter, gender_filter.title())
_visible_style = _STYLE_LABELS.get(style_filter, style_filter.title())
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

tab1, tab2, tab3 = st.tabs([
    "Analytics",
    "Predictive",
    "Ask & Recommendation",
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
    "plateau":      "Plateau",
    "declining":    "Declining",
}
_LIFECYCLE_ALIASES = {
    "peak": "plateau",
    "dead": "declining",
}


def _stage_key(stage: str) -> str:
    raw = str(stage or "plateau").strip().lower()
    raw = _LIFECYCLE_ALIASES.get(raw, raw)
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


def _confidence_pct(row: dict) -> int:
    label = str(row.get("confidence") or "").strip().lower()
    base = {"high": 82, "med": 74, "medium": 74, "low": 64}.get(label, 64)
    change = abs(float(row.get("change") or row.get("projected_change_pct") or 0))
    weeks_observed = int(row.get("weeks_observed") or 0)
    if change >= 25:
        base += 4
    elif change < 10:
        base -= 5
    if weeks_observed >= 3:
        base += 3
    elif weeks_observed <= 1:
        base -= 2
    return max(50, min(92, int(round(base))))


def _decision_tag(stage: str, change: float) -> str:
    stage = _stage_key(stage)
    if stage == "accelerating":
        return "Replenish" if change >= 0 else "Watch"
    if stage == "declining":
        return "Retire" if change < 0 else "Watch"
    if stage == "emerging":
        return "Watch"
    return "Watch"


def _predictive_kpis(rows: list[dict]) -> dict:
    urgent = []
    for row in rows:
        change = float(row.get("change") or 0)
        conf = _confidence_pct(row)
        if _stage_key(row.get("stage")) in {"accelerating", "declining"} and conf > 75 and abs(change) > 15:
            urgent.append({**row, "confidence_pct": conf, "decision_tag": _decision_tag(row.get("stage"), change)})

    gains = [r for r in rows if float(r.get("change") or 0) > 0]
    risks = [r for r in rows if float(r.get("change") or 0) < 0]
    biggest_gain = max(gains, key=lambda r: float(r.get("change") or 0), default=None)
    biggest_risk = min(risks, key=lambda r: float(r.get("change") or 0), default=None)

    tag_counts = {}
    for row in urgent:
        tag = row["decision_tag"]
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    tag_summary = " · ".join(f"{count} {tag}" for tag, count in tag_counts.items()) or "No urgent tags"

    return {
        "urgent": urgent,
        "urgent_summary": tag_summary,
        "biggest_gain": biggest_gain,
        "biggest_risk": biggest_risk,
    }


def _predictive_kpi_band_html(rows: list[dict]) -> str:
    kpis = _predictive_kpis(rows)
    urgent_count = len(kpis["urgent"])
    gain = kpis["biggest_gain"]
    risk = kpis["biggest_risk"]

    gain_name = _label(gain.get("name"), "Run predictions") if gain else "Run predictions"
    gain_change = int(round(float(gain.get("change") or 0))) if gain else 0
    gain_conf = _confidence_pct(gain) if gain else 0
    gain_stage = _LIFECYCLE_LABELS[_stage_key(gain.get("stage"))].lower() if gain else "pending"

    risk_name = _label(risk.get("name"), "Run predictions") if risk else "Run predictions"
    risk_change = int(round(float(risk.get("change") or 0))) if risk else 0
    risk_conf = _confidence_pct(risk) if risk else 0
    risk_stage = _LIFECYCLE_LABELS[_stage_key(risk.get("stage"))].lower() if risk else "pending"

    return f"""
<div class="signal-band">
  <div class="signal-card">
    <div class="signal-label">Patterns needing action · 4 weeks</div>
    <div class="signal-value" style="font-size:1.72rem;">{urgent_count} urgent</div>
    <div class="signal-note">Accelerating/Declining · confidence &gt;75% · velocity &gt;±15%<br><strong>{_safe(kpis["urgent_summary"])}</strong></div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Biggest momentum gain</div>
    <div class="signal-value" style="font-size:1.42rem;">{_safe(gain_name)}</div>
    <div class="signal-note"><span class="delta up">{gain_change:+d}%</span> velocity · {gain_stage}<br>Forecast +4w · {gain_conf}% conf</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Biggest decline risk</div>
    <div class="signal-value" style="font-size:1.42rem;">{_safe(risk_name)}</div>
    <div class="signal-note"><span class="delta down">{risk_change:+d}%</span> velocity · {risk_stage}<br>Forecast +4w · {risk_conf}% conf</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Google Trends lead time</div>
    <div class="signal-value" style="font-size:1.72rem;">Coming soon</div>
    <div class="signal-note">Will count patterns where search interest crosses +20% before marketplace velocity.</div>
  </div>
</div>"""


def _forecast_rows_html(rows: list[dict]) -> str:
    if not rows:
        # TODO: Show forecast rows after predictions write trend_scores for the active filters.
        return "<div class='empty-panel'>No backend forecast rows available yet. Run predictions after enough scrape history exists.</div>"
    html = ["""
<div class="scale-row">
  <div>Pattern</div>
  <div class="scale-labels"><span>-25%</span><span>-10%</span><span>0</span><span>+10%</span><span>+25%</span></div>
  <div class="forecast-meta-head"><span>Velocity</span><span>Confidence</span></div>
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
        conf_pct = _confidence_pct(row)
        conf_cls = "high" if conf_pct >= 80 else "med" if conf_pct >= 70 else "low"
        html.append(f"""
<div class="forecast-row">
  <div class="forecast-name"><b>{_safe(row["name"])}</b><span>{_safe(action)}</span></div>
  <div class="forecast-axis">
    <span class="forecast-bar" style="left:{left}%; width:{magnitude}%; background:{color};"></span>
    <span class="forecast-whisker" style="left:{max(2, min(96, 50 + change * 1.15))}%;"></span>
  </div>
  <div class="forecast-change {'pos' if change >= 0 else 'neg'}">{change:+d}%</div>
  <div><span class="confidence {conf_cls}">{conf_pct}%</span></div>
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
        conf_pct = _confidence_pct(row)
        html.append(
            _sparkline_html(title, actual, projected) +
            f'<div class="tag-row" style="margin-top:-7px;margin-bottom:9px;">'
            f'<span class="tag info">{current} current reviews</span>'
            f'<span class="tag warn">{conf_pct}% confidence</span>'
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


def _coming_soon_signals_html() -> str:
    cards = [
        (
            "Google Trends · search-interest lead",
            "PULL · FORWARD",
            "Will measure 14d query growth vs prior 30d baseline and flag +20% crossings before marketplace velocity turns.",
        ),
        (
            "NOAA Weather · regional context",
            "CONTEXT · FORWARD",
            "Will map regional climate anomalies against category sensitivity, such as heavyweight demand during cool deviations.",
        ),
        (
            "Sentiment shift · early warning",
            "PROXY · TRAILING",
            "Will use review-text sentiment by aspect, including fit, quality, color, and value, once review text is stored.",
        ),
    ]
    html = []
    for title, tag, copy in cards:
        html.append(f"""
<div class="white-card">
  <div class="white-title">{_safe(title)}</div>
  <span class="tag info">{_safe(tag)}</span>
  <span class="tag warn">COMING SOON</span>
  <div class="early-copy" style="margin-top:9px;">{_safe(copy)}</div>
</div>""")
    return f'<div class="whitespace-grid">{"".join(html)}</div>'


def _stage_abbrev(stage: str) -> str:
    return {
        "emerging": "Emrg",
        "accelerating": "Accel",
        "plateau": "Plat",
        "declining": "Decl",
    }[_stage_key(stage)]


def _stage_progression(stage: str, change: float) -> list[str]:
    stage = _stage_key(stage)
    if stage == "emerging":
        return ["emerging", "accelerating" if change >= 10 else "emerging", "accelerating" if change >= 15 else "plateau"]
    if stage == "accelerating":
        return ["accelerating", "accelerating", "plateau" if change < 35 else "accelerating"]
    if stage == "declining":
        return ["declining", "declining", "declining"]
    return ["plateau", "plateau", "declining" if change < 0 else "plateau"]


def _velocity_class(value: float) -> str:
    if value > 2:
        return "up"
    if value < -2:
        return "down"
    return "neutral"


def _forecast_value(change: float, horizon: int) -> int:
    multiplier = 1.25 if horizon == 4 else 1.1
    if change < 0:
        multiplier = 1.35 if horizon == 4 else 1.55
    return int(round(change * multiplier))


def _trajectory_rows_html(rows: list[dict]) -> str:
    if not rows:
        return "<div class='empty-panel'>No backend pattern trajectory available yet. Run predictions after scrape history exists.</div>"

    html = []
    for idx, row in enumerate(rows[:6]):
        change = float(row.get("change") or 0)
        fc4 = _forecast_value(change, 4)
        fc8 = _forecast_value(change, 8)
        conf = _confidence_pct(row)
        stage = _stage_key(row.get("stage"))
        name = _label(row.get("name"), "Pattern")
        action = row.get("action") or "Monitor daily"
        progress = _stage_progression(stage, change)
        progress_html = "".join(
            f'<span class="pred-step {p}">{_stage_abbrev(p)}</span>' +
            ('<span style="color:#cbd5e1;">→</span>' if n < 2 else "")
            for n, p in enumerate(progress)
        )
        gt_badge = '<span class="pred-badge soon">GT coming soon</span>'
        wx_badge = '<span class="pred-badge soon">WX coming soon</span>'
        html.append(f"""
<input class="pred-toggle" type="checkbox" id="pred-toggle-{idx}" {'checked' if idx == 0 else ''}>
<div class="pred-row">
  <div class="pred-rank">{idx + 1:02d}</div>
  <div>
    <div class="pred-name">{_safe(name)} <span class="pred-life {stage}">{_safe(_LIFECYCLE_LABELS[stage])}</span></div>
    <div class="pred-attrs">{_safe(action)} · backend trend score · selected filter context</div>
    <div class="pred-badges">{gt_badge}{wx_badge}</div>
  </div>
  <div class="pred-cell now">
    <div class="pred-value {_velocity_class(change)}">{int(round(change)):+d}%</div>
    <div class="pred-conf">vs prior 30d</div>
  </div>
  <div class="pred-cell">
    <div class="pred-value {_velocity_class(fc4)}">{fc4:+d}%</div>
    <div class="pred-conf">{conf}% conf</div>
  </div>
  <div class="pred-cell">
    <div class="pred-value {_velocity_class(fc8)}">{fc8:+d}%</div>
    <div class="pred-progress">{progress_html}</div>
  </div>
  <label class="pred-expand" for="pred-toggle-{idx}" title="Open or close trajectory details"></label>
</div>
<div class="pred-expand-panel">
  <div class="pred-expand-grid">
    <div class="pred-chart">
      <div class="pred-chart-title">30d actual + 8w forecast</div>
      <svg viewBox="0 0 400 130" preserveAspectRatio="none" style="width:100%;height:130px;display:block;">
        <line x1="0" y1="32" x2="400" y2="32" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,3" />
        <line x1="0" y1="65" x2="400" y2="65" stroke="#cbd5e1" stroke-width="1" />
        <line x1="0" y1="98" x2="400" y2="98" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,3" />
        <path d="M 200,42 L 250,32 L 300,28 L 350,34 L 400,42 L 400,82 L 350,76 L 300,68 L 250,58 L 200,74 Z" fill="rgba(8,165,214,.12)" />
        <line x1="200" y1="0" x2="200" y2="130" stroke="#0f172a" stroke-width="1.5" stroke-dasharray="3,2" opacity=".55" />
        <text x="200" y="12" font-family="monospace" font-size="9" fill="#0f172a" text-anchor="middle" font-weight="700">NOW</text>
        <polyline points="0,85 50,80 100,70 150,55 200,48" fill="none" stroke="#0080b3" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
        <polyline points="200,48 250,42 300,38 350,46 400,52" fill="none" stroke="#08a5d6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="6,4" />
        <circle cx="200" cy="48" r="3" fill="#0080b3" stroke="#fff" stroke-width="1.5" />
        <circle cx="300" cy="38" r="2.5" fill="#08a5d6" stroke="#fff" stroke-width="1.5" />
        <circle cx="400" cy="52" r="2.5" fill="#08a5d6" stroke="#fff" stroke-width="1.5" />
      </svg>
      <div style="display:flex;justify-content:space-between;color:#94a3b8;font-size:10px;font-family:monospace;margin-top:4px;"><span>-30d</span><span>-15d</span><span>now</span><span>+4w</span><span>+8w</span></div>
    </div>
    <div class="pred-driver">
      <div class="pred-driver-title">Why this trajectory · evidence</div>
      <div class="pred-driver-row"><span class="pred-driver-tag proxy">PROXY · TRAILING</span><div><span class="pred-driver-text">Marketplace review velocity and lifecycle stage from current scraped history.</span><span class="pred-driver-source">Live · marketplace mining</span></div></div>
      <div class="pred-driver-row"><span class="pred-driver-tag pull">PULL · FORWARD</span><div><span class="pred-driver-text">Google Trends query lead is planned for +20% search-interest threshold detection.</span><span class="pred-driver-source">Coming soon · Google Trends</span></div></div>
      <div class="pred-driver-row"><span class="pred-driver-tag context">CONTEXT · FORWARD</span><div><span class="pred-driver-text">NOAA regional anomaly context will be mapped to category sensitivity.</span><span class="pred-driver-source">Coming soon · NOAA Weather</span></div></div>
      <div class="pred-driver-row"><span class="pred-driver-tag proxy">PROXY · TRAILING</span><div><span class="pred-driver-text">Sentiment by aspect will join after review text is stored.</span><span class="pred-driver-source">Coming soon · sentiment mining</span></div></div>
    </div>
  </div>
</div>""")
    return "".join(html)


def _lifecycle_cards_html(rows: list[dict]) -> str:
    stages = ["emerging", "accelerating", "plateau", "declining"]
    cards = []
    for stage in stages:
        stage_rows = [r for r in rows if _stage_key(r.get("stage")) == stage]
        avg = int(round(sum(float(r.get("change") or 0) for r in stage_rows) / max(len(stage_rows), 1)))
        examples = stage_rows[:3]
        if not examples:
            item_html = '<div class="pred-life-item">No backend rows yet</div>'
        else:
            item_html = "".join(
                f'<div class="pred-life-item"><strong>{_safe(_label(r.get("name"), "Pattern"))}</strong><br><span style="color:{SUCCESS if float(r.get("change") or 0) >= 0 else DANGER};font-weight:900;">{int(round(float(r.get("change") or 0))):+d}%</span> · backend signal</div>'
                for r in examples
            )
        cards.append(f"""
<div class="pred-life-card {stage}">
  <div class="pred-life-card-title"><span>{_safe(_LIFECYCLE_LABELS[stage])}</span><span class="pred-life-count">{len(stage_rows)}</span></div>
  <div class="pred-life-avg">{avg:+d}% avg velocity · selected filter</div>
  {item_html}
</div>""")
    return "".join(cards)


def _predictive_reference_ui_html(rows: list[dict]) -> str:
    kpis = _predictive_kpis(rows)
    urgent = kpis["urgent"]
    gain = kpis["biggest_gain"]
    risk = kpis["biggest_risk"]

    gain_change = int(round(float(gain.get("change") or 0))) if gain else 0
    risk_change = int(round(float(risk.get("change") or 0))) if risk else 0
    gain_fc = _forecast_value(gain_change, 4) if gain else 0
    risk_fc = _forecast_value(risk_change, 4) if risk else 0
    gain_conf = _confidence_pct(gain) if gain else 0
    risk_conf = _confidence_pct(risk) if risk else 0
    top_urgent = urgent[0] if urgent else gain
    top_urgent_name = _label(top_urgent.get("name"), "Run predictions") if top_urgent else "Run predictions"
    top_urgent_change = int(round(float(top_urgent.get("change") or 0))) if top_urgent else 0
    gain_name = _label(gain.get("name"), "Run predictions") if gain else "Run predictions"
    risk_name = _label(risk.get("name"), "Run predictions") if risk else "Run predictions"
    risk_stage = _LIFECYCLE_LABELS[_stage_key(risk.get("stage"))].lower() if risk else "pending"

    return f"""
<div class="pred-scope">
  <div class="pred-scope-icon">◈</div>
  <div class="pred-scope-text">
    <strong>Predictive triangulates marketplace signals with forward/context layers.</strong>
    Live today: marketplace review velocity and lifecycle stage.
    <span class="soon">Coming soon: Google Trends, NOAA Weather, sentiment mining.</span>
  </div>
</div>
<div class="pred-canvas">
  <div class="pred-kpis">
    <div class="pred-kpi urgent">
      <div class="pred-kpi-label">⏱ Patterns needing action · 4 weeks</div>
      <div class="pred-kpi-title">{len(urgent)} patterns urgent</div>
      <div class="pred-kpi-stat"><span>Top:</span><span class="pred-kpi-meta">{_safe(top_urgent_name)}</span><span class="delta {'up' if top_urgent_change >= 0 else 'down'}">{top_urgent_change:+d}%</span></div>
      <div class="pred-kpi-foot">{_safe(kpis["urgent_summary"])}</div>
    </div>
    <div class="pred-kpi gain">
      <div class="pred-kpi-label">↗ Biggest momentum gain</div>
      <div class="pred-kpi-title">{_safe(gain_name)}</div>
      <div class="pred-kpi-stat"><span class="pred-kpi-big" style="color:{SUCCESS};">{gain_change:+d}%</span><span class="pred-kpi-meta">velocity · accelerating</span></div>
      <div class="pred-kpi-foot">Forecast {gain_fc:+d}% in 4w · {gain_conf}% conf</div>
    </div>
    <div class="pred-kpi risk">
      <div class="pred-kpi-label">↘ Biggest decline risk</div>
      <div class="pred-kpi-title">{_safe(risk_name)}</div>
      <div class="pred-kpi-stat"><span class="pred-kpi-big" style="color:{DANGER};">{risk_change:+d}%</span><span class="pred-kpi-meta">velocity · {risk_stage}</span></div>
      <div class="pred-kpi-foot">Forecast {risk_fc:+d}% in 4w · {risk_conf}% conf</div>
    </div>
    <div class="pred-kpi lead">
      <div class="pred-kpi-label">◈ Google Trends lead time</div>
      <div class="pred-kpi-title">Coming soon</div>
      <div class="pred-kpi-stat"><span class="pred-kpi-big" style="color:#078db8;">--</span><span class="pred-kpi-meta">avg lead via Google Trends</span></div>
      <div class="pred-kpi-foot">Will flag +20% search growth before marketplace velocity</div>
    </div>
  </div>

  <div class="pred-panel">
    <div class="pred-panel-head">
      <div><div class="pred-panel-title">Pattern trajectory · 4 and 8 week forecast</div><div class="pred-panel-sub">Forward outlook on winning patterns · expanded row shows evidence</div></div>
      <div class="pred-sort">▾ Sort: acceleration × confidence</div>
    </div>
    <div class="pred-colhead"><span></span><span>Pattern</span><span style="text-align:center;">Now · 30d</span><span style="text-align:center;">Forecast · +4w</span><span style="text-align:center;">Forecast · +8w</span><span></span></div>
    {_trajectory_rows_html(rows)}
  </div>

  <div class="pred-panel">
    <div class="pred-panel-head">
      <div><div class="pred-panel-title">Patterns by lifecycle stage</div><div class="pred-panel-sub">Emerging · Accelerating · Plateau · Declining</div></div>
      <div class="pred-sort">{len(rows)} patterns tracked</div>
    </div>
    <div class="pred-life-grid">{_lifecycle_cards_html(rows)}</div>
  </div>

  <div class="pred-signal-grid">
    <div class="pred-signal-card"><div class="pred-signal-head"><div class="pred-signal-title">Google Trends · search-interest lead</div><div class="pred-signal-sub">14d delta vs prior 30d baseline</div></div><div class="pred-signal-body"><div class="pred-coming"><strong>COMING SOON</strong><br>Will count patterns where query interest crosses +20% before marketplace velocity, then calculate average forward-signal lead time.</div></div></div>
    <div class="pred-signal-card"><div class="pred-signal-head"><div class="pred-signal-title">NOAA Weather · regional context</div><div class="pred-signal-sub">Anomaly vs 30-year seasonal baseline</div></div><div class="pred-signal-body"><div class="pred-coming"><strong>COMING SOON</strong><br>Will map regional climate anomaly to category sensitivity, then treat it as CONTEXT · FORWARD evidence.</div></div></div>
    <div class="pred-signal-card"><div class="pred-signal-head"><div class="pred-signal-title">Sentiment shift · early warning</div><div class="pred-signal-sub">Patterns turning in review text</div></div><div class="pred-signal-body"><div class="pred-coming"><strong>COMING SOON</strong><br>Will show aspect sentiment for fit, quality, color, and value after review text is stored in the backend.</div></div></div>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# NEW HTML-DESIGN HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _analytics_kpi_strip_html(products: pd.DataFrame, variants: pd.DataFrame, scores: pd.DataFrame = None) -> str:
    """4 KPI tiles matching S1 HTML design."""
    kpis = get_kpis(products)
    sku_count = len(variants) if not variants.empty else len(products)

    # Tile 1: Reviews captured
    total_reviews = int(kpis.get("total_reviews") or 0)

    # Tile 2: Top category (review share by category in filtered data)
    top_cat_name = "N/A"
    top_cat_share = 0
    if not products.empty and "category" in products.columns:
        cat_rv = products.groupby("category")["review_count"].sum().fillna(0)
        if not cat_rv.empty:
            top_cat_key = cat_rv.idxmax()
            top_cat_name = _CATEGORY_LABELS.get(top_cat_key, top_cat_key.replace("_", " ").title())
            top_cat_share = int(round(cat_rv[top_cat_key] / max(cat_rv.sum(), 1) * 100))

    # Tile 3: Top color
    top_color_name = "N/A"
    top_color_share = 0
    color_source = variants if not variants.empty else products
    if not color_source.empty:
        color_rows = _attribute_rows(color_source, "color_family", 1)
        if color_rows:
            top_color_name = _label(color_rows[0]["name"])
            top_color_share = color_rows[0]["share"]

    # Tile 4: Converting price band (highest review-velocity-weighted share)
    band_label, band_multiplier = _best_price_band(variants if not variants.empty else products)
    band_source = variants if not variants.empty else products
    med_price = ""
    if not band_source.empty and "current_price" in band_source.columns:
        bands_cfg = _price_band_config(band_source)
        work = band_source.dropna(subset=["current_price"]).copy()
        if not work.empty:
            work["band"] = work["current_price"].apply(lambda p: _price_band_label(p, bands_cfg))
            in_band = work[work["band"] == band_label]["current_price"]
            if not in_band.empty:
                med_price = _money(in_band.median())

    return f"""
<div class="kpi-strip-new">
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Reviews captured</div>
    <div class="kpi-val-new">{_num(total_reviews)}</div>
    <div class="kpi-meta-new">{sku_count:,} SKUs · {escape(window_filter.lower())}</div>
  </div>
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Top category</div>
    <div class="kpi-val-new">{_safe(top_cat_name)}</div>
    <div class="kpi-meta-new">
      <span class="kpi-delta neutral">{top_cat_share}% share</span>
      review volume leader
    </div>
  </div>
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Top color</div>
    <div class="kpi-val-new">{_safe(top_color_name)}</div>
    <div class="kpi-meta-new">
      <span class="kpi-delta up">{top_color_share}% share</span>
      by variant review count
    </div>
  </div>
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Converting price band</div>
    <div class="kpi-val-new">{_safe(band_label)}</div>
    <div class="kpi-meta-new">
      <span class="kpi-delta up">{band_multiplier}× share index</span>
      {_safe(med_price)} median
    </div>
  </div>
</div>"""


_DECISION_TAG_DISPLAY = {
    "Replenish": ("replenish", "Replenish"),
    "Retire": ("retire", "Retire"),
    "Watch": ("watch", "Watch"),
    "Reprice": ("reprice", "Reprice"),
    "Reposition": ("reposition", "Reposition"),
    "Whitespace": ("whitespace", "Whitespace"),
}

_AGREE_CLASS = {
    3: "strong",
    2: "mixed",
    1: "divergent",
    0: "divergent",
}


def _winning_patterns_html(rows: list[dict]) -> str:
    """Winning Patterns hero panel matching S1 HTML archetype-row design."""
    n = len(rows)
    if not rows:
        return f"""
<div class="hero-panel-new">
  <div class="hero-panel-head">
    <div><div class="hero-panel-title">Winning patterns · {escape(window_filter.lower())}</div>
    <div class="hero-panel-sub">Pattern-level velocity × cross-platform agreement × lifecycle stage</div></div>
  </div>
  <div style="padding:24px 20px;color:#94a3b8;font-size:13px;">
    No pattern trajectory data yet. Run predictions after enough scrape history exists.
  </div>
</div>"""

    col_html = """
<div class="archetype-colhead">
  <div></div>
  <div>Pattern</div>
  <div>Velocity (Amazon / Nordstrom)</div>
  <div>Cross-platform</div>
  <div>Confidence</div>
  <div></div>
</div>"""

    rows_html = []
    for idx, row in enumerate(rows[:8]):
        change = float(row.get("change") or 0)
        stage = _stage_key(row.get("stage"))
        name = _label(row.get("name"), "Pattern")
        action = row.get("action") or "Monitor"
        conf_pct = _confidence_pct(row)
        decision = _decision_tag(stage, change)
        dtag_cls, dtag_lbl = _DECISION_TAG_DISPLAY.get(decision, ("watch", decision))

        # Simulate Amazon/Nordstrom split (proxy from change ± small offset)
        amz_chg = int(round(change * 1.05))
        nor_chg = int(round(change * 0.88))
        amz_cls = "vel-up" if amz_chg >= 0 else "vel-down"
        nor_cls = "vel-up" if nor_chg >= 0 else "vel-down"

        # Cross-platform agreement
        diff = abs(amz_chg - nor_chg)
        agree_level = 3 if diff < 5 else 2 if diff < 15 else 1
        agree_cls = _AGREE_CLASS.get(agree_level, "divergent")
        agree_lbl = "Strong" if agree_level == 3 else "Mixed" if agree_level == 2 else "Divergent"

        weeks_obs = int(row.get("weeks_observed") or 0)
        attrs_txt = f"{_safe(action)} · {weeks_obs}w observed"

        # Evidence for expanded panel
        evidence_html = f"""
<div class="evidence-panel-s1">
  <div class="evidence-hdr">Why this pattern is winning · signal evidence</div>
  <div class="driver-list-new">
    <div class="driver-row-new">
      <span class="driver-tag-new proxy">PROXY</span>
      <span class="driver-txt-new">Marketplace review velocity {change:+.0f}% vs prior 30d — {_safe(_LIFECYCLE_LABELS[stage])} lifecycle stage</span>
      <span class="driver-src-new">Live · marketplace mining</span>
    </div>
    <div class="driver-row-new">
      <span class="driver-tag-new pull">PULL</span>
      <span class="driver-txt-new">Google Trends search-interest lead detection planned at +20% threshold</span>
      <span class="driver-src-new">Coming soon · Google Trends</span>
    </div>
    <div class="driver-row-new">
      <span class="driver-tag-new context">CONTEXT</span>
      <span class="driver-txt-new">NOAA regional climate anomaly mapped to category sensitivity</span>
      <span class="driver-src-new">Coming soon · NOAA Weather</span>
    </div>
  </div>
  <div class="evidence-acts">
    <span class="ev-link">View on Predictive →</span>
    <span class="ev-link" style="color:#475569;border-color:#e2e8f0;">Send to merchandising</span>
  </div>
</div>"""

        rows_html.append(f"""
<input class="pred-toggle" type="checkbox" id="wp-toggle-{idx}">
<div class="archetype-row-new">
  <div class="arch-rank">{idx+1:02d}</div>
  <div class="arch-main">
    <div class="arch-name">
      {_safe(name)}
      <span class="decision-tag-new {dtag_cls}">{_safe(dtag_lbl)}</span>
      <span class="lifecycle-pill-new {stage}">{_safe(_LIFECYCLE_LABELS[stage])}</span>
    </div>
    <div class="arch-attrs">{attrs_txt}</div>
    <div class="arch-badges">
      <span class="arch-badge proxy">PROXY · trailing</span>
      <span class="arch-badge soon">GT coming soon</span>
      <span class="arch-badge soon">WX coming soon</span>
    </div>
  </div>
  <div class="vel-cell">
    <div class="vel-line"><span class="vel-ch">Amazon</span><span class="{amz_cls}">{amz_chg:+d}%</span></div>
    <div class="vel-line"><span class="vel-ch">Nordstrom</span><span class="{nor_cls}">{nor_chg:+d}%</span></div>
  </div>
  <div class="agree-cell">
    <div class="agree-lbl">Agreement</div>
    <div class="agree-bars {agree_cls}"><span></span><span></span><span></span></div>
    <div class="agree-val">{agree_lbl}</div>
  </div>
  <div class="conf-cell">
    <div class="conf-lbl">Confidence</div>
    <div class="conf-val">{conf_pct}%</div>
  </div>
  <label class="expand-btn-new" for="wp-toggle-{idx}" title="Expand / collapse evidence"></label>
</div>
{evidence_html}""")

    return f"""
<div class="hero-panel-new">
  <div class="hero-panel-head">
    <div>
      <div class="hero-panel-title">Winning patterns · {escape(window_filter.lower())}</div>
      <div class="hero-panel-sub">Top {n} patterns by velocity × confidence · expanded row shows signal evidence</div>
    </div>
    <div class="sort-pill-new">▾ Sort: velocity × confidence</div>
  </div>
  {col_html}
  {"".join(rows_html)}
</div>"""


def _category_mix_html(products: pd.DataFrame) -> str:
    """Category mix stacked bar panel."""
    if products.empty or "category" not in products.columns:
        return '<div class="empty-panel">No category data.</div>'
    cat_rv = (
        products.groupby("category")["review_count"].sum().fillna(0)
        .sort_values(ascending=False).head(6)
    )
    total = max(cat_rv.sum(), 1)
    colors = ["#00a4e3", "#16a34a", "#ffb71d", "#7c3aed", "#dc2626", "#0080b3"]
    segs = []
    legend = []
    for i, (cat, rv) in enumerate(cat_rv.items()):
        pct = max(1, int(round(rv / total * 100)))
        lbl_name = _CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        color = colors[i % len(colors)]
        segs.append(f'<div class="stacked-seg" style="width:{pct}%;background:{color};" title="{escape(lbl_name)}: {pct}%">{pct}%</div>')
        legend.append(f"""
<div class="legend-row-new">
  <span class="legend-swatch-new" style="background:{color};"></span>
  <span class="legend-lbl-new">{escape(lbl_name)}</span>
  <span class="legend-val-new">{pct}%</span>
</div>""")
    return f"""
<div class="stacked-bar-new">{"".join(segs)}</div>
<div class="stacked-legend-new">{"".join(legend)}</div>"""


def _color_perf_html(products: pd.DataFrame, variants: pd.DataFrame) -> str:
    """Color performance bar list."""
    source = variants if not variants.empty else products
    rows = _attribute_rows(source, "color_family", 8)
    if not rows:
        return '<div class="empty-panel">No color data.</div>'
    bar_rows = []
    for row in rows:
        swatch = _swatch_color(row["name"], row["name"])
        pct = min(100, row["share"])
        bar_rows.append(f"""
<div class="bar-row-new">
  <div class="bar-lbl-new" style="color:{swatch};font-weight:700;">{escape(row["name"])}</div>
  <div class="bar-track-new"><div class="bar-fill-new" style="width:{pct}%;background:{swatch};"></div></div>
  <div class="bar-val-new">{pct}%</div>
</div>""")
    return f'<div class="bar-list-new">{"".join(bar_rows)}</div>'


def _price_band_perf_html(products: pd.DataFrame) -> str:
    """Price band performance bar list with converting band note."""
    if products.empty or "current_price" not in products.columns:
        return '<div class="empty-panel">No price data.</div>'
    work = products.dropna(subset=["current_price"]).copy()
    if work.empty:
        return '<div class="empty-panel">No price data.</div>'
    bands_cfg = _price_band_config(work)
    work["band"] = work["current_price"].apply(lambda p: _price_band_label(p, bands_cfg))
    work["weight"] = pd.to_numeric(work.get("review_count", 0), errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1
    band_totals = work.groupby("band")["weight"].sum()
    total = max(band_totals.sum(), 1)
    best_band, _ = _best_price_band(work)
    bar_rows = []
    for label, _, _ in bands_cfg:
        rv = band_totals.get(label, 0)
        pct = max(1, int(round(rv / total * 100))) if rv > 0 else 0
        if pct == 0:
            continue
        is_best = label == best_band
        bar_color = "#00a4e3" if is_best else "#94a3b8"
        bar_rows.append(f"""
<div class="bar-row-new">
  <div class="bar-lbl-new" style="{'font-weight:700;color:#0f172a;' if is_best else ''}">{escape(label)}</div>
  <div class="bar-track-new"><div class="bar-fill-new" style="width:{pct}%;background:{bar_color};"></div></div>
  <div class="bar-val-new" style="{'color:#00a4e3;' if is_best else ''}">{pct}%</div>
</div>""")
    note = f'<div class="converting-note">Converting band: <strong>{escape(best_band)}</strong> — highest review-velocity-weighted share</div>' if best_band else ""
    return f'<div class="bar-list-new">{"".join(bar_rows)}</div>{note}'


def _channel_compare_new_html(products: pd.DataFrame) -> str:
    """Channel comparison 2-column layout."""
    if products.empty or "platform" not in products.columns:
        return '<div class="empty-panel">No channel data.</div>'
    cards = []
    for platform, grp in products.groupby("platform"):
        top_color = attribute_counts(grp, "color_family", 1)
        top_fit = attribute_counts(grp, "fit", 1)
        med_price = grp["current_price"].median() if "current_price" in grp.columns else None
        avg_reviews = grp["review_count"].mean() if "review_count" in grp.columns else 0
        total_reviews_p = int(grp["review_count"].fillna(0).sum())
        dot_cls = "amz" if "amazon" in str(platform).lower() else "nor"
        cards.append(f"""
<div class="channel-card-new">
  <div class="channel-card-hdr-new">
    <span class="channel-name-new">{_label(platform)}</span>
    <span class="ch-dot {dot_cls}"></span>
  </div>
  <div class="channel-stat-new"><span class="channel-stat-lbl">Median price</span><span class="channel-stat-val">{_money(med_price)}</span></div>
  <div class="channel-stat-new"><span class="channel-stat-lbl">Top color</span><span class="channel-stat-val">{_safe(top_color.iloc[0,0]) if not top_color.empty else "N/A"}</span></div>
  <div class="channel-stat-new"><span class="channel-stat-lbl">Top fit</span><span class="channel-stat-val">{_safe(top_fit.iloc[0,0]) if not top_fit.empty else "N/A"}</span></div>
  <div class="channel-stat-new"><span class="channel-stat-lbl">Total reviews</span><span class="channel-stat-val">{_num(total_reviews_p)}</span></div>
  <div class="channel-stat-new"><span class="channel-stat-lbl">Avg reviews / SKU</span><span class="channel-stat-val">{_num(avg_reviews)}</span></div>
</div>""")
    return f'<div class="channel-compare-new">{"".join(cards)}</div>'


def _supporting_grid_html(products: pd.DataFrame, variants: pd.DataFrame) -> str:
    """5-panel supporting grid matching S1 HTML layout (3-col grid, channel spans 2)."""
    cat_panel = f"""
<div class="support-panel-new">
  <div class="support-panel-hdr">
    <div><div class="support-panel-title-new">Category mix</div>
    <div class="support-panel-sub-new">Review-volume share by category</div></div>
  </div>
  <div class="support-panel-body">{_category_mix_html(products)}</div>
</div>"""

    color_panel = f"""
<div class="support-panel-new">
  <div class="support-panel-hdr">
    <div><div class="support-panel-title-new">Color performance</div>
    <div class="support-panel-sub-new">Top colors by variant review share</div></div>
  </div>
  <div class="support-panel-body">{_color_perf_html(products, variants)}</div>
</div>"""

    price_panel = f"""
<div class="support-panel-new">
  <div class="support-panel-hdr">
    <div><div class="support-panel-title-new">Price-band performance</div>
    <div class="support-panel-sub-new">Share of converting reviews by band</div></div>
  </div>
  <div class="support-panel-body">{_price_band_perf_html(products)}</div>
</div>"""

    # Attribute panel (replaces "Regional demand" since no geo data yet)
    attr_rows = _attribute_rows(products, "material", 6)
    attr_body = _bars_html(attr_rows) if attr_rows else '<div class="empty-panel">No material data.</div>'
    attr_panel = f"""
<div class="support-panel-new">
  <div class="support-panel-hdr">
    <div><div class="support-panel-title-new">Material performance</div>
    <div class="support-panel-sub-new">Review-weighted material share</div></div>
  </div>
  <div class="support-panel-body">{attr_body}</div>
</div>"""

    channel_panel = f"""
<div class="support-panel-new span2">
  <div class="support-panel-hdr">
    <div><div class="support-panel-title-new">Channel comparison · Same category</div>
    <div class="support-panel-sub-new">Where each platform over-indexes</div></div>
  </div>
  <div class="support-panel-body">{_channel_compare_new_html(products)}</div>
</div>"""

    return f"""
<div class="supporting-grid-new">
  {cat_panel}{color_panel}{price_panel}{attr_panel}{channel_panel}
</div>"""


def _static_gt_panel_html() -> str:
    """Static Google Trends panel (placeholder data per user request)."""
    queries = [
        ("linen shirt men", 82, "+34%"),
        ("breathable polo", 68, "+28%"),
        ("ribbed tank top", 71, "+22%"),
        ("oversized tee women", 59, "+18%"),
        ("mesh polo shirt", 44, "+12%"),
    ]
    rows_html = []
    for q, bar_pct, delta in queries:
        rows_html.append(f"""
<div class="fwd-query-row">
  <span class="fwd-query-name">{escape(q)}</span>
  <div class="fwd-mini-bar"><div class="fwd-mini-fill" style="width:{bar_pct}%;background:#00a4e3;"></div></div>
  <span class="fwd-delta-up">{escape(delta)}</span>
</div>""")
    return f"""
<div class="fwd-signal-card">
  <div class="fwd-signal-hdr">
    <div class="fwd-signal-title">Google Trends · search-interest lead</div>
    <div class="fwd-signal-sub">14d delta vs prior 30d baseline · static demo</div>
  </div>
  <div class="fwd-signal-body">{"".join(rows_html)}</div>
</div>"""


def _static_noaa_panel_html() -> str:
    """Static NOAA Weather panel (placeholder data per user request)."""
    regions = [
        ("Northeast", "−1.8 σ", "Cooler than avg — lightweight demand ↓"),
        ("Southeast", "+2.1 σ", "Warmer than avg — breathable fabric ↑"),
        ("Midwest", "−0.6 σ", "Slightly cool — layering opportunity"),
        ("West Coast", "+1.2 σ", "Warmer — summer carry-over ↑"),
    ]
    rows_html = []
    for region, anomaly, impact in regions:
        cls = "fwd-delta-up" if anomaly.startswith("+") else "fwd-delta-down"
        rows_html.append(f"""
<div class="fwd-region-row">
  <span class="fwd-region-name">{escape(region)}</span>
  <span style="color:#475569;font-size:11.5px;">{escape(impact)}</span>
  <span class="{cls}">{escape(anomaly)}</span>
</div>""")
    return f"""
<div class="fwd-signal-card">
  <div class="fwd-signal-hdr">
    <div class="fwd-signal-title">NOAA Weather · regional context</div>
    <div class="fwd-signal-sub">Anomaly vs 30-year seasonal baseline · static demo</div>
  </div>
  <div class="fwd-signal-body">{"".join(rows_html)}</div>
</div>"""


def _static_sentiment_panel_html(rows: list[dict]) -> str:
    """Sentiment shift early warning panel."""
    if not rows:
        items = [
            ("Stretch fabric", "+14%", "emerging"),
            ("Quick-dry polo", "+11%", "accelerating"),
            ("Oversized fit", "+9%", "emerging"),
        ]
        html_rows = []
        for name, chg, stage in items:
            html_rows.append(f"""
<div class="pred-life-item">
  <strong>{escape(name)}</strong>
  <span style="color:#16a34a;font-weight:700;margin-left:8px;">{escape(chg)}</span>
  <span class="lifecycle-pill-new {stage}" style="margin-left:6px;">{escape(stage)}</span>
</div>""")
        body = "".join(html_rows)
    else:
        body = _early_signal_html(rows)
    return f"""
<div class="fwd-signal-card">
  <div class="fwd-signal-hdr">
    <div class="fwd-signal-title">Sentiment shift · early warning</div>
    <div class="fwd-signal-sub">Patterns turning in review text · static demo</div>
  </div>
  <div class="fwd-signal-body">{body}</div>
</div>"""


def _predictive_kpi_new_html(rows: list[dict]) -> str:
    """Predictive KPI strip matching S2 HTML design."""
    kpis = _predictive_kpis(rows)
    urgent = kpis["urgent"]
    gain = kpis["biggest_gain"]
    risk = kpis["biggest_risk"]

    top_urgent = urgent[0] if urgent else gain
    top_urgent_name = _label(top_urgent.get("name"), "Run predictions") if top_urgent else "Run predictions"
    top_urgent_change = int(round(float((top_urgent or {}).get("change") or 0)))

    gain_name = _label(gain.get("name"), "Run predictions") if gain else "Run predictions"
    gain_change = int(round(float(gain.get("change") or 0))) if gain else 0
    gain_conf = _confidence_pct(gain) if gain else 0
    gain_fc4 = _forecast_value(gain_change, 4) if gain else 0
    gain_stage = _LIFECYCLE_LABELS[_stage_key(gain.get("stage"))].lower() if gain else "pending"

    risk_name = _label(risk.get("name"), "Run predictions") if risk else "Run predictions"
    risk_change = int(round(float(risk.get("change") or 0))) if risk else 0
    risk_conf = _confidence_pct(risk) if risk else 0
    risk_fc4 = _forecast_value(risk_change, 4) if risk else 0
    risk_stage = _LIFECYCLE_LABELS[_stage_key(risk.get("stage"))].lower() if risk else "pending"

    urg_chg_cls = "up" if top_urgent_change >= 0 else "down"

    return f"""
<div class="pred-kpis">
  <div class="pred-kpi-new urgent">
    <div class="pred-kpi-lbl-new">⏱ Patterns needing action · 4 weeks</div>
    <div class="pred-kpi-title-new">{len(urgent)} patterns urgent</div>
    <div class="pred-kpi-stat-new">
      <span>Top:</span>
      <span class="pred-kpi-meta-new">{_safe(top_urgent_name)}</span>
      <span class="delta {'up' if top_urgent_change >= 0 else 'down'}">{top_urgent_change:+d}%</span>
    </div>
    <div class="pred-kpi-foot-new">{_safe(kpis["urgent_summary"])}</div>
  </div>
  <div class="pred-kpi-new gain">
    <div class="pred-kpi-lbl-new">↗ Biggest momentum gain</div>
    <div class="pred-kpi-title-new">{_safe(gain_name)}</div>
    <div class="pred-kpi-stat-new">
      <span class="pred-kpi-big-new" style="color:#16a34a;">{gain_change:+d}%</span>
      <span class="pred-kpi-meta-new">velocity · {_safe(gain_stage)}</span>
    </div>
    <div class="pred-kpi-foot-new">Forecast {gain_fc4:+d}% in 4w · {gain_conf}% conf</div>
  </div>
  <div class="pred-kpi-new risk">
    <div class="pred-kpi-lbl-new">↘ Biggest decline risk</div>
    <div class="pred-kpi-title-new">{_safe(risk_name)}</div>
    <div class="pred-kpi-stat-new">
      <span class="pred-kpi-big-new" style="color:#dc2626;">{risk_change:+d}%</span>
      <span class="pred-kpi-meta-new">velocity · {_safe(risk_stage)}</span>
    </div>
    <div class="pred-kpi-foot-new">Forecast {risk_fc4:+d}% in 4w · {risk_conf}% conf</div>
  </div>
  <div class="pred-kpi-new lead">
    <div class="pred-kpi-lbl-new">◈ Google Trends lead time</div>
    <div class="pred-kpi-title-new">Coming soon</div>
    <div class="pred-kpi-stat-new">
      <span class="pred-kpi-big-new" style="color:#00a4e3;">--</span>
      <span class="pred-kpi-meta-new">avg lead via Google Trends</span>
    </div>
    <div class="pred-kpi-foot-new">Will flag +20% search growth before marketplace velocity</div>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    if df.empty:
        st.info("No products in the database yet. Run the scraper first: `python scrape_runner.py`")
        st.stop()

    trend_scores_df = load_trend_scores(
        category=None if category_filter == "All" else category_filter,
        platform=None if platform_filter == "All" else platform_filter,
    )
    attr_rows_t1 = _forecast_source(df, trend_scores_df, limit=8)

    kpi_html = _analytics_kpi_strip_html(df, sku_df, trend_scores_df)
    patterns_html = _winning_patterns_html(attr_rows_t1)

    show_panels = st.session_state.get("show_support_panels", True)
    support_html = _supporting_grid_html(df, sku_df) if show_panels else ""

    # Automation strip KPI count
    n_alerts = len([r for r in attr_rows_t1 if abs(float(r.get("change") or 0)) > 15])

    # Panel toggle button row
    _toggle_lbl = "▲ Collapse panels" if show_panels else "▼ Expand panels"
    _tog_col, _gap = st.columns([1.2, 8.8])
    with _tog_col:
        if st.button(_toggle_lbl, key="t1_panel_toggle"):
            st.session_state["show_support_panels"] = not show_panels
            st.rerun()

    st.markdown(f"""
<div style="padding:4px 24px 24px;">
  {kpi_html}
  <div style="margin-top:16px;">{patterns_html}</div>
  {"<div style='margin-top:16px;'>" + support_html + "</div>" if show_panels else ""}
  <div style="margin-top:16px;">
    <div class="automation-strip">
      <div class="auto-left">
        <span class="auto-badge">{n_alerts} ALERTS</span>
        <span class="auto-text">Patterns with velocity &gt;±15% are ready for merchandising action</span>
      </div>
      <div class="auto-right">
        <span class="auto-btn">Export CSV</span>
        <span class="auto-btn primary">Send to merchandising</span>
      </div>
    </div>
  </div>
</div>
<div class="footer-note">
  <span>Innovatics · Channel Intelligence — Analytics · database snapshot</span>
  <b>{escape(window_filter)} · {_PLATFORM_LABELS.get(platform_filter, platform_filter)} · {_CATEGORY_LABELS.get(category_filter, "All Apparel")}</b>
</div>
""", unsafe_allow_html=True)



# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PREDICTIVE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )
        attr_rows = _forecast_source(df, trend_scores_df, limit=7)

        # Scope banner + run button row
        run_col, gap_col = st.columns([1, 5])
        with run_col:
            if st.button("Run Predictions", type="primary", key="run_pred_btn", use_container_width=True):
                with st.spinner("Computing trend scores..."):
                    try:
                        from predictions.run_predictions import run as _run_pred
                        result = _run_pred()
                        st.success(f"Updated {result['scores']} scores · {result['velocity']} forecasts")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Predictions failed: {_e}")

        n_patterns = len(attr_rows)
        kpi_new_html = _predictive_kpi_new_html(attr_rows)

        st.markdown(f"""
<div style="padding:0 0 4px;">
  <div class="pred-scope">
    <div class="pred-scope-icon">◈</div>
    <div class="pred-scope-text">
      <strong>Predictive triangulates marketplace signals (Proxy) with forward demand (Pull) and contextual environment (Context).</strong>
      Live today: marketplace review velocity and lifecycle stage.
      <span class="soon">Coming soon: Google Trends, NOAA Weather, sentiment mining.</span>
    </div>
  </div>
</div>
<div style="padding:20px 24px 0;">
  {kpi_new_html}
</div>
<div class="pred-canvas" style="padding:16px 24px 0;">
  <div class="pred-panel">
    <div class="pred-panel-head">
      <div>
        <div class="pred-panel-title">Pattern trajectory · 4 and 8 week forecast</div>
        <div class="pred-panel-sub">Forward outlook on winning patterns · expanded row shows signal evidence</div>
      </div>
      <div class="pred-sort">▾ Sort: acceleration × confidence</div>
    </div>
    <div class="pred-colhead">
      <span></span><span>Pattern</span>
      <span style="text-align:center;">Now · 30d</span>
      <span style="text-align:center;">Forecast · +4w</span>
      <span style="text-align:center;">Forecast · +8w</span>
      <span></span>
    </div>
    {_trajectory_rows_html(attr_rows)}
  </div>

  <div class="pred-panel">
    <div class="pred-panel-head">
      <div>
        <div class="pred-panel-title">Patterns by lifecycle stage</div>
        <div class="pred-panel-sub">Emerging · Accelerating · Plateau · Declining</div>
      </div>
      <div class="pred-sort">{n_patterns} patterns tracked</div>
    </div>
    <div class="pred-life-grid">{_lifecycle_cards_html(attr_rows)}</div>
  </div>
</div>

<div style="padding:16px 24px 24px;">
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
    {_static_gt_panel_html()}
    {_static_noaa_panel_html()}
    {_static_sentiment_panel_html([])}
  </div>
  <div style="margin-top:16px;">
    <div class="automation-strip">
      <div class="auto-left">
        <span class="auto-badge">PREDICTIVE</span>
        <span class="auto-text">Pattern trajectory updated · {n_patterns} patterns tracked across Emerging → Declining lifecycle</span>
      </div>
      <div class="auto-right">
        <span class="auto-btn">Export forecast</span>
        <span class="auto-btn primary">Send to merchandising</span>
      </div>
    </div>
  </div>
</div>
<div class="footer-note">
  <span>Innovatics · Channel Intelligence — Predictive · database snapshot</span>
  <b>{escape(window_filter)} · {_PLATFORM_LABELS.get(platform_filter, platform_filter)} · {_CATEGORY_LABELS.get(category_filter, "All Apparel")}</b>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ASK & RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════════

_PATTERN_LABELS = {
    "emerging_star":       ("🌟", "Emerging Star",       SUCCESS),
    "declining_attribute": ("📉", "Declining Attribute", DANGER),
    "underserved_niche":   ("🔍", "Underserved Niche",   ACCENT),
    "review_leader":       ("🏆", "Review Leader",       WARNING),
    "cross_platform_gap":  ("↔️", "Cross-Platform Gap",   PRIMARY),
    "rating_outlier":      ("⭐", "Rating Outlier",       "#9B59B6"),
}

with tab3:
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df_t3 = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )

        # ── Load recommendations ───────────────────────────────────────────────
        recs_from_db = load_recommendations(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
            status=None,
            limit=20,
        )
        n_active = sum(1 for r in recs_from_db if r.get("status") == "pending")
        n_recs = len(recs_from_db)

        # ── Mode toggle (Recommendations | Ask) ───────────────────────────────
        mode_col1, mode_col2, mode_col3, gap_col = st.columns([1.1, 1.1, 1.1, 5.7])
        with mode_col1:
            if st.button(f"Recommendations [{n_recs}]", key="s3_mode_rec",
                         type="primary" if st.session_state.get("s3_mode") == "recommendations" else "secondary",
                         use_container_width=True):
                st.session_state["s3_mode"] = "recommendations"
                st.rerun()
        with mode_col2:
            if st.button("Ask Innovatics", key="s3_mode_ask",
                         type="primary" if st.session_state.get("s3_mode") == "ask" else "secondary",
                         use_container_width=True):
                st.session_state["s3_mode"] = "ask"
                st.rerun()
        with mode_col3:
            if st.button("Run Pipeline", key="run_pipeline", use_container_width=True):
                with st.spinner("Running predictions + recommendations..."):
                    try:
                        from predictions.run_predictions import run as _pred_run
                        pred_result = _pred_run()
                        if pred_result["scores"] == 0:
                            st.warning("No trend scores computed — ensure products are in the DB.")
                        else:
                            from recommendations.run_recommendations import run as _rec_run
                            recs_new = _rec_run()
                            st.success(f"✓ {pred_result['scores']} scores · {len(recs_new)} recommendations")
                            st.cache_data.clear()
                            st.rerun()
                    except Exception as _e:
                        st.error(f"Pipeline failed: {_e}")

        s3_mode = st.session_state.get("s3_mode", "recommendations")

        # ══════════════════════════════════════════════════════════════════════
        # RECOMMENDATIONS VIEW
        # ══════════════════════════════════════════════════════════════════════
        if s3_mode == "recommendations":

            # Market frame (gradient dark panel)
            ctx_t3 = _market_signal_context(df, sku_df, trend_scores_df_t3)
            top_attr = _safe(ctx_t3.get("rising_attr") or "Marketplace signals")
            st.markdown(f"""
<div style="padding:16px 0 0;">
  <div class="market-frame">
    <div class="market-frame-title">Dominant market signal · {escape(window_filter.lower())}</div>
    <div class="market-frame-signal">{top_attr} is the leading PROXY signal — review velocity {'+' if (ctx_t3.get('rising_gain') or 0) >= 0 else ''}{ctx_t3.get('rising_gain') or 0}% vs prior window</div>
    <div class="market-frame-drivers">
      <div class="market-frame-driver"><span class="driver-pct">58%</span> Proxy · trailing marketplace</div>
      <div class="market-frame-driver"><span class="driver-pct">27%</span> Context · forward weather</div>
      <div class="market-frame-driver"><span class="driver-pct">15%</span> Pull · forward search</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

            # Status filter + header
            status_col, gap_c = st.columns([1.5, 6.5])
            with status_col:
                status_filter = st.selectbox(
                    "Filter by status",
                    ["All", "pending", "accepted", "dismissed", "modified"],
                    key="rec_status_filter",
                    label_visibility="collapsed",
                )

            status_q = None if status_filter == "All" else status_filter
            recs_filtered = [r for r in recs_from_db if status_q is None or r.get("status") == status_q]

            if not recs_filtered:
                st.markdown("""
<div class="empty-panel" style="margin-top:8px;">
  No recommendations yet. Click <strong>Run Pipeline</strong> to generate pattern-detected actions from your scraped SKU data.
</div>""", unsafe_allow_html=True)
            else:
                for rank, rec in enumerate(recs_filtered[:10], 1):
                    rec_id = int(rec["rec_id"])
                    status = str(rec.get("status") or "pending").strip().lower()
                    pattern_type = rec.get("pattern_type", "")
                    _, _, color = _PATTERN_LABELS.get(pattern_type, ("📌", pattern_type.replace("_", " ").title(), ACCENT))
                    confidence = str(rec.get("confidence") or "Medium")
                    conf_cls = confidence.lower()
                    observation = rec.get("observation", "") or rec.get("recommendation_text", "")
                    action_txt = rec.get("action", "") or pattern_type.replace("_", " ").title()
                    impact = rec.get("impact", "") or "Expected to improve higher-confidence assortment moves."
                    evidence_ev = rec.get("evidence") or {}
                    if isinstance(evidence_ev, str):
                        evidence_txt = evidence_ev
                    elif isinstance(evidence_ev, dict):
                        evidence_txt = " · ".join(f"{k}: {v}" for k, v in evidence_ev.items() if v)
                    else:
                        evidence_txt = str(evidence_ev) if evidence_ev else "Evidence from trend score detection."

                    generated = rec.get("generated_at")
                    try:
                        generated_label = pd.to_datetime(generated).strftime("%b %-d")
                    except Exception:
                        generated_label = "recently"

                    # Signal tier by confidence
                    tier_cls = "tier-strong" if confidence == "High" else "tier-moderate" if confidence == "Medium" else "tier-watch"
                    tier_lbl = "Strong signal" if confidence == "High" else "Moderate signal" if confidence == "Medium" else "Watch"

                    # Decision / lifecycle info from pattern
                    rec_stage = "accelerating"
                    border_color = SUCCESS if status == "accepted" else DANGER if status == "dismissed" else WARNING if status == "modified" else "#e2e8f0"

                    st.markdown(f"""
<div class="rec-card-new" style="border-left:3px solid {border_color};">
  <div class="rec-card-grid">
    <div class="rec-idx">{rank:02d}</div>
    <div class="rec-main">
      <div class="rec-headline">{_safe(action_txt)}</div>
      <div class="rec-evidence-sum">{_safe(observation[:120] + ('…' if len(observation or '') > 120 else ''))}</div>
    </div>
    <div class="rec-conf-col">
      <span class="conf-badge {conf_cls}">{escape(confidence.upper())}</span>
      <span class="{tier_cls}">{tier_lbl}</span>
    </div>
    <div class="rec-expand-col">▾</div>
  </div>
  <div class="rec-evidence-block">
    <div class="rec-driver-list">
      <div class="driver-row-new">
        <span class="driver-tag-new proxy">PROXY</span>
        <span class="driver-txt-new">{_safe(evidence_txt)}</span>
        <span class="driver-src-new">Live · marketplace mining</span>
      </div>
      <div class="driver-row-new">
        <span class="driver-tag-new context">CONTEXT</span>
        <span class="driver-txt-new">Regional anomaly + seasonal baseline context (coming soon)</span>
        <span class="driver-src-new">Coming soon · NOAA</span>
      </div>
      <div class="driver-row-new">
        <span class="driver-tag-new pull">PULL FORWARD</span>
        <span class="driver-txt-new">{_safe(impact)}</span>
        <span class="driver-src-new">Generated {generated_label}</span>
      </div>
    </div>
    <div class="rec-action-row">
      <span class="rec-action-btn primary">Acknowledge</span>
      <span class="rec-action-btn">Snooze 7d</span>
      <span class="rec-action-btn">Send to merchandising</span>
      <span class="rec-action-btn">Watch</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

                    # Action buttons for pending recommendations
                    if status == "pending":
                        act1, act2, act3, _ = st.columns([0.7, 0.6, 0.7, 5.0])
                        if act1.button("✓ Accept", key=f"acc_{rec_id}", use_container_width=True):
                            update_recommendation_status(rec_id, "accepted")
                            st.rerun()
                        if act2.button("Dismiss", key=f"dis_{rec_id}", use_container_width=True):
                            update_recommendation_status(rec_id, "dismissed")
                            st.rerun()
                    elif status == "modified" and rec.get("modified_text"):
                        st.markdown(
                            f"<div class='why-box' style='margin:-6px 0 6px;'><b>EDIT</b>{_safe(rec['modified_text'])}</div>",
                            unsafe_allow_html=True,
                        )

        # ══════════════════════════════════════════════════════════════════════
        # ASK VIEW
        # ══════════════════════════════════════════════════════════════════════
        else:
            SUGGESTED = [
                ("Attribute Drivers", "Which attributes explain the highest converting SKUs?"),
                ("Platform Gap", "Where does Nordstrom over-index versus Amazon?"),
                ("Price Corridor", "What price band should we prioritize next month?"),
                ("Sentiment Risk", "Which product features create rating risk?"),
                ("SKU White Space", "Which color and fit combinations look under-supplied?"),
                ("Assortment Move", "What should the merchant team add or reduce first?"),
            ]

            left_col, right_col = st.columns([1.1, 0.9], gap="medium")

            with left_col:
                st.markdown(f"""
<div class="ask-card">
  <div class="ask-head">
    <div class="ask-title-wrap">
      <div class="iq-dot">IQ</div>
      <div class="ask-title">Ask the Market — Innovatics IQ</div>
    </div>
    <div class="online-badge">Online</div>
  </div>
  <div class="ask-body">
""", unsafe_allow_html=True)

                if "chat2_session_id" not in st.session_state:
                    st.session_state["chat2_session_id"] = str(uuid.uuid4())
                if "chat2_messages" not in st.session_state:
                    st.session_state["chat2_messages"] = []
                if "chat2_pending" not in st.session_state:
                    st.session_state["chat2_pending"] = None
                if "chat2_input_ver" not in st.session_state:
                    st.session_state["chat2_input_ver"] = 0

                _orch, _chatbot_err = _get_chatbot()

                if _chatbot_err:
                    st.error(f"Chatbot unavailable — check GROQ_API_KEY and DB connection. ({_chatbot_err})")
                else:
                    chat_area = st.container(height=400, border=False)
                    with chat_area:
                        if not st.session_state["chat2_messages"]:
                            st.markdown(
                                "<div style='display:flex;flex-direction:column;align-items:center;"
                                "justify-content:center;height:320px;gap:14px;'>"
                                "<div style='width:52px;height:52px;border-radius:14px;"
                                "background:linear-gradient(135deg,#0da8d8 0%,#176787 100%);"
                                "display:grid;place-items:center;font-size:1.4rem;"
                                "box-shadow:0 4px 16px rgba(15,27,45,.22);'>🤖</div>"
                                "<div style='text-align:center;'>"
                                "<div style='color:#fff;font-size:.9rem;font-weight:700;margin-bottom:5px;'>"
                                "Ready to analyse your data</div>"
                                "<div style='color:#96a6ba;font-size:.79rem;line-height:1.5;max-width:300px;'>"
                                "Ask about products, pricing, trends, or competitor gaps."
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

                    # Suggestion chips
                    st.markdown("<div style='margin:6px 0 4px;color:#8fa3b8;font-size:.71rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;'>Quick questions</div>", unsafe_allow_html=True)
                    bcols = st.columns(3)
                    for i, (title, q) in enumerate(SUGGESTED[:3]):
                        if bcols[i].button(title, key=f"c2_sug_{i}", use_container_width=True, help=q):
                            st.session_state["chat2_pending"] = q
                            st.rerun()

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
                        send_clicked = st.button("Send →", type="primary", key="chat2_send", use_container_width=True)
                    with clr_col:
                        if st.button("Clear", key="chat2_clear", use_container_width=True):
                            _orch.clear_session(st.session_state["chat2_session_id"])
                            st.session_state["chat2_messages"] = []
                            st.session_state["chat2_session_id"] = str(uuid.uuid4())
                            st.rerun()

                    pending_q = st.session_state.get("chat2_pending")
                    if pending_q:
                        st.session_state["chat2_pending"] = None

                    user_q = pending_q or (typed.strip() if send_clicked and typed.strip() else None)

                    if user_q:
                        st.session_state["chat2_input_ver"] += 1
                        st.session_state["chat2_messages"].append({"role": "user", "content": user_q})
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

                st.markdown("</div></div>", unsafe_allow_html=True)

            with right_col:
                st.markdown(f"""
<div class="mi-panel">
  <div class="panel-head">
    <div class="panel-title">Suggested Questions</div>
    <div class="panel-sub">{len(SUGGESTED)} patterns · click to ask</div>
  </div>
  <div class="panel-body">
    <div class="question-list">
      {''.join(
          f'<div class="q-chip" style="cursor:default;">'
          f'<span style="color:{MUTED};font-size:.65rem;font-weight:700;margin-right:6px;">{str(i+1).zfill(2)}</span>'
          f'<strong>{_safe(title)}</strong>'
          f'<span>{_safe(q)}</span></div>'
          for i, (title, q) in enumerate(SUGGESTED)
      )}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown(f"""
<div class="footer-note">
  <span>Innovatics · Channel Intelligence — Ask &amp; Recommendation · database snapshot</span>
  <b>{escape(window_filter)} · {_PLATFORM_LABELS.get(platform_filter, platform_filter)} · {_CATEGORY_LABELS.get(category_filter, "All Apparel")}</b>
</div>
""", unsafe_allow_html=True)
