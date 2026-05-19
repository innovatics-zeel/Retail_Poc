"""
Channel Intelligence — Visual Demo Reference PDF
Every UI card is drawn as a mockup box, followed by its exact calculation.
Run: python3 generate_visual_pdf.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image
)
from reportlab.graphics.shapes import (
    Drawing, Rect, String, Line, Polygon, PolyLine, Group
)
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor, Color
import datetime, math

# ── Palette ────────────────────────────────────────────────────────────────
NAVY   = HexColor("#0D1B2A")
BLUE   = HexColor("#1E88E5")
BLUE_L = HexColor("#E3F2FD")
TEAL   = HexColor("#00BFA5")
TEAL_L = HexColor("#E0F7F4")
GREEN  = HexColor("#2E7D32")
GREEN_L= HexColor("#E8F5E9")
ORANGE = HexColor("#E65100")
ORANGE_L=HexColor("#FFF3E0")
RED    = HexColor("#C62828")
RED_L  = HexColor("#FFEBEE")
PURPLE = HexColor("#6A1B9A")
PURPLE_L=HexColor("#F3E5F5")
GREY_D = HexColor("#424242")
GREY_M = HexColor("#757575")
GREY_L = HexColor("#F5F5F5")
CARD_BG= HexColor("#FAFBFC")
BORDER = HexColor("#E2E8F0")
WHITE  = colors.white
BLACK  = colors.black

W, H = A4
OUTPUT = "Channel_Intelligence_Visual_Reference.pdf"

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=14*mm, rightMargin=14*mm,
    topMargin=20*mm, bottomMargin=16*mm,
    title="Channel Intelligence — Visual Demo Reference",
)

# ── Styles ──────────────────────────────────────────────────────────────────
def S(name, **kw): return ParagraphStyle(name, **kw)
H1   = S("H1",  fontName="Helvetica-Bold", fontSize=18, textColor=NAVY,   spaceAfter=4, spaceBefore=8,  leading=24)
H2   = S("H2",  fontName="Helvetica-Bold", fontSize=13, textColor=BLUE,   spaceAfter=3, spaceBefore=12, leading=17)
H3   = S("H3",  fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,   spaceAfter=2, spaceBefore=6,  leading=14)
BODY = S("BODY",fontName="Helvetica",      fontSize=8.5,textColor=GREY_D, spaceAfter=2, spaceBefore=1,  leading=13)
CODE = S("CODE",fontName="Courier",        fontSize=7.5,textColor=NAVY,   spaceAfter=1, spaceBefore=1,  leading=11, backColor=GREY_L, leftIndent=4)
BOLD = S("BOLD",fontName="Helvetica-Bold", fontSize=8.5,textColor=GREY_D, spaceAfter=2, spaceBefore=1,  leading=13)
SMALL= S("SMALL",fontName="Helvetica",     fontSize=7.5,textColor=GREY_M, spaceAfter=1, spaceBefore=0,  leading=11)
CTXT = S("CTXT",fontName="Helvetica",      fontSize=8,  textColor=GREY_M, spaceAfter=0, spaceBefore=0,  leading=11, alignment=TA_CENTER)

def p(t, s=BODY): return Paragraph(t, s)
def h1(t): return p(t, H1)
def h2(t): return p(t, H2)
def h3(t): return p(t, H3)
def body(t): return p(t, BODY)
def code(t): return p(t, CODE)
def bold(t): return p(t, BOLD)
def small(t): return p(t, SMALL)
def sp(h=4): return Spacer(1, h)
def hr(): return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3, spaceBefore=3)
def hr2(clr=BLUE): return HRFlowable(width="100%", thickness=1.5, color=clr, spaceAfter=4, spaceBefore=4)

# ── Page deco ───────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, H-12*mm, W, 12*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE); canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(14*mm, H-8*mm, "Channel Intelligence  ·  Visual Demo Reference")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(W-14*mm, H-8*mm, f"Page {doc.page}")
    canvas.setFillColor(GREY_M); canvas.setFont("Helvetica", 6.5)
    canvas.drawString(14*mm, 9*mm, "Confidential — Innovatics")
    canvas.drawRightString(W-14*mm, 9*mm, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    canvas.restoreState()

# ═══════════════════════════════════════════════
# DRAWING HELPERS
# ═══════════════════════════════════════════════
CW = W - 28*mm   # content width in points

def _card_drawing(height, bg=CARD_BG, border=BORDER, radius=6):
    """Base card drawing canvas."""
    d = Drawing(CW, height)
    r = Rect(0, 0, CW, height, rx=radius, ry=radius,
             fillColor=bg, strokeColor=border, strokeWidth=0.8)
    d.add(r)
    return d

def _label_pill(x, y, text, bg, fg=WHITE, w=None, h=14):
    g = Group()
    tw = w or (len(text)*5.5 + 10)
    g.add(Rect(x, y, tw, h, rx=4, ry=4, fillColor=bg, strokeColor=None))
    g.add(String(x+5, y+3.5, text, fontName="Helvetica-Bold", fontSize=6.5, fillColor=fg))
    return g

def _sparkline(x, y, w, h, vals, color=BLUE, dashed=False):
    if not vals or len(vals) < 2:
        return Group()
    mn, mx = min(vals), max(vals)
    rng = max(mx - mn, 1e-9)
    pts = []
    for i, v in enumerate(vals):
        px = x + w * i / (len(vals)-1)
        py = y + h * (v - mn) / rng
        pts.append(px); pts.append(py)
    g = Group()
    pl = PolyLine(pts, strokeColor=color, strokeWidth=1.5)
    if dashed:
        pl.strokeDashArray = [3, 2]
    g.add(pl)
    return g

def _bar_h(x, y, w, h, fill):
    return Rect(x, y, w, h, fillColor=fill, strokeColor=None)

# ── Formula table ───────────────────────────────────────────────────────────
def ftable(rows, cw=None):
    cw = cw or [42*mm, 121*mm]
    t = Table(rows, colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1), BLUE_L),
        ("FONTNAME",  (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (1,0),(1,-1), "Courier"),
        ("FONTSIZE",  (0,0),(-1,-1), 8),
        ("GRID",      (0,0),(-1,-1), 0.3, BORDER),
        ("VALIGN",    (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",(0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",(0,0),(-1,-1), 5),
    ]))
    return t

def itable(rows, cw=None, header_bg=NAVY):
    cw = cw or [50*mm, 113*mm]
    t = Table(rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), header_bg),
        ("TEXTCOLOR", (0,0),(-1,0), WHITE),
        ("FONTNAME",  (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0),(-1,0), 8),
        ("FONTNAME",  (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",  (0,1),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GREY_L]),
        ("GRID",      (0,0),(-1,-1), 0.3, BORDER),
        ("VALIGN",    (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",(0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",(0,0),(-1,-1), 5),
    ]))
    return t

# ═══════════════════════════════════════════════════════════════════════════
# CARD DRAWING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def draw_kpi_strip():
    """4 KPI tiles — Analytics top row."""
    H_card = 76
    d = Drawing(CW, H_card)
    # background
    d.add(Rect(0, 0, CW, H_card, rx=8, ry=8, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    tile_w = CW / 4
    labels  = ["Reviews captured", "Top style", "Top color", "Converting price band"]
    values  = ["124,832", "Crew Neck  · 38%", "Navy Blue  · 27%", "$24–32"]
    metas   = ["Across 8,441 SKUs · 30d", "Review share  +3.2%", "Share  +1.8%", "3.4× share index · med $28"]
    colors_ = [BLUE, TEAL, PURPLE, ORANGE]
    for i, (lbl, val, meta, clr) in enumerate(zip(labels, values, metas, colors_)):
        x0 = i * tile_w + 4
        if i < 3:
            d.add(Line(x0 + tile_w - 4, 10, x0 + tile_w - 4, H_card-10,
                       strokeColor=BORDER, strokeWidth=0.5))
        d.add(String(x0+8, H_card-18, lbl, fontName="Helvetica", fontSize=7, fillColor=GREY_M))
        d.add(String(x0+8, H_card-34, val, fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
        d.add(String(x0+8, H_card-48, meta, fontName="Helvetica", fontSize=7, fillColor=GREY_M))
        # accent line
        d.add(Rect(x0+6, H_card-54, 22, 2, fillColor=clr, strokeColor=None))
    return d

def draw_winning_patterns_card():
    """Winning Patterns row with signal pills."""
    H_card = 115
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=8, ry=8, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    # header
    d.add(Rect(0, H_card-22, CW, 22, rx=8, ry=8, fillColor=NAVY, strokeColor=None))
    d.add(Rect(0, H_card-22, CW, 11, fillColor=NAVY, strokeColor=None))
    d.add(String(10, H_card-15, "Winning patterns · last 30 days", fontName="Helvetica-Bold", fontSize=9, fillColor=WHITE))
    d.add(String(10, H_card-21, "Pattern-level velocity × cross-platform agreement × lifecycle stage", fontName="Helvetica", fontSize=7, fillColor=HexColor("#94A3B8")))
    # row
    y0 = 12
    attrs = [("Crew Neck", "Cotton", "+23%", "Strong", "Replenish"),
             ("Navy Blue", "Fit",    "+18%", "Mixed",  "Reprice"),
             ("Slim Fit",  "Pattern","+12%", "Divergent","Watch")]
    row_h = 22
    for i, (name, attr, chg, agr, tag) in enumerate(attrs):
        y = H_card - 30 - i*row_h
        if y < 10: break
        d.add(String(12, y+5, f"{i+1:02d}", fontName="Helvetica-Bold", fontSize=8, fillColor=GREY_M))
        d.add(String(30, y+10, name, fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
        d.add(String(30, y+2, attr, fontName="Helvetica", fontSize=7, fillColor=GREY_M))
        clr_map = {"Strong": GREEN, "Mixed": ORANGE, "Divergent": RED}
        d.add(_label_pill(100, y+4, agr, clr_map.get(agr, GREY_M), w=42))
        tag_clr = {"Replenish": TEAL, "Reprice": ORANGE, "Watch": GREY_M}.get(tag, GREY_M)
        d.add(_label_pill(148, y+4, tag, tag_clr, w=40))
        # small mini sparkline
        mock = [10, 12, 11, 15, 18, 20] if i==0 else ([14, 15, 13, 12, 11, 9] if i==1 else [12, 13, 12, 13, 12, 13])
        d.add(_sparkline(195, y+2, 50, 14, mock, color=clr_map.get(agr, GREY_M)))
        chg_clr = GREEN if "+" in chg else RED
        d.add(String(255, y+6, chg, fontName="Helvetica-Bold", fontSize=8, fillColor=chg_clr))
    return d

def draw_signal_drivers_card():
    """PROXY / PULL / CONTEXT driver bars."""
    H_card = 90
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=8, ry=8, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    d.add(String(10, H_card-14, "Why-engine signal drivers", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    items = [
        ("PROXY · TRAILING", 72, TEAL,   "Review velocity +23% vs prior 30d — Accelerating lifecycle"),
        ("PULL · FORWARD",   20, BLUE,   'Google Trends "Crew Neck T-Shirts" +18% delta (live SerpAPI)'),
        ("CONTEXT · FORWARD", 0, GREY_M, "NOAA Climate Anomaly — static placeholder (not live)"),
    ]
    bar_maxw = CW - 160
    for i, (lbl, pct, clr, desc) in enumerate(items):
        y = H_card - 28 - i*22
        d.add(String(10, y+5, lbl, fontName="Helvetica-Bold", fontSize=7, fillColor=clr))
        d.add(Rect(85, y+3, bar_maxw, 8, rx=2, ry=2, fillColor=GREY_L, strokeColor=None))
        if pct > 0:
            d.add(Rect(85, y+3, bar_maxw * pct / 100, 8, rx=2, ry=2, fillColor=clr, strokeColor=None))
        d.add(String(85 + bar_maxw + 4, y+4, f"{pct}%", fontName="Helvetica-Bold", fontSize=7, fillColor=NAVY))
    return d

def draw_predictive_kpi_strip():
    H_card = 82
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=8, ry=8, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    tile_w = CW / 4
    tiles = [
        ("⏱ Patterns needing action · 4w", "3 urgent",  "2 Reprice · 1 Retire",       RED),
        ("↗ Biggest momentum gain",         "Crew Neck", "+23% vel · accelerating",    GREEN),
        ("↘ Biggest decline risk",          "Solid Print","−17% vel · 60d structural", RED),
        ("◈ Google Trends lead time",       "4 leading", "avg ~9d ahead · +5pp conf",  BLUE),
    ]
    for i, (lbl, val, meta, clr) in enumerate(tiles):
        x0 = i * tile_w + 4
        if i < 3:
            d.add(Line(x0+tile_w-4, 8, x0+tile_w-4, H_card-8, strokeColor=BORDER, strokeWidth=0.5))
        d.add(String(x0+6, H_card-15, lbl, fontName="Helvetica", fontSize=6.5, fillColor=GREY_M))
        d.add(String(x0+6, H_card-30, val, fontName="Helvetica-Bold", fontSize=10, fillColor=clr))
        d.add(String(x0+6, H_card-44, meta, fontName="Helvetica", fontSize=6.5, fillColor=GREY_M))
        d.add(Rect(x0+5, H_card-50, 20, 2, fillColor=clr, strokeColor=None))
    return d

def draw_trajectory_row():
    """Single trajectory row with sparkline + forecast + lifecycle bars."""
    H_card = 100
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=6, ry=6, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    # rank + name
    d.add(Rect(6, H_card-22, 20, 20, rx=3, ry=3, fillColor=NAVY, strokeColor=None))
    d.add(String(9, H_card-13, "01", fontName="Helvetica-Bold", fontSize=8, fillColor=WHITE))
    d.add(String(32, H_card-14, "Crew Neck", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    d.add(_label_pill(32, H_card-24, "Accelerating", GREEN, w=55))

    # Now · 30d column
    d.add(String(120, H_card-14, "+23%", fontName="Helvetica-Bold", fontSize=11, fillColor=GREEN))
    d.add(String(120, H_card-24, "vs prior 30d", fontName="Helvetica", fontSize=7, fillColor=GREY_M))

    # Trajectory SVG area (historical + forecast)
    svg_x, svg_y, svg_w, svg_h = 6, 8, int(CW*0.48), 55
    d.add(Rect(svg_x, svg_y, svg_w, svg_h, fillColor=WHITE, strokeColor=BORDER, strokeWidth=0.5))
    # divider line (now/future)
    mid_x = svg_x + svg_w // 2
    d.add(Line(mid_x, svg_y, mid_x, svg_y+svg_h, strokeColor=NAVY, strokeWidth=1, strokeDashArray=[3,2]))
    d.add(String(svg_x+4, svg_y+svg_h-10, "HISTORICAL", fontName="Helvetica", fontSize=5.5, fillColor=GREY_M))
    d.add(String(mid_x+4, svg_y+svg_h-10, "FORECAST", fontName="Helvetica", fontSize=5.5, fillColor=ORANGE))
    hist = [20,22,21,25,28,30,32,35,38,42]
    fcast= [42,44,46,49,52,55,58,60]
    d.add(_sparkline(svg_x+4, svg_y+8, svg_w//2-8, svg_h-20, hist, color=BLUE))
    d.add(_sparkline(mid_x+4, svg_y+8, svg_w//2-8, svg_h-20, fcast, color=ORANGE, dashed=True))

    # +4w / +8w forecast cells
    fc_x = svg_x + svg_w + 8
    d.add(String(fc_x, H_card-14, "+4w  +29%", fontName="Helvetica-Bold", fontSize=8.5, fillColor=GREEN))
    d.add(String(fc_x, H_card-24, "85% conf", fontName="Helvetica", fontSize=7, fillColor=GREY_M))
    d.add(String(fc_x, H_card-38, "+8w  +34%", fontName="Helvetica-Bold", fontSize=8.5, fillColor=GREEN))
    d.add(String(fc_x, H_card-48, "78% conf", fontName="Helvetica", fontSize=7, fillColor=GREY_M))
    # lifecycle progression
    lc_x = fc_x + 55
    d.add(String(lc_x, H_card-14, "Emerging → Acc → Acc", fontName="Helvetica", fontSize=7, fillColor=GREY_M))
    return d

def draw_confidence_breakdown_card():
    """Confidence score breakdown bar chart."""
    H_card = 115
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=8, ry=8, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    d.add(String(10, H_card-14, "Confidence Score Breakdown — example: 87%", fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    components = [
        ("Base",                     50, GREY_M,  "Always 50 (floor)"),
        ("Momentum score ×100",      22, BLUE,    "momentum=0.22 → +22pts"),
        ("Sample size (reviews)",    12, TEAL,    "14,000 reviews → +12pts"),
        ("Rating delta ×20",          5, PURPLE,  "|Δrating|=0.25 → +5pts"),
        ("Lifecycle bonus",           5, GREEN,   "Accelerating → +5pts"),
        ("Platform agreement",        8, ORANGE,  "Strong agreement → +8pts"),
    ]
    bar_maxw = CW - 130
    total = sum(c[1] for c in components)
    x_start = 90
    cum = 0
    y_bar = 28
    bar_h = 16
    # stacked bar
    for lbl, pts, clr, note in components:
        w = bar_maxw * pts / max(total, 1)
        d.add(Rect(x_start + bar_maxw * cum / max(total,1), y_bar, w, bar_h,
                   fillColor=clr, strokeColor=WHITE, strokeWidth=0.5))
        cum += pts
    d.add(String(x_start + bar_maxw + 4, y_bar+5, f"= {total}pts → 87%", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    # legend
    for i, (lbl, pts, clr, note) in enumerate(components):
        row = i % 3; col = i // 3
        xleg = 10 + col * (CW // 2 - 10)
        yleg = H_card - 30 - row * 15
        d.add(Rect(xleg, yleg+2, 8, 8, fillColor=clr, strokeColor=None))
        d.add(String(xleg+12, yleg+3, f"{lbl}  (+{pts}pts) — {note}", fontName="Helvetica", fontSize=6.5, fillColor=GREY_D))
    return d

def draw_recommendation_card():
    """S3 Recommendation card mockup."""
    H_card = 130
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=8, ry=8, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    # header bar
    d.add(Rect(0, H_card-24, CW, 24, rx=8, ry=8, fillColor=NAVY, strokeColor=None))
    d.add(Rect(0, H_card-24, CW, 12, fillColor=NAVY, strokeColor=None))
    d.add(String(10, H_card-17, "01", fontName="Helvetica-Bold", fontSize=10, fillColor=WHITE))
    d.add(_label_pill(32, H_card-20, "Emerging Star", TEAL, w=58))
    d.add(_label_pill(96, H_card-20, "Replenish", GREEN, w=42))
    d.add(_label_pill(144, H_card-20, "Strong signal", BLUE, w=50))
    d.add(String(CW-50, H_card-17, "87% conf", fontName="Helvetica-Bold", fontSize=9, fillColor=WHITE))
    # content
    d.add(String(10, H_card-36, "Observation:", fontName="Helvetica-Bold", fontSize=7.5, fillColor=NAVY))
    d.add(String(70, H_card-36, "Cotton Crew Neck review velocity +23% — momentum score 0.22", fontName="Helvetica", fontSize=7.5, fillColor=GREY_D))
    d.add(String(10, H_card-48, "Action:", fontName="Helvetica-Bold", fontSize=7.5, fillColor=NAVY))
    d.add(String(70, H_card-48, "Expand inventory depth in Crew Neck · Cotton within $24-32 band", fontName="Helvetica", fontSize=7.5, fillColor=GREY_D))
    d.add(String(10, H_card-60, "Impact:", fontName="Helvetica-Bold", fontSize=7.5, fillColor=NAVY))
    d.add(String(70, H_card-60, "Expected +15-20% revenue capture in this segment within 4-8 weeks", fontName="Helvetica", fontSize=7.5, fillColor=GREY_D))
    # driver bars
    d.add(String(10, H_card-74, "Signal drivers:", fontName="Helvetica-Bold", fontSize=7, fillColor=GREY_M))
    for i, (lbl, pct, clr) in enumerate([("PROXY", 72, TEAL), ("PULL", 28, BLUE), ("CONTEXT", 0, GREY_M)]):
        x0 = 80 + i * 70
        d.add(String(x0, H_card-72, lbl, fontName="Helvetica-Bold", fontSize=6.5, fillColor=clr))
        d.add(Rect(x0, H_card-80, 60, 5, rx=2, ry=2, fillColor=GREY_L, strokeColor=None))
        if pct > 0:
            d.add(Rect(x0, H_card-80, 60*pct/100, 5, rx=2, ry=2, fillColor=clr, strokeColor=None))
        d.add(String(x0+62, H_card-80, f"{pct}%", fontName="Helvetica-Bold", fontSize=6.5, fillColor=NAVY))
    # action buttons row
    btn_y = 8
    btns = [("✓ Acknowledge","#00BFA5"), ("⏰ Snooze 7d","#94A3B8"),
            ("→ Send to merch","#1E88E5"), ("○ Watch","#6366F1")]
    bx = 10
    for txt, clr_hex in btns:
        bw = len(txt)*5 + 14
        d.add(Rect(bx, btn_y, bw, 13, rx=3, ry=3, fillColor=HexColor(clr_hex), strokeColor=None))
        d.add(String(bx+6, btn_y+3, txt, fontName="Helvetica-Bold", fontSize=6, fillColor=WHITE))
        bx += bw + 6
    return d

def draw_sql_agent_flow():
    """SQL chatbot pipeline flow diagram."""
    H_card = 55
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=6, ry=6, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    steps = ["User Question", "Intent Classifier", "SQL Generator\n(LLM)", "SQL Validator", "DB Execute\n+ Redis Cache", "Response LLM", "Chat Output"]
    colors_s = [NAVY, BLUE, TEAL, ORANGE, PURPLE, GREEN, NAVY]
    n = len(steps)
    sw = (CW - 20) / n
    for i, (step, clr) in enumerate(zip(steps, colors_s)):
        x0 = 10 + i*sw
        box_w = sw - 6
        d.add(Rect(x0, 14, box_w, 28, rx=3, ry=3, fillColor=clr, strokeColor=None))
        lines = step.split("\n")
        for li, ln in enumerate(lines):
            d.add(String(x0+3, 14+28-10-li*9, ln, fontName="Helvetica-Bold", fontSize=5.5, fillColor=WHITE))
        if i < n-1:
            ax = x0 + box_w + 1; ay = 28
            d.add(Line(ax, ay, ax+4, ay, strokeColor=GREY_M, strokeWidth=1))
            d.add(Polygon([ax+4, ay-2, ax+4, ay+2, ax+6, ay], fillColor=GREY_M, strokeColor=None))
    d.add(String(10, 6, "Ask Tab Pipeline  ·  Redis TTL 5min (SQL results)  ·  Temperature=0 (deterministic SQL)", fontName="Helvetica", fontSize=6, fillColor=GREY_M))
    return d

def draw_pattern_types_card():
    """6 pattern type chips."""
    H_card = 44
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=6, ry=6, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    patterns = [
        ("Emerging Star",       TEAL,   "change>20% AND score>0.3 AND rating>4.0"),
        ("Declining Attribute", RED,    "change<−15% AND score<0.3"),
        ("Underserved Niche",   PURPLE, "platform_count=1 AND score>0.2"),
        ("Review Leader",       GREEN,  "rating≥4.5 AND reviews≥500"),
        ("Cross-Platform Gap",  ORANGE, "|amz−nor|>30"),
        ("Rating Outlier",      HexColor("#7C3AED"), "rating<3.5 AND reviews>200"),
    ]
    chip_w = (CW - 16) / 3
    for i, (name, clr, cond) in enumerate(patterns):
        col, row = i % 3, i // 3
        x0 = 8 + col * chip_w
        y0 = H_card - 18 - row * 18
        d.add(Rect(x0, y0, chip_w-6, 14, rx=3, ry=3, fillColor=clr, strokeColor=None))
        d.add(String(x0+4, y0+5, name, fontName="Helvetica-Bold", fontSize=6.5, fillColor=WHITE))
        d.add(String(x0+4, y0+1, cond, fontName="Helvetica", fontSize=5, fillColor=WHITE))
    return d

def draw_google_trends_bar_chart():
    """Google Trends query bar chart mockup."""
    H_card = 88
    d = Drawing(CW, H_card)
    d.add(Rect(0, 0, CW, H_card, rx=6, ry=6, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
    d.add(String(10, H_card-14, "Google Trends · search-interest lead  (PULL · FORWARD)", fontName="Helvetica-Bold", fontSize=8.5, fillColor=NAVY))
    d.add(String(10, H_card-22, "14d delta vs prior 30d baseline · Live SerpAPI", fontName="Helvetica", fontSize=7, fillColor=GREY_M))
    queries = [
        ("Crew Neck T-Shirts",  82, "+31%"),
        ("Navy Blue shirts",     65, "+24%"),
        ("Cotton polo men",      50, "+18%"),
        ("Slim fit shirts",      38, "+11%"),
        ("Henley shirts",        22,  "+7%"),
    ]
    bar_maxw = CW - 160
    for i, (q, score, delta) in enumerate(queries):
        y = H_card - 32 - i*12
        d.add(String(10, y+2, q, fontName="Helvetica", fontSize=7, fillColor=GREY_D))
        d.add(Rect(110, y+1, bar_maxw*score/100, 8, rx=2, ry=2, fillColor=BLUE, strokeColor=None))
        d.add(Rect(110, y+1, bar_maxw, 8, rx=2, ry=2, fillColor=GREY_L, strokeColor=None, fillOpacity=0))
        d.add(String(110 + bar_maxw + 4, y+2, delta, fontName="Helvetica-Bold", fontSize=7,
                     fillColor=GREEN if "+" in delta else RED))
    return d

# ═══════════════════════════════════════════════════════════════════════════
# BUILD STORY
# ═══════════════════════════════════════════════════════════════════════════
story = []
A = story.append

# ── COVER ───────────────────────────────────────────────────────────────────
A(sp(50))
cov = Drawing(CW, 80)
cov.add(Rect(0, 0, CW, 80, rx=12, ry=12, fillColor=NAVY, strokeColor=None))
cov.add(String(20, 55, "Channel Intelligence", fontName="Helvetica-Bold", fontSize=26, fillColor=WHITE))
cov.add(String(20, 38, "Visual Demo Reference — Every Card, Every Calculation", fontName="Helvetica", fontSize=11, fillColor=HexColor("#94A3B8")))
cov.add(String(20, 22, "Analytics  ·  Predictive  ·  Ask & Recommendation", fontName="Helvetica-Bold", fontSize=9, fillColor=TEAL))
cov.add(String(CW-105, 8, datetime.datetime.now().strftime("Generated %Y-%m-%d"), fontName="Helvetica", fontSize=7.5, fillColor=HexColor("#64748B")))
A(cov); A(sp(10))
A(p("This document walks through every visible UI card in order, shows a mockup of what it looks like, then explains exactly which database columns feed it and how the number is calculated.", BODY))
A(sp(8))
A(itable([
    ["Tab", "Cards covered"],
    ["S1 — Analytics",        "4 KPI tiles · Winning Patterns · Signal drivers · Price band · Google Trends panel"],
    ["S2 — Predictive",       "4 KPI cards · Trajectory chart row · Confidence score · Lifecycle panel"],
    ["S3 — Ask & Recommendation", "6 Pattern type chips · Recommendation card · Signal tiers · Driver bars · SQL chatbot flow"],
]))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════
A(h1("Screen 1 — Analytics"))
A(hr2(BLUE))
A(body("The Analytics tab provides real-time market intelligence. Each card below is drawn as it appears in the UI, followed by the exact calculation behind it."))
A(sp(6))

# ── Card 1: KPI Strip ───────────────────────────────────────────────────────
A(h2("Card 1 — KPI Strip  (4 tiles at the top)"))
A(draw_kpi_strip()); A(sp(6))

A(itable([["Tile", "Label", "Source column", "Calculation"]],
         cw=[8*mm, 38*mm, 45*mm, 72*mm]))
A(itable([
    ["Tile", "Label",                "Source",                              "Calculation"],
    ["①",  "Reviews captured",      "reviews.review_count",                "SUM(review_count) for all products in the filter window (default 30d). Sub-line: COUNT(DISTINCT product_id)."],
    ["②",  "Top style",             "trend_scores.latest_week_share\nattr_key = 'neck_type'",
                                                                            "Style value with highest latest_week_share. Delta = (latest_week_share − previous_week_share) × 100. Source: trend_scores table, neck_type rows."],
    ["③",  "Top color",             "trend_scores.latest_week_share\nattr_key = 'color_family'",
                                                                            "Color family with highest latest_week_share in filter context. Same delta formula as style."],
    ["④",  "Converting price band", "reviews.review_count\nproduct_variants.price",
                                                                            "share_index = (band_reviews / total_reviews) ÷ (band_listings / total_listings). Band with highest share_index wins. Median = PERCENTILE(0.5) of price in that band."],
], cw=[8*mm, 32*mm, 48*mm, 75*mm]))
A(sp(4))
A(bold("Converting price band — exact formula:"))
A(ftable([
    ["share_index",  "(band_reviews / total_reviews) ÷ (band_listings / total_listings)"],
    ["Example",      "Band $24–32: 30% reviews, 10% listings → 3.0× share index"],
    ["Best band",    "argmax(share_index) across all price bands"],
    ["Median price", "PERCENTILE_CONT(0.5) over product_variants.price in that band"],
]))
A(sp(8))

# ── Card 2: Winning Patterns ────────────────────────────────────────────────
A(h2("Card 2 — Winning Patterns Panel"))
A(draw_winning_patterns_card()); A(sp(6))
A(body("Each pattern row shows: attribute name · cross-platform agreement badge · decision tag · sparkline · velocity %. "
       "Rows are ranked by momentum_score from trend_scores, descending."))
A(sp(4))
A(itable([
    ["Element", "Source & Calculation"],
    ["Attribute name",        "trend_scores.attr_value — e.g. 'Crew Neck', 'Navy Blue'"],
    ["Platform agreement",    "_real_agreement(amz_score, nor_score): same direction + diff<10 → Strong (+8 conf); diff 10–30 or single ch → Mixed; opposite direction → Divergent (−6 conf)"],
    ["Decision tag",          "_decision_tag_full(): Reposition if channels diverge >5%; Reprice if price_band_shifted; Replenish if accelerating; Retire if declining; Whitespace if single platform; Watch default"],
    ["Sparkline chart",       "hist_vals list from product_review_snapshots → scaled to SVG coordinate space via _vals_to_svg_points(). Blue line = historical, orange dashed = forecast."],
    ["Velocity %",            "(latest_week_share − previous_week_share) × 100 from trend_scores"],
]))
A(sp(8))

# ── Card 3: Signal Drivers ──────────────────────────────────────────────────
A(h2("Card 3 — Signal Drivers  (PROXY · PULL · CONTEXT)"))
A(draw_signal_drivers_card()); A(sp(6))
A(body("These three bars show the source mix driving a pattern's forecast. They sum to ~100% per pattern."))
A(sp(4))
A(ftable([
    ["PROXY · TRAILING",   "Marketplace review velocity last 7–30 days. pct = 100 − pull_pct. Always present."],
    ["PULL · FORWARD",     "Google Trends delta_pct for matching query (SerpAPI, 14d vs prior 30d baseline). pull_pct = min(35, max(10, |delta_pct| ÷ 2)) when GT data exists; else 0."],
    ["CONTEXT · FORWARD",  "NOAA Climate Anomaly. STATIC placeholder — always 0% because NOAA API is not live."],
    ["Sum invariant",      "proxy_pct + pull_pct + context_pct = 100% always."],
    ["Code",               "_compute_driver_pcts(gt_delta) in app.py"],
]))
A(sp(8))

# ── Card 4: Google Trends Bar ───────────────────────────────────────────────
A(h2("Card 4 — Google Trends Panel"))
A(draw_google_trends_bar_chart()); A(sp(6))
A(body("Shows up to 5 Google Trends queries matched to the top trending attributes in the current filter. "
       "Bar width = search interest score (0–100). Delta = % change vs prior 30d baseline."))
A(sp(4))
A(ftable([
    ["Query construction", "_gt_query_for_row(): attr_value + category + optional gender/style → e.g. 'Crew Neck T-Shirts Men'"],
    ["Score",              "SerpAPI interest_over_time — normalised 0–100 (100 = peak interest in window)"],
    ["Delta %",            "(current_14d_avg − prior_30d_avg) / prior_30d_avg × 100"],
    ["Cache",              "Redis TTL 3600s (1 hour) keyed by SHA256 of query tuple + geo + window"],
    ["Lead badge",         "query shown as 'leading' when delta_pct ≥ 20%"],
]))
A(sp(8))

# ── Card 5: Cross-platform Agreement ───────────────────────────────────────
A(h2("Card 5 — Cross-Platform Agreement Badge"))
A(sp(4))
agree_d = Drawing(CW, 44)
agree_d.add(Rect(0, 0, CW, 44, rx=6, ry=6, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
for i, (lbl, desc, clr) in enumerate([
    ("STRONG", "Both channels same direction · diff < 10", GREEN),
    ("MIXED",  "Channels diverging · diff 10–30 or single channel", ORANGE),
    ("DIVERGENT", "Channels moving opposite directions · diff > 30", RED),
]):
    x0 = 8 + i*(CW//3)
    agree_d.add(Rect(x0, 14, CW//3-10, 20, rx=4, ry=4, fillColor=clr, strokeColor=None))
    agree_d.add(String(x0+5, 28, lbl, fontName="Helvetica-Bold", fontSize=8, fillColor=WHITE))
    agree_d.add(String(x0+2, 6, desc, fontName="Helvetica", fontSize=5.5, fillColor=GREY_M))
A(agree_d); A(sp(4))
A(ftable([
    ["Input",        "amz_score (Amazon trend_scores int 0–100), nor_score (Nordstrom trend_scores int 0–100)"],
    ["Strong",       "(amz≥0)==(nor≥0)  AND  |amz−nor| < 10  →  Confidence +8pts"],
    ["Mixed",        "Same direction but |diff| 10–30, OR one platform missing  →  0pts"],
    ["Divergent",    "Opposite directions (one positive, one negative)  →  Confidence −6pts"],
    ["Single ch",    "One platform has no data  →  −3pts confidence penalty"],
    ["Code",         "_real_agreement(amz, nor) in app.py"],
]))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — PREDICTIVE
# ═══════════════════════════════════════════════════════════════════════════
A(h1("Screen 2 — Predictive"))
A(hr2(TEAL))
A(body("All forecasts use linear regression on historical trend_scores data. "
       "Every confidence score now incorporates cross-platform agreement, sample size, and model signal strength."))
A(sp(6))

# ── Card 6: Predictive KPI Strip ────────────────────────────────────────────
A(h2("Card 6 — Predictive KPI Strip  (4 tiles)"))
A(draw_predictive_kpi_strip()); A(sp(6))
A(itable([
    ["KPI tile", "Glossary definition", "How calculated"],
    ["⏱ Patterns needing action · 4w",
     "Count meeting ALL 3: lifecycle Acc/Dec, conf >75%, |Δ|>15%",
     "for row in attr_rows: if stage in {acc,dec} AND conf>75 AND |change|>15 → append to urgent list. Tag breakdown counted per decision_tag."],
    ["↗ Biggest momentum gain",
     "Pattern with highest velocity gain. Named explicitly. Forecast +4w with conf score.",
     "max(rows, key=change). gain_fc4 = change × (1 + 0.05×4) or projected_change_pct × 28/30 from velocity_forecast."],
    ["↘ Biggest decline risk",
     "Pattern with worst velocity decline. '60d structural' = 60+ days, both channels, strong agreement.",
     "min(rows, key=change). 60d structural: hist_days span ≥ 60d AND slope < 0 AND both platform slopes < 0."],
    ["◈ GT lead time",
     "Count where GT crossed +20% before velocity. Avg lead = mean gap in days.",
     "lead_count = COUNT(rows where delta_pct≥20). avg_lead_days = mean(max(7, min(21, 7+(delta-20)×0.2))). +5pp conf boost shown."],
]))
A(sp(8))

# ── Card 7: Trajectory Row + Chart ─────────────────────────────────────────
A(h2("Card 7 — Pattern Trajectory Row  (with sparkline chart)"))
A(draw_trajectory_row()); A(sp(6))
A(body("Each row = one attribute pattern. The left SVG chart shows historical (blue) and forecast (orange dashed). "
       "The NOW · 30d, +4W, +8W columns are computed from the linear regression model."))
A(sp(4))
A(ftable([
    ["Now · 30d",         "(latest_week_share − previous_week_share) × 100  from trend_scores"],
    ["Forecast · +4w",    "projected_change_pct × 28/30  (if velocity_forecast data exists)\nfallback: change × (1 + 0.05×4)"],
    ["Forecast · +8w",    "projected_change_pct × 56/30  (from same linear regression)\nfallback: change × (1 + 0.05×8)"],
    ["Chart: hist line",  "hist_vals list [14 daily review counts] → _vals_to_svg_points(vals, x_start=0, x_end=200, y_top=12, y_bot=118)\nBlue polyline drawn left half of SVG"],
    ["Chart: forecast",   "future_vals list [30-day extrapolation] → same SVG scaler, drawn right half\nOrange dashed polyline + confidence band polygon"],
    ["Confidence band",   "±8px above/below forecast polyline → grey shaded polygon"],
    ["Linear regression", "numpy.polyfit(x=[0..n-1], y=hist_vals, deg=1) → slope, intercept\nfuture[t] = slope×(n+t) + intercept, clamped to [0,1]"],
]))
A(sp(4))
A(bold("Lifecycle progression (3 step arrows):"))
A(ftable([
    ["Now stage",    "Derived from slope: slope>0.02 AND score<0.4 → Emerging; slope>0.02 AND score≥0.4 → Accelerating; |slope|≤0.02 → Plateau; slope<−0.02 → Declining"],
    ["+4w stage",    "Apply same rule to extrapolated score at 4w"],
    ["+8w stage",    "Apply same rule to extrapolated score at 8w — naturally lower confidence"],
]))
A(sp(8))

# ── Card 8: Confidence Breakdown ───────────────────────────────────────────
A(h2("Card 8 — Confidence Score Breakdown"))
A(draw_confidence_breakdown_card()); A(sp(6))
A(body("Glossary: 'Derived from cross-platform agreement + sample size + forecast model error bars. 80%+ = high-confidence; <70% = exploratory.'"))
A(sp(4))
A(ftable([
    ["Component",          "Formula"],
    ["Base",               "50  (always — floor)"],
    ["Momentum",           "min(30,  int(momentum_score × 100))  — forecast model strength"],
    ["Sample size",        "min(15,  int(review_count / 8000 × 15))  — data reliability"],
    ["Rating signal",      "min(10,  int(|rating_delta| × 20))  — quality signal strength"],
    ["Lifecycle bonus",    "+5 Accelerating / +3 Emerging / 0 Plateau / −3 Declining / −8 Dead"],
    ["Agreement bonus",    "+8 Strong / 0 Mixed / −3 Single-channel / −6 Divergent"],
    ["Clamp",              "max(50, min(95, total))  — always between 50% and 95%"],
    ["Signal tier display","≥80% = Strong signal (green) · 70–79% = Moderate signal · <70% = Watch"],
]))
A(sp(8))

# ── Card 9: Lifecycle Stages ────────────────────────────────────────────────
A(h2("Card 9 — Lifecycle Stage Cards"))
A(sp(4))
lc_d = Drawing(CW, 50)
lc_d.add(Rect(0, 0, CW, 50, rx=6, ry=6, fillColor=CARD_BG, strokeColor=BORDER, strokeWidth=0.7))
stages = [("Emerging", BLUE, "Slope>0.02 AND score<0.4"),
          ("Accelerating", GREEN, "Slope>0.02 AND score≥0.4"),
          ("Plateau", GREY_M, "−0.02≤slope≤0.02"),
          ("Declining", RED, "Slope<−0.02")]
sw2 = CW / 4
for i, (lbl, clr, cond) in enumerate(stages):
    x0 = i*sw2 + 4
    lc_d.add(Rect(x0, 14, sw2-8, 28, rx=4, ry=4, fillColor=clr, strokeColor=None))
    lc_d.add(String(x0+4, 34, lbl, fontName="Helvetica-Bold", fontSize=8, fillColor=WHITE))
    lc_d.add(String(x0+3, 7, cond, fontName="Helvetica", fontSize=5.5, fillColor=GREY_M))
A(lc_d); A(sp(4))
A(ftable([
    ["Source",    "velocity_snapshots.lifecycle_stage or computed from linear regression slope + score level"],
    ["Emerging",  "slope > 0.02  AND  score < 0.4  (rising, not yet mainstream)"],
    ["Accelerating","slope > 0.02 AND score ≥ 0.4 (mainstream and growing fast)"],
    ["Plateau",   "|slope| ≤ 0.02 (flat — score stable)"],
    ["Declining", "slope < −0.02 (falling; distinguish from 60d structural using hist_days span)"],
]))
A(PageBreak())

# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — ASK & RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════
A(h1("Screen 3 — Ask & Recommendation"))
A(hr2(PURPLE))
A(body("Pattern detection runs on DB data. LLM drafts recommendations via Groq API. "
       "Confidence is computed from evidence JSONB, not just the LLM label."))
A(sp(6))

# ── Card 10: 6 Pattern Types ────────────────────────────────────────────────
A(h2("Card 10 — 6 Pattern Detection Chips"))
A(draw_pattern_types_card()); A(sp(6))
A(body("These 6 pattern types are detected by pattern_detector.py on every pipeline run. Each is an independent DB query."))
A(sp(4))
patterns_data = [
    ("Emerging Star",       TEAL,   "velocity_snapshots.change_pct > 20%",   "AND trend_scores.score > 0.3  AND reviews.rating_avg > 4.0",     "momentum_score, rating_avg, review_count, lifecycle_stage"),
    ("Declining Attribute", RED,    "velocity_snapshots.change_pct < −15%",  "AND trend_scores.score < 0.3",                                    "momentum_score (negative), rating_delta, velocity_trend"),
    ("Underserved Niche",   PURPLE, "platform_count = 1  (single channel)",  "AND trend_scores.score > 0.2  AND competitor_count < threshold",   "platform_count, score, competitor_gap"),
    ("Review Leader",       GREEN,  "reviews.rating_avg ≥ 4.5",             "AND reviews.review_count ≥ 500  AND velocity above median",        "rating_avg, review_count, velocity_pct"),
    ("Cross-Platform Gap",  ORANGE, "|amz_score − nor_score| > 30",         "AND both platforms have data",                                    "amz_score, nor_score, score_diff"),
    ("Rating Outlier",      HexColor("#7C3AED"), "reviews.rating_avg < 3.5", "AND reviews.review_count > 200  AND above-median listing count",  "rating_avg, review_count, variant_count"),
]
for (name, clr, cond1, cond2, evidence) in patterns_data:
    A(KeepTogether([
        Table([[Paragraph(f"  {name}  ",
                ParagraphStyle("ptag", fontName="Helvetica-Bold", fontSize=8.5, textColor=WHITE))]],
              colWidths=[55*mm],
              style=TableStyle([("BACKGROUND",(0,0),(0,0),clr),
                                ("TOPPADDING",(0,0),(0,0),3),("BOTTOMPADDING",(0,0),(0,0),3),
                                ("LEFTPADDING",(0,0),(0,0),6)])),
        sp(2),
        ftable([
            ["Trigger condition 1", cond1],
            ["Trigger condition 2", cond2],
            ["Evidence JSONB fields", evidence],
        ]),
        sp(5),
    ]))

A(sp(4))

# ── Card 11: Recommendation Card ────────────────────────────────────────────
A(h2("Card 11 — Recommendation Card"))
A(draw_recommendation_card()); A(sp(6))
A(body("Each recommendation card maps to one row in the recommendations table. "
       "The LLM generates Observation/Action/Impact/Confidence from the evidence JSONB. "
       "The confidence % displayed is independently computed from the evidence, not the LLM text."))
A(sp(4))
A(itable([
    ["UI Element", "DB column / Calculation"],
    ["Rank badge (01, 02…)",     "Position in ORDER BY created_at DESC (top 10 shown)"],
    ["Pattern type chip",        "recommendations.pattern_type → mapped to display label + color"],
    ["Decision tag",             "recommendations.pattern_type → _decision_tag_full() or dt_map lookup"],
    ["Signal tier badge",        "Strong signal if conf≥80% / Moderate signal if conf 65–79% / Watch if <65%"],
    ["Confidence %",             "_rec_confidence_pct(rec): 50 + momentum×100 + reviews/8000×15 + |Δrating|×20 + lifecycle_bonus + agreement_bonus. Clamped 50–95%."],
    ["Observation text",         "recommendations.observation — LLM-generated (Groq API, temperature=0)"],
    ["Action text",              "recommendations.action — LLM-generated"],
    ["Impact text",              "recommendations.impact — LLM-generated"],
    ["Evidence bullets",         "recommendations.evidence JSONB — raw metrics (momentum_score, review_count, etc.)"],
    ["PROXY bar %",              "100 − pull_pct  (see _compute_driver_pcts())"],
    ["PULL bar %",               "min(35, max(10, |gt_delta| ÷ 2))  when GT data exists; else 0%"],
    ["CONTEXT bar %",            "Always 0%  (NOAA not live)"],
    ["✓ Acknowledge",            "UPDATE recommendations SET status='accepted' WHERE rec_id=X"],
    ["⏰ Snooze 7d",             "UPDATE recommendations SET status='dismissed' WHERE rec_id=X"],
    ["→ Send to merchandising",  "st.toast() notification (no DB write — demo mode)"],
    ["○ Watch this pattern",     "st.toast() notification (no DB write — demo mode)"],
    ["↗ View on Predictive",     "st.query_params['view']='predictive'; st.rerun()"],
]))
A(sp(8))

# ── Card 12: LLM Drafting Pipeline ─────────────────────────────────────────
A(h2("Card 12 — LLM Drafting (Groq API)"))
A(sp(4))
A(body("Each pattern dict is sent to the LLM with a system prompt requiring exact structured output:"))
A(sp(2))
A(ftable([
    ["LLM provider",   "Groq API  (Llama / Mixtral) — via LLMClient in chatbot/llm_config.py"],
    ["Temperature",    "0  (deterministic, reproducible output)"],
    ["Output format",  "Observation: / Action: / Reasoning: / Evidence: / Impact: / Confidence:"],
    ["Confidence rule","High: momentum>0.20 AND reviews>2000 AND lifecycle=emerging/accelerating\nMedium: momentum 0.08–0.20 OR reviews 500–2000 OR lifecycle=plateau\nLow: momentum<0.08 OR conflicting OR lifecycle=dead/declining"],
    ["Stored in DB",   "recommendations.observation, .action, .impact, .confidence — all from LLM parse"],
    ["Display conf",   "_rec_confidence_pct() — recomputed from evidence JSONB at render time, ignores LLM label"],
]))
A(sp(8))

# ── Card 13: SQL Chatbot ────────────────────────────────────────────────────
A(h2("Card 13 — Ask Tab  (SQL Chatbot Pipeline)"))
A(draw_sql_agent_flow()); A(sp(6))
A(ftable([
    ["Step 1 — Intent",     "LLM classifies question type + confidence. Routes to sql_agent for data questions."],
    ["Step 2 — SQL gen",    "LLM generates SELECT query with full schema context in system prompt (temperature=0)."],
    ["Step 3 — Validate",   "_validate_sql(): first token must be SELECT; blocks INSERT/UPDATE/DROP/ALTER/TRUNCATE/CREATE/GRANT/REVOKE."],
    ["Step 4 — Cache check","Redis key = 'sql:' + SHA256(sql_string)[:32]. TTL = 300s (5 min)."],
    ["Step 5 — Execute",    "psycopg2 cursor on PostgreSQL. Returns list[dict] (max 50 rows per LIMIT clause)."],
    ["Step 6 — Response",   "LLM formats results as business-friendly Markdown (temperature=0, max 15 rows shown, 120-word cap)."],
    ["Step 7 — Render",     "_answer_to_html() parses markdown pipe tables → HTML. _markdown_table_to_html() handles | syntax."],
    ["History context",     "Last 4 conversation turns prepended to SQL generation prompt."],
]))
A(sp(8))

# ── QUICK REFERENCE ─────────────────────────────────────────────────────────
A(PageBreak())
A(h1("Quick Reference — All Formulas"))
A(hr2(NAVY))
A(sp(4))
A(ftable([
    ["Formula", "Expression"],
    ["Proportional share index",  "(band_reviews / total_reviews) ÷ (band_listings / total_listings)"],
    ["Trend delta %",             "(latest_week_share − previous_week_share) × 100"],
    ["Linear forecast y[t]",      "slope×(n+t) + intercept  — numpy.polyfit(deg=1)"],
    ["Projected % change",        "(forecast_score − last_hist_score) / last_hist_score × 100"],
    ["+4w forecast",              "projected_change_pct × 28/30  (or fallback: change×1.2)"],
    ["+8w forecast",              "projected_change_pct × 56/30  (or fallback: change×1.4)"],
    ["SVG y-coordinate",          "y_bot − (y_bot − y_top) × (v − vmin) / (vmax − vmin)"],
    ["GT delta %",                "(current_14d_avg − prior_30d_avg) / prior_30d_avg × 100"],
    ["GT lead days estimate",     "max(7, min(21,  7 + (delta_pct − 20) × 0.2))"],
    ["Driver PULL %",             "min(35, max(10, |gt_delta| ÷ 2))  when GT data present"],
    ["Driver PROXY %",            "100 − pull_pct  (CONTEXT always 0%)"],
    ["Confidence base",           "50 + min(30, momentum×100) + min(15, reviews/8000×15) + min(10, |Δrating|×20)"],
    ["Confidence lifecycle",      "+5 acc / +3 emerging / 0 plateau / −3 declining / −8 dead"],
    ["Confidence agreement",      "+8 strong / 0 mixed / −3 single-ch / −6 divergent"],
    ["Confidence clamp",          "max(50, min(95, total))"],
    ["Agreement: Strong",         "(amz≥0)==(nor≥0)  AND  |amz−nor| < 10"],
    ["Agreement: Divergent",      "(amz≥0) != (nor≥0)"],
    ["60d structural",            "hist_days span ≥ 60d  AND  slope < 0  AND  both platforms slope < 0"],
    ["SQL cache key",             "'sql:' + sha256(sql_string).hexdigest()[:32]"],
], cw=[62*mm, 101*mm]))

A(sp(10))
A(itable([
    ["Term", "Glossary definition"],
    ["Pattern",          "Cluster of marketplace listings sharing design attributes (e.g. 'Crew Neck · Cotton · Navy · Regular Fit')"],
    ["Review velocity",  "Rate of new reviews per listing over time — primary leading indicator (reviews lag orders ~2 weeks)"],
    ["Converting band",  "Price band attracting highest review-velocity-weighted share — measured by proportional share index"],
    ["PROXY",            "Trailing-truth signal — marketplace review velocity, sentiment, price history (last 7–30 days)"],
    ["PULL",             "Forward signal — Google Trends 14d delta vs prior 30d baseline"],
    ["CONTEXT",          "Environmental signal — NOAA weather anomalies (STATIC placeholder — not live in POC)"],
    ["PUSH",             "Marketing-led signal — TikTok/Instagram creator trends (Phase 2 — not in POC)"],
    ["Signal tier",      "Strong = conf≥80% + strong agreement + |Δ|≥15%  /  Moderate = 70–80%  /  Watch = <70%"],
], cw=[38*mm, 125*mm]))

# ── BUILD ───────────────────────────────────────────────────────────────────
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"PDF written → {OUTPUT}")
