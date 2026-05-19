"""
Channel Intelligence — Demo Technical Reference PDF
Run: python3 generate_demo_pdf.py
Output: Channel_Intelligence_Technical_Reference.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor
import datetime

# ── Palette ────────────────────────────────────────────────────────────────
NAVY      = HexColor("#0D1B2A")
BLUE      = HexColor("#1E88E5")
BLUE_LIGHT= HexColor("#E8F4FD")
TEAL      = HexColor("#00BFA5")
ORANGE    = HexColor("#FF6D00")
PURPLE    = HexColor("#7C4DFF")
RED       = HexColor("#E53935")
GREEN     = HexColor("#43A047")
GREY_DARK = HexColor("#424242")
GREY_MID  = HexColor("#757575")
GREY_LIGHT= HexColor("#F5F5F5")
WHITE     = colors.white
BLACK     = colors.black

W, H = A4   # 595 x 842 pt

OUTPUT = "Channel_Intelligence_Technical_Reference.pdf"

# ── Document setup ──────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=18*mm,  rightMargin=18*mm,
    topMargin=22*mm,   bottomMargin=20*mm,
    title="Channel Intelligence — Technical Reference",
    author="Innovatics",
)

styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

# Custom paragraph styles
H1  = S("H1",  fontName="Helvetica-Bold",  fontSize=20, textColor=NAVY,   spaceAfter=6, spaceBefore=10, leading=26)
H2  = S("H2",  fontName="Helvetica-Bold",  fontSize=14, textColor=BLUE,   spaceAfter=4, spaceBefore=14, leading=18)
H3  = S("H3",  fontName="Helvetica-Bold",  fontSize=11, textColor=NAVY,   spaceAfter=3, spaceBefore=8,  leading=15)
H4  = S("H4",  fontName="Helvetica-Bold",  fontSize=9,  textColor=GREY_DARK, spaceAfter=2, spaceBefore=5, leading=13)
BODY= S("BODY",fontName="Helvetica",       fontSize=9,  textColor=GREY_DARK, spaceAfter=3, spaceBefore=1, leading=14)
SMALL=S("SMALL",fontName="Helvetica",      fontSize=8,  textColor=GREY_MID,  spaceAfter=2, spaceBefore=0, leading=11)
CODE= S("CODE",fontName="Courier",         fontSize=8,  textColor=NAVY,      spaceAfter=2, spaceBefore=2, leading=11, backColor=GREY_LIGHT, leftIndent=6, rightIndent=6)
BOLD= S("BOLD",fontName="Helvetica-Bold",  fontSize=9,  textColor=GREY_DARK, spaceAfter=2, spaceBefore=2, leading=13)
TAG = S("TAG", fontName="Helvetica-Bold",  fontSize=8,  textColor=WHITE,     spaceAfter=0, spaceBefore=0, leading=11)

def p(text, style=BODY): return Paragraph(text, style)
def h1(t): return p(t, H1)
def h2(t): return p(t, H2)
def h3(t): return p(t, H3)
def h4(t): return p(t, H4)
def body(t): return p(t, BODY)
def small(t): return p(t, SMALL)
def code(t): return p(t, CODE)
def bold(t): return p(t, BOLD)
def sp(h=4): return Spacer(1, h)
def hr(): return HRFlowable(width="100%", thickness=0.5, color=GREY_LIGHT, spaceAfter=4, spaceBefore=4)
def hr2(): return HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=6, spaceBefore=4)

# ── Table helpers ──────────────────────────────────────────────────────────
def schema_table(rows, col_widths=None):
    cw = col_widths or [38*mm, 28*mm, 95*mm]
    t = Table(rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  8),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GREY_LIGHT]),
        ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#BDBDBD")),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
    ]))
    return t

def info_table(rows, col_widths=None):
    cw = col_widths or [50*mm, 115*mm]
    t = Table(rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  8.5),
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, BLUE_LIGHT]),
        ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#BDBDBD")),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
    ]))
    return t

def formula_table(rows, col_widths=None):
    cw = col_widths or [45*mm, 120*mm]
    t = Table(rows, colWidths=cw, repeatRows=0)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), HexColor("#E3F2FD")),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",    (1,0), (1,-1), "Courier"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#BBDEFB")),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
    ]))
    return t

def badge_table(items, colors_list):
    cells = []
    for text, clr in zip(items, colors_list):
        cell = Paragraph(f"<b>{text}</b>", TAG)
        cells.append(cell)
    t = Table([cells], colWidths=[35*mm]*len(items))
    ts = TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                     ("ALIGN", (0,0),(-1,-1),"CENTER"),
                     ("TOPPADDING",(0,0),(-1,-1),3),
                     ("BOTTOMPADDING",(0,0),(-1,-1),3)])
    for i, clr in enumerate(colors_list):
        ts.add("BACKGROUND",(i,0),(i,0),clr)
        ts.add("ROUNDEDCORNERS",(i,0),(i,0),3)
    t.setStyle(ts)
    return t

# ── Page header / footer ───────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, H-14*mm, W, 14*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18*mm, H-9*mm, "Channel Intelligence  ·  Technical Reference")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W-18*mm, H-9*mm, f"Page {doc.page}")
    # Footer
    canvas.setFillColor(GREY_MID)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(18*mm, 10*mm, "Confidential — Innovatics")
    canvas.drawRightString(W-18*mm, 10*mm,
        f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.restoreState()

# ═══════════════════════════════════════════════════════════════════════════
# BUILD STORY
# ═══════════════════════════════════════════════════════════════════════════
story = []
A = story.append

# ── COVER ──────────────────────────────────────────────────────────────────
A(sp(60))
cover_title = Table(
    [[Paragraph(
        "<font color='#0D1B2A'><b>Channel Intelligence</b></font>",
        S("ct", fontName="Helvetica-Bold", fontSize=32, textColor=NAVY, leading=38, alignment=TA_CENTER)
    )],
    [Paragraph(
        "Technical Reference — Calculations, Models & Data Flow",
        S("ct2", fontName="Helvetica", fontSize=14, textColor=GREY_MID, leading=18, alignment=TA_CENTER)
    )],
    [Paragraph(
        "Analytics  ·  Predictive  ·  Ask & Recommendation",
        S("ct3", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE, leading=16, alignment=TA_CENTER)
    )]],
    colWidths=[W - 36*mm]
)
cover_title.setStyle(TableStyle([
    ("ALIGN",(0,0),(-1,-1),"CENTER"),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),8),
]))
A(cover_title)
A(sp(18))
A(HRFlowable(width="70%", thickness=2, color=TEAL, spaceAfter=18, spaceBefore=4))

meta = [
    ["Platform", "Fashion Retail SaaS POC"],
    ["Scope",    "3 Screens: Analytics · Predictive · Ask & Recommendation"],
    ["Database", "PostgreSQL — normalized fashion retail schema"],
    ["LLM",      "Groq API (Llama / Mixtral) via unified LLMClient"],
    ["Trends",   "SerpAPI Google Trends — live, per-query, cached 1 h"],
    ["Forecast", "Linear Regression (numpy.polyfit) on trend_scores"],
    ["Date",     datetime.datetime.now().strftime("%B %d, %Y")],
]
meta_t = Table(meta, colWidths=[45*mm, 110*mm])
meta_t.setStyle(TableStyle([
    ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
    ("FONTNAME",(1,0),(1,-1),"Helvetica"),
    ("FONTSIZE",(0,0),(-1,-1),9),
    ("TEXTCOLOR",(0,0),(0,-1),NAVY),
    ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE,GREY_LIGHT]),
    ("GRID",(0,0),(-1,-1),0.3,HexColor("#BDBDBD")),
    ("TOPPADDING",(0,0),(-1,-1),5),
    ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ("LEFTPADDING",(0,0),(-1,-1),8),
]))
A(meta_t)
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 0 — DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════
A(h1("0.  Database Schema"))
A(hr2())
A(body("All data originates from a single PostgreSQL instance. The tables below document every column, its type, and business meaning relevant to the Channel Intelligence application."))
A(sp(6))

A(h3("0.1  Core Tables"))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["products.product_id", "INTEGER PK", "Unique product identifier"],
    ["products.title", "TEXT", "Product display name"],
    ["products.brand_id", "FK → brands", "Linked brand"],
    ["products.category_id", "FK → categories", "Linked category (T-Shirts, Dresses…)"],
    ["products.url", "TEXT", "Source marketplace URL"],
    ["brands.brand_id / .name", "INT / TEXT", "Brand lookup (Nike, H&M, Zara…)"],
    ["categories.category_id / .name", "INT / TEXT", "Category name"],
    ["categories.gender", "TEXT", "Men / Women / Unisex"],
]))
A(sp(6))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["product_variants.variant_id", "INTEGER PK", "One row per SKU variant"],
    ["product_variants.product_id", "FK → products", "Parent product"],
    ["product_variants.color_id", "FK → colors", "Color lookup"],
    ["product_variants.size_id", "FK → sizes", "Size lookup"],
    ["product_variants.material_id", "FK → materials", "Material lookup (Cotton, Polyester…)"],
    ["product_variants.neck_type_id", "FK → neck_types", "Neck style (Crew, V-Neck, Polo…)"],
    ["product_variants.sleeve_type_id", "FK → sleeve_types", "Sleeve (Short, Long, Sleeveless…)"],
    ["product_variants.fit_id", "FK → fits", "Fit (Slim, Regular, Relaxed…)"],
    ["product_variants.pattern_id", "FK → patterns", "Pattern (Solid, Stripes, Floral…)"],
    ["product_variants.is_available", "BOOLEAN", "In-stock flag"],
    ["product_variants.price", "NUMERIC", "Listed price"],
    ["product_variants.currency", "TEXT", "Currency code (USD, GBP…)"],
]))
A(sp(6))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["reviews.review_id", "INTEGER PK", "Unique review aggregation row"],
    ["reviews.product_id", "FK → products", "Parent product"],
    ["reviews.rating_avg", "NUMERIC 1–5", "Average star rating (scraped)"],
    ["reviews.review_count", "INTEGER", "Total number of reviews"],
    ["reviews.comment_json", "JSONB", "Array of customer comment objects"],
]))
A(sp(6))

A(h3("0.2  Analytics & Trend Tables"))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["trend_scores.id", "INTEGER PK", "Unique trend observation"],
    ["trend_scores.category", "TEXT", "Category name (joins categories.name)"],
    ["trend_scores.attr_key", "TEXT", "Attribute dimension: color, material, fit, pattern…"],
    ["trend_scores.attr_value", "TEXT", "Attribute value: 'Blue', 'Cotton', 'Slim Fit'…"],
    ["trend_scores.platform", "TEXT", "Amazon / Nordstrom"],
    ["trend_scores.score", "NUMERIC 0–1", "Relative popularity score for this attr in this window"],
    ["trend_scores.gender", "TEXT", "Men / Women / Unisex — dimension filter"],
    ["trend_scores.style", "TEXT", "Casual / Formal / Sporty — dimension filter"],
    ["trend_scores.window_label", "TEXT", "Time window: 'Last 30 Days', 'Last 60 Days'…"],
    ["trend_scores.recorded_at", "TIMESTAMPTZ", "When this score was scraped/computed"],
]))
A(sp(6))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["velocity_snapshots.id", "INTEGER PK", "Per-attribute velocity observation"],
    ["velocity_snapshots.attr_key", "TEXT", "Attribute dimension"],
    ["velocity_snapshots.attr_value", "TEXT", "Attribute value"],
    ["velocity_snapshots.category", "TEXT", "Category filter"],
    ["velocity_snapshots.platform", "TEXT", "Amazon / Nordstrom"],
    ["velocity_snapshots.change_pct", "NUMERIC", "% change vs prior window (raw scrape delta)"],
    ["velocity_snapshots.snapshot_date", "DATE", "Date of this snapshot"],
]))
A(sp(6))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["price_intelligence.id", "INTEGER PK", "Per-platform price observation"],
    ["price_intelligence.category", "TEXT", "Category"],
    ["price_intelligence.platform", "TEXT", "Amazon / Nordstrom"],
    ["price_intelligence.price_band", "TEXT", "$0–25 / $25–50 / $50–100 / $100+"],
    ["price_intelligence.median_price", "NUMERIC", "Median listing price in that band"],
    ["price_intelligence.conversion_rate", "NUMERIC 0–1", "Estimated conversion rate"],
    ["price_intelligence.recorded_at", "TIMESTAMPTZ", "Observation timestamp"],
]))
A(sp(6))
A(schema_table([
    ["Table / Column", "Type", "Business Meaning"],
    ["recommendations.rec_id", "INTEGER PK", "Unique recommendation"],
    ["recommendations.pattern_type", "TEXT", "One of 6 pattern types (see §3.1)"],
    ["recommendations.category", "TEXT", "Category this rec applies to"],
    ["recommendations.platform", "TEXT", "Amazon / Nordstrom / Both"],
    ["recommendations.attr_key", "TEXT", "Attribute dimension"],
    ["recommendations.attr_value", "TEXT", "Attribute value"],
    ["recommendations.observation", "TEXT", "LLM-generated observation sentence"],
    ["recommendations.action", "TEXT", "Concrete brand action (LLM-generated)"],
    ["recommendations.impact", "TEXT", "Expected business impact (LLM-generated)"],
    ["recommendations.confidence", "TEXT", "High / Medium / Low (LLM-assessed)"],
    ["recommendations.status", "TEXT", "pending / accepted / dismissed"],
    ["recommendations.evidence", "JSONB", "Raw metrics blob: momentum_score, review_count, etc."],
    ["recommendations.created_at", "TIMESTAMPTZ", "When the rec was generated"],
]))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — TAB 1: ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════
A(h1("1.  Tab 1 — Analytics"))
A(hr2())
A(body(
    "The Analytics tab provides real-time market intelligence: trending attributes, "
    "cross-platform velocity, price band performance, and winning pattern signals. "
    "Every metric is computed live from the database and enriched with Google Trends data via SerpAPI."
))
A(sp(6))

A(h2("1.1  KPI Cards (Top Row)"))
A(body("Four headline KPIs are loaded by <b>load_kpi_summary()</b> in db.py, which queries multiple tables in one pass."))
A(sp(4))
A(info_table([
    ["KPI Card", "Source & Calculation"],
    ["Trending Attributes",
     "COUNT of distinct (attr_key, attr_value) pairs in trend_scores WHERE window_label = selected_window AND score rank is in top quartile. Filtered by gender / category / platform."],
    ["Avg Velocity",
     "AVG(change_pct) across all velocity_snapshots for the selected filters. Displayed as ±X%."],
    ["Price Band Leader",
     "The price_band row with highest conversion_rate in price_intelligence for the selected platform and category. Shows band label + conversion%."],
    ["Active Platforms",
     "COUNT(DISTINCT platform) from trend_scores matching current filters. Always 1 or 2 (Amazon / Nordstrom)."],
]))
A(sp(8))

A(h2("1.2  Trending Attributes Table"))
A(body("Loaded by <b>load_trend_attributes()</b>. Returns one row per (attr_key, attr_value, platform, category) tuple."))
A(sp(4))
A(schema_table([
    ["Column Displayed", "Source", "Calculation"],
    ["Attribute",   "trend_scores.attr_value", "Display value, e.g. 'Navy Blue'"],
    ["Category",    "trend_scores.category",   "Category name"],
    ["Platform",    "trend_scores.platform",   "Amazon / Nordstrom"],
    ["Score",       "trend_scores.score",      "Raw popularity score 0–1"],
    ["Window",      "trend_scores.window_label","Filter: Last 30 / 60 / 90 Days"],
    ["Change %",    "velocity_snapshots.change_pct", "Joined on (category, platform, attr_key, attr_value)"],
    ["Decision Tag","Computed — see §1.4",     "Reprice / Replenish / Retire / Reposition / Whitespace / Watch"],
], col_widths=[38*mm, 38*mm, 85*mm]))
A(sp(8))

A(h2("1.3  Platform Map — Cross-Platform Agreement"))
A(body("The <b>_build_platform_map()</b> helper pivots the trend_scores rows into a dict keyed by (attr_key, attr_value):"))
A(sp(4))
A(code("platform_map[(attr_key, attr_value)] = {'amz': score_int, 'nor': score_int}"))
A(sp(2))
A(body("It converts the 0–1 score to an integer 0–100 for readability. None means that platform had no score for that attribute in the selected window."))
A(sp(4))
A(formula_table([
    ["Agreement Type",  "Threshold"],
    ["Strong Agreement","abs(amz_score − nor_score) < 10  AND  both platforms have data"],
    ["Mixed",           "abs(amz_score − nor_score) 10–30  OR  one platform missing"],
    ["Divergent",       "abs(amz_score − nor_score) > 30  OR  only one platform present"],
]))
A(sp(4))
A(body("Implemented in <b>_real_agreement(amz, nor)</b> in app.py. Returns (label, icon, diff)."))
A(sp(8))

A(h2("1.4  Decision Tag Logic"))
A(body("Every attribute row receives one of six decision tags. Computed by <b>_decision_tag_full()</b>:"))
A(sp(4))
A(formula_table([
    ["Tag",         "Condition (evaluated in order)"],
    ["Replenish",   "change > 15%  AND  lifecycle in ('emerging', 'accelerating')"],
    ["Reprice",     "price_band_shifted=True  OR  (change > 5% AND amz vs nor spread > 20)"],
    ["Reposition",  "change < -10%  AND  lifecycle = 'plateau'"],
    ["Retire",      "change < -20%  OR  lifecycle = 'dead'"],
    ["Whitespace",  "amz_change OR nor_change is None (attribute on only one platform)"],
    ["Watch",       "Default when no strong signal (|change| ≤ 5%)"],
]))
A(sp(4))
A(body("Parameters: <i>stage</i> (lifecycle_stage from velocity row), <i>change</i> (velocity change_pct), "
       "<i>amz_change</i>, <i>nor_change</i> (per-platform velocity), <i>price_band_shifted</i> (bool)."))
A(sp(8))

A(h2("1.5  Winning Patterns Panel"))
A(body("Loaded by <b>load_winning_patterns()</b> — returns top-N attributes ranked by momentum score from recommendations.evidence JSONB. "
       "Three signals are combined per pattern:"))
A(sp(4))
A(info_table([
    ["Signal", "Source & Meaning"],
    ["PUSH (Platform Velocity)",
     "From velocity_snapshots.change_pct for Amazon or Nordstrom. "
     "Computed separately per platform then labeled: e.g. '+23% on Amazon, +18% on Nordstrom'."],
    ["PULL (Google Trends)",
     "Live SerpAPI call. Query constructed from attr_value + category. "
     "Returns delta_pct = ((current_interest − prior_interest) / prior_interest) × 100. "
     "Cached in Redis for 1 hour. Source: 'Live · SerpAPI Google Trends'."],
    ["CONTEXT (Weather/Seasonal)",
     "STATIC placeholder — NOAA API not integrated. Shows seasonal narrative text only. "
     "Not used in any calculation. Marked 'Static · NOAA not live'."],
]))
A(sp(8))

A(h2("1.6  Price Band Chart"))
A(body("Loaded by <b>load_price_band_performance()</b>. Queries price_intelligence grouped by price_band and platform."))
A(sp(4))
A(formula_table([
    ["Metric", "Calculation"],
    ["Median Price",     "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) over variants in that band"],
    ["Conversion Rate",  "price_intelligence.conversion_rate — scraped/estimated, stored directly"],
    ["Velocity",         "AVG(velocity_snapshots.change_pct) joined on matching category + platform + price_band"],
    ["Band Boundary",    "$0–25, $25–50, $50–100, $100+ — stored as price_intelligence.price_band text"],
]))
A(sp(8))

A(h2("1.7  Google Trends Integration (Analytics Tab)"))
A(body("The Analytics tab builds live GT queries via <b>_google_trends_queries()</b> using the top trending attributes from trend_scores. "
       "Function <b>_fetch_google_trends_live()</b> is called with:"))
A(sp(4))
A(formula_table([
    ["Parameter",   "Value"],
    ["queries",     "Up to 5 attribute + category combos, e.g. 'Navy Blue T-Shirts'"],
    ["geo",         "SERPAPI_GOOGLE_TRENDS_GEO env var, default 'US'"],
    ["time_window", "SERPAPI_GOOGLE_TRENDS_WINDOW env var, default 'today 3-m' (3 months)"],
    ["cache TTL",   "3600 seconds (1 hour) in Redis"],
]))
A(sp(4))
A(body("The result dict is indexed as <b>gt_by_query[query_string]</b> and passed to both "
       "_winning_patterns_html() and _trajectory_rows_html() to annotate PULL evidence."))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — TAB 2: PREDICTIVE
# ═══════════════════════════════════════════════════════════════════════════
A(h1("2.  Tab 2 — Predictive"))
A(hr2())
A(body(
    "The Predictive tab shows forecast trajectories for trending attributes, "
    "lifecycle stages, and projected velocity over 4-week and 8-week horizons. "
    "All forecasts use linear regression on historical trend_scores data."
))
A(sp(6))

A(h2("2.1  Forecast Model — Linear Regression"))
A(body("Implemented in <b>_linear_forecast()</b> (db.py). Uses <b>numpy.polyfit(degree=1)</b> on the historical score series."))
A(sp(4))
A(formula_table([
    ["Step", "Operation"],
    ["1. Input",     "Array of score values ordered by recorded_at ASC from trend_scores"],
    ["2. X axis",    "Integer indices [0, 1, 2, … n-1] representing time steps"],
    ["3. polyfit",   "numpy.polyfit(x, y, 1) → returns [slope, intercept]"],
    ["4. Extrapolate","future_score[t] = slope × (n + t) + intercept, clamped to [0, 1]"],
    ["5. % change",  "projected_change_pct = (future_score[horizon] − last_score) / last_score × 100"],
    ["6. 4-week",    "horizon = 4 data points (≈ 4 weeks if weekly snapshots)"],
    ["7. 8-week",    "horizon = 8 data points"],
]))
A(sp(4))
A(body("Returns from <b>load_review_velocity_forecast()</b>:"))
A(sp(2))
A(code("hist_vals: list[float]   # historical score series\nfuture_vals: list[float] # extrapolated future scores\nprojected_change_pct: float  # % from last hist to end of forecast\nslope: float             # regression slope (positive = accelerating)"))
A(sp(8))

A(h2("2.2  Trajectory Sparklines (SVG Charts)"))
A(body("Each attribute row in the Predictive tab renders a 400×130 SVG trajectory chart via <b>_trajectory_svg()</b> in app.py."))
A(sp(4))
A(info_table([
    ["SVG Component", "Data Source"],
    ["Blue polyline (historical)", "hist_vals — actual trend_scores from DB, scaled to SVG coordinate space"],
    ["Orange dashed polyline (forecast)", "future_vals — linear regression extrapolation"],
    ["X axis", "Time steps; historical and forecast segments separated by a vertical dashed divider"],
    ["Y axis", "Min-max scaled to SVG height: y = y_top + (1 − val/max_val) × (y_bot − y_top)"],
    ["Coordinate scaler", "_vals_to_svg_points(vals, x_start, x_end, y_top=10, y_bot=120)"],
]))
A(sp(4))
A(body("The 4-week / 8-week percentage forecasts shown in the table use:"))
A(sp(2))
A(code("fc4 = round(projected_change_pct × 28/30)   # ≈ 4-week\nfc8 = round(projected_change_pct × 56/30)   # ≈ 8-week"))
A(sp(4))
A(body("If no velocity data exists for a row, falls back to <b>_forecast_value(change, weeks)</b>:"))
A(sp(2))
A(code("_forecast_value(change, weeks) = change × (1 + 0.05 × weeks)  # linear extrapolation from change_pct"))
A(sp(8))

A(h2("2.3  Lifecycle Stage Classification"))
A(body("Lifecycle stages are derived from the regression slope and current score level. "
       "Stored in velocity_snapshots or computed on-the-fly:"))
A(sp(4))
A(formula_table([
    ["Stage",        "Condition"],
    ["Emerging",     "slope > 0.02  AND  score < 0.4  (rising, not yet mainstream)"],
    ["Accelerating", "slope > 0.02  AND  score ≥ 0.4  (mainstream and growing fast)"],
    ["Plateau",      "|slope| ≤ 0.02 (flat trend — score stable)"],
    ["Declining",    "slope < -0.02  AND  score > 0.1  (falling but still visible)"],
    ["Dead",         "slope < -0.02  AND  score ≤ 0.1  (nearly zero interest)"],
]))
A(sp(8))

A(h2("2.4  Confidence Score Bands"))
A(body("Each trajectory row displays a confidence band for the forecast. Computed in app.py <b>_rec_confidence_pct(rec)</b>:"))
A(sp(4))
A(formula_table([
    ["Component", "Calculation"],
    ["Base score",          "50 (always)"],
    ["Momentum contribution", "min(30, int(momentum_score × 100))  from evidence JSONB"],
    ["Review count contribution", "min(15, int(review_count / 8000 × 15))  from evidence JSONB"],
    ["Rating delta contribution", "min(10, int(abs(rating_delta) × 20))  from evidence JSONB"],
    ["Lifecycle bonus/penalty",   "+5 accelerating / +3 emerging / 0 plateau / −3 declining / −8 dead"],
    ["Final clamp", "max(50, min(95, sum))"],
]))
A(sp(4))
A(body("This ensures confidence is always between 50% and 95%, dynamically reflecting each recommendation's evidence strength."))
A(sp(8))

A(h2("2.5  Cross-Platform Velocity (Per-Platform)"))
A(body("Amazon and Nordstrom velocities are computed independently — never interpolated from each other. "
       "Both come from <b>load_velocity_by_platform()</b> which queries velocity_snapshots filtered by platform."))
A(sp(4))
A(formula_table([
    ["Metric", "Source"],
    ["Amazon velocity",    "velocity_snapshots WHERE platform = 'Amazon'  →  change_pct"],
    ["Nordstrom velocity", "velocity_snapshots WHERE platform = 'Nordstrom' → change_pct"],
    ["Agreement label",   "_real_agreement(amz_score, nor_score) — see §1.3"],
    ["Score diff badge",  "abs(amz_score − nor_score) displayed as diff integer"],
]))
A(sp(8))

A(h2("2.6  Google Trends — Predictive Tab"))
A(body("The Predictive tab independently calls <b>_fetch_google_trends_live()</b> for its own set of queries, "
       "built from the top-scoring attributes in the current filter context. "
       "Annotated as PULL evidence in trajectory row cards. Same Redis cache (TTL 1 h) shared with Analytics tab."))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — TAB 3: ASK & RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════
A(h1("3.  Tab 3 — Ask & Recommendation"))
A(hr2())
A(body(
    "The Ask & Recommendation tab combines an LLM-powered SQL chatbot with "
    "AI-generated, evidence-backed merchandising recommendations. "
    "Pattern detection runs on the DB; recommendations are drafted by the LLM and stored back to PostgreSQL."
))
A(sp(6))

A(h2("3.1  Pattern Detection — 6 Pattern Types"))
A(body("Implemented in <b>recommendations/pattern_detector.py</b>. Runs across all categories and platforms."))
A(sp(6))

patterns = [
    ("Emerging Star", TEAL,
     "emerging_star",
     "velocity_snapshots.change_pct > 20%\nAND trend_scores.score > 0.3\nAND review avg rating > 4.0",
     "momentum_score, rating_avg, review_count, lifecycle_stage",
     "Attribute rising fast with high reviews. Stock up and prioritize listing."),
    ("Declining Attribute", RED,
     "declining_attribute",
     "velocity_snapshots.change_pct < −15%\nAND trend_scores.score < 0.3\nAND review count falling",
     "momentum_score (negative), rating_delta, velocity_trend",
     "Attribute losing popularity. Reduce inventory, consider markdown."),
    ("Underserved Niche", PURPLE,
     "underserved_niche",
     "Present on only 1 platform\nAND score > 0.2\nAND competitor_count < threshold",
     "platform_count, score, competitor_gap",
     "High demand on one channel but absent on the other. Whitespace opportunity."),
    ("Review Leader", GREEN,
     "review_leader",
     "rating_avg ≥ 4.5\nAND review_count ≥ 500\nAND above-median velocity",
     "rating_avg, review_count, velocity_pct",
     "Top-rated attributes driving purchases. Double down on these variants."),
    ("Cross-Platform Gap", ORANGE,
     "cross_platform_gap",
     "abs(amz_score − nor_score) > 30\nAND both platforms have data",
     "amz_score, nor_score, score_diff",
     "Attribute popular on one platform but not the other. Reprice or reposition."),
    ("Rating Outlier", HexColor("#9C27B0"),
     "rating_outlier",
     "rating_avg < 3.5\nAND review_count > 200 (significant data)\nAND above-median listing count",
     "rating_avg, review_count, variant_count",
     "High visibility but poor ratings. Quality issue flag — reduce exposure."),
]

for (label, clr, key, conditions, evidence_fields, action) in patterns:
    A(KeepTogether([
        Table([[Paragraph(f"  {label}  ", S("ptag", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE))],],
              colWidths=[50*mm],
              style=TableStyle([("BACKGROUND",(0,0),(0,0),clr),
                                ("TOPPADDING",(0,0),(0,0),3),("BOTTOMPADDING",(0,0),(0,0),3),
                                ("LEFTPADDING",(0,0),(0,0),5)])),
        sp(2),
        info_table([
            ["Field", "Value"],
            ["Pattern key",     key],
            ["Detection conditions", conditions.replace("\n", "<br/>")],
            ["Evidence fields", evidence_fields],
            ["Default action",  action],
        ]),
        sp(6),
    ]))

A(sp(4))
A(h2("3.2  Pattern Detection Pipeline"))
A(body("Full pipeline in <b>recommendations/run_recommendations.py</b>:"))
A(sp(4))
A(formula_table([
    ["Step", "Operation"],
    ["1. Load patterns",     "detect_all_patterns() → list[dict] from pattern_detector.py"],
    ["2. Draft via LLM",     "llm_drafter.draft_all(patterns) — calls Groq API per pattern"],
    ["3. Store to DB",       "INSERT INTO recommendations (…) ON CONFLICT DO UPDATE"],
    ["4. Load for display",  "load_recommendations() from db.py → ordered by created_at DESC"],
]))
A(sp(8))

A(h2("3.3  LLM Recommendation Drafting (Groq API)"))
A(body("Each pattern is sent to the LLM with a structured system prompt requiring this exact output format:"))
A(sp(4))
A(code(
    "Observation: <data-backed observation>\n"
    "Action:      <concrete brand action>\n"
    "Reasoning:   <why this action follows from evidence>\n"
    "Evidence:    <2-3 cited metrics from evidence block>\n"
    "Impact:      <expected business impact in 4-8 weeks>\n"
    "Confidence:  High / Medium / Low"
))
A(sp(4))
A(body("Confidence is constrained by these LLM-level rules:"))
A(sp(2))
A(formula_table([
    ["LLM Confidence", "Required Conditions"],
    ["High",   "momentum_score > 0.20  AND  review_count > 2000  AND  lifecycle = emerging or accelerating"],
    ["Medium", "momentum_score 0.08–0.20  OR  review_count 500–2000  OR  lifecycle = plateau"],
    ["Low",    "momentum_score < 0.08  OR  conflicting signals  OR  lifecycle = dead/declining"],
]))
A(sp(4))
A(body("The LLM confidence text is stored in <b>recommendations.confidence</b>. The display confidence % (50–95) is "
       "independently computed by <b>_rec_confidence_pct()</b> from the evidence JSONB at render time (see §2.4)."))
A(sp(8))

A(h2("3.4  Recommendation Card UI"))
A(info_table([
    ["UI Element", "Data Source"],
    ["Rank badge",        "Position in ORDER BY created_at DESC (top 10 shown)"],
    ["Pattern type tag",  "recommendations.pattern_type → _PATTERN_LABELS dict"],
    ["Confidence %",      "_rec_confidence_pct(rec) — computed from evidence JSONB (§2.4)"],
    ["Observation text",  "recommendations.observation — LLM-generated, stored in DB"],
    ["Action text",       "recommendations.action — LLM-generated, stored in DB"],
    ["Impact text",       "recommendations.impact — LLM-generated, stored in DB"],
    ["Evidence bullets",  "recommendations.evidence JSONB — raw metrics"],
    ["Status badge",      "recommendations.status: pending / accepted / dismissed"],
    ["✓ Acknowledge btn", "Updates status → 'accepted' via UPDATE recommendations SET status"],
    ["⏰ Snooze 7d btn",  "Updates status → 'dismissed'; button changes to '↩ Undo snooze'"],
    ["→ Send to merch",   "st.toast notification (no DB write — demo mode)"],
    ["○ Watch pattern",   "st.toast notification (no DB write — demo mode)"],
    ["↗ View on Predictive","Sets st.query_params['view']='predictive', triggers st.rerun()"],
]))
A(sp(8))

A(h2("3.5  Ask Tab — SQL Chatbot"))
A(body("The Ask tab routes natural-language questions through an intent classifier to the SQL agent."))
A(sp(4))
A(info_table([
    ["Component", "Description"],
    ["Intent classifier",   "chatbot/tools/intent_classifier.py — LLM call, returns intent + confidence"],
    ["SQL generator",       "_generate_sql() in sql_agent.py — LLM generates SELECT query from schema context"],
    ["SQL validator",       "_validate_sql() — checks first token = SELECT, blocks INSERT/UPDATE/DROP/etc."],
    ["SQL executor",        "_execute_sql() — runs against PostgreSQL, caches result in Redis for 5 min"],
    ["Response generator",  "_build_response() — LLM formats query result as business-friendly Markdown"],
    ["Table renderer",      "_answer_to_html() + _markdown_table_to_html() — parses | pipe tables → HTML"],
    ["Chat history",        "format_history_for_prompt() — last 4 messages used as context for SQL gen"],
]))
A(sp(4))
A(formula_table([
    ["SQL Agent Step", "Detail"],
    ["1. Schema context",  "Full DB schema embedded in system prompt (see sql_agent.py _SQL_SYSTEM_PROMPT)"],
    ["2. History context", "Last 4 conversation turns prepended to user question"],
    ["3. LLM call",        "temperature=0 for deterministic SQL generation"],
    ["4. Cache key",       "SHA-256 of SQL string, first 32 chars → Redis TTL 300s (5 min)"],
    ["5. Row limit",       "LIMIT 50 enforced unless pure aggregation (COUNT/SUM/AVG/GROUP BY)"],
    ["6. Response LLM",    "temperature=0, max 15 rows shown, 120-word response cap"],
]))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — FULL DATA PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
A(h1("4.  End-to-End Data Pipeline"))
A(hr2())
A(sp(4))

pipeline_rows = [
    ["Stage", "Component", "Input", "Output", "Storage"],
    ["1. Scrape",
     "Scrapers (marketplace)",
     "Amazon / Nordstrom product pages",
     "Raw product, variant, review, price data",
     "products, product_variants, reviews, price_intelligence"],
    ["2. Score",
     "Score calculator",
     "variant counts per (attr, category, platform, window)",
     "Normalized popularity score 0–1",
     "trend_scores.score"],
    ["3. Velocity",
     "Velocity calculator",
     "trend_scores for current vs prior window",
     "change_pct per (attr, category, platform)",
     "velocity_snapshots.change_pct"],
    ["4. Forecast",
     "linear_forecast()\n(numpy.polyfit)",
     "hist_vals from trend_scores",
     "future_vals, projected_change_pct, slope",
     "In-memory (no table — computed at render)"],
    ["5. Patterns",
     "pattern_detector.py",
     "velocity_snapshots + trend_scores + reviews",
     "list[dict] — 6 pattern types",
     "In-memory → passed to LLM drafter"],
    ["6. LLM Draft",
     "llm_drafter.py\n(Groq API)",
     "Pattern dict with evidence JSONB",
     "Observation, Action, Impact, Confidence text",
     "recommendations table"],
    ["7. Display",
     "streamlit_app/app.py",
     "All tables + Redis cache + SerpAPI",
     "3-tab UI with charts, tables, buttons",
     "No write (read-only display)"],
]
t = Table(pipeline_rows, colWidths=[22*mm, 32*mm, 38*mm, 38*mm, 35*mm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND",   (0,0),(-1,0), NAVY),
    ("TEXTCOLOR",    (0,0),(-1,0), WHITE),
    ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
    ("FONTSIZE",     (0,0),(-1,0), 8),
    ("FONTNAME",     (0,1),(-1,-1),"Helvetica"),
    ("FONTSIZE",     (0,1),(-1,-1), 7.5),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GREY_LIGHT]),
    ("GRID",         (0,0),(-1,-1), 0.3, HexColor("#BDBDBD")),
    ("VALIGN",       (0,0),(-1,-1), "TOP"),
    ("TOPPADDING",   (0,0),(-1,-1), 3),
    ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ("LEFTPADDING",  (0,0),(-1,-1), 4),
]))
A(t)
A(sp(12))

A(h2("4.1  Caching Strategy"))
A(info_table([
    ["Cache Layer", "Key", "TTL", "Purpose"],
    ["Redis", "sql:<SHA256-32>",          "300s (5 min)",  "SQL query results — avoids re-running identical DB queries"],
    ["Redis", "gt:<queries-digest>",      "3600s (1 h)",   "Google Trends SerpAPI results — rate-limit protection"],
    ["Streamlit", "@st.cache_data",       "Per-session",   "DB calls in db.py — cleared on button actions"],
    ["Redis", "rec:<pattern>",            "1800s (30 min)","Recommendation drafts (if enabled)"],
]))
A(sp(12))

A(h2("4.2  Static vs. Dynamic — Summary"))
A(body("Per the Channel Intelligence glossary, only two data points are intentionally static:"))
A(sp(4))
A(info_table([
    ["Item", "Status", "Reason"],
    ["Weather / Seasonal context (NOAA)", "STATIC", "NOAA API not integrated — narrative text only, not used in any calculation"],
    ["Sentiment analysis scores", "STATIC", "No live NLP pipeline — comment_json stored but not processed at render time"],
    ["All trend scores", "DYNAMIC", "Queried live from PostgreSQL trend_scores per filter selection"],
    ["All velocity %", "DYNAMIC", "Queried live from velocity_snapshots"],
    ["Forecast sparklines", "DYNAMIC", "Generated from hist_vals/future_vals via numpy.polyfit at render"],
    ["Cross-platform agreement", "DYNAMIC", "Computed from live platform_map diff threshold"],
    ["Decision tags", "DYNAMIC", "Computed by _decision_tag_full() from live velocity + lifecycle"],
    ["Confidence scores", "DYNAMIC", "Computed by _rec_confidence_pct() from evidence JSONB"],
    ["Google Trends (PULL signal)", "DYNAMIC", "Live SerpAPI calls, 1h Redis cache"],
    ["LLM recommendations", "DYNAMIC", "Groq API-generated, stored in DB, fetched per session"],
    ["SQL chatbot answers", "DYNAMIC", "LLM generates SQL → live DB query → LLM formats response"],
]))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — FORMULA QUICK-REFERENCE
# ═══════════════════════════════════════════════════════════════════════════
A(h1("5.  Formula Quick-Reference"))
A(hr2())
A(sp(4))

A(h3("All Key Formulas at a Glance"))
A(formula_table([
    ["Formula Name", "Expression"],
    ["Linear forecast",       "y[t] = slope × (n + t) + intercept  (numpy.polyfit degree=1)"],
    ["Projected % change",    "(forecast_score − last_hist_score) / last_hist_score × 100"],
    ["4-week fc from monthly","projected_change_pct × 28 / 30"],
    ["8-week fc from monthly","projected_change_pct × 56 / 30"],
    ["SVG y-coordinate",      "y = y_top + (1 − val/max_val) × (y_bot − y_top)"],
    ["Google Trends delta%",  "(current_interest − prior_interest) / prior_interest × 100"],
    ["Confidence base",       "50 + min(30, momentum×100) + min(15, reviews/8000×15) + min(10, |Δrating|×20) + lifecycle_bonus"],
    ["Confidence clamp",      "max(50, min(95, score))"],
    ["Platform agreement",    "diff = abs(amz_score − nor_score);  <10 Strong, 10–30 Mixed, >30 Divergent"],
    ["KPI Avg Velocity",      "AVG(velocity_snapshots.change_pct) for selected filters"],
    ["Price band leader",     "argmax(conversion_rate) in price_intelligence per platform+category"],
    ["Pattern: Emerging Star","change_pct > 20%  AND  score > 0.3  AND  rating_avg > 4.0"],
    ["Pattern: Declining",    "change_pct < −15%  AND  score < 0.3"],
    ["Pattern: Underserved",  "platform_count = 1  AND  score > 0.2"],
    ["Pattern: Review Leader","rating_avg ≥ 4.5  AND  review_count ≥ 500"],
    ["Pattern: Cross-Gap",    "abs(amz_score − nor_score) > 30"],
    ["Pattern: Rating Outlier","rating_avg < 3.5  AND  review_count > 200"],
    ["SQL cache key",         "sha256(sql_string).hexdigest()[:32]"],
    ["Fallback forecast",     "_forecast_value(change, weeks) = change × (1 + 0.05 × weeks)"],
], col_widths=[55*mm, 110*mm]))

A(sp(12))
A(hr2())
A(sp(6))

A(body(
    "<b>Questions?</b>  All source code lives in streamlit_app/app.py (frontend), "
    "streamlit_app/db.py (all DB queries), recommendations/pattern_detector.py (6 pattern types), "
    "recommendations/llm_drafter.py (LLM prompt), and chatbot/tools/sql_agent.py (Ask tab)."
))

# ═══════════════════════════════════════════════════════════════════════════
# BUILD
# ═══════════════════════════════════════════════════════════════════════════
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"PDF written → {OUTPUT}")
