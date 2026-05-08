from __future__ import annotations

from pathlib import Path
import textwrap


OUT = Path("docs/retail_market_intelligence_demo_guide.pdf")
PAGE_W, PAGE_H = 595, 842
MARGIN_X = 46
TOP_Y = 790
BOTTOM_Y = 54

INK = (15, 27, 45)
MUTED = (92, 105, 128)
ACCENT = (8, 165, 214)
SUCCESS = (32, 164, 100)
WARNING = (255, 176, 0)
DANGER = (229, 57, 63)
LIGHT = (244, 247, 251)
LINE = (220, 228, 238)


def esc(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


class Page:
    def __init__(self, number: int):
        self.number = number
        self.ops: list[str] = []
        self.y = TOP_Y

    def color(self, rgb):
        r, g, b = [v / 255 for v in rgb]
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg")

    def stroke_color(self, rgb):
        r, g, b = [v / 255 for v in rgb]
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG")

    def rect(self, x, y, w, h, fill=LIGHT):
        self.color(fill)
        self.ops.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re f")

    def line(self, x1, y1, x2, y2, color=LINE, width=1):
        self.stroke_color(color)
        self.ops.append(f"{width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")

    def text(self, text, x, y, size=10, font="F1", color=INK):
        self.color(color)
        self.ops.append(f"BT /{font} {size:.1f} Tf {x:.1f} {y:.1f} Td ({esc(text)}) Tj ET")

    def header(self, title: str, subtitle: str = ""):
        self.rect(0, 812, PAGE_W, 30, fill=INK)
        self.text("Innovatics Retail Market Intelligence", MARGIN_X, 822, 9, "F2", (255, 255, 255))
        self.text(title, MARGIN_X, 776, 18, "F2", INK)
        if subtitle:
            self.text(subtitle, MARGIN_X, 758, 9.5, "F1", MUTED)
        self.line(MARGIN_X, 746, PAGE_W - MARGIN_X, 746)
        self.y = 724

    def footer(self):
        self.line(MARGIN_X, 38, PAGE_W - MARGIN_X, 38)
        self.text(f"Demo guide | Page {self.number}", MARGIN_X, 24, 8.5, "F1", MUTED)


class PDF:
    def __init__(self):
        self.pages: list[Page] = []

    def new_page(self, title: str, subtitle: str = "") -> Page:
        p = Page(len(self.pages) + 1)
        p.header(title, subtitle)
        self.pages.append(p)
        return p

    def write(self, path: Path):
        objects: list[bytes] = []

        def add(obj: str | bytes) -> int:
            if isinstance(obj, str):
                obj = obj.encode("latin-1", "replace")
            objects.append(obj)
            return len(objects)

        font_regular = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font_bold = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        page_ids = []

        for page in self.pages:
            page.footer()
            stream = "\n".join(page.ops).encode("latin-1", "replace")
            content_id = add(
                b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" +
                stream + b"\nendstream"
            )
            page_id = add(
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
            page_ids.append(page_id)

        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")

        for idx, pid in enumerate(page_ids):
            objects[pid - 1] = objects[pid - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_id} 0 R".encode())

        catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode())
            out.extend(obj)
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n".encode())
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode())
        out.extend(
            f"trailer << /Size {len(objects)+1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n".encode()
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(out)


def wrap_lines(text: str, width: int = 84) -> list[str]:
    if not text:
        return [""]
    return textwrap.wrap(text, width=width, break_long_words=False) or [""]


def para(p: Page, text: str, size=10.5, color=INK, gap=9, width=86):
    for line in wrap_lines(text, width):
        if p.y < BOTTOM_Y + 30:
            return
        p.text(line, MARGIN_X, p.y, size, "F1", color)
        p.y -= size + 4
    p.y -= gap


def h2(p: Page, text: str):
    p.text(text, MARGIN_X, p.y, 13, "F2", INK)
    p.y -= 20


def bullet(p: Page, text: str, size=10):
    lines = wrap_lines(text, 78)
    if p.y < BOTTOM_Y + 28:
        return
    p.text("-", MARGIN_X + 4, p.y, size, "F2", ACCENT)
    p.text(lines[0], MARGIN_X + 18, p.y, size, "F1", INK)
    p.y -= size + 4
    for line in lines[1:]:
        p.text(line, MARGIN_X + 18, p.y, size, "F1", INK)
        p.y -= size + 4


def callout(p: Page, title: str, body: str, color=ACCENT):
    h = 72
    p.rect(MARGIN_X, p.y - h + 12, PAGE_W - 2 * MARGIN_X, h, fill=(232, 247, 252))
    p.rect(MARGIN_X, p.y - h + 12, 5, h, fill=color)
    p.text(title, MARGIN_X + 16, p.y - 6, 10, "F2", color)
    yy = p.y - 24
    for line in wrap_lines(body, 78)[:3]:
        p.text(line, MARGIN_X + 16, yy, 9.5, "F1", INK)
        yy -= 13
    p.y -= h + 12


def metric_box(p: Page, x, y, title, body, color=ACCENT):
    p.rect(x, y, 238, 64, fill=(255, 255, 255))
    p.line(x, y, x + 238, y, color=LINE)
    p.rect(x, y + 58, 238, 6, fill=color)
    p.text(title, x + 12, y + 39, 10, "F2", INK)
    for i, line in enumerate(wrap_lines(body, 36)[:2]):
        p.text(line, x + 12, y + 23 - i * 12, 8.8, "F1", MUTED)


def build_pdf() -> PDF:
    pdf = PDF()

    p = pdf.new_page("Retail Market Intelligence Demo Guide", "End-to-end explanation for the Streamlit project")
    p.rect(0, 0, PAGE_W, PAGE_H, fill=(255, 255, 255))
    p.rect(0, 642, PAGE_W, 200, fill=INK)
    p.text("Innovatics", MARGIN_X, 764, 18, "F2", (255, 255, 255))
    p.text("Product & Market Intelligence", MARGIN_X, 724, 28, "F2", (255, 255, 255))
    p.text("Demo guide for descriptive, conversational, predictive, and recommendation layers", MARGIN_X, 700, 11, "F1", (218, 228, 238))
    p.y = 610
    callout(
        p,
        "Core story",
        "The system converts scraped marketplace SKU data into merchant decisions: what is selling, why it matters, what is changing, and what action to take.",
        ACCENT,
    )
    h2(p, "Best opening line")
    para(
        p,
        "We scrape Amazon and Nordstrom apparel data, normalize product and SKU attributes into PostgreSQL, and use Streamlit to turn price, review, and attribute signals into retail decisions.",
        width=82,
    )
    h2(p, "Four layers")
    for item in [
        "Descriptive Intelligence: current market snapshot and strongest visible signals.",
        "Conversational Intelligence: natural language analyst grounded in filtered data.",
        "Predictive Intelligence: trend momentum and lifecycle stage modeling.",
        "Recommendation Intelligence: action queue for merchant decisions.",
    ]:
        bullet(p, item)

    p = pdf.new_page("System Flow", "How scraped data becomes UI intelligence")
    h2(p, "Pipeline")
    for item in [
        "Scrapers collect platform, category, product, variant, price, stock, review, and attribute data.",
        "pipeline/ingest.py validates raw records with scraper-specific Pydantic schemas.",
        "pipeline/ingest_normalized.py writes normalized tables: products, product_variants, reviews, brands, categories, colors, sizes, and attribute masters.",
        "streamlit_app/db.py reads filtered product and SKU views from the normalized schema.",
        "predictions write trend_scores; recommendations write action-ready records to recommendations.",
    ]:
        bullet(p, item)
    callout(
        p,
        "Important demo phrase",
        "This is not only a scraping demo. The valuable layer is normalization plus decision logic: attributes, price, reviews, and scrape time become structured retail signals.",
        SUCCESS,
    )
    h2(p, "Main tables")
    for item in [
        "products: one row per listing URL, including platform, category, brand, title, and high-level attributes.",
        "product_variants: one row per color/size SKU variant, with price, availability, stock note, and scraped_at.",
        "reviews: rating, review_count, star split, pros/cons, and scraped_at.",
        "trend_scores: attribute momentum, trend direction, lifecycle stage, and retailer action.",
        "recommendations: generated merchant actions with evidence, status, and confidence.",
    ]:
        bullet(p, item)

    p = pdf.new_page("Global Controls", "What the top filters mean")
    metric_box(p, MARGIN_X, 640, "Category", "mens_tshirts, womens_dresses, or All")
    metric_box(p, MARGIN_X + 260, 640, "Platform", "Amazon, Nordstrom, or All")
    metric_box(p, MARGIN_X, 560, "Window", "UI control for business context; most current panels read the active DB snapshot")
    metric_box(p, MARGIN_X + 260, 560, "Cache", "Streamlit caches DB helper output for 300 seconds")
    p.y = 520
    h2(p, "How filters affect every layer")
    para(
        p,
        "The selected platform and category are passed into load_products() and load_variant_skus(). That means each tab is grounded in the same filtered slice of the database.",
    )
    h2(p, "Demo tip")
    para(
        p,
        "If new scrape data was ingested but the UI still looks empty, clear Streamlit cache or restart the app. The helper functions use st.cache_data with a five-minute TTL.",
    )

    p = pdf.new_page("Descriptive Analysis: What It Means", "This is the most important demo layer")
    callout(
        p,
        "Purpose",
        "Descriptive analysis answers: What is happening in the market right now? Which SKUs, prices, platforms, and attributes already have customer validation?",
        ACCENT,
    )
    h2(p, "Data source")
    para(
        p,
        "Tab 1 uses product rows from load_products() and SKU/variant rows from load_variant_skus(). Product rows are better for product-level summaries; variant rows are better for SKU-level color, size, and price detail.",
    )
    h2(p, "Signal philosophy")
    for item in [
        "Review count is used as a demand proxy because we do not have actual sales.",
        "Rating is used as a quality/satisfaction proxy.",
        "Price bands show where reviewed demand is concentrated.",
        "Attributes show what product features are repeatedly present in validated products.",
        "Platform comparison shows whether a marketplace behaves more like a volume channel or premium channel.",
    ]:
        bullet(p, item)
    callout(
        p,
        "How to say it",
        "This layer does not claim true sales. It reads market validation from reviews, ratings, price, and SKU availability.",
        WARNING,
    )

    p = pdf.new_page("Descriptive: Top Signal Band", "Four cards at the top of the dashboard")
    h2(p, "Trending Styles Detected")
    para(p, "Shows SKU/variant count when variants exist; otherwise product count. It tells the viewer how much market surface area is being analyzed.")
    h2(p, "Converting Price Band")
    para(p, "Prices are grouped into bands, then weighted by review_count. The winning band is where reviewed demand is most concentrated.")
    para(p, "Calculation concept: group current_price into bands, sum review_count per band, pick the highest-share band.")
    h2(p, "Top Rising Attribute")
    para(p, "Comes from trend_scores after predictions run. It picks the attribute with strongest positive review growth or momentum for the active filter.")
    h2(p, "Top Declining Attribute")
    para(p, "Also comes from trend_scores. It identifies the attribute with weakest or negative movement, useful for markdown or exit thinking.")
    callout(
        p,
        "Demo framing",
        "These cards act like an executive summary: market size, best price corridor, strongest attribute, and weakest attribute.",
        SUCCESS,
    )

    p = pdf.new_page("Descriptive: Trending Styles", "How the top SKU cards are calculated")
    h2(p, "What the viewer sees")
    para(p, "Four product/SKU cards with title, color, material, fit, pattern, size, price, platform, and review count.")
    h2(p, "Calculation")
    para(p, "The function _top_skus() builds a score:")
    callout(p, "Score formula", "score = review_count * 0.75 + rating * 150", ACCENT)
    h2(p, "Why this works for demo")
    for item in [
        "High review count means broad market validation.",
        "High rating boosts products that are not only popular but also liked.",
        "The result is a practical proxy for best-performing visible styles.",
        "Rows are deduplicated by product/color when possible, so one product does not dominate only because it has many size variants.",
    ]:
        bullet(p, item)
    h2(p, "How to say it")
    para(p, "These are not random scraped products. They are ranked by customer validation: reviews plus satisfaction.")

    p = pdf.new_page("Descriptive: Price-Band Performance", "Converting corridor and premium positioning")
    h2(p, "What the panel shows")
    para(p, "A grid by platform/category group and price band: Under, Value, Sweet, Premium, High, Luxury.")
    h2(p, "Price bands")
    for item in ["<$20 = Under", "$20-24 = Value", "$24-32 = Sweet", "$32-45 = Premium", "$45-60 = High", ">$60 = Luxury"]:
        bullet(p, item)
    h2(p, "Calculation")
    para(p, "Each product is assigned to a price band using current_price. The panel sums review_count within each band. If review_count is missing, each product receives equal weight.")
    h2(p, "Interpretation")
    for item in [
        "The hottest cell is the band with the highest share of reviewed demand for that platform/category.",
        "Median price is shown to explain where the platform is naturally positioned.",
        "The converting corridor is the price zone where customer engagement is already strongest.",
    ]:
        bullet(p, item)

    p = pdf.new_page("Descriptive: Platform Comparison", "Volume play vs premium play")
    h2(p, "Volume Play")
    para(p, "A platform is marked Volume Play when its total review volume is at or above the average platform review volume in the current filter. It means broader demand and faster movement.")
    h2(p, "Premium Play")
    para(p, "A platform is marked Premium Play when review volume is below the average platform threshold. In context, this often means curated assortment, higher median price, or margin/brand positioning rather than mass velocity.")
    h2(p, "Other fields")
    for item in [
        "Median price: platform price positioning.",
        "Top color: most frequent color family in the platform slice.",
        "Top fit: most frequent fit signal.",
        "Top material: leading material signal.",
        "Average reviews per SKU: average customer validation per listing/SKU.",
    ]:
        bullet(p, item)
    callout(
        p,
        "Demo phrase",
        "Amazon usually tells us volume behavior; Nordstrom often helps us understand premium or curated behavior. The dashboard lets the data decide per filter.",
        ACCENT,
    )

    p = pdf.new_page("Descriptive: Attribute Performance", "Why attributes matter")
    h2(p, "What the panel shows")
    para(p, "Attribute tabs show top color family, pattern, material, neck type, fit, and sleeve type.")
    h2(p, "Calculation")
    para(p, "The function _attribute_rows() splits multi-value attributes, explodes them into individual rows, weights by review_count, groups by attribute value, and calculates each value's share inside the top group.")
    h2(p, "Interpretation")
    for item in [
        "Color family: useful for buy depth and assortment color planning.",
        "Pattern: helps decide solid, floral, graphic, stripe, etc.",
        "Material: helps with fabric and quality positioning.",
        "Neck, fit, sleeve: silhouette and design direction.",
        "Review weighting means validated products matter more than low-signal products.",
    ]:
        bullet(p, item)
    callout(p, "Demo phrase", "This is the bridge from products to design decisions: which features are attached to market-validated SKUs?", SUCCESS)

    p = pdf.new_page("Conversational Intelligence", "Ask the market analyst")
    h2(p, "Purpose")
    para(p, "This layer lets a merchant ask natural-language questions while staying grounded in the selected data slice.")
    h2(p, "What is sent to the LLM")
    for item in [
        "Total products, platforms, categories, average price, average rating, and total reviews.",
        "Top colors, patterns, materials, neck types, and fits.",
        "Price band distribution and platform comparison.",
        "The active category and platform filters.",
    ]:
        bullet(p, item)
    h2(p, "Answer format")
    para(p, "The system prompt asks for Key Finding, Supporting Data, and Implication. If data is insufficient, it should say so instead of inventing.")
    callout(p, "Demo phrase", "This converts the dashboard from click-only analytics into an analyst you can question.", ACCENT)

    p = pdf.new_page("Predictive Intelligence", "Trend lifecycle ideology")
    h2(p, "Purpose")
    para(p, "Predictive analysis answers: What is changing, where is the trend in its lifecycle, and what should the retailer do next?")
    h2(p, "Trend score inputs")
    for item in [
        "Rating delta: attribute average rating compared with category average.",
        "Review velocity proxy: review count compared with category baseline.",
        "Product share: how much of the category contains this attribute.",
    ]:
        bullet(p, item)
    callout(p, "Momentum formula", "0.40 rating + 0.35 review velocity + 0.25 product share", ACCENT)
    h2(p, "Lifecycle stages")
    for item in [
        "Emerging: test buy, small quantity, fast turn.",
        "Accelerating: load up.",
        "Peak: maintain, prepare exit.",
        "Plateau: maintain core quantity, monitor weekly.",
        "Declining: mark down, clear.",
        "Dead: stop reorder, liquidate residual stock.",
    ]:
        bullet(p, item)

    p = pdf.new_page("Predictive Modes", "How weekly scrape history changes the analysis")
    h2(p, "Timing field")
    para(p, "Trend timing is based on scraped_at, especially product_variants.scraped_at. This is the correct field because every scrape represents a market observation.")
    h2(p, "Modes")
    for item in [
        "1 scrape week: snapshot baseline. Stage is inferred from current momentum because no comparison exists.",
        "2 scrape weeks: previous scrape week vs current scrape week comparison.",
        "3+ scrape weeks: full lifecycle curve classification.",
    ]:
        bullet(p, item)
    h2(p, "Other predictive panels")
    for item in [
        "Review-Velocity Forecast: intended to show review momentum over time as a sales proxy.",
        "Price-Band Momentum Forecast: intended to track demand movement by price corridor.",
        "Whitespace: intended to detect high demand with low supply.",
        "Early-Signal Detection: intended to flag movement before broad consensus.",
    ]:
        bullet(p, item)
    callout(p, "Demo caveat", "The more weekly scrapes we collect, the stronger the predictive layer becomes.", WARNING)

    p = pdf.new_page("Recommendation Intelligence", "Turning analysis into action")
    h2(p, "Flow")
    for item in [
        "Run predictions to populate trend_scores.",
        "pattern_detector.py finds actionable patterns.",
        "claude_drafter.py turns patterns into structured recommendations.",
        "recommendation_store.py saves the action queue.",
        "Streamlit lets users accept, dismiss, or modify recommendations.",
    ]:
        bullet(p, item)
    h2(p, "Pattern types")
    for item in [
        "Emerging Star: high momentum, good rating, strong reviews.",
        "Declining Attribute: weak lifecycle or negative momentum.",
        "Underserved Niche: high rating but low product count.",
        "Review Leader: very high review count.",
        "Cross-Platform Gap: strong on one platform, weak on another.",
        "Rating Outlier: rating far above or below category average.",
    ]:
        bullet(p, item)
    callout(p, "Demo phrase", "This is where analytics becomes workflow: every insight becomes an action with evidence and confidence.", SUCCESS)

    p = pdf.new_page("Demo Talk Track", "A clean 8-10 minute flow")
    h2(p, "1. Start with the system")
    para(p, "This project scrapes marketplace apparel data and turns it into product and market intelligence for merchants.")
    h2(p, "2. Show Descriptive first")
    para(p, "Explain current market snapshot: top SKUs, converting price bands, platform positioning, and attribute performance.")
    h2(p, "3. Explain Volume vs Premium")
    para(p, "Volume Play means stronger review volume and broad demand. Premium Play means lower volume but potential margin/curation positioning.")
    h2(p, "4. Show Conversational")
    para(p, "Ask a question like: Which attributes explain the strongest SKUs? Mention that answers cite the active data context.")
    h2(p, "5. Show Predictive")
    para(p, "Explain lifecycle modeling and retailer actions. With two scrape weeks, it compares previous week vs current week; with three or more, it models the curve.")
    h2(p, "6. Show Recommendations")
    para(p, "Run or show generated recommendations as the final action layer: observation, action, impact, confidence.")
    callout(p, "Closing line", "The end goal is not scraping. The end goal is faster, evidence-backed merchandising decisions.", ACCENT)

    return pdf


if __name__ == "__main__":
    pdf = build_pdf()
    pdf.write(OUT)
    print(OUT)
