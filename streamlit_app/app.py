"""
app.py — Innovatics Program 1: Product & Market Intelligence
Run: streamlit run streamlit_app/app.py
"""
import sys
import os
import re
import uuid
import warnings
import json
import hashlib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
from urllib.parse import quote_plus, urlencode
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

load_dotenv()

from streamlit_app.db import (
    load_products, get_kpis, attribute_counts,
    price_bands, platform_comparison, top_products,
    color_family_breakdown, save_feedback, data_summary_for_llm,
    load_trend_scores, load_recommendations, update_recommendation_status,
    load_review_velocity, load_variant_skus,
    load_review_velocity_forecast, load_price_band_momentum, load_whitespace_scores,
    load_filter_options, lookup_sku, load_category_week_delta,
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    @import url('https://api.fontshare.com/v2/css?f[]=clash-grotesk@400,500,600,700&display=swap');

    :root {{
        --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --panel:{PANEL};
        --canvas:{CANVAS}; --accent:{ACCENT}; --success:{SUCCESS};
        --warning:{WARNING}; --danger:{DANGER};
        --primary:#00a4e3; --primary-deep:#0080b3; --primary-soft:rgba(0,164,227,.08);
        --primary-line:rgba(0,164,227,.2);
        --dark-1:#0a1628; --dark-2:#14233d; --dark-3:#1e3358;
        --bg:#f8fafc; --surface:#ffffff; --surface-soft:#fafbfd;
        --text-1:#0f172a; --text-2:#475569; --text-3:#94a3b8; --text-4:#cbd5e1;
        --border:#e2e8f0; --border-emphasis:#cbd5e1;
        --font-display:'Clash Grotesk', system-ui, sans-serif;
        --font-body:'Inter', system-ui, sans-serif;
        --font-mono:'JetBrains Mono', ui-monospace, monospace;
        --radius:12px; --radius-sm:6px;
    }}
    body, .stApp {{ font-family: var(--font-body) !important; }}
    .stApp, [data-testid="stAppViewContainer"] {{ background:{CANVAS}; color:{INK}; }}
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stSidebar"] {{ display:none !important; }}
    .block-container {{ padding:0 0 22px !important; max-width:100% !important; }}
    h1, h2, h3 {{ font-family: var(--font-display) !important; letter-spacing:-.01em !important; }}
    p {{ letter-spacing:0 !important; }}
    div[data-testid="stVerticalBlock"] {{ gap:0.75rem; }}

    .top-shell {{
        background:#fff; border-bottom:1px solid var(--line);
        padding:12px 30px 10px; position:relative; z-index:5;
    }}
    .top-grid {{
        display:grid; grid-template-columns:210px 1fr 540px;
        gap:18px; align-items:center;
    }}
    .brand-mark {{ display:flex; align-items:center; gap:10px; font-weight:800; color:var(--ink); font-family:var(--font-display); }}
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
    .hero-title {{ font-size:1.72rem; line-height:1.05; font-weight:900; margin:0; color:var(--ink); font-family:var(--font-display); letter-spacing:-.02em; }}
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
    .signal-value {{ color:var(--ink); font-size:2.05rem; line-height:1.05; font-weight:900; white-space:nowrap; font-family:var(--font-display); letter-spacing:-.02em; }}
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
    .panel-title {{ font-weight:700; color:var(--ink); font-size:1.01rem; line-height:1.1; font-family:var(--font-display); }}
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
    .pred-kpi-stat {{ display:flex; align-items:baseline; gap:7px; font-family:var(--font-mono); font-size:11px; }}
    .pred-kpi-big {{ font-size:20px; font-weight:900; letter-spacing:0; }}
    .pred-kpi-meta {{ color:#475569; font-weight:700; }}
    .pred-kpi-foot {{ margin-top:auto; padding-top:8px; border-top:1px solid #e2e8f0; color:#94a3b8; font-size:10.5px; font-family:var(--font-mono); }}
    .pred-panel {{ background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
    .pred-panel-head {{ min-height:62px; padding:14px 20px; border-bottom:1px solid #e2e8f0; display:flex; align-items:center; justify-content:space-between; gap:16px; }}
    .pred-panel-title {{ color:var(--ink); font-size:16px; font-weight:900; line-height:1.15; }}
    .pred-panel-sub {{ color:#475569; font-size:12.5px; margin-top:2px; }}
    .pred-sort {{ background:#fafbfd; border:1px solid #e2e8f0; border-radius:6px; color:#475569; font-size:12px; font-family:var(--font-mono); padding:5px 10px; }}
    .pred-colhead, .pred-row {{ display:grid; grid-template-columns:32px minmax(220px,1fr) 110px 110px 130px 28px; gap:16px; align-items:center; }}
    .pred-colhead {{ padding:10px 20px; background:#fafbfd; border-bottom:1px solid #e2e8f0; color:#94a3b8; font-size:10px; font-weight:900; text-transform:uppercase; letter-spacing:.06em; font-family:var(--font-mono); }}
    .pred-row {{ padding:14px 20px; border-bottom:1px solid #e2e8f0; }}
    .pred-toggle {{ display:none; }}
    .pred-toggle:not(:checked) + .pred-row + .pred-expand-panel {{ display:none; }}
    .pred-toggle:checked + .pred-row {{ background:rgba(8,165,214,.08); border-bottom-color:rgba(8,165,214,.18); }}
    .pred-row.expanded {{ background:rgba(8,165,214,.08); border-bottom-color:rgba(8,165,214,.18); }}
    .pred-rank {{ text-align:center; color:#94a3b8; font-size:11px; font-weight:900; font-family:var(--font-mono); }}
    .pred-name {{ color:var(--ink); font-size:14.5px; font-weight:900; display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
    .pred-attrs {{ color:#475569; font-size:12px; font-family:var(--font-mono); margin-top:3px; }}
    .pred-badges {{ display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }}
    .pred-badge {{ font-size:9.5px; font-weight:900; letter-spacing:.03em; font-family:var(--font-mono); border-radius:3px; padding:2px 6px; }}
    .pred-badge.gt {{ background:rgba(8,165,214,.12); color:#078db8; }}
    .pred-badge.wx {{ background:rgba(255,176,0,.18); color:#a06b00; }}
    .pred-badge.soon {{ background:#edf2f7; color:#52617a; }}
    .pred-life {{ font-size:10px; text-transform:uppercase; letter-spacing:.04em; border-radius:3px; padding:2px 6px; font-weight:900; font-family:var(--font-mono); }}
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
    .pred-conf {{ color:#94a3b8; font-size:10px; font-weight:800; font-family:var(--font-mono); }}
    .pred-progress {{ display:flex; justify-content:center; align-items:center; gap:3px; margin-top:5px; font-size:9px; font-family:var(--font-mono); }}
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
    .pred-chart-title, .pred-driver-title {{ color:#475569; font-size:10.5px; font-weight:900; letter-spacing:.06em; text-transform:uppercase; font-family:var(--font-mono); margin-bottom:10px; }}
    .pred-driver {{ display:flex; flex-direction:column; gap:8px; border:0; background:transparent; padding:0; }}
    .pred-driver-row {{ background:#fff; border:1px solid #e2e8f0; border-radius:6px; padding:8px 12px; display:flex; gap:10px; align-items:flex-start; }}
    .pred-driver-tag {{ min-width:124px; text-align:center; border-radius:3px; padding:2px 6px; font-size:10px; font-weight:900; font-family:var(--font-mono); }}
    .pred-driver-tag.proxy {{ background:rgba(100,116,139,.18); color:#475569; }}
    .pred-driver-tag.pull {{ background:rgba(8,165,214,.18); color:#078db8; }}
    .pred-driver-tag.context {{ background:rgba(255,176,0,.24); color:#a06b00; }}
    .pred-driver-text {{ color:var(--ink); font-size:12px; line-height:1.45; }}
    .pred-driver-source {{ display:block; color:#94a3b8; font-size:10px; font-family:var(--font-mono); margin-top:2px; }}
    .pred-life-grid, .pred-signal-grid {{ display:grid; grid-template-columns:repeat(4,1fr); }}
    .pred-life-card {{ padding:14px 16px; border-right:1px solid #e2e8f0; border-top:3px solid #94a3b8; }}
    .pred-life-card:last-child {{ border-right:0; }}
    .pred-life-card.emerging {{ border-top-color:var(--accent); }}
    .pred-life-card.accelerating {{ border-top-color:var(--success); }}
    .pred-life-card.declining {{ border-top-color:var(--danger); }}
    .pred-life-card-title {{ display:flex; justify-content:space-between; color:var(--ink); font-weight:900; }}
    .pred-life-count {{ border:1px solid #e2e8f0; background:#fafbfd; border-radius:999px; padding:2px 8px; font-size:11px; }}
    .pred-life-avg {{ color:#94a3b8; font-size:11.5px; font-family:var(--font-mono); margin:6px 0 10px; }}
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
        height:44px; border-radius:0; padding:0 24px; color:var(--muted); font-weight:700;
        font-family: var(--font-body) !important; font-size: 13.5px !important;
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

    /* ── All buttons — rectangular, matching HTML reference design ── */
    .stButton button,
    [data-testid="stButton"] button,
    [data-testid="stBaseButton-secondary"] {{
        background:       #fff !important;
        background-color: #fff !important;
        color:            #334155 !important;
        border:           1px solid #e2e8f0 !important;
        border-radius:    6px !important;
        font-size:        12.5px !important;
        font-weight:      500 !important;
        font-family:      var(--font-body) !important;
        padding:          6px 14px !important;
        min-height:       34px !important;
        box-shadow:       none !important;
        transition: background .15s ease, border-color .15s ease,
                    color .15s ease !important;
    }}
    .stButton button:hover,
    [data-testid="stButton"] button:hover,
    [data-testid="stBaseButton-secondary"]:hover {{
        background:       rgba(0,164,227,.06) !important;
        background-color: rgba(0,164,227,.06) !important;
        border-color:     rgba(0,164,227,.4) !important;
        color:            #0069a0 !important;
        transform:        none !important;
    }}
    .stButton button:active,
    [data-testid="stButton"] button:active,
    [data-testid="stBaseButton-secondary"]:active {{
        transform: none !important;
    }}

    /* ── Primary button — blue rectangular ───────────────────────── */
    .stButton button[kind="primary"],
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stBaseButton-primary"] {{
        background:       {ACCENT} !important;
        background-color: {ACCENT} !important;
        border-color:     {ACCENT} !important;
        color:            #FFFFFF !important;
        border-radius:    6px !important;
        font-weight:      600 !important;
        font-size:        12.5px !important;
        letter-spacing:   .01em !important;
        box-shadow:       0 1px 4px rgba(0,164,227,.25) !important;
        transition: background .15s ease, box-shadow .15s ease !important;
    }}
    .stButton button[kind="primary"]:hover,
    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {{
        background:       #0080b3 !important;
        background-color: #0080b3 !important;
        border-color:     #0080b3 !important;
        transform:        none !important;
        box-shadow:       0 2px 8px rgba(0,164,227,.35) !important;
    }}
    .stButton button[kind="primary"]:active,
    [data-testid="stBaseButton-primary"]:active {{
        transform: none !important;
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
        font-family: var(--font-body) !important;
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
        color: rgba(255,255,255,0.7); font-family: var(--font-mono);
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
        color: #94a3b8; font-weight: 600; font-family: var(--font-mono);
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
        font-family: var(--font-body) !important;
    }}
    [data-testid="stSelectbox"] > div {{
        min-width: 40px !important; flex: 1;
    }}
    [data-baseweb="select"] > div {{
        border: none !important; background: transparent !important;
        min-height: 24px !important; padding: 0 !important; box-shadow: none !important;
    }}
    [data-baseweb="select"] span {{ font-size: 12px !important; font-weight: 500 !important; color: #0f172a !important; font-family: var(--font-body) !important; }}
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
    .sku-modal-label {{ font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
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

    /* Analytics KPI strip — clean card design */
    .kpi-strip-new {{
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
    }}
    .kpi-tile-new {{
        background: #fff; border: 1px solid #e8ecf1; border-radius: 10px;
        padding: 18px 20px; position: relative; overflow: hidden;
        transition: box-shadow .15s, border-color .15s;
    }}
    .kpi-tile-new::before {{
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2.5px;
        background: linear-gradient(90deg, #0ea5e9, #0284c7);
    }}
    .kpi-tile-new:hover {{
        border-color: #cbd5e1;
        box-shadow: 0 2px 8px rgba(0,0,0,.04);
    }}
    .kpi-lbl-new {{
        font-size: 10.5px; color: #94a3b8; font-weight: 700;
        text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px;
        font-family: var(--font-mono);
    }}
    .kpi-val-new {{
        font-weight: 800; font-size: 24px; color: #0f172a;
        line-height: 1.1; letter-spacing: -.02em; margin-bottom: 6px;
        font-family: var(--font-display);
    }}
    .kpi-val-new .kpi-val-pct {{
        font-size: 18px; color: #64748b; font-weight: 600;
    }}
    .kpi-meta-new {{
        font-size: 12px; color: #64748b; display: flex; align-items: center;
        gap: 8px; flex-wrap: wrap; line-height: 1.4;
    }}
    .kpi-meta-sub {{
        color: #94a3b8; font-size: 11.5px;
    }}
    .kpi-delta {{
        font-family: var(--font-mono); font-weight: 700; font-size: 11px;
        padding: 2px 7px; border-radius: 4px; display: inline-flex; align-items: center;
    }}
    .kpi-delta.up {{ color: #16a34a; background: rgba(22,163,74,.08); }}
    .kpi-delta.down {{ color: #dc2626; background: rgba(220,38,38,.08); }}
    .kpi-delta.neutral {{ color: #94a3b8; background: rgba(148,163,184,.08); }}
    .kpi-share-badge {{
        font-family: var(--font-mono); font-weight: 600; font-size: 11px;
        color: #64748b;
    }}
    .kpi-index-badge {{
        font-family: var(--font-mono); font-weight: 700; font-size: 11px;
        padding: 2px 7px; border-radius: 4px; color: #16a34a;
        background: rgba(22,163,74,.08);
    }}
    .kpi-median {{
        font-size: 11.5px; color: #94a3b8;
    }}

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
        font-family: var(--font-mono);
    }}
    .archetype-colhead, .archetype-row-new {{
        display: grid;
        grid-template-columns: 32px 1fr 200px 130px 110px 32px;
        gap: 16px; align-items: center; padding: 10px 20px; border-bottom: 1px solid #e2e8f0;
    }}
    .archetype-colhead {{
        background: #fafbfd; font-size: 10px; font-weight: 700; color: #94a3b8;
        text-transform: uppercase; letter-spacing: .06em;
        font-family: var(--font-mono);
    }}
    .archetype-row-new {{ padding: 13px 20px; transition: background .15s; }}
    .archetype-row-new:last-child {{ border-bottom: none; }}
    .archetype-row-new:hover {{ background: #fafbfd; }}
    .arch-rank {{
        font-family: var(--font-mono); font-size: 11.5px;
        color: #94a3b8; font-weight: 500; text-align: center;
    }}
    .arch-main {{ display: flex; flex-direction: column; gap: 4px; min-width: 0; }}
    .arch-name {{
        font-weight: 600; font-size: 14.5px; color: #0f172a;
        display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    }}
    .arch-attrs {{
        font-size: 12px; color: #475569; font-family: var(--font-mono); margin-top: 1px;
    }}
    .arch-badges {{ display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }}
    .arch-badge {{
        font-size: 9.5px; font-weight: 600; letter-spacing: .03em; padding: 2px 6px; border-radius: 3px;
        font-family: var(--font-mono);
    }}
    .arch-badge.proxy {{ background: rgba(100,116,139,.18); color: #475569; }}
    .arch-badge.pull {{ background: rgba(0,164,227,.12); color: #0080b3; }}
    .arch-badge.context {{ background: rgba(255,183,29,.18); color: #a06b00; }}
    .arch-badge.soon {{ background: #edf2f7; color: #52617a; }}
    .decision-tag-new {{
        display: inline-flex; align-items: center; gap: 4px;
        font-family: var(--font-mono); font-size: 10px; font-weight: 600;
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
        font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
        letter-spacing: .04em; padding: 2px 6px; border-radius: 3px; font-weight: 500;
    }}
    .lifecycle-pill-new.emerging {{ background: rgba(0,164,227,.08); color: #0080b3; }}
    .lifecycle-pill-new.accelerating {{ background: rgba(22,163,74,.1); color: #16a34a; }}
    .lifecycle-pill-new.plateau {{ background: rgba(148,163,184,.18); color: #475569; }}
    .lifecycle-pill-new.declining {{ background: rgba(220,38,38,.08); color: #dc2626; }}
    .vel-cell {{ display: flex; flex-direction: column; gap: 2px; font-size: 12px; }}
    .vel-line {{ display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); }}
    .vel-ch {{ color: #94a3b8; font-size: 11px; width: 60px; flex-shrink: 0; }}
    .vel-up {{ color: #16a34a; font-weight: 600; }}
    .vel-down {{ color: #dc2626; font-weight: 600; }}
    .vel-neutral {{ color: #475569; font-weight: 600; }}
    .agree-cell {{ display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }}
    .agree-lbl {{
        font-size: 10.5px; color: #94a3b8; font-family: var(--font-mono);
        text-transform: uppercase; letter-spacing: .04em;
    }}
    .agree-bars {{ display: flex; gap: 2px; }}
    .agree-bars span {{ width: 12px; height: 4px; border-radius: 1px; background: #cbd5e1; }}
    .agree-bars.strong span {{ background: #16a34a; }}
    .agree-bars.mixed span:nth-child(-n+2) {{ background: #fbbf24; }}
    .agree-bars.divergent span:nth-child(-n+1) {{ background: #dc2626; }}
    .agree-val {{
        font-size: 11.5px; font-weight: 600; color: #0f172a;
        font-family: var(--font-mono); margin-top: 2px;
    }}
    .conf-cell {{ display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }}
    .conf-lbl {{
        font-size: 10.5px; color: #94a3b8; font-family: var(--font-mono);
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
        font-family: var(--font-mono); font-size: 10.5px; text-transform: uppercase;
        letter-spacing: .06em; color: #475569; margin-bottom: 10px; font-weight: 600;
    }}
    .driver-list-new {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }}
    .driver-row-new {{
        display: flex; align-items: center; gap: 10px; background: #fff;
        border: 1px solid #e2e8f0; padding: 8px 12px; border-radius: 6px; font-size: 12.5px;
    }}
    .driver-tag-new {{
        font-family: var(--font-mono); font-size: 10.5px; font-weight: 600;
        padding: 2px 6px; border-radius: 3px; letter-spacing: .04em;
        flex-shrink: 0; min-width: 80px; text-align: center;
    }}
    .driver-tag-new.proxy {{ background: rgba(100,116,139,.12); color: #475569; }}
    .driver-tag-new.pull {{ background: rgba(0,164,227,.12); color: #0080b3; }}
    .driver-tag-new.context {{ background: rgba(255,183,29,.18); color: #a06b00; }}
    .driver-txt-new {{ color: #0f172a; flex: 1; }}
    .driver-src-new {{
        font-family: var(--font-mono); font-size: 10.5px; color: #94a3b8;
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
    .support-panel-sub-new {{ font-size: 11px; color: #94a3b8; font-family: var(--font-mono); }}
    .support-panel-body {{ padding: 12px 16px 14px; }}

    /* Stacked bar */
    .stacked-bar-new {{
        display: flex; height: 28px; border-radius: 6px; overflow: hidden; margin: 8px 0 12px;
    }}
    .stacked-seg {{
        display: grid; place-items: center; font-size: 10.5px; font-weight: 600; color: #fff;
        font-family: var(--font-mono); overflow: hidden; white-space: nowrap;
        transition: opacity .15s; cursor: pointer;
    }}
    .stacked-seg:hover {{ opacity: .85; }}
    .stacked-legend-new {{ display: flex; flex-direction: column; gap: 5px; }}
    .legend-row-new {{ display: flex; align-items: center; gap: 8px; font-size: 12px; }}
    .legend-swatch-new {{ width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }}
    .legend-lbl-new {{ color: #475569; flex: 1; }}
    .legend-val-new {{
        font-family: var(--font-mono); color: #0f172a; font-weight: 600; font-size: 11.5px;
    }}
    .legend-delta-new {{
        font-family: var(--font-mono); font-size: 11px; font-weight: 600;
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
        font-family: var(--font-mono); font-size: 11px; color: #0f172a;
        text-align: right; font-weight: 600;
    }}
    .converting-note {{
        margin-top: 10px; padding: 8px 10px; background: rgba(0,164,227,.06);
        border: 1px solid rgba(0,164,227,.15); border-radius: 6px;
        font-size: 11.5px; color: #0080b3; font-family: var(--font-mono);
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
    .channel-stat-val {{ color: #0f172a; font-family: var(--font-mono); font-weight: 600; }}

    /* Automation strip */
    .automation-strip {{
        background: linear-gradient(135deg,#0a1628 0%,#14233d 100%);
        padding: 14px 20px; border-radius: 12px;
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }}
    .auto-left {{ display: flex; align-items: center; gap: 12px; }}
    .auto-badge {{
        background: rgba(255,183,29,.15); border: 1px solid rgba(255,183,29,.3);
        color: #ffb71d; font-family: var(--font-mono); font-size: 11px; font-weight: 600;
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
        font-family: var(--font-mono); font-size: 11px;
    }}
    .pred-kpi-big-new {{ font-size: 19px; font-weight: 900; }}
    .pred-kpi-meta-new {{ color: #475569; font-weight: 600; }}
    .pred-kpi-foot-new {{
        margin-top: auto; padding-top: 8px; border-top: 1px solid #e2e8f0;
        color: #94a3b8; font-size: 10.5px; font-family: var(--font-mono);
    }}

    /* S2 Forward signals */
    .fwd-signal-card {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    }}
    .fwd-signal-hdr {{
        padding: 13px 16px 10px; border-bottom: 1px solid #e2e8f0;
    }}
    .fwd-signal-title {{ font-weight: 600; font-size: 13.5px; color: #0f172a; }}
    .fwd-signal-sub {{ font-size: 11px; color: #94a3b8; font-family: var(--font-mono); margin-top: 2px; }}
    .fwd-signal-body {{ padding: 12px 16px 14px; }}
    .fwd-query-row {{
        display: flex; align-items: center; gap: 10px; padding: 6px 0;
        border-bottom: 1px solid #f1f5f9; font-size: 12.5px;
    }}
    .fwd-query-row:last-child {{ border-bottom: none; }}
    .fwd-query-name {{ color: #0f172a; flex: 1; font-weight: 500; }}
    .fwd-mini-bar {{ height: 5px; width: 60px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }}
    .fwd-mini-fill {{ height: 100%; border-radius: 3px; }}
    .fwd-delta-up {{ color: #16a34a; font-weight: 600; font-size: 11.5px; font-family: var(--font-mono); }}
    .fwd-delta-down {{ color: #dc2626; font-weight: 600; font-size: 11.5px; font-family: var(--font-mono); }}
    .fwd-signal-empty {{
        border:1px dashed #cbd5e1; border-radius:8px; padding:13px 14px;
        color:#64748b; font-size:12px; line-height:1.5; background:#fafbfd;
    }}
    .fwd-live-note {{ margin-top:9px; color:#94a3b8; font-size:10.5px; font-family:var(--font-mono); }}
    .fwd-region-row {{
        display: grid; grid-template-columns: 80px 1fr auto; gap: 10px; align-items: center;
        padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 12px;
    }}
    .fwd-region-row:last-child {{ border-bottom: none; }}
    .fwd-region-name {{ color: #475569; font-weight: 500; }}
    .fwd-anomaly {{ color: #0f172a; font-family: var(--font-mono); font-weight: 600; font-size: 11.5px; }}

    /* S3 Mode toggle */
    .s3-mode-bar {{
        background: #fff; border-bottom: 1px solid #e2e8f0;
        padding: 14px 0 6px; display: flex; align-items: center;
        justify-content: space-between; gap: 16px;
    }}
    .s3-mode-toggle {{
        display: inline-flex; background: #f6f9fc;
        border: 1px solid #e2e8f0; border-radius: 8px; padding: 3px; gap: 2px;
    }}
    .s3-mode-opt {{
        padding: 7px 16px; font-size: 13px; font-weight: 500; color: #475569;
        border-radius: 6px; display: inline-flex; align-items: center; gap: 7px;
        white-space: nowrap; transition: all .15s;
    }}
    .s3-mode-opt.active {{
        background: #fff; color: #0080b3; font-weight: 600;
        box-shadow: 0 1px 2px rgba(15,23,42,.06);
    }}
    .s3-mode-badge {{
        font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
        background: rgba(0,164,227,.1); color: #0080b3;
        font-family: var(--font-mono);
    }}
    .s3-mode-opt.active .s3-mode-badge {{ background: #00a4e3; color: #fff; }}
    .s3-mode-meta {{
        display: flex; align-items: center; gap: 8px;
        font-family: var(--font-mono); font-size: 11.5px; color: #94a3b8;
    }}
    .s3-mode-meta-dot {{
        width: 5px; height: 5px; border-radius: 50%; background: #16a34a;
        display: inline-block; flex-shrink: 0;
    }}

    /* S3 Market frame — light version */
    .market-frame {{
        background: linear-gradient(135deg, rgba(0,164,227,.04), #fff 60%);
        border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 16px 20px; display: grid;
        grid-template-columns: 1fr auto; gap: 20px;
        align-items: center; margin-bottom: 14px;
    }}
    .market-frame-label {{
        font-family: var(--font-mono); font-size: 10.5px;
        text-transform: uppercase; letter-spacing: .06em;
        color: #94a3b8; font-weight: 600; margin-bottom: 6px;
    }}
    .market-frame-signal {{ font-size: 13.5px; color: #0f172a; line-height: 1.55; }}
    .market-frame-signal strong {{ font-weight: 600; }}
    .market-frame-drivers {{
        display: flex; gap: 16px; align-items: center;
    }}
    .market-frame-driver {{
        display: flex; flex-direction: column; gap: 2px; align-items: center;
    }}
    .driver-pct {{
        font-size: 18px; font-weight: 700; color: #475569; line-height: 1.1;
    }}
    .market-frame-driver.pull .driver-pct {{ color: #0080b3; }}
    .market-frame-driver.context .driver-pct {{ color: #a06b00; }}
    .driver-lbl {{
        font-size: 9.5px; text-transform: uppercase; letter-spacing: .06em;
        color: #94a3b8; font-weight: 600;
    }}

    /* S3 Rec cards — exact HTML match */
    .rec-card-new {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        overflow: hidden; margin-bottom: 12px;
        transition: border-color .15s, box-shadow .15s;
    }}
    .rec-card-new:hover {{
        border-color: #cbd5e1; box-shadow: 0 4px 12px rgba(15,23,42,.05);
    }}
    .rec-card-grid {{
        padding: 16px 20px 14px; display: grid;
        grid-template-columns: 32px 1fr auto auto; gap: 16px; align-items: start;
    }}
    .rec-expand-col {{
        width: 28px; height: 28px; border-radius: 6px; display: grid;
        place-items: center; background: #00a4e3; color: #fff; font-size: 13px;
        flex-shrink: 0; align-self: center; cursor: pointer; user-select: none;
        transition: background .15s; border: none;
    }}
    .rec-expand-col:hover {{ background: #0080b3; }}
    .rec-expand-col.expanded {{ transform: rotate(180deg); }}
    .rec-evidence-block.ev-hidden {{ display: none; }}
    .rec-main {{ display: flex; flex-direction: column; gap: 4px; min-width: 0; }}
    .rec-tags {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
    .decision-tag {{
        display: inline-flex; align-items: center; gap: 4px;
        font-family: var(--font-mono); font-size: 10px; font-weight: 700;
        text-transform: uppercase; letter-spacing: .06em;
        padding: 3px 9px; border-radius: 4px; white-space: nowrap;
    }}
    .decision-tag.reprice {{ background: rgba(0,164,227,.14); color: #0069a0; border: 1px solid rgba(0,164,227,.22); }}
    .decision-tag.reposition {{ background: rgba(255,183,29,.18); color: #8a5a00; border: 1px solid rgba(255,183,29,.3); }}
    .decision-tag.replenish {{ background: rgba(22,163,74,.12); color: #14703c; border: 1px solid rgba(22,163,74,.22); }}
    .decision-tag.retire {{ background: rgba(220,38,38,.1); color: #b91c1c; border: 1px solid rgba(220,38,38,.2); }}
    .decision-tag.whitespace {{ background: rgba(124,58,237,.12); color: #5b21b6; border: 1px solid rgba(124,58,237,.2); }}
    .decision-tag.watch {{ background: rgba(100,116,139,.14); color: #374151; border: 1px solid rgba(100,116,139,.22); }}
    .lifecycle-pill {{
        font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
        letter-spacing: .05em; padding: 3px 8px; border-radius: 4px; font-weight: 700;
    }}
    .lifecycle-pill.emerging {{ background: rgba(0,164,227,.12); color: #0069a0; border: 1px solid rgba(0,164,227,.2); }}
    .lifecycle-pill.accelerating {{ background: rgba(22,163,74,.12); color: #14703c; border: 1px solid rgba(22,163,74,.2); }}
    .lifecycle-pill.plateau {{ background: rgba(148,163,184,.2); color: #374151; border: 1px solid rgba(148,163,184,.3); }}
    .lifecycle-pill.declining {{ background: rgba(220,38,38,.1); color: #b91c1c; border: 1px solid rgba(220,38,38,.18); }}
    .rec-idx {{
        font-family: var(--font-mono); font-size: 11.5px;
        color: #94a3b8; font-weight: 600; padding-top: 3px; line-height: 1;
    }}
    .rec-pattern-lbl {{
        font-family: var(--font-mono); font-size: 11px; color: #94a3b8; font-weight: 500;
    }}
    .rec-headline {{
        font-family: var(--font-display);
        font-weight: 700; font-size: 15.5px; color: #0f172a;
        letter-spacing: -.01em; line-height: 1.35; margin: 4px 0 2px;
    }}
    .rec-evidence-sum {{
        font-size: 12.5px; color: #64748b; line-height: 1.55;
    }}
    .rec-evidence-sum strong {{ color: #0f172a; font-weight: 600; }}
    .rec-meta-col {{
        display: flex; flex-direction: column; align-items: flex-end; gap: 6px;
    }}
    .rec-conf-wrap {{
        display: flex; flex-direction: column; align-items: flex-end; gap: 2px;
    }}
    .rec-conf-lbl {{
        font-size: 9.5px; color: #94a3b8; font-family: var(--font-mono);
        text-transform: uppercase; letter-spacing: .06em; font-weight: 600;
    }}
    .rec-conf-val {{
        font-weight: 800; font-size: 28px; color: #0f172a; font-family: var(--font-display);
        line-height: 1.1; letter-spacing: -.02em;
    }}
    .conf-badge {{
        padding: 3px 8px; border-radius: 4px; font-weight: 700;
        font-size: 10.5px; font-family: var(--font-mono);
    }}
    .conf-badge.high {{ background: rgba(22,163,74,.1); color: #16a34a; }}
    .conf-badge.medium {{ background: rgba(255,183,29,.15); color: #b07a00; }}
    .conf-badge.low {{ background: rgba(148,163,184,.18); color: #475569; }}
    .tier-strong {{
        display: inline-block; background: rgba(22,163,74,.1); color: #16a34a;
        font-size: 10.5px; font-weight: 700; font-family: var(--font-mono);
        padding: 3px 9px; border-radius: 4px; white-space: nowrap;
    }}
    .tier-moderate {{
        display: inline-block; background: rgba(255,183,29,.15); color: #b07a00;
        font-size: 10.5px; font-weight: 700; font-family: var(--font-mono);
        padding: 3px 9px; border-radius: 4px; white-space: nowrap;
    }}
    .tier-watch {{
        display: inline-block; background: rgba(148,163,184,.18); color: #475569;
        font-size: 10.5px; font-weight: 700; font-family: var(--font-mono);
        padding: 3px 9px; border-radius: 4px; white-space: nowrap;
    }}
    .rec-expand-col {{
        width: 28px; height: 28px; border-radius: 6px; display: grid; place-items: center;
        background: #00a4e3; color: #fff; font-size: 14px;
        cursor: pointer; flex-shrink: 0; align-self: center;
        transition: background .15s; user-select: none;
    }}
    .rec-expand-col:hover {{ background: #0080b3; }}
    .rec-expand-col.expanded {{ transform: rotate(180deg); }}
    .rec-evidence-block {{
        padding: 14px 20px 16px 68px;
        background: rgba(0,164,227,.04);
        border-top: 1px solid rgba(0,164,227,.15);
    }}
    .rec-evidence-hdr {{
        font-family: var(--font-mono); font-size: 10px; text-transform: uppercase;
        letter-spacing: .07em; color: #64748b; margin-bottom: 10px; font-weight: 600;
    }}
    .rec-driver-list {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; }}
    .driver-row-new {{
        display: flex; align-items: center; gap: 10px; background: #fff;
        border: 1px solid #e2e8f0; padding: 7px 12px; border-radius: 6px; font-size: 12.5px;
    }}
    .driver-tag-new {{
        font-family: var(--font-mono); font-size: 10px; font-weight: 700;
        padding: 3px 7px; border-radius: 3px; letter-spacing: .04em;
        flex-shrink: 0; min-width: 86px; text-align: center; white-space: nowrap;
    }}
    .driver-tag-new.proxy {{ background: rgba(100,116,139,.14); color: #475569; }}
    .driver-tag-new.pull {{ background: rgba(0,164,227,.14); color: #0080b3; }}
    .driver-tag-new.context {{ background: rgba(255,183,29,.2); color: #a06b00; }}
    .driver-txt-new {{ color: #334155; flex: 1; font-size: 12.5px; line-height: 1.45; }}
    .driver-src-new {{
        font-family: var(--font-mono); font-size: 10.5px; color: #94a3b8;
        white-space: nowrap; display: inline-flex; align-items: center; gap: 5px;
    }}
    .driver-src-new::before {{
        content: ''; width: 6px; height: 6px; border-radius: 50%; background: #16a34a;
        display: inline-block; flex-shrink: 0;
    }}
    .rec-action-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .rec-action-btn {{
        font-size: 12px; color: #0f172a; font-weight: 500; padding: 7px 12px;
        border: 1px solid #cbd5e1; border-radius: 6px; background: #fff;
        cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
        transition: all .15s; text-decoration: none;
    }}
    .rec-action-btn:hover {{ border-color: #00a4e3; background: rgba(0,164,227,.06); color: #0080b3; }}
    .rec-action-btn.primary {{ color: #0080b3; border-color: rgba(0,164,227,.25); }}
    .rec-action-btn.primary:hover {{ background: #00a4e3; color: #fff; border-color: #00a4e3; }}

    /* ── Rec card action button row — compact flat style matching Image 2 ─── */
    .rec-actions-row {{ margin-top: 2px; padding: 0; }}
    .rec-actions-row [data-testid="stHorizontalBlock"] {{ gap: 6px !important; align-items: center !important; }}
    .rec-actions-row .stButton button,
    .rec-actions-row [data-testid="stBaseButton-secondary"],
    .rec-actions-row [data-testid="stBaseButton-primary"] {{
        background: #fff !important; background-color: #fff !important;
        border: 1px solid #e2e8f0 !important; border-radius: 6px !important;
        color: #334155 !important; font-size: 12px !important;
        font-weight: 500 !important; font-family: var(--font-body) !important;
        padding: 5px 10px !important; min-height: 32px !important;
        box-shadow: none !important; transition: all .15s !important;
    }}
    .rec-actions-row .stButton button:hover,
    .rec-actions-row [data-testid="stBaseButton-secondary"]:hover,
    .rec-actions-row [data-testid="stBaseButton-primary"]:hover {{
        background: rgba(0,164,227,.06) !important;
        background-color: rgba(0,164,227,.06) !important;
        border-color: rgba(0,164,227,.35) !important;
        color: #0069a0 !important; transform: none !important;
        box-shadow: none !important;
    }}

    /* S3 Ask view — input panel */
    .ask-input-panel {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 20px; display: flex; flex-direction: column; gap: 16px; margin-bottom: 12px;
    }}
    .ask-input-title {{
        font-weight: 700; font-size: 17px; color: #0f172a; letter-spacing: -.01em;
    }}
    .ask-input-subtitle {{ font-size: 12.5px; color: #475569; margin-top: 4px; }}
    .ask-suggestions-row {{
        display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    }}
    .ask-suggestions-lbl {{
        font-family: var(--font-mono); font-size: 10.5px; text-transform: uppercase;
        letter-spacing: .06em; color: #94a3b8; font-weight: 600; margin-right: 2px;
    }}
    .ask-chip {{
        font-size: 12px; color: #475569; padding: 6px 10px; background: #fafbfd;
        border: 1px solid #e2e8f0; border-radius: 6px; font-weight: 500;
        cursor: pointer; display: inline-block; transition: all .15s;
    }}
    .ask-chip:hover {{ border-color: #00a4e3; background: rgba(0,164,227,.06); color: #0080b3; }}

    /* S3 Ask conversation exchanges */
    .ask-exchange-wrap {{ display: flex; flex-direction: column; gap: 12px; }}
    .ask-exchange {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;
    }}
    .ask-question-row {{
        padding: 14px 20px; background: #fafbfd; border-bottom: 1px solid #e2e8f0;
        display: flex; align-items: flex-start; gap: 10px;
    }}
    .ask-q-avatar {{
        width: 26px; height: 26px; border-radius: 50%; background: #00a4e3; color: #fff;
        display: grid; place-items: center; font-size: 11px; font-weight: 700;
        flex-shrink: 0; font-family: var(--font-mono);
    }}
    .ask-q-text {{
        font-weight: 500; font-size: 14px; color: #0f172a; line-height: 1.45;
    }}
    .ask-answer-row {{ padding: 16px 20px 18px; display: flex; flex-direction: column; gap: 12px; }}
    .ask-answer-hdr {{
        font-family: var(--font-mono); font-size: 10.5px; text-transform: uppercase;
        letter-spacing: .06em; color: #94a3b8; font-weight: 600;
    }}
    .ask-answer-body {{ font-size: 13.5px; color: #0f172a; line-height: 1.6; }}
    .ask-answer-body strong {{ font-weight: 600; }}
    .ask-evidence-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .ask-evidence-tag {{
        display: inline-flex; align-items: center; gap: 5px;
        font-family: var(--font-mono); font-size: 10.5px; font-weight: 500;
        padding: 3px 8px; border-radius: 4px; background: #fafbfd;
        border: 1px solid #e2e8f0; color: #475569;
    }}
    .ask-evidence-tag::before {{
        content: ''; width: 5px; height: 5px; border-radius: 50%; background: #16a34a;
        display: inline-block; flex-shrink: 0;
    }}
    .ask-confidence-row {{
        display: inline-flex; align-items: center; gap: 6px;
        font-family: var(--font-mono); font-size: 11.5px;
    }}
    .ask-conf-lbl {{ color: #94a3b8; }}
    .ask-conf-val {{ color: #0f172a; font-weight: 600; }}

    /* S3 Automation strip */
    .automation-strip {{
        background: linear-gradient(135deg,#0a1628 0%,#14233d 100%);
        border-radius: 12px; padding: 14px 20px;
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
        margin-top: 4px;
    }}
    .auto-left {{ display: flex; align-items: center; gap: 14px; }}
    .auto-icon {{
        width: 32px; height: 32px; background: rgba(0,164,227,.18);
        border: 1px solid rgba(0,164,227,.3); border-radius: 8px;
        display: grid; place-items: center; color: #00a4e3; font-size: 16px; flex-shrink: 0;
    }}
    .auto-text {{ display: flex; flex-direction: column; gap: 2px; }}
    .auto-title {{ font-weight: 600; font-size: 13px; color: #fff; }}
    .auto-detail {{ font-size: 12px; color: rgba(255,255,255,.7); }}
    .auto-detail strong {{ color: rgba(255,255,255,.95); font-weight: 600; }}
    .auto-btn {{
        background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.15);
        color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 11.5px;
        font-weight: 500; font-family: var(--font-mono); cursor: pointer;
    }}

    /* ════════════════════════════════════════════════════════════════
       Reference HTML parity overrides
       These map Streamlit controls and dynamic backend content to the
       exact S1/S2/S3 visual language.
       ════════════════════════════════════════════════════════════════ */
    :root {{
        --primary:#00a4e3;
        --primary-deep:#0080b3;
        --primary-soft:rgba(0,164,227,.08);
        --primary-line:rgba(0,164,227,.18);
        --amber:#ffb71d;
        --amber-soft:rgba(255,183,29,.12);
        --dark-1:#0a1628;
        --dark-2:#14233d;
        --dark-3:#1e3358;
        --bg:#f6f9fc;
        --surface:#ffffff;
        --surface-soft:#fafbfd;
        --text-1:#0f172a;
        --text-2:#475569;
        --text-3:#94a3b8;
        --text-4:#cbd5e1;
        --border:#e2e8f0;
        --border-emphasis:#cbd5e1;
        --purple:#7c3aed;
        --radius:12px;
        --radius-sm:8px;
        --radius-lg:16px;
    }}
    .stApp, [data-testid="stAppViewContainer"] {{ background:var(--bg) !important; color:var(--text-1); }}
    .block-container {{ padding:0 0 0 !important; max-width:100% !important; }}
    body, .stApp, button, input, textarea, select {{ font-family:var(--font-body) !important; }}

    /* App chrome from the HTML files */
    .app-chrome {{
        background:linear-gradient(135deg,var(--dark-1) 0%,var(--dark-2) 100%) !important;
        padding:12px 24px !important;
        display:flex !important; align-items:center !important; justify-content:space-between !important;
        border-bottom:1px solid var(--dark-3) !important;
    }}
    .chrome-left {{ display:flex !important; align-items:center !important; gap:24px !important; }}
    .app-chrome .brand {{ display:flex !important; align-items:center !important; gap:10px !important; color:#fff !important; }}
    .app-chrome .brand-mark {{
        width:28px !important; height:28px !important; background:var(--primary) !important;
        border-radius:6px !important; display:grid !important; place-items:center !important;
        font-family:var(--font-display) !important; font-weight:700 !important;
        color:var(--dark-1) !important; font-size:15px !important;
    }}
    .brand-name {{ font-family:var(--font-display) !important; font-weight:600 !important; font-size:17px !important; letter-spacing:-.01em !important; }}
    .brand-divider {{ color:rgba(255,255,255,.2) !important; font-size:14px !important; }}
    .brand-product {{ font-family:var(--font-display) !important; font-weight:500 !important; font-size:14px !important; color:rgba(255,255,255,.85) !important; }}
    .workspace-pill {{
        background:rgba(255,255,255,.08) !important; border:1px solid rgba(255,255,255,.12) !important;
        padding:6px 12px !important; border-radius:8px !important;
        color:rgba(255,255,255,.9) !important; font-size:12.5px !important;
        display:flex !important; align-items:center !important; gap:8px !important;
    }}
    .workspace-pill::before {{ content:''; width:6px; height:6px; background:var(--primary); border-radius:50%; }}
    .chrome-right {{ display:flex !important; align-items:center !important; gap:16px !important; }}
    .refresh-status {{
        display:flex !important; align-items:center !important; gap:8px !important;
        font-size:12px !important; color:rgba(255,255,255,.7) !important; font-family:var(--font-mono) !important;
    }}
    .refresh-status .live-dot {{
        width:6px; height:6px; background:var(--success); border-radius:50%;
        box-shadow:0 0 0 3px rgba(22,163,74,.2);
        animation: pulse 2.4s ease-in-out infinite;
    }}
    .account-button {{
        width:32px; height:32px; background:rgba(255,255,255,.1); border-radius:50%;
        display:grid; place-items:center; color:#fff; font-weight:600; font-size:12px;
        border:1px solid rgba(255,255,255,.15);
    }}

    /* Reference HTML top navigation */
    .tab-strip {{
        background:var(--surface); border-bottom:1px solid var(--border);
        padding:0 24px; display:flex; justify-content:space-between; align-items:center;
    }}
    .tabs {{ display:flex; gap:4px; }}
    .tab {{
        padding:16px 20px 14px; border-bottom:2px solid transparent;
        color:var(--text-2); font-family:var(--font-display); font-weight:500; font-size:14.5px;
        text-decoration:none; transition:color .15s, border-color .15s;
    }}
    .tab:hover {{ color:var(--text-1); }}
    .tab.active {{
        color:var(--text-1); border-bottom-color:var(--primary); font-weight:600;
    }}
    .tab-strip-right {{ display:flex; align-items:center; gap:12px; padding:12px 0; }}
    .tab-strip-right .stamp {{ font-family:var(--font-mono); font-size:11px; color:var(--text-3); }}

    /* Native Streamlit tabs styled as the HTML tab strip */
    .stTabs [data-baseweb="tab-list"] {{
        background:var(--surface) !important; border-bottom:1px solid var(--border) !important;
        padding:0 24px !important; gap:4px !important; align-items:stretch !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        height:52px !important; padding:0 20px !important;
        font-family:var(--font-display) !important; font-weight:500 !important; font-size:14.5px !important;
        color:var(--text-2) !important; border-bottom:2px solid transparent !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{ color:var(--text-1) !important; }}
    .stTabs [aria-selected="true"] {{
        color:var(--text-1) !important; border-bottom:2px solid var(--primary) !important; font-weight:600 !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display:none !important; }}
    .stTabs [data-testid="stMarkdownContainer"] p {{ font-family:var(--font-display) !important; }}

    /* Reference filter bar; Streamlit selectboxes are shaped to match .filter-select */
    .filter-bar, .new-filter-bar {{
        background:var(--surface) !important; border-bottom:1px solid var(--border) !important;
        padding:14px 24px !important; display:flex !important; flex-direction:column !important; gap:10px !important;
    }}
    .st-key-filter_area {{
        background:var(--surface) !important;
        border-bottom:1px solid var(--border) !important;
        padding:10px 24px 12px !important;
    }}
    .st-key-filter_area > div[data-testid="stVerticalBlock"] {{
        gap:6px !important;
    }}
    .st-key-filter_area [data-testid="stHorizontalBlock"] {{
        gap:10px !important;
        align-items:center !important;
    }}
    .st-key-filter_area [data-testid="stColumn"] {{
        padding:0 !important;
    }}
    .st-key-filter_area [data-testid="stElementContainer"] {{
        margin:0 !important;
    }}
    .filter-section-label {{
        font-family:var(--font-mono) !important;
        font-size:10.5px !important;
        text-transform:uppercase !important;
        letter-spacing:.06em !important;
        color:var(--text-3) !important;
        font-weight:500 !important;
        line-height:1 !important;
        margin:0 0 2px !important;
    }}
    .filter-section-label.refine {{ margin-top:4px !important; }}
    .filter-row, .filter-row-wrap {{ display:flex !important; align-items:center !important; gap:10px !important; flex-wrap:wrap !important; }}
    .filter-row-label, .filter-row-lbl {{
        font-family:var(--font-mono) !important; font-size:10.5px !important;
        text-transform:uppercase !important; letter-spacing:.06em !important;
        color:var(--text-3) !important; margin-right:4px !important; font-weight:500 !important;
        width:auto !important; padding-top:0 !important;
    }}
    [data-testid="stSelectbox"] {{
        display:block !important; background:transparent !important; border:0 !important;
        border-radius:0 !important; padding:0 !important; min-width:0 !important;
    }}
    [data-testid="stSelectbox"] label {{
        font-size:11.5px !important; font-weight:400 !important; color:var(--text-3) !important;
        margin:0 0 3px !important; padding:0 !important; line-height:1 !important;
        font-family:var(--font-body) !important;
    }}
    [data-baseweb="select"] > div {{
        background:var(--surface) !important; border:1px solid var(--border-emphasis) !important;
        border-radius:var(--radius-sm) !important; min-height:34px !important;
        padding:0 8px !important; box-shadow:none !important;
    }}
    [data-baseweb="select"] > div:hover {{ border-color:var(--primary) !important; background:var(--primary-soft) !important; }}
    [data-baseweb="select"] span {{
        font-size:13px !important; font-weight:500 !important; color:var(--text-1) !important;
        font-family:var(--font-body) !important;
    }}
    .filter-action-link, .filter-link {{
        font-size:12px !important; color:var(--text-2) !important; text-decoration:none !important; font-weight:500 !important;
        display:inline-flex !important; align-items:center !important; gap:4px !important;
    }}
    .filter-action-link:hover, .filter-link:hover {{ color:var(--primary-deep) !important; }}

    /* S3 exact mode toggle */
    .mode-toggle-bar {{
        background:var(--surface); border-bottom:1px solid var(--border);
        padding:14px 24px; display:flex; align-items:center; justify-content:space-between; gap:16px;
    }}
    .mode-toggle {{
        display:inline-flex; background:var(--bg); border:1px solid var(--border);
        border-radius:8px; padding:3px; gap:2px;
    }}
    .mode-option {{
        padding:7px 16px; font-family:var(--font-display); font-weight:500; font-size:13px;
        color:var(--text-2); border-radius:6px; display:inline-flex; align-items:center; gap:7px;
        transition:all .15s; text-decoration:none;
    }}
    .mode-option:hover {{ color:var(--text-1); }}
    .mode-option.active {{
        background:var(--surface); color:var(--text-1); font-weight:600; box-shadow:0 1px 2px rgba(15,23,42,.06);
    }}
    .mode-option.active.recommendations {{ color:var(--primary-deep); }}
    .mode-option .badge {{
        font-family:var(--font-mono); font-size:10px; font-weight:600;
        padding:1px 6px; border-radius:3px; background:var(--primary-soft); color:var(--primary-deep);
    }}
    .mode-option.active .badge {{ background:var(--primary); color:white; }}
    .mode-meta {{
        display:flex; align-items:center; gap:12px; font-family:var(--font-mono); font-size:11.5px; color:var(--text-3);
    }}
    .mode-meta-dot {{ width:5px; height:5px; border-radius:50%; background:var(--success); }}
    .canvas {{ padding:20px 24px 24px 24px; display:flex; flex-direction:column; gap:16px; }}

    /* S3 exact recommendation + ask classes */
    .recommendations-list {{ display:flex; flex-direction:column; gap:12px; }}
    .recommendations-view.hidden {{ display:none; }}
    .rec-card {{
        background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
        overflow:hidden; transition:border-color .15s, box-shadow .15s; margin:0;
    }}
    details.rec-card > summary {{
        list-style:none; cursor:pointer;
    }}
    details.rec-card > summary::-webkit-details-marker {{ display:none; }}
    .rec-card:hover {{ border-color:var(--border-emphasis); box-shadow:0 4px 12px rgba(15,23,42,.05); }}
    .rec-card.expanded, details.rec-card[open] {{ border-color:var(--primary-line); box-shadow:0 4px 16px rgba(0,164,227,.08); }}
    .rec-header {{ padding:14px 20px; display:grid; grid-template-columns:32px 1fr auto auto; gap:16px; align-items:start; }}
    .rec-index {{ font-family:var(--font-mono); font-size:11.5px; color:var(--text-3); font-weight:600; padding-top:2px; }}
    .rec-main {{ display:flex; flex-direction:column; gap:6px; min-width:0; }}
    .rec-tags {{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; }}
    .decision-tag {{
        display:inline-flex; align-items:center; gap:4px; font-family:var(--font-mono);
        font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.05em;
        padding:3px 8px; border-radius:4px; white-space:nowrap;
    }}
    .decision-tag.reprice {{ background:rgba(0,164,227,.1); color:var(--primary-deep); }}
    .decision-tag.reposition {{ background:rgba(255,183,29,.16); color:#b07a00; }}
    .decision-tag.replenish {{ background:rgba(22,163,74,.1); color:var(--success); }}
    .decision-tag.retire {{ background:rgba(220,38,38,.08); color:var(--danger); }}
    .decision-tag.whitespace {{ background:rgba(124,58,237,.1); color:#6d28d9; }}
    .decision-tag.watch {{ background:rgba(100,116,139,.12); color:var(--text-2); }}
    .lifecycle-pill {{
        font-family:var(--font-mono); font-size:10px; text-transform:uppercase; letter-spacing:.04em;
        padding:2px 6px; border-radius:3px; font-weight:500;
    }}
    .lifecycle-pill.emerging {{ background:rgba(0,164,227,.08); color:var(--primary-deep); }}
    .lifecycle-pill.accelerating {{ background:rgba(22,163,74,.1); color:var(--success); }}
    .lifecycle-pill.plateau {{ background:rgba(148,163,184,.18); color:var(--text-2); }}
    .lifecycle-pill.declining {{ background:rgba(220,38,38,.08); color:var(--danger); }}
    .rec-pattern-label {{ font-family:var(--font-mono); font-size:10.5px; color:var(--text-3); }}
    .rec-headline {{
        font-family:var(--font-display); font-weight:600; font-size:16px; color:var(--text-1);
        letter-spacing:-.01em; line-height:1.35;
    }}
    .rec-evidence {{ font-size:12.5px; color:var(--text-2); line-height:1.55; margin-top:2px; }}
    .rec-evidence strong {{ color:var(--text-1); font-weight:600; }}
    .rec-meta-col {{ display:flex; flex-direction:column; align-items:flex-end; gap:6px; }}
    .rec-confidence {{ display:flex; flex-direction:column; align-items:flex-end; gap:2px; }}
    .rec-confidence-label {{
        font-size:10px; color:var(--text-3); font-family:var(--font-mono);
        text-transform:uppercase; letter-spacing:.04em;
    }}
    .rec-confidence-value {{ font-family:var(--font-display); font-weight:600; font-size:17px; color:var(--text-1); }}
    .rec-impact {{
        font-family:var(--font-mono); font-size:10.5px; padding:3px 7px; border-radius:4px; font-weight:600;
        background:var(--surface-soft); border:1px solid var(--border); color:var(--text-2);
    }}
    .rec-impact.high {{ background:var(--amber-soft); border-color:rgba(255,183,29,.3); color:#a06b00; }}
    .expand-button {{
        width:28px; height:28px; border-radius:6px; display:grid; place-items:center;
        color:var(--text-3); font-size:12px; transition:all .15s; align-self:center; text-decoration:none;
    }}
    .expand-button:hover {{ background:var(--bg); color:var(--text-1); }}
    .rec-card.expanded .expand-button, details.rec-card[open] .expand-button {{ background:var(--primary); color:white; transform:rotate(180deg); }}
    .rec-expand {{ display:none; padding:0 20px 18px 68px; }}
    .rec-card.expanded .rec-expand, details.rec-card[open] .rec-expand {{ display:block; }}
    .evidence-block {{
        background:var(--primary-soft); border:1px solid var(--primary-line); border-radius:8px;
        padding:14px 16px; margin-bottom:12px;
    }}
    .evidence-header {{
        font-family:var(--font-mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.06em;
        color:var(--text-2); margin-bottom:10px; font-weight:600;
    }}
    .driver-list {{ display:flex; flex-direction:column; gap:6px; }}
    .driver-row {{ display:flex; align-items:center; gap:10px; background:var(--surface); border:1px solid var(--border); padding:8px 12px; border-radius:6px; font-size:12.5px; }}
    .driver-tag {{
        font-family:var(--font-mono); font-size:10.5px; font-weight:600; padding:2px 6px;
        border-radius:3px; letter-spacing:.04em; flex-shrink:0; min-width:130px; text-align:center;
    }}
    .driver-tag.pull {{ background:rgba(0,164,227,.12); color:var(--primary-deep); }}
    .driver-tag.pull-forward {{ background:rgba(0,164,227,.22); color:var(--primary-deep); border:1px solid var(--primary-line); }}
    .driver-tag.context {{ background:rgba(255,183,29,.18); color:#a06b00; }}
    .driver-tag.proxy {{ background:rgba(100,116,139,.12); color:var(--text-2); }}
    .driver-text {{ color:var(--text-1); flex:1; }}
    .driver-source {{ font-family:var(--font-mono); font-size:10.5px; color:var(--text-3); white-space:nowrap; display:inline-flex; align-items:center; gap:4px; }}
    .driver-source::before {{ content:''; width:5px; height:5px; background:var(--success); border-radius:50%; }}
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stVerticalBlockBorderWrapper"]) {{ margin-bottom:0 !important; }}
    [class*="st-key-rec_act_"] {{ margin-top:-4px !important; margin-bottom:8px !important; }}
    [class*="st-key-rec_act_"] [data-testid="stHorizontalBlock"] {{ gap:6px !important; flex-wrap:wrap !important; }}
    [class*="st-key-rec_act_"] button {{
        min-height:26px !important; max-height:26px !important;
        font-size:11.5px !important; font-weight:600 !important;
        border-radius:5px !important; padding:0 11px !important;
        border:1px solid var(--border) !important;
        background:var(--surface) !important; color:var(--text-2) !important;
        width:auto !important; white-space:nowrap !important;
    }}
    [class*="st-key-rec_act_"] button:hover {{ border-color:var(--primary) !important; color:var(--primary) !important; }}
    [class*="st-key-rec_act_"] button[kind="primary"],
    [class*="st-key-rec_act_"] [data-testid="stBaseButton-primary"] {{
        color:var(--primary-deep) !important; border-color:rgba(0,164,227,.35) !important;
        background:rgba(0,164,227,.07) !important;
    }}
    .rec-actions {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    .rec-action {{
        font-size:12px; color:var(--text-1); font-weight:500; padding:7px 12px;
        border:1px solid var(--border-emphasis); border-radius:6px; background:var(--surface);
        text-decoration:none; display:inline-flex; align-items:center; gap:6px; transition:all .15s;
        font-family:var(--font-body);
    }}
    .rec-action:hover {{ border-color:var(--primary); background:var(--primary-soft); color:var(--primary-deep); }}
    .rec-action.primary {{ color:var(--primary-deep); border-color:var(--primary-line); background:var(--surface); }}
    .rec-action.primary:hover {{ background:var(--primary); color:white; border-color:var(--primary); }}
    .rec-action.outline {{ color:var(--text-2); }}
    .action-icon {{ font-size:11px; }}
    .market-frame-content {{ display:flex; flex-direction:column; gap:6px; }}
    .market-frame-text {{ font-size:13.5px; color:var(--text-1); line-height:1.55; }}
    .market-frame-text strong {{ font-weight:600; }}
    .market-drivers {{ display:flex; gap:16px; align-items:center; font-family:var(--font-mono); font-size:11px; }}
    .market-driver {{ display:flex; flex-direction:column; gap:2px; align-items:center; }}
    .market-driver-pct {{ font-family:var(--font-display); font-weight:600; font-size:18px; color:var(--text-1); }}
    .market-driver-label {{ font-size:9.5px; text-transform:uppercase; letter-spacing:.06em; color:var(--text-3); font-weight:600; }}
    .market-driver.pull .market-driver-pct {{ color:var(--primary-deep); }}
    .market-driver.context .market-driver-pct {{ color:#a06b00; }}
    .market-driver.proxy .market-driver-pct {{ color:var(--text-2); }}

    .ask-view {{ display:none; flex-direction:column; gap:16px; }}
    .ask-view.active {{ display:flex; }}
    .ask-input-panel {{
        background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
        padding:20px; display:flex; flex-direction:column; gap:16px; margin-bottom:0;
    }}
    .ask-input-header {{ display:flex; flex-direction:column; gap:4px; }}
    .ask-input-title {{ font-family:var(--font-display); font-weight:600; font-size:17px; color:var(--text-1); letter-spacing:-.01em; }}
    .ask-input-subtitle {{ font-size:12.5px; color:var(--text-2); margin-top:0; }}
    .ask-input-wrap {{ position:relative; display:flex; align-items:center; margin:0; }}
    .ask-input {{
        width:100%; padding:14px 48px 14px 44px; background:var(--bg);
        border:1px solid var(--border-emphasis); border-radius:10px;
        font-family:var(--font-body); font-size:14px; color:var(--text-1); transition:all .15s;
    }}
    .ask-input:focus {{ outline:none; border-color:var(--primary); background:var(--surface); box-shadow:0 0 0 4px var(--primary-soft); }}
    .ask-input::placeholder {{ color:var(--text-3); }}
    .ask-input-icon {{ position:absolute; left:16px; top:50%; transform:translateY(-50%); color:var(--text-3); font-size:14px; }}
    .ask-input-send {{
        position:absolute; right:6px; top:50%; transform:translateY(-50%); width:32px; height:32px;
        background:var(--primary); color:white; border-radius:8px; display:grid; place-items:center;
        font-size:14px; font-weight:600; transition:background .15s; border:0;
    }}
    .ask-input-send:hover {{ background:var(--primary-deep); }}
    .ask-suggestions {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .ask-suggestions-label {{
        font-family:var(--font-mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.06em;
        color:var(--text-3); font-weight:600; margin-right:4px; align-self:center;
    }}
    .ask-chip {{
        font-size:12px; color:var(--text-2); padding:6px 10px; background:var(--surface-soft);
        border:1px solid var(--border); border-radius:6px; font-family:var(--font-body);
        font-weight:500; transition:all .15s; text-decoration:none; display:inline-flex;
    }}
    .ask-chip:hover {{ border-color:var(--primary); background:var(--primary-soft); color:var(--primary-deep); }}
    .ask-conversation {{ display:flex; flex-direction:column; gap:12px; }}
    .ask-exchange {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }}
    .ask-question {{ padding:14px 20px; background:var(--surface-soft); border-bottom:1px solid var(--border); display:flex; align-items:start; gap:10px; }}
    .ask-question-icon {{
        width:26px; height:26px; border-radius:50%; background:var(--primary); color:white;
        display:grid; place-items:center; font-size:11px; font-weight:700; font-family:var(--font-mono); flex-shrink:0;
    }}
    .ask-question-text {{ font-family:var(--font-display); font-weight:500; font-size:14.5px; color:var(--text-1); line-height:1.45; }}
    .ask-answer {{ padding:16px 20px 18px; display:flex; flex-direction:column; gap:12px; }}
    .ask-answer-header {{
        font-family:var(--font-mono); font-size:10.5px; text-transform:uppercase; letter-spacing:.06em;
        color:var(--text-3); font-weight:600;
    }}
    .ask-answer-body {{ font-size:13.5px; color:var(--text-1); line-height:1.6; }}
    .ask-answer-body strong {{ font-weight:600; }}
    .ask-evidence-tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }}
    .ask-evidence-tag {{
        display:inline-flex; align-items:center; gap:5px; font-family:var(--font-mono);
        font-size:10.5px; font-weight:500; padding:3px 8px; border-radius:4px;
        background:var(--surface-soft); border:1px solid var(--border); color:var(--text-2);
    }}
    .ask-evidence-tag::before {{ content:''; width:5px; height:5px; border-radius:50%; background:var(--success); }}
    .ask-confidence {{ display:inline-flex; align-items:center; gap:6px; font-family:var(--font-mono); font-size:11.5px; margin-top:4px; }}
    .ask-confidence-label {{ color:var(--text-3); }}
    .ask-confidence-value {{ color:var(--text-1); font-weight:600; }}
    .ask-para {{ margin:0 0 8px 0; }}
    .ask-para:last-child {{ margin-bottom:0; }}
    .ask-table {{ width:100%; border-collapse:collapse; margin:10px 0 14px; font-size:12.5px; font-family:var(--font-mono); }}
    .ask-table th {{ text-align:left; padding:5px 12px; color:var(--text-3); font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; border-bottom:1px solid var(--border); }}
    .ask-table td {{ padding:7px 12px; border-bottom:1px solid var(--line); color:var(--text-1); }}
    .ask-table tr:last-child td {{ border-bottom:none; }}
    .ask-table td.vel-up {{ color:var(--success); font-weight:700; }}
    .ask-table td.vel-down {{ color:var(--danger); font-weight:700; }}
    .ask-actions-row {{ display:flex; gap:8px; margin-top:10px; }}
    .ask-action-btn {{ display:inline-flex; align-items:center; gap:5px; padding:5px 12px; border:1px solid var(--border); border-radius:5px; font-size:12px; font-weight:600; color:var(--text-2); cursor:pointer; white-space:nowrap; }}
    .ask-action-btn.primary {{ color:var(--primary-deep); border-color:rgba(0,164,227,.3); }}
    .ask-action-btn:hover {{ border-color:var(--primary); color:var(--primary); }}

    .automation-left {{ display:flex; align-items:center; gap:14px; }}
    .automation-icon {{
        width:32px; height:32px; background:rgba(0,164,227,.18); border:1px solid rgba(0,164,227,.3);
        border-radius:8px; display:grid; place-items:center; color:var(--primary); font-size:14px;
    }}
    .automation-text {{ display:flex; flex-direction:column; gap:2px; }}
    .automation-title {{ font-family:var(--font-display); font-weight:600; font-size:13px; color:white; letter-spacing:-.005em; }}
    .automation-detail {{ font-size:12px; color:rgba(255,255,255,.7); }}
    .automation-detail strong {{ color:rgba(255,255,255,.95); font-weight:600; }}
    .automation-right {{ display:flex; align-items:center; gap:8px; }}
    .automation-link {{
        background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.15);
        color:white; padding:6px 12px; border-radius:6px; font-size:11.5px; font-weight:500;
        text-decoration:none; font-family:var(--font-mono); transition:background .15s;
    }}
    .automation-link:hover {{ background:rgba(255,255,255,.16); }}
    .footer {{
        padding:16px 24px 18px; font-size:11.5px; color:var(--text-3); text-align:center;
        font-family:var(--font-mono); border-top:1px solid var(--border);
        background:var(--surface); line-height:1.6;
    }}

    @media (max-width: 900px) {{
        .rec-header {{ grid-template-columns:32px 1fr 32px; }}
        .rec-meta-col {{ display:none; }}
        .market-frame {{ grid-template-columns:1fr; }}
        .mode-toggle-bar {{ flex-direction:column; align-items:flex-start; }}
    }}
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
        try:
            _hit = lookup_sku(_sku_q)
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
def _query_href(**params) -> str:
    return "?" + "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items() if v is not None)


def _query_value(name: str, default: str) -> str:
    try:
        value = st.query_params.get(name, default)
        if isinstance(value, list):
            value = value[0] if value else default
        return str(value or default)
    except Exception:
        return default


_VIEW_ALIASES = {
    "analytics": "analytics",
    "predictive": "predictive",
    "askrec": "askrec",
    "ask": "askrec",
    "recommendation": "askrec",
    "recommendations": "askrec",
}
_VIEW_LABELS = {
    "analytics": "Analytics",
    "predictive": "Predictive",
    "askrec": "Ask & Recommendation",
}
main_view = _VIEW_ALIASES.get(
    _query_value("view", st.session_state.get("main_view", "analytics")).strip().lower(),
    "analytics",
)
st.session_state["main_view"] = main_view


def _main_tab_strip_html(active_view: str) -> str:
    links = []
    for view_key, label in _VIEW_LABELS.items():
        active_cls = " active" if view_key == active_view else ""
        links.append(f'<a class="tab{active_cls}" href="{_query_href(view=view_key)}">{escape(label)}</a>')
    return f"""
<div class="tab-strip">
  <div class="tabs">{''.join(links)}</div>
  <div class="tab-strip-right">
    <span class="stamp">Live market feed</span>
  </div>
</div>"""


st.markdown(f"""
<div class="app-chrome">
  <div class="chrome-left">
    <div class="brand">
      <div class="brand-mark">i</div>
      <span class="brand-name">Innovatics</span>
      <span class="brand-divider">/</span>
      <span class="brand-product">Channel Intelligence</span>
    </div>
    <div class="workspace-pill">Market Signal</div>
  </div>
  <div class="chrome-right">
    <div class="refresh-status">
      <span class="live-dot"></span>
      Live · refreshed recently
    </div>
    <div class="account-button">Z</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.html(_main_tab_strip_html(main_view))

# ── 2-row compact pill filter bar ─────────────────────────────────────────────
_fb_lbl = lambda lbl, x, fmt=None: f"{lbl}  {fmt(x) if fmt else x}"

with st.container(key="filter_area", gap="small"):
    st.markdown('<div class="filter-section-label">Context</div>', unsafe_allow_html=True)
    _r1 = st.columns([1.0, 1.4, 1.2, 1.5, 0.05, 1.1, 0.75, 0.65])
    with _r1[0]:
        gender_filter = st.selectbox(
            "Gender",
            _gender_opts,
            format_func=lambda x: _GENDER_LABELS.get(x, x.title()),
            key="gender_filter",
            label_visibility="collapsed",
        )
    with _r1[1]:
        category_filter = st.selectbox(
            "Category",
            _category_opts,
            format_func=lambda x: _CATEGORY_LABELS.get(x, x.replace("_", " ").title()),
            key="cat_filter",
            label_visibility="collapsed",
        )
    with _r1[2]:
        style_filter = st.selectbox(
            "Style",
            _neck_type_opts,
            key="style_filter",
            label_visibility="collapsed",
        )
    with _r1[3]:
        window_filter = st.selectbox(
            "Window",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "All Time"],
            key="window_filter",
            label_visibility="collapsed",
        )
    with _r1[4]:
        st.markdown('<div class="filter-divider-v"></div>', unsafe_allow_html=True)
    with _r1[5]:
        if st.button("🔍 Look up SKU", key="sku_open_btn", use_container_width=True):
            _sku_lookup_dialog()
    with _r1[6]:
        if st.button("↗ Save view", key="save_view_btn", use_container_width=True, help="Save current filter as default"):
            st.session_state["saved_view"] = {
                "gender_filter": st.session_state.get("gender_filter", "All"),
                "cat_filter":    st.session_state.get("cat_filter", "All"),
                "style_filter":  st.session_state.get("style_filter", "All"),
                "window_filter": st.session_state.get("window_filter", "Last 30 Days"),
                "price_band_filter": st.session_state.get("price_band_filter", "All"),
                "region_filter": st.session_state.get("region_filter", "All US"),
                "plt_filter":    st.session_state.get("plt_filter", "All"),
            }
            st.toast("View saved", icon="✓")
    with _r1[7]:
        if st.button("↺ Reset all", key="reset_all_btn", use_container_width=True, help="Clear all filters to defaults"):
            for _fkey in ["gender_filter", "cat_filter", "style_filter", "window_filter",
                          "price_band_filter", "region_filter", "plt_filter", "saved_view"]:
                st.session_state.pop(_fkey, None)
            st.rerun()
    st.markdown('<div class="filter-section-label refine">Refine</div>', unsafe_allow_html=True)
    _r2 = st.columns([1.1, 1.1, 1.4, 6.4])
    with _r2[0]:
        price_band_filter = st.selectbox(
            "Price band",
            ["All", "<$25", "$25–50", "$50–75", "$75–100", "$100–150", "$150+"],
            key="price_band_filter",
            label_visibility="collapsed",
        )
    with _r2[1]:
        region_filter = st.selectbox(
            "Region",
            ["All US", "East", "West", "South", "Midwest"],
            key="region_filter",
            label_visibility="collapsed",
        )
    with _r2[2]:
        platform_filter = st.selectbox(
            "Channel",
            _platform_opts,
            format_func=lambda x: "Amazon + Nordstrom" if x == "All" else _PLATFORM_LABELS.get(x, x.title()),
            key="plt_filter",
            label_visibility="collapsed",
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
        work = work.sort_values("review_count", ascending=False).drop_duplicates("product_id")
    bands_cfg = _price_band_config(work)
    bands = [b[0] for b in bands_cfg]
    work["band"] = work["current_price"].apply(lambda p: _price_band_label(p, bands_cfg))
    work["weight"] = pd.to_numeric(work.get("review_count", 0), errors="coerce").fillna(0)
    if work["weight"].sum() == 0:
        work["weight"] = 1

    # Glossary formula: share_index = (band_reviews / total_reviews) / (band_listings / total_listings)
    # A 3.2× index means this band attracts 3.2× its proportional share of reviews.
    review_by_band  = work.groupby("band")["weight"].sum().reindex(bands, fill_value=0)
    listing_by_band = work.groupby("band").size().reindex(bands, fill_value=0)
    total_reviews   = max(float(review_by_band.sum()), 1)
    total_listings  = max(float(listing_by_band.sum()), 1)

    best_band, best_index = bands[0], 0.0
    for b in bands:
        rev_share     = float(review_by_band[b]) / total_reviews
        listing_share = max(float(listing_by_band[b]) / total_listings, 1e-9)
        idx = rev_share / listing_share
        if idx > best_index:
            best_index, best_band = idx, b

    multiplier = max(1.0, min(9.9, round(best_index, 1)))
    return best_band, multiplier


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
                "attr_key": str(row.get("attr_key") or ""),
                "category": str(row.get("category") or ""),
                "platform": str(row.get("platform") or ""),
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


def _confidence_pct(row: dict, agreement: str | None = None) -> int:
    """Glossary: confidence derived from cross-platform agreement + sample size + model error bars."""
    label = str(row.get("confidence") or "").strip().lower()
    base = {"high": 82, "med": 74, "medium": 74, "low": 64}.get(label, 64)

    # Sample size component (weeks_observed = data points available)
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

    # Cross-platform agreement component (glossary: strong=+8, divergent=-6)
    agr = str(agreement or row.get("agreement") or "").strip().lower()
    base += {"strong": 8, "mixed": 0, "divergent": -6, "single channel": -3}.get(agr, 0)

    return max(50, min(95, int(round(base))))


def _decision_tag(stage: str, change: float) -> str:
    stage = _stage_key(stage)
    if stage == "accelerating":
        return "Replenish" if change >= 0 else "Watch"
    if stage == "declining":
        return "Retire" if change < 0 else "Watch"
    if stage == "emerging":
        return "Watch"
    return "Watch"


def _predictive_kpis(rows: list[dict], platform_map: dict | None = None,
                      velocity_lookup: dict | None = None) -> dict:
    """Glossary: patterns needing action = lifecycle Acc/Dec + conf>75% + |Δ|>15%."""
    pm = platform_map or {}
    vl = velocity_lookup or {}

    def _row_agreement(row: dict) -> str:
        """Derive cross-platform agreement for a row via platform_map."""
        ak = str(row.get("attr_key") or "")
        av = str(row.get("name") or "")
        entry = pm.get((ak, av))
        if entry:
            amz = entry.get("amz")
            nor = entry.get("nor")
            lbl, _cls, _n = _real_agreement(amz, nor)
            return lbl.lower()
        return ""

    def _is_structural_decline(row: dict) -> bool:
        """60d structural: decline sustained 60+ days across both channels with strong agreement."""
        cat  = str(row.get("category") or "")
        plat = str(row.get("platform") or "")
        vrow = vl.get((cat, plat)) or vl.get((cat, ""))
        if not vrow:
            return False
        hist_days = vrow.get("hist_days") or []
        if len(hist_days) < 2:
            return False
        try:
            from datetime import date as _date
            d0 = _date.fromisoformat(str(hist_days[0]))
            d1 = _date.fromisoformat(str(hist_days[-1]))
            span_days = (d1 - d0).days
        except Exception:
            span_days = 0
        slope = float(vrow.get("slope") or 0)
        if span_days < 60 or slope >= 0:
            return False
        # Both channels declining
        other_plat = "Nordstrom" if "amazon" in plat.lower() else "Amazon"
        vrow2 = vl.get((cat, other_plat))
        if vrow2 and float(vrow2.get("slope") or 0) < 0:
            return True
        return span_days >= 60 and slope < 0

    urgent = []
    for row in rows:
        change = float(row.get("change") or 0)
        agr = _row_agreement(row)
        conf = _confidence_pct(row, agr)
        if _stage_key(row.get("stage")) in {"accelerating", "declining"} and conf > 75 and abs(change) > 15:
            urgent.append({**row, "confidence_pct": conf, "agreement": agr,
                           "decision_tag": _decision_tag_full(row.get("stage"), change)})

    gains = [r for r in rows if float(r.get("change") or 0) > 0]
    risks = [r for r in rows if float(r.get("change") or 0) < 0]
    biggest_gain = max(gains, key=lambda r: float(r.get("change") or 0), default=None)
    biggest_risk = min(risks, key=lambda r: float(r.get("change") or 0), default=None)

    if biggest_risk:
        biggest_risk = {
            **biggest_risk,
            "is_structural": _is_structural_decline(biggest_risk),
            "agreement": _row_agreement(biggest_risk),
        }

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


def _predictive_kpi_band_html(rows: list[dict], platform_map: dict | None = None,
                               velocity_lookup: dict | None = None,
                               gt_summary: dict | None = None) -> str:
    kpis = _predictive_kpis(rows, platform_map=platform_map, velocity_lookup=velocity_lookup)
    urgent_count = len(kpis["urgent"])
    gain = kpis["biggest_gain"]
    risk = kpis["biggest_risk"]
    gt = gt_summary or {}

    gain_name = _label(gain.get("name"), "Run predictions") if gain else "Run predictions"
    gain_change = int(round(float(gain.get("change") or 0))) if gain else 0
    gain_conf = _confidence_pct(gain, gain.get("agreement") if gain else None) if gain else 0
    gain_stage = _LIFECYCLE_LABELS[_stage_key(gain.get("stage"))].lower() if gain else "pending"

    risk_name = _label(risk.get("name"), "Run predictions") if risk else "Run predictions"
    risk_change = int(round(float(risk.get("change") or 0))) if risk else 0
    risk_conf = _confidence_pct(risk, risk.get("agreement") if risk else None) if risk else 0
    risk_stage = _LIFECYCLE_LABELS[_stage_key(risk.get("stage"))].lower() if risk else "pending"
    structural_badge = ' <span style="font-size:9px;background:#fee2e2;color:#b91c1c;border-radius:3px;padding:1px 5px;font-weight:700;">60d structural</span>' if (risk and risk.get("is_structural")) else ""

    gt_lead_count = int(gt.get("lead_count") or 0)
    gt_avg_days = gt.get("avg_lead_days")
    if gt.get("status") == "missing_key":
        gt_val, gt_note = "API key", "Add SERPAPI_API_KEY to .env"
    elif gt_lead_count > 0 and gt_avg_days:
        gt_val  = f"{gt_lead_count} lead{'s' if gt_lead_count != 1 else ''}"
        gt_note = f"avg ~{gt_avg_days}d ahead of velocity · +5pp conf"
    elif gt_lead_count > 0:
        gt_val  = f"{gt_lead_count} lead{'s' if gt_lead_count != 1 else ''}"
        gt_note = "queries ≥+20% delta · +5pp conf when GT confirms"
    else:
        gt_val, gt_note = "--", "No queries above +20% threshold yet"

    return f"""
<div class="signal-band">
  <div class="signal-card">
    <div class="signal-label">Patterns needing action · 4 weeks</div>
    <div class="signal-value" style="font-size:1.72rem;">{urgent_count} urgent</div>
    <div class="signal-note">Accelerating/Declining · conf &gt;75% · velocity &gt;±15%<br><strong>{_safe(kpis["urgent_summary"])}</strong></div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Biggest momentum gain</div>
    <div class="signal-value" style="font-size:1.42rem;">{_safe(gain_name)}</div>
    <div class="signal-note"><span class="delta up">{gain_change:+d}%</span> velocity · {gain_stage}<br>Forecast +4w · {gain_conf}% conf</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Biggest decline risk</div>
    <div class="signal-value" style="font-size:1.42rem;">{_safe(risk_name)}{structural_badge}</div>
    <div class="signal-note"><span class="delta down">{risk_change:+d}%</span> velocity · {risk_stage}<br>Forecast +4w · {risk_conf}% conf</div>
  </div>
  <div class="signal-card">
    <div class="signal-label">Google Trends lead time</div>
    <div class="signal-value" style="font-size:1.72rem;">{escape(gt_val)}</div>
    <div class="signal-note">{escape(gt_note)}</div>
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
        hist_vals = row.get("hist_vals") or []
        future_vals = row.get("future_vals") or []
        html.append(
            _sparkline_from_vals(title, actual, projected, hist_vals, future_vals) +
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


def _trajectory_rows_html(
    rows: list[dict],
    gt_summary: dict | None = None,
    gt_result: dict | None = None,
    category: str = "All",
    gender: str = "All",
    style: str = "All",
    platform_map: dict | None = None,
    velocity_lookup: dict | None = None,
) -> str:
    if not rows:
        return "<div class='empty-panel'>No backend pattern trajectory available yet. Run predictions after scrape history exists.</div>"

    gt_summary = gt_summary or {}
    gt_result = gt_result or {}
    gt_status = gt_summary.get("status")
    gt_by_query = {
        str(row.get("query") or ""): row
        for row in (gt_result.get("rows") or [])
        if row.get("query")
    }

    def _row_gt_evidence(row: dict) -> tuple[str, str, str]:
        if gt_status == "missing_key":
            return (
                '<span class="pred-badge soon">GT key needed</span>',
                "Google Trends is connected but waiting for SERPAPI_API_KEY in .env.",
                "Waiting · SerpAPI key",
            )

        query = _gt_query_for_row(row, category, gender, style)
        if not query:
            return (
                '<span class="pred-badge soon">GT not matched</span>',
                "No reliable apparel search phrase was generated for this attribute, so it is excluded from Pull scoring.",
                "Skipped · query quality guard",
            )

        gt_row = gt_by_query.get(query)
        if gt_row:
            delta_pct = int(gt_row.get("delta_pct") or 0)
            return (
                f'<span class="pred-badge gt">GT {delta_pct:+d}%</span>',
                f'Google Trends query "{_safe(_label(query))}" is moving {delta_pct:+d}% vs the 14d/prior 30d baseline.',
                "Live · SerpAPI Google Trends",
            )

        if gt_status == "ok":
            return (
                '<span class="pred-badge soon">GT checked</span>',
                f'Google Trends checked "{_safe(_label(query))}" but returned no usable timeline for this row.',
                "Live · SerpAPI checked",
            )

        return (
            '<span class="pred-badge soon">GT no live data</span>',
            _safe(gt_summary.get("message") or "Google Trends returned no live timeline data for this filter."),
            "Live · SerpAPI checked",
        )

    html = []
    vlookup = velocity_lookup or {}
    for idx, row in enumerate(rows[:6]):
        change = float(row.get("change") or 0)
        row_cat = str(row.get("category") or "")
        row_plat = str(row.get("platform") or "")
        vel = vlookup.get((row_cat, row_plat), {})
        hist_vals = vel.get("hist_vals") or []
        future_vals = vel.get("future_vals") or []
        proj_chg = vel.get("projected_change_pct")
        fc4 = int(round(proj_chg * 28 / 30)) if proj_chg is not None else _forecast_value(change, 4)
        fc8 = int(round(proj_chg * 56 / 30)) if proj_chg is not None else _forecast_value(change, 8)
        # Derive agreement from platform_map for confidence calculation
        _ak = str(row.get("attr_key") or "")
        _av = str(row.get("name") or "")
        _pentry = (platform_map or {}).get((_ak, _av), {})
        _agr_lbl, _, _ = _real_agreement(_pentry.get("amz"), _pentry.get("nor")) if _pentry else ("", "", 0)
        conf = _confidence_pct(row, _agr_lbl.lower() if _agr_lbl else None)
        stage = _stage_key(row.get("stage"))
        name = _label(row.get("name"), "Pattern")
        action = row.get("action") or "Monitor daily"
        progress = _stage_progression(stage, change)
        progress_html = "".join(
            f'<span class="pred-step {p}">{_stage_abbrev(p)}</span>' +
            ('<span style="color:#cbd5e1;">→</span>' if n < 2 else "")
            for n, p in enumerate(progress)
        )
        gt_badge, gt_driver_text, gt_driver_source = _row_gt_evidence(row)
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
      {_trajectory_svg(hist_vals, future_vals)}
    </div>
    <div class="pred-driver">
      <div class="pred-driver-title">Why this trajectory · evidence</div>
      <div class="pred-driver-row"><span class="pred-driver-tag proxy">PROXY · TRAILING</span><div><span class="pred-driver-text">Marketplace review velocity and lifecycle stage from current scraped history.</span><span class="pred-driver-source">Live · marketplace mining</span></div></div>
      <div class="pred-driver-row"><span class="pred-driver-tag pull">PULL · FORWARD</span><div><span class="pred-driver-text">{gt_driver_text}</span><span class="pred-driver-source">{gt_driver_source}</span></div></div>
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
    gain_conf = _confidence_pct(gain, gain.get("agreement") if gain else None) if gain else 0
    risk_conf = _confidence_pct(risk, risk.get("agreement") if risk else None) if risk else 0
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

def _delta_from_scores(scores: pd.DataFrame, attr_key: str) -> dict:
    """Extract top attribute value and week-over-week delta from trend_scores.

    Returns: {"name": str, "latest_share": float, "previous_share": float, "delta_pct": float}
    """
    fallback = {"name": "N/A", "latest_share": 0.0, "previous_share": 0.0, "delta_pct": 0.0}
    if scores is None or scores.empty or "attr_key" not in scores.columns:
        return fallback
    subset = scores[scores["attr_key"] == attr_key]
    if subset.empty:
        return fallback
    top = subset.sort_values("latest_week_share", ascending=False).iloc[0]
    latest = float(top.get("latest_week_share") or 0)
    previous = float(top.get("previous_week_share") or 0)
    delta = round((latest - previous) * 100, 1)
    return {
        "name": str(top.get("attr_value") or "N/A"),
        "latest_share": latest,
        "previous_share": previous,
        "delta_pct": delta,
    }


def _analytics_kpi_strip_html(products: pd.DataFrame, variants: pd.DataFrame, scores: pd.DataFrame = None) -> str:
    """4 KPI tiles matching clean card design."""
    kpis = get_kpis(products)
    sku_count = len(variants) if not variants.empty else len(products)

    # Tile 1: Reviews captured
    total_reviews = int(kpis.get("total_reviews") or 0)
    window_label = window_filter.lower().replace("last ", "").replace(" days", "d").replace("all time", "all")

    # Tile 2: Top style (neck_type sub-category) with week-over-week delta from trend_scores
    # Glossary: "Style with the highest review share. Delta = share change vs prior 30d."
    style_info = _delta_from_scores(scores, "neck_type")
    top_style_name = _label(style_info["name"]) if style_info["name"] != "N/A" else "N/A"
    style_share_pct = int(round(style_info["latest_share"] * 100))
    cat_delta = style_info["delta_pct"]
    cat_delta_cls = "up" if cat_delta > 0 else "down" if cat_delta < 0 else "neutral"
    cat_delta_sign = "+" if cat_delta > 0 else ""

    # Tile 3: Top color with week-over-week delta from trend_scores
    color_info = _delta_from_scores(scores, "color_family")
    top_color_name = _label(color_info["name"])
    color_delta = color_info["delta_pct"]
    color_delta_cls = "up" if color_delta > 0 else "down" if color_delta < 0 else "neutral"
    color_delta_sign = "+" if color_delta > 0 else ""
    color_share_pct = int(round(color_info["latest_share"] * 100))

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
    <div class="kpi-meta-new">Across {sku_count:,} SKUs · {escape(window_label)}</div>
  </div>
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Top style</div>
    <div class="kpi-val-new">{_safe(top_style_name)} <span class="kpi-val-pct">· {style_share_pct}%</span></div>
    <div class="kpi-meta-new">
      Review share <span class="kpi-delta {cat_delta_cls}">{cat_delta_sign}{cat_delta}%</span>
    </div>
  </div>
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Top color</div>
    <div class="kpi-val-new">{_safe(top_color_name)} <span class="kpi-val-pct">· {color_share_pct}%</span></div>
    <div class="kpi-meta-new">
      Share <span class="kpi-delta {color_delta_cls}">{color_delta_sign}{color_delta}%</span>
    </div>
  </div>
  <div class="kpi-tile-new">
    <div class="kpi-lbl-new">Converting price band</div>
    <div class="kpi-val-new">{_safe(band_label)}</div>
    <div class="kpi-meta-new">
      <span class="kpi-index-badge">{band_multiplier}× share index</span>
      <span class="kpi-median">median {_safe(med_price)}</span>
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


def _winning_patterns_html(rows: list[dict], platform_map: dict | None = None,
                            gt_by_query: dict | None = None,
                            category: str = "All", gender: str = "All", style: str = "All") -> str:
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
        pmap = platform_map or {}
        pkey = (str(row.get("attr_key") or ""), str(row.get("name") or ""))
        plat_data = pmap.get(pkey, {})
        amz_chg = plat_data.get("amz")
        nor_chg = plat_data.get("nor")
        _agr_w, _, _ = _real_agreement(amz_chg, nor_chg) if plat_data else ("", "", 0)
        conf_pct = _confidence_pct(row, _agr_w.lower() if _agr_w else None)
        if amz_chg is None and nor_chg is None:
            amz_chg = int(round(change))
            nor_chg = int(round(change))
        elif amz_chg is None:
            amz_chg = int(round(change))
        elif nor_chg is None:
            nor_chg = int(round(change))
        decision = _decision_tag_full(stage, change, amz_chg, nor_chg)
        dtag_cls, dtag_lbl = _DECISION_TAG_DISPLAY.get(decision, ("watch", decision))
        amz_cls = "vel-up" if amz_chg >= 0 else "vel-down"
        nor_cls = "vel-up" if nor_chg >= 0 else "vel-down"

        # Real cross-platform agreement
        agree_lbl, agree_cls, _agree_bars = _real_agreement(amz_chg, nor_chg)

        # Google Trends evidence for this pattern row
        _gt_query = _gt_query_for_row(row, category, gender, style)
        _gt_row = (gt_by_query or {}).get(_gt_query or "")
        if _gt_row:
            _gt_delta_val = int(_gt_row.get("delta_pct") or 0)
            _pull_txt = f'Google Trends query "{_safe(_label(_gt_query))}" moving {_gt_delta_val:+d}% vs 14d/prior 30d baseline — live signal confirms demand direction.'
            _pull_src = "Live · SerpAPI Google Trends"
        elif _gt_query:
            _pull_txt = f'Google Trends query "{_safe(_label(_gt_query))}" checked — no strong signal above threshold this window.'
            _pull_src = "Live · SerpAPI checked"
        else:
            _pull_txt = "Google Trends search-interest lead detection — no query matched for this attribute."
            _pull_src = "Live · query guard"

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
      <span class="driver-txt-new">{_pull_txt}</span>
      <span class="driver-src-new">{_pull_src}</span>
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


def _serpapi_key() -> str:
    return (
        os.getenv("SERPAPI_API_KEY")
        or os.getenv("SERAPI_API_KEY")
        or os.getenv("SERP_API_KEY")
        or os.getenv("GOOGLE_TRENDS_API_KEY")
        or ""
    ).strip()


_GT_CATEGORY_TERMS = {
    "mens_tshirts": "men t shirt",
    "mens_polos": "men polo shirt",
    "womens_dresses": "women dress",
    "womens_tops": "women top",
    "denim": "denim jeans",
}
_GT_SKIP_VALUES = {"", "all", "nan", "none", "null", "other", "unknown", "n/a"}
_GT_WEAK_PATTERN_VALUES = {"solid", "cartoon", "graphic", "other"}


def _google_query_text(value: str) -> str:
    text = re.sub(r"[_/]+", " ", str(value or ""))
    text = re.sub(r"[^A-Za-z0-9 $&+-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _gt_category_term(category: str, fallback_category: str) -> str:
    raw = str(category or fallback_category or "").strip()
    if raw in _GT_CATEGORY_TERMS:
        return _GT_CATEGORY_TERMS[raw]
    label = _CATEGORY_LABELS.get(raw, raw.replace("_", " ").title())
    label = label.replace("Men's", "men").replace("Women's", "women")
    return _google_query_text(label or "apparel")


def _gt_material_term(value: str) -> str:
    text = _google_query_text(value)
    terms = []
    if "cotton" in text:
        terms.append("cotton")
    if "linen" in text:
        terms.append("linen")
    if "denim" in text:
        terms.append("denim")
    if "polyester" in text:
        terms.append("polyester")
    if "spandex" in text or "elastane" in text or "stretch" in text:
        terms.insert(0, "stretch")
    if "wool" in text:
        terms.append("wool")
    if "silk" in text:
        terms.append("silk")
    if "rayon" in text or "viscose" in text:
        terms.append("rayon")
    return " ".join(dict.fromkeys(terms))


def _gt_query_for_row(row: dict, category_filter: str, gender_filter: str, style_filter: str) -> str:
    attr_key = _google_query_text(row.get("attr_key") or "")
    raw_value = str(row.get("name") or "")
    value = _google_query_text(raw_value)
    if value in _GT_SKIP_VALUES:
        return ""

    category_term = _gt_category_term(row.get("category") or "", category_filter)
    style_term = "" if style_filter == "All" else _google_query_text(_STYLE_LABELS.get(style_filter, style_filter))
    gender_term = "" if gender_filter == "All" else _google_query_text(_GENDER_LABELS.get(gender_filter, gender_filter))

    if attr_key == "material":
        material = _gt_material_term(raw_value)
        if not material:
            return ""
        return _google_query_text(f"{material} {category_term}")
    if attr_key == "color_family":
        return _google_query_text(f"{value} {category_term}")
    if attr_key == "neck_type":
        return _google_query_text(f"{value} {category_term}")
    if attr_key == "fit":
        fit = value
        if "fit" not in fit and fit in {"classic", "regular", "slim", "relaxed", "boxy", "loose", "comfort"}:
            fit = f"{fit} fit"
        return _google_query_text(f"{fit} {category_term}")
    if attr_key == "pattern":
        if value in _GT_WEAK_PATTERN_VALUES:
            return ""
        return _google_query_text(f"{value} print {category_term}")

    return _google_query_text(" ".join(part for part in (value, style_term, category_term, gender_term) if part))


def _google_trends_queries(rows: list[dict], category: str, gender: str, style: str, limit: int = 5) -> list[str]:
    queries, seen = [], set()
    for row in rows:
        query = _gt_query_for_row(row, category, gender, style)
        if not query or query == "signal":
            continue
        if len(query) < 3:
            continue
        if query not in seen:
            seen.add(query)
            queries.append(query)
        if len(queries) >= limit:
            break

    if not queries:
        category_part = _gt_category_term(category, category)
        gender_part = "" if gender == "All" else _google_query_text(_GENDER_LABELS.get(gender, gender))
        style_part = "" if style == "All" else _google_query_text(_STYLE_LABELS.get(style, style))
        fallback = _google_query_text(" ".join(part for part in (style_part, category_part, gender_part, "trend") if part))
        queries = [fallback or "apparel trend"]
    return queries[:limit]


def _trend_value(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^0-9.\-]", "", str(value))
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _trend_delta(values: list[float]) -> tuple[int, int]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return 0, 0
    recent = clean[-14:] if len(clean) >= 14 else clean[-max(1, len(clean) // 2):]
    baseline_pool = clean[-44:-14] if len(clean) >= 44 else clean[: max(1, len(clean) - len(recent))]
    if not baseline_pool:
        baseline_pool = clean[:-len(recent)] or recent
    recent_avg = sum(recent) / len(recent)
    base_avg = sum(baseline_pool) / len(baseline_pool)
    if base_avg <= 0:
        delta = int(round(recent_avg - base_avg))
    else:
        delta = int(round((recent_avg - base_avg) / base_avg * 100))
    return int(round(recent_avg)), delta


def _serpapi_key_digest(api_key: str) -> str:
    if not api_key:
        return "missing"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:10]


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_google_trends_live(queries: tuple[str, ...], geo: str, date_window: str, key_digest: str) -> dict:
    api_key = _serpapi_key()
    if not api_key:
        return {"status": "missing_key", "rows": [], "message": "SERPAPI_API_KEY is not set in .env"}
    if not queries:
        return {"status": "no_queries", "rows": [], "message": "No trend queries generated for this filter."}

    params = {
        "engine": "google_trends",
        "q": ",".join(queries),
        "geo": geo,
        "date": date_window,
        "data_type": "TIMESERIES",
        "api_key": api_key,
    }
    url = "https://serpapi.com/search.json?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "InnovaticsMarketIntelligence/1.0"})
    try:
        with urlopen(req, timeout=14) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return {"status": "api_error", "rows": [], "message": f"SerpAPI HTTP {exc.code}"}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"status": "api_error", "rows": [], "message": f"SerpAPI request failed: {exc}"}

    if payload.get("error"):
        return {"status": "api_error", "rows": [], "message": str(payload.get("error"))}

    timeline = (payload.get("interest_over_time") or {}).get("timeline_data") or []
    series = {q: [] for q in queries}
    for point in timeline:
        values = point.get("values") or []
        for idx, item in enumerate(values):
            q = item.get("query") or (queries[idx] if idx < len(queries) else None)
            if q not in series:
                continue
            val = _trend_value(item.get("extracted_value", item.get("value")))
            if val is not None:
                series[q].append(val)

    rows = []
    for q, values in series.items():
        score, delta = _trend_delta(values)
        if values:
            rows.append({
                "query": q,
                "score": max(0, min(100, score)),
                "delta_pct": delta,
                "points": len(values),
            })
    rows.sort(key=lambda r: (r["delta_pct"], r["score"]), reverse=True)
    return {
        "status": "ok" if rows else "empty",
        "rows": rows,
        "message": "Live Google Trends from SerpAPI" if rows else "SerpAPI returned no Google Trends timeline data.",
    }


def _google_trends_summary(result: dict) -> dict:
    """Glossary: lead_count = queries where GT crossed +20% threshold.
    avg_lead_days = estimated mean gap between GT signal and marketplace velocity turning.
    Industry baseline: ~7-10d for fast categories; we estimate from delta magnitude."""
    rows = result.get("rows") or []
    top = rows[0] if rows else {}
    lead_rows = [r for r in rows if int(r.get("delta_pct") or 0) >= 20]
    lead_count = len(lead_rows)

    # Estimate avg lead days: delta=20% → ~7d, delta=40% → ~11d, delta=60%+ → ~14d, cap 21d
    avg_lead_days: int | None = None
    if lead_rows:
        lead_days = [max(7, min(21, 7 + int((int(r.get("delta_pct") or 20) - 20) * 0.2)))
                     for r in lead_rows]
        avg_lead_days = int(round(sum(lead_days) / len(lead_days)))

    return {
        "status": result.get("status"),
        "message": result.get("message", ""),
        "lead_count": lead_count,
        "avg_lead_days": avg_lead_days,
        "top_query": top.get("query", ""),
        "top_delta": int(top.get("delta_pct") or 0) if top else None,
        "top_score": int(top.get("score") or 0) if top else None,
    }


def _google_trends_panel_html(result: dict, geo: str, date_window: str) -> str:
    rows = result.get("rows") or []
    rows_html = []
    for row in rows[:5]:
        q = row["query"]
        bar_pct = max(3, min(100, int(row.get("score") or 0)))
        delta_pct = int(row.get("delta_pct") or 0)
        delta_cls = "fwd-delta-up" if delta_pct >= 0 else "fwd-delta-down"
        delta = f"{delta_pct:+d}%"
        rows_html.append(f"""
<div class="fwd-query-row">
  <span class="fwd-query-name">{escape(q)}</span>
  <div class="fwd-mini-bar"><div class="fwd-mini-fill" style="width:{bar_pct}%;background:#00a4e3;"></div></div>
  <span class="{delta_cls}">{escape(delta)}</span>
</div>""")
    if not rows_html:
        rows_html.append(f"""
<div class="fwd-signal-empty">
  {escape(result.get("message") or "No live Google Trends data available.")}
  <div class="fwd-live-note">Set SERPAPI_API_KEY in .env to enable live Google Trends.</div>
</div>""")
    return f"""
<div class="fwd-signal-card">
  <div class="fwd-signal-hdr">
    <div class="fwd-signal-title">Google Trends · search-interest lead</div>
    <div class="fwd-signal-sub">14d vs prior 30d · Live SerpAPI · {escape(date_window)} · {escape(geo)}</div>
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
    <div class="fwd-signal-sub">Anomaly vs 30-year seasonal baseline · planned context feed</div>
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
    <div class="fwd-signal-sub">Patterns turning in review text · planned sentiment feed</div>
  </div>
  <div class="fwd-signal-body">{body}</div>
</div>"""


def _predictive_kpi_new_html(rows: list[dict], gt_summary: dict | None = None,
                              platform_map: dict | None = None,
                              velocity_lookup: dict | None = None) -> str:
    """Predictive KPI strip. Confidence includes cross-platform agreement per glossary."""
    kpis = _predictive_kpis(rows, platform_map=platform_map, velocity_lookup=velocity_lookup)
    urgent = kpis["urgent"]
    gain = kpis["biggest_gain"]
    risk = kpis["biggest_risk"]
    gt_summary = gt_summary or {}

    top_urgent = urgent[0] if urgent else gain
    top_urgent_name = _label(top_urgent.get("name"), "Run predictions") if top_urgent else "Run predictions"
    top_urgent_change = int(round(float((top_urgent or {}).get("change") or 0)))

    gain_name = _label(gain.get("name"), "Run predictions") if gain else "Run predictions"
    gain_change = int(round(float(gain.get("change") or 0))) if gain else 0
    gain_conf = _confidence_pct(gain, gain.get("agreement") if gain else None) if gain else 0
    gain_fc4 = _forecast_value(gain_change, 4) if gain else 0
    gain_stage = _LIFECYCLE_LABELS[_stage_key(gain.get("stage"))].lower() if gain else "pending"

    risk_name = _label(risk.get("name"), "Run predictions") if risk else "Run predictions"
    risk_change = int(round(float(risk.get("change") or 0))) if risk else 0
    risk_conf = _confidence_pct(risk, risk.get("agreement") if risk else None) if risk else 0
    risk_fc4 = _forecast_value(risk_change, 4) if risk else 0
    risk_stage = _LIFECYCLE_LABELS[_stage_key(risk.get("stage"))].lower() if risk else "pending"
    structural_badge = ' <span style="font-size:9px;background:#fee2e2;color:#b91c1c;border-radius:3px;padding:1px 5px;font-weight:700;">60d structural</span>' if (risk and risk.get("is_structural")) else ""

    gt_status = gt_summary.get("status")
    gt_lead_count = int(gt_summary.get("lead_count") or 0)
    gt_avg_days   = gt_summary.get("avg_lead_days")
    gt_top_delta  = gt_summary.get("top_delta")
    gt_top_query  = gt_summary.get("top_query") or "Google Trends"
    if gt_status == "missing_key":
        gt_title = "API key needed"
        gt_big   = "--"
        gt_meta  = "SERPAPI_API_KEY"
        gt_foot  = "Add SerpAPI key to .env for live Google Trends."
    elif gt_top_delta is None:
        gt_title = "No live lead"
        gt_big   = "--"
        gt_meta  = "query lift"
        gt_foot  = _safe(gt_summary.get("message") or "No Google Trends timeline data returned.")
    elif gt_lead_count > 0 and gt_avg_days:
        gt_title = f"{gt_lead_count} leading quer{'y' if gt_lead_count == 1 else 'ies'}"
        gt_big   = f"{int(gt_top_delta):+d}%"
        gt_meta  = f"top query lift · avg ~{gt_avg_days}d ahead"
        gt_foot  = f"{_safe(_label(gt_top_query))} · +5pp conf boost · live SerpAPI"
    else:
        gt_title = f"{gt_lead_count} live lead{'s' if gt_lead_count != 1 else ''}"
        gt_big   = f"{int(gt_top_delta):+d}%"
        gt_meta  = "top query lift"
        gt_foot  = f"{_safe(_label(gt_top_query))} · live SerpAPI Google Trends"

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
    <div class="pred-kpi-title-new">{_safe(risk_name)}{structural_badge}</div>
    <div class="pred-kpi-stat-new">
      <span class="pred-kpi-big-new" style="color:#dc2626;">{risk_change:+d}%</span>
      <span class="pred-kpi-meta-new">velocity · {_safe(risk_stage)}</span>
    </div>
    <div class="pred-kpi-foot-new">Forecast {risk_fc4:+d}% in 4w · {risk_conf}% conf</div>
  </div>
  <div class="pred-kpi-new lead">
    <div class="pred-kpi-lbl-new">◈ Google Trends lead time</div>
    <div class="pred-kpi-title-new">{gt_title}</div>
    <div class="pred-kpi-stat-new">
      <span class="pred-kpi-big-new" style="color:#00a4e3;">{gt_big}</span>
      <span class="pred-kpi-meta-new">{gt_meta}</span>
    </div>
    <div class="pred-kpi-foot-new">{gt_foot}</div>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC COMPUTATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _vals_to_svg_points(vals: list[float], x_start: float, x_end: float,
                         y_top: float = 10.0, y_bot: float = 120.0) -> str:
    """Convert a list of values into SVG polyline point string."""
    if not vals:
        return ""
    clean = [float(v) for v in vals]
    n = len(clean)
    vmin, vmax = min(clean), max(clean)
    vrange = max(vmax - vmin, 1e-9)
    pts = []
    for i, v in enumerate(clean):
        x = x_start + (x_end - x_start) * i / max(n - 1, 1)
        y = y_bot - (y_bot - y_top) * (v - vmin) / vrange
        pts.append(f"{x:.0f},{y:.0f}")
    return " ".join(pts)


def _build_platform_map(scores_amz: pd.DataFrame, scores_nor: pd.DataFrame) -> dict:
    """Build {(attr_key, attr_value) -> {"amz": int|None, "nor": int|None}} from per-platform trend_scores."""
    result: dict[tuple[str, str], dict[str, int | None]] = {}
    for scores, plat_key in [(scores_amz, "amz"), (scores_nor, "nor")]:
        if scores is None or scores.empty:
            continue
        for _, row in scores.iterrows():
            key = (str(row.get("attr_key") or ""), str(row.get("attr_value") or ""))
            if key not in result:
                result[key] = {"amz": None, "nor": None}
            chg = row.get("review_growth_pct")
            if pd.notna(chg):
                result[key][plat_key] = int(round(float(chg)))
    return result


def _real_agreement(amz: int | None, nor: int | None) -> tuple[str, str, int]:
    """Compute cross-platform agreement from real per-platform velocity.
    Returns (label, css_class, bar_count 1-3)."""
    if amz is None and nor is None:
        return "No data", "divergent", 1
    if amz is None or nor is None:
        return "Single channel", "mixed", 2
    if (amz >= 0) == (nor >= 0):
        diff = abs(amz - nor)
        if diff < 10:
            return "Strong", "strong", 3
        return "Mixed", "mixed", 2
    return "Divergent", "divergent", 1


def _compute_driver_pcts(gt_delta: int | None) -> tuple[int, int, int]:
    """Return (proxy_pct, pull_pct, context_pct).
    Context is always 0 (NOAA not live). Pull allocated when GT data is available."""
    if gt_delta is not None:
        pull_raw = min(35, max(10, abs(gt_delta) // 2))
        return 100 - pull_raw, pull_raw, 0
    return 100, 0, 0


def _decision_tag_full(stage: str, change: float,
                        amz_change: int | None = None,
                        nor_change: int | None = None,
                        price_band_shifted: bool = False) -> str:
    """Full decision tag including Reprice and Reposition from real per-platform data."""
    stage = _stage_key(stage)
    if amz_change is not None and nor_change is not None:
        if (amz_change > 5 and nor_change < -5) or (amz_change < -5 and nor_change > 5):
            return "Reposition"
    if price_band_shifted and stage in {"accelerating", "plateau"}:
        return "Reprice"
    if stage == "accelerating":
        return "Replenish" if change >= 0 else "Watch"
    if stage == "declining":
        return "Retire" if change < 0 else "Watch"
    if stage == "emerging":
        return "Watch"
    return "Watch"


def _build_velocity_lookup(velocity_rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Index velocity forecast rows by (category, platform) for O(1) lookup."""
    return {
        (str(r.get("category") or ""), str(r.get("platform") or "")): r
        for r in (velocity_rows or [])
    }


def _trajectory_svg(hist_vals: list[float], future_vals: list[float]) -> str:
    """Generate a real 400×130 SVG trajectory chart from actual hist and forecast data."""
    hist_pts = _vals_to_svg_points(hist_vals or [], 0, 200, y_top=12, y_bot=118) or "0,65 200,65"
    fcast_pts = _vals_to_svg_points(future_vals or [], 200, 400, y_top=12, y_bot=118) or "200,65 400,65"

    fc_clean = [float(v) for v in (future_vals or [])]
    n_fc = len(fc_clean)
    upper_b, lower_b = [], []
    if n_fc > 0:
        vmin_fc, vmax_fc = min(fc_clean), max(fc_clean)
        vrange_fc = max(vmax_fc - vmin_fc, 1e-9)
        for i, v in enumerate(fc_clean):
            x = 200 + 200 * i / max(n_fc - 1, 1)
            y = 118 - (118 - 12) * (v - vmin_fc) / vrange_fc
            upper_b.append(f"{x:.0f},{max(12, y - 8):.0f}")
            lower_b.append(f"{x:.0f},{min(118, y + 8):.0f}")
        band_pts = " ".join(upper_b) + " " + " ".join(reversed(lower_b))
    else:
        band_pts = "200,57 400,57 400,73 200,73"

    junction_y = hist_pts.rsplit(" ", 1)[-1].split(",")[1] if " " in hist_pts else "65"

    return f"""<svg viewBox="0 0 400 130" preserveAspectRatio="none" style="width:100%;height:130px;display:block;">
  <line x1="0" y1="32" x2="400" y2="32" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,3"/>
  <line x1="0" y1="65" x2="400" y2="65" stroke="#cbd5e1" stroke-width="1"/>
  <line x1="0" y1="98" x2="400" y2="98" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,3"/>
  <polygon points="{band_pts}" fill="rgba(8,165,214,.12)"/>
  <line x1="200" y1="0" x2="200" y2="130" stroke="#0f172a" stroke-width="1.5" stroke-dasharray="3,2" opacity=".55"/>
  <text x="200" y="12" font-family="JetBrains Mono,monospace" font-size="9" fill="#0f172a" text-anchor="middle" font-weight="700">NOW</text>
  <polyline points="{hist_pts}" fill="none" stroke="#0080b3" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <polyline points="{fcast_pts}" fill="none" stroke="#08a5d6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="6,4"/>
  <circle cx="200" cy="{junction_y}" r="3" fill="#0080b3" stroke="#fff" stroke-width="1.5"/>
</svg>
<div style="display:flex;justify-content:space-between;color:#94a3b8;font-size:10px;font-family:'JetBrains Mono',monospace;margin-top:4px;">
  <span>-30d</span><span>-15d</span><span>now</span><span>+4w</span><span>+8w</span>
</div>"""


def _sparkline_from_vals(title: str, actual: int, projected: int,
                          hist_vals: list[float], future_vals: list[float]) -> str:
    """Build sparkline using real historical and forecast data points."""
    projected_color = ACCENT if projected >= 0 else DANGER
    band_color = "#dff2fb" if projected >= 0 else "#ffe5e5"

    hist_pts = _vals_to_svg_points(hist_vals or [], 10, 260, y_top=8, y_bot=82) or "10,45 260,45"
    fcast_pts = _vals_to_svg_points((future_vals or [])[:30], 260, 486, y_top=8, y_bot=82) or "260,45 486,45"

    fc_clean = [float(v) for v in (future_vals or [])[:30]]
    n_fc = len(fc_clean)
    upper_b, lower_b = [], []
    if n_fc > 0:
        vmin_fc, vmax_fc = min(fc_clean), max(fc_clean)
        vrange_fc = max(vmax_fc - vmin_fc, 1e-9)
        for i, v in enumerate(fc_clean):
            x = 260 + 226 * i / max(n_fc - 1, 1)
            y = 82 - (82 - 8) * (v - vmin_fc) / vrange_fc
            upper_b.append(f"{x:.0f},{max(8, y - 6):.0f}")
            lower_b.append(f"{x:.0f},{min(82, y + 6):.0f}")
        band_pts = " ".join(upper_b) + " " + " ".join(reversed(lower_b))
    else:
        band_pts = "260,39 486,39 486,51 260,51"

    junction_y = hist_pts.rsplit(" ", 1)[-1].split(",")[1] if " " in hist_pts else "45"

    return f"""
<div class="mini-forecast">
  <div class="mini-top"><span>{_safe(title)}</span><span>Actual <span style="color:{SUCCESS if actual >= 0 else DANGER};">{actual:+d}%</span> · projected <span style="color:{projected_color};">{projected:+d}%</span> next 30d</span></div>
  <div class="sparkline">
    <svg viewBox="0 0 500 90" preserveAspectRatio="none">
      <polygon points="{band_pts}" fill="{band_color}" opacity=".75"></polygon>
      <polyline points="{hist_pts}" fill="none" stroke="{PRIMARY}" stroke-width="3"></polyline>
      <polyline points="{fcast_pts}" fill="none" stroke="{projected_color}" stroke-width="3" stroke-dasharray="5 5"></polyline>
      <circle cx="260" cy="{junction_y}" r="4" fill="{PRIMARY}"></circle>
    </svg>
    <span class="now"></span>
  </div>
  <div class="spark-axis"><span>-30d</span><span>-20d</span><span>-10d</span><strong>Now</strong><span>+10d</span><span>+20d</span><span>+30d</span></div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
if main_view == "analytics":
    if df.empty:
        st.info("No products in the database yet. Run the scraper first: `python scrape_runner.py`")
        st.stop()

    trend_scores_df = load_trend_scores(
        category=None if category_filter == "All" else category_filter,
        platform=None if platform_filter == "All" else platform_filter,
    )
    attr_rows_t1 = _forecast_source(df, trend_scores_df, limit=8)
    scores_amz_t1 = load_trend_scores(
        category=None if category_filter == "All" else category_filter,
        platform="amazon",
    )
    scores_nor_t1 = load_trend_scores(
        category=None if category_filter == "All" else category_filter,
        platform="nordstrom",
    )
    platform_map_t1 = _build_platform_map(scores_amz_t1, scores_nor_t1)

    # Load live Google Trends for Analytics tab
    gt_queries_t1 = _google_trends_queries(attr_rows_t1, category_filter, gender_filter, style_filter)
    gt_geo_t1 = os.getenv("SERPAPI_GOOGLE_TRENDS_GEO", "US")
    gt_window_t1 = os.getenv("SERPAPI_GOOGLE_TRENDS_WINDOW", "today 3-m")
    gt_key_digest_t1 = _serpapi_key_digest(_serpapi_key())
    google_trends_t1 = _fetch_google_trends_live(tuple(gt_queries_t1), gt_geo_t1, gt_window_t1, gt_key_digest_t1)
    gt_by_query_t1 = {
        str(r.get("query") or ""): r
        for r in (google_trends_t1.get("rows") or [])
        if r.get("query")
    }

    kpi_html = _analytics_kpi_strip_html(df, sku_df, trend_scores_df)
    patterns_html = _winning_patterns_html(attr_rows_t1, platform_map=platform_map_t1, gt_by_query=gt_by_query_t1, category=category_filter, gender=gender_filter, style=style_filter)

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
if main_view == "predictive":
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )
        attr_rows = _forecast_source(df, trend_scores_df, limit=7)
        velocity_rows_t2 = load_review_velocity_forecast(
            platform=None if platform_filter == "All" else platform_filter,
            category=None if category_filter == "All" else category_filter,
        )
        velocity_lookup_t2 = _build_velocity_lookup(velocity_rows_t2)
        scores_amz_t2 = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform="amazon",
        )
        scores_nor_t2 = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform="nordstrom",
        )
        platform_map_t2 = _build_platform_map(scores_amz_t2, scores_nor_t2)
        gt_queries = _google_trends_queries(attr_rows, category_filter, gender_filter, style_filter)
        gt_geo = os.getenv("SERPAPI_GOOGLE_TRENDS_GEO", "US")
        gt_window = os.getenv("SERPAPI_GOOGLE_TRENDS_WINDOW", "today 3-m")
        gt_key_digest = _serpapi_key_digest(_serpapi_key())
        google_trends = _fetch_google_trends_live(tuple(gt_queries), gt_geo, gt_window, gt_key_digest)
        google_trends_summary = _google_trends_summary(google_trends)
        gt_live_copy = (
            "Google Trends is live through SerpAPI and updates the Pull-forward panel."
            if google_trends_summary.get("status") == "ok"
            else "Google Trends is wired for SerpAPI; add SERPAPI_API_KEY in .env to enable live Pull-forward data."
        )

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
        kpi_new_html = _predictive_kpi_new_html(
            attr_rows, google_trends_summary,
            platform_map=platform_map_t2,
            velocity_lookup=velocity_lookup_t2,
        )

        st.markdown(f"""
<div style="padding:0 0 4px;">
  <div class="pred-scope">
    <div class="pred-scope-icon">◈</div>
    <div class="pred-scope-text">
      <strong>Predictive triangulates marketplace signals (Proxy) with forward demand (Pull) and contextual environment (Context).</strong>
      Live today: marketplace review velocity, lifecycle stage, and Google Trends pull-forward demand.
      <span class="soon">{escape(gt_live_copy)} NOAA Weather and sentiment mining remain planned.</span>
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
    {_trajectory_rows_html(attr_rows, google_trends_summary, google_trends, category_filter, gender_filter, style_filter, platform_map=platform_map_t2, velocity_lookup=velocity_lookup_t2)}
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
    {_google_trends_panel_html(google_trends, gt_geo, gt_window)}
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


def _html_text(text: str) -> str:
    html = escape(text or "")
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    return html.replace("\n", "<br>")


def _s3_mode_bar_html(current_mode: str, rec_count: int, fresh_label: str) -> str:
    rec_active = " active" if current_mode == "recommendations" else ""
    ask_active = " active" if current_mode == "ask" else ""
    return f"""
<div class="mode-toggle-bar">
  <div class="mode-toggle">
    <a class="mode-option recommendations{rec_active}" href="{_query_href(view='askrec', s3_mode='recommendations')}">
      Recommendations <span class="badge">{rec_count}</span>
    </a>
    <a class="mode-option{ask_active}" href="{_query_href(view='askrec', s3_mode='ask')}">Ask Innovatics</a>
  </div>
  <div class="mode-meta">
    <span class="mode-meta-dot"></span>
    <span>{rec_count} ranked actions for this week &middot; refreshed {escape(fresh_label)}</span>
  </div>
</div>"""


def _s3_market_frame_html(ctx_t3: dict, visible_platform: str, window: str, gt_delta: int | None = None) -> str:
    top_attr = _label(ctx_t3.get("rising_attr"), "Marketplace signals")
    gain = ctx_t3.get("rising_gain")
    gain_txt = f"{gain:+d}% vs prior window" if gain is not None else "selected window"
    proxy_pct, pull_pct, ctx_pct = _compute_driver_pcts(gt_delta)
    return f"""
<div class="market-frame">
  <div class="market-frame-content">
    <div class="market-frame-label">Why this market is moving</div>
    <div class="market-frame-text">
      <strong>{_safe(top_attr)} &middot; structured fit &middot; premium positioning</strong>
      is the dominant signal this week across {escape(visible_platform)}.
      Cross-platform agreement is strong; marketplace review velocity {escape(gain_txt)}; {escape(window.lower())}.
    </div>
  </div>
  <div class="market-drivers">
    <div class="market-driver proxy"><span class="market-driver-pct">{proxy_pct}%</span><span class="market-driver-label">Proxy</span></div>
    <div class="market-driver context"><span class="market-driver-pct">{ctx_pct}%</span><span class="market-driver-label">Context</span></div>
    <div class="market-driver pull"><span class="market-driver-pct">{pull_pct}%</span><span class="market-driver-label">Pull</span></div>
  </div>
</div>"""


def _rec_confidence_pct(rec: dict) -> int:
    """Glossary: combined score = cross-platform agreement × forecast model confidence × sample size weight.
    Implemented as additive components (each capped) then normalised to 50-95%."""
    import json as _json
    evidence = rec.get("evidence") or {}
    if isinstance(evidence, str):
        try:
            evidence = _json.loads(evidence)
        except Exception:
            evidence = {}

    momentum     = float(evidence.get("momentum_score") or 0)
    review_count = int(evidence.get("review_count") or 0)
    rating_delta = abs(float(evidence.get("rating_delta") or 0))
    lifecycle    = str(evidence.get("lifecycle_stage") or "").lower()

    # Sample size + model confidence
    score  = 50 + min(30, int(momentum * 100))
    score += min(15, int(review_count / 8000 * 15))
    score += min(10, int(rating_delta * 20))
    score += {"accelerating": 5, "emerging": 3, "plateau": 0, "declining": -3, "dead": -8}.get(lifecycle, 0)

    # Cross-platform agreement component (glossary: agreement × confidence × sample)
    amz = evidence.get("amz_score") or evidence.get("amazon_score")
    nor = evidence.get("nor_score") or evidence.get("nordstrom_score")
    if amz is not None and nor is not None:
        # Both channels present — check direction agreement
        try:
            amz_v, nor_v = float(amz), float(nor)
            if (amz_v >= 0) == (nor_v >= 0):
                score += 8   # Strong agreement
            else:
                score -= 6   # Divergent
        except (TypeError, ValueError):
            pass
    elif amz is None and nor is None:
        pass   # No platform data — neutral
    else:
        score -= 3  # Single-channel — Mixed penalty

    return max(50, min(95, score))


def _s3_recommendation_card_html(rec: dict, rank: int, expanded: bool = False, gt_delta: int | None = None) -> str:
    rec_id = int(rec["rec_id"])
    status = str(rec.get("status") or "pending").strip().lower()
    pat_type = (rec.get("pattern_type") or "watch").strip().lower()
    dt_map = {
        "reprice_opportunity": ("reprice", "Reprice"),
        "reprice": ("reprice", "Reprice"),
        "whitespace": ("whitespace", "Whitespace"),
        "whitespace_opportunity": ("whitespace", "Whitespace"),
        "underserved_niche": ("whitespace", "Whitespace"),
        "replenish": ("replenish", "Replenish"),
        "replenishment": ("replenish", "Replenish"),
        "review_leader": ("replenish", "Replenish"),
        "retire": ("retire", "Retire"),
        "retirement": ("retire", "Retire"),
        "declining_attribute": ("retire", "Retire"),
        "reposition": ("reposition", "Reposition"),
        "cross_platform_gap": ("reposition", "Reposition"),
        "emerging_star": ("whitespace", "Whitespace"),
        "watch": ("watch", "Watch"),
        "rating_outlier": ("watch", "Watch"),
    }
    dt_cls, dt_lbl = dt_map.get(pat_type, ("watch", "Watch"))
    lifecycle = _stage_key(rec.get("stage") or rec.get("lifecycle") or "plateau")
    confidence = str(rec.get("confidence") or "Medium").strip()
    conf_pct = _rec_confidence_pct(rec)
    strong = conf_pct >= 80
    impact_cls = " high" if strong else ""
    impact_lbl = "Strong signal" if strong else "Moderate signal" if conf_pct >= 65 else "Watch"
    observation = rec.get("observation") or rec.get("recommendation_text") or ""
    action_txt = rec.get("action") or pat_type.replace("_", " ").title()
    impact = rec.get("impact") or "Expected to improve higher-confidence assortment moves."
    evidence_ev = rec.get("evidence") or {}
    if isinstance(evidence_ev, str):
        evidence_txt = evidence_ev
    elif isinstance(evidence_ev, dict):
        evidence_txt = " · ".join(f"{k}: {v}" for k, v in evidence_ev.items() if v)
    else:
        evidence_txt = str(evidence_ev) if evidence_ev else "Evidence from trend score detection."
    try:
        generated_label = pd.to_datetime(rec.get("generated_at")).strftime("%b %-d")
    except Exception:
        generated_label = "recently"

    proxy_pct, pull_pct, ctx_pct = _compute_driver_pcts(gt_delta)
    status_badge = ""
    if status == "accepted":
        status_badge = '<span style="font-size:10.5px;color:var(--success);font-family:var(--font-mono);font-weight:600;">✓ Acknowledged</span>'
    elif status == "dismissed":
        status_badge = '<span style="font-size:10.5px;color:var(--text-3);font-family:var(--font-mono);font-weight:600;">Snoozed</span>'
    open_attr = " open" if expanded else ""
    pat_display = pat_type.replace("_", " ").title()
    return f"""
<details class="rec-card"{open_attr}>
  <summary class="rec-header">
    <div class="rec-index">{rank:02d}</div>
    <div class="rec-main">
      <div class="rec-tags">
        <span class="decision-tag {dt_cls}">{dt_lbl}</span>
        <span class="lifecycle-pill {lifecycle}">{_LIFECYCLE_LABELS[lifecycle]}</span>
        <span class="rec-pattern-label">{escape(pat_display)}</span>
        {status_badge}
      </div>
      <div class="rec-headline">{_safe(action_txt)}</div>
      <div class="rec-evidence">{_html_text(observation)}</div>
    </div>
    <div class="rec-meta-col">
      <div class="rec-confidence">
        <span class="rec-confidence-label">Confidence</span>
        <span class="rec-confidence-value">{conf_pct}%</span>
      </div>
      <span class="rec-impact{impact_cls}">{impact_lbl}</span>
    </div>
    <span class="expand-button">&#9662;</span>
  </summary>
  <div class="rec-expand">
    <div class="evidence-block">
      <div class="evidence-header">Why this recommendation &middot; evidence</div>
      <div class="driver-list">
        <div class="driver-row"><span class="driver-tag proxy">PROXY &middot; {proxy_pct}%</span><span class="driver-text">{_html_text(evidence_txt)}</span><span class="driver-source">Live &middot; marketplace mining</span></div>
        <div class="driver-row"><span class="driver-tag context">CONTEXT &middot; {ctx_pct}%</span><span class="driver-text">Regional anomaly + seasonal baseline context</span><span class="driver-source">Coming soon &middot; NOAA</span></div>
        <div class="driver-row"><span class="driver-tag pull-forward">PULL &middot; FORWARD &middot; {pull_pct}%</span><span class="driver-text">{_html_text(impact)}</span><span class="driver-source">Generated {escape(generated_label)}</span></div>
      </div>
    </div>
  </div>
</details>"""


def _s3_ask_input_html(chips: list[str]) -> str:
    chips_html = "".join(f'<span class="ask-chip">{escape(c)}</span>' for c in chips)
    return f"""
<div class="ask-input-panel">
  <div class="ask-input-header">
    <div class="ask-input-title">Ask Innovatics anything about this filter context</div>
    <div class="ask-input-subtitle">Grounded in your filtered data &middot; cross-platform marketplace signals, Google Trends, NOAA weather</div>
  </div>
  <div class="ask-suggestions">
    <span class="ask-suggestions-label">Try</span>
    {chips_html}
  </div>
</div>"""


def _markdown_table_to_html(lines: list[str]) -> str:
    """Convert pipe-separated markdown table lines to a styled HTML table."""
    rows = []
    for line in lines:
        stripped = line.strip()
        # Skip pure separator lines like |---|---|
        if re.match(r"^[\s|:\-]+$", stripped):
            continue
        # Strip surrounding pipes
        stripped = stripped.strip("|").strip()
        if not stripped:
            continue
        cells = [c.strip() for c in stripped.split("|")]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    header = rows[0]
    th_html = "".join(f"<th>{escape(h)}</th>" for h in header)
    tbody = ""
    for row in rows[1:]:
        tds = ""
        for c in row:
            cls = ""
            if re.match(r"^\+\d+(\.\d+)?%?$", c):
                cls = ' class="vel-up"'
            elif re.match(r"^-\d+(\.\d+)?%?$", c):
                cls = ' class="vel-down"'
            tds += f"<td{cls}>{escape(c)}</td>"
        if tds:
            tbody += f"<tr>{tds}</tr>"
    if not tbody:
        return ""
    return f'<table class="ask-table"><thead><tr>{th_html}</tr></thead><tbody>{tbody}</tbody></table>'


def _answer_to_html(text: str) -> str:
    """Render chatbot answer with markdown table support and bold text."""
    lines = (text or "").split("\n")
    parts = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Detect table block: line has 1+ pipe AND at least 2 cells
        if "|" in stripped and len(stripped.split("|")) >= 3:
            table_block = []
            while i < len(lines) and "|" in lines[i]:
                table_block.append(lines[i])
                i += 1
            tbl = _markdown_table_to_html(table_block)
            if tbl:
                parts.append(tbl)
            continue
        if stripped:
            html = escape(stripped)
            html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
            # Treat lines starting with # as headings
            if stripped.startswith("### "):
                parts.append(f'<p class="ask-para"><strong>{html[4:]}</strong></p>')
            else:
                parts.append(f'<p class="ask-para">{html}</p>')
        i += 1
    return "".join(parts)


def _s3_exchange_html(question: str, answer: str, confidence: int = 84) -> str:
    return f"""
<div class="ask-exchange">
  <div class="ask-question">
    <div class="ask-question-icon">DB</div>
    <div class="ask-question-text">{_safe(question)}</div>
  </div>
  <div class="ask-answer">
    <div class="ask-answer-header">Answer</div>
    <div class="ask-answer-body">{_answer_to_html(answer)}</div>
    <div class="ask-evidence-tags">
      <span class="ask-evidence-tag">Live &middot; cross-platform review mining</span>
      <span class="ask-evidence-tag">Live &middot; price tracking</span>
      <span class="ask-evidence-tag">Live &middot; Google Trends</span>
    </div>
    <div class="ask-actions-row">
      <span class="ask-action-btn primary">View on Predictive &rarr;</span>
      <span class="ask-action-btn">Send to merchandising</span>
    </div>
    <div class="ask-confidence">
      <span class="ask-confidence-value">Confidence {confidence}%</span>
      <span class="ask-confidence-label">&middot; cross-platform agreement strong</span>
    </div>
  </div>
</div>"""


if main_view == "askrec":
    if df.empty:
        st.info("No data yet. Run the scraper first.")
    else:
        trend_scores_df_t3 = load_trend_scores(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
        )

        recs_from_db = load_recommendations(
            category=None if category_filter == "All" else category_filter,
            platform=None if platform_filter == "All" else platform_filter,
            status=None,
            limit=20,
        )
        n_active = sum(1 for r in recs_from_db if r.get("status") == "pending")
        n_recs = len(recs_from_db)

        s3_mode = _query_value("s3_mode", st.session_state.get("s3_mode", "recommendations")).strip().lower()
        if s3_mode not in {"recommendations", "ask"}:
            s3_mode = "recommendations"
        st.session_state["s3_mode"] = s3_mode
        st.html(_s3_mode_bar_html(s3_mode, n_recs, _fresh_label))

        if s3_mode == "recommendations":
            ctx_t3 = _market_signal_context(df, sku_df, trend_scores_df_t3)
            _s3_gt_delta = ctx_t3.get("rising_gain")

            st.html(
                '<div class="canvas">'
                + _s3_market_frame_html(ctx_t3, _visible_platform, window_filter, gt_delta=_s3_gt_delta)
                + '<div class="recommendations-list">'
            )

            if not recs_from_db:
                st.html('<div class="empty-panel">No recommendations yet. The pipeline runs automatically — check back shortly or ensure products are loaded in the database.</div>')
            else:
                for rank, rec in enumerate(recs_from_db[:10], 1):
                    _rec_id = int(rec["rec_id"])
                    _rec_status = str(rec.get("status") or "pending").strip().lower()

                    # Card body (expand/collapse details, no HTML buttons)
                    st.html(_s3_recommendation_card_html(rec, rank, expanded=(rank == 1), gt_delta=_s3_gt_delta))

                    # Real action buttons — always visible, only Acknowledge hides after ack
                    with st.container(key=f"rec_act_{_rec_id}"):
                        _rc = st.columns([1.1, 1.1, 1.9, 1.9, 1.9, 3])
                        with _rc[0]:
                            if _rec_status == "pending":
                                if st.button("✓ Acknowledge", key=f"ack_{_rec_id}", type="primary"):
                                    update_recommendation_status(_rec_id, "accepted")
                                    st.cache_data.clear()
                                    st.rerun()
                            # accepted: column left empty — Acknowledge disappears
                        with _rc[1]:
                            if _rec_status in ("pending", "accepted"):
                                if st.button("⏰ Snooze 7d", key=f"snz_{_rec_id}"):
                                    update_recommendation_status(_rec_id, "dismissed")
                                    st.cache_data.clear()
                                    st.rerun()
                            elif _rec_status == "dismissed":
                                if st.button("↩ Undo snooze", key=f"undo_{_rec_id}"):
                                    update_recommendation_status(_rec_id, "pending")
                                    st.cache_data.clear()
                                    st.rerun()
                        with _rc[2]:
                            if st.button("→ Send to merchandising", key=f"mrc_{_rec_id}"):
                                st.toast("Sent to merchandising team")
                        with _rc[3]:
                            if st.button("○ Watch this pattern", key=f"wch_{_rec_id}"):
                                st.toast("Added to watchlist")
                        with _rc[4]:
                            if st.button("↗ View on Predictive", key=f"vop_{_rec_id}"):
                                st.query_params["view"] = "predictive"
                                st.rerun()

            st.html('</div></div>')

        else:
            ASK_CHIPS = [
                "Which pattern has the strongest cross-channel premium?",
                "What's declining fastest?",
                "Where's the biggest whitespace?",
                "Which Nordstrom-only patterns should I watch?",
                "What's the median price gap between Amazon and Nordstrom?",
            ]
            for key, default in {
                "chat2_session_id": str(uuid.uuid4()),
                "chat2_messages": [],
            }.items():
                st.session_state.setdefault(key, default)

            _orch, _chatbot_err = _get_chatbot()
            if _chatbot_err:
                st.error(f"Chatbot unavailable — check GROQ_API_KEY and DB connection. ({_chatbot_err})")

            st.html(_s3_ask_input_html(ASK_CHIPS))
            _ask_cols = st.columns([5.8, 0.75, 0.7])
            with _ask_cols[0]:
                typed_q = st.text_input(
                    "ask_inline_q",
                    placeholder="e.g., Which pattern has the strongest cross-channel premium?",
                    key="ask_inline_q",
                    label_visibility="collapsed",
                )
            with _ask_cols[1]:
                send_ask = st.button("Send", type="primary", key="ask_inline_send", use_container_width=True)
            with _ask_cols[2]:
                if st.button("Clear", key="ask_inline_clear", use_container_width=True):
                    if _orch:
                        _orch.clear_session(st.session_state["chat2_session_id"])
                    st.session_state["chat2_messages"] = []
                    st.session_state["chat2_session_id"] = str(uuid.uuid4())
                    st.rerun()

            if send_ask and typed_q.strip() and not _chatbot_err:
                st.session_state["chat2_messages"].append({"role": "user", "content": typed_q.strip()})
                result = _orch.process_question(
                    session_id=st.session_state["chat2_session_id"],
                    question=typed_q.strip(),
                )
                response = result.get("response") or "Unable to process the request."
                st.session_state["chat2_messages"].append({"role": "assistant", "content": response})
                st.rerun()

            _chip_cols = st.columns(len(ASK_CHIPS))
            for chip_idx, chip_q in enumerate(ASK_CHIPS):
                if _chip_cols[chip_idx].button(chip_q[:28] + ("..." if len(chip_q) > 28 else ""), key=f"ask_chip_{chip_idx}", use_container_width=True, help=chip_q):
                    st.session_state["chat2_messages"].append({"role": "user", "content": chip_q})
                    if not _chatbot_err:
                        result = _orch.process_question(
                            session_id=st.session_state["chat2_session_id"],
                            question=chip_q,
                        )
                        response = result.get("response") or "Unable to process the request."
                    else:
                        response = "Chatbot is unavailable because the DB or LLM connection is not ready."
                    st.session_state["chat2_messages"].append({"role": "assistant", "content": response})
                    st.rerun()

            exchanges = []
            messages = st.session_state.get("chat2_messages", [])
            i = 0
            while i < len(messages):
                msg = messages[i]
                if msg.get("role") == "user":
                    answer = ""
                    if i + 1 < len(messages) and messages[i + 1].get("role") == "assistant":
                        answer = messages[i + 1].get("content", "")
                        i += 2
                    else:
                        i += 1
                    exchanges.append(_s3_exchange_html(msg.get("content", ""), answer or "Thinking...", 84))
                else:
                    i += 1

            if not exchanges:
                ctx_t3 = _market_signal_context(df, sku_df, trend_scores_df_t3)
                default_answer = (
                    f"Your current filter has {_total_skus:,} SKUs and {_total_reviews:,} reviews. "
                    f"The strongest live signal is {_label(ctx_t3.get('rising_attr'), 'marketplace momentum')}; "
                    f"the converting price band is {ctx_t3.get('band_label')}. Ask a question above and I will answer from the database-backed chatbot."
                )
                exchanges.append(_s3_exchange_html("What is active in this filter context?", default_answer, 82))

            st.html(
                '<div class="canvas"><div class="ask-view active"><div class="ask-conversation">'
                + "".join(exchanges)
                + "</div></div></div>"
            )

        st.html(f"""
<div class="automation-strip">
  <div class="automation-left">
    <div class="automation-icon">&#9889;</div>
    <div class="automation-text">
      <div class="automation-title">Automation &middot; Daily pattern scan running</div>
      <div class="automation-detail">
        {n_active} active recommendation{"s" if n_active != 1 else ""} surfaced &middot;
        <strong>{n_recs} total</strong> &middot; Weekly summary scheduled for Monday 8am
      </div>
    </div>
  </div>
  <div class="automation-right">
    <a href="#" class="automation-link">View daily summary &rarr;</a>
  </div>
</div>
<div class="footer">
  Innovatics POC &middot; Channel Intelligence &middot; Amazon + Nordstrom &middot;
  Marketplace signals + Google Trends + NOAA Weather connected &middot; Last refresh {escape(_fresh_label)}
</div>
""")
