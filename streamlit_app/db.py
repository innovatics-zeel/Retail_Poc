"""
db.py — Database query helpers for the Streamlit app.
Reads from the normalized schema: products, product_variants, reviews,
brands, categories, colors, sizes, platforms.
"""
import sys
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, ".")
from database.connection import SessionLocal

MAX_REALISTIC_REVIEW_COUNT = 1_000_000


def _session():
    return SessionLocal()


def _clean_review_count(value) -> int:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return count if 0 <= count < MAX_REALISTIC_REVIEW_COUNT else 0


def _pickle_safe_image(value):
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytearray):
        return bytes(value)
    return value


# ── Main product query (joins all 7 normalized tables) ────────────────────────

_LOAD_SQL = """
WITH current_variants AS (
    SELECT DISTINCT ON (product_id, color_id, size_id)
        *
    FROM product_variants
    ORDER BY product_id, color_id, size_id, scraped_at DESC, variant_id DESC
)
SELECT
    p.product_id,
    p.title,
    p.url,
    p.platform_item_id,
    p.image,
    COALESCE(STRING_AGG(DISTINCT mat.name, ', ' ORDER BY mat.name), p.material) AS material,
    COALESCE(STRING_AGG(DISTINCT nt.name,  ', ' ORDER BY nt.name),  p.neck_type) AS neck_type,
    COALESCE(STRING_AGG(DISTINCT st.name,  ', ' ORDER BY st.name),  p.sleeve_type) AS sleeve_type,
    COALESCE(STRING_AGG(DISTINCT ft.name,  ', ' ORDER BY ft.name),  p.fit) AS fit,
    COALESCE(STRING_AGG(DISTINCT pat.name, ', ' ORDER BY pat.name), p.pattern) AS pattern,
    p.care,
    p.scraped_at,
    pl.name             AS platform,
    pl.display_name     AS platform_display,
    b.name              AS brand,
    cat.name            AS category,
    cat.gender,
    r.rating_avg        AS rating,
    r.review_count,
    MAX(r.fit_feedback::text) AS fit_feedback,
    MAX(r.pros::text) AS pros,
    MAX(r.cons::text) AS cons,
    r.stars_1_pct,
    r.stars_2_pct,
    r.stars_3_pct,
    r.stars_4_pct,
    r.stars_5_pct,
    MIN(pv.price)                                                  AS current_price,
    MAX(pv.original_price)                                         AS original_price,
    AVG(pv.discount_pct)                                           AS discount_pct,
    STRING_AGG(DISTINCT c.name,         ', ' ORDER BY c.name)     AS color,
    STRING_AGG(DISTINCT c.color_family, ', ' ORDER BY c.color_family) AS color_family,
    STRING_AGG(DISTINCT s.label,        ', ')                      AS size,
    BOOL_OR(pv.is_available)                                       AS is_available
FROM products p
JOIN platforms pl        ON pl.id           = p.platform_id
LEFT JOIN brands b       ON b.brand_id      = p.brand_id
LEFT JOIN categories cat ON cat.category_id = p.category_id
LEFT JOIN LATERAL (
    SELECT rating_avg, review_count, fit_feedback, pros, cons,
           stars_1_pct, stars_2_pct, stars_3_pct, stars_4_pct, stars_5_pct
    FROM reviews
    WHERE product_id = p.product_id
    ORDER BY scraped_at DESC
    LIMIT 1
) r ON TRUE
LEFT JOIN current_variants pv ON pv.product_id = p.product_id
LEFT JOIN colors c            ON c.color_id    = pv.color_id
LEFT JOIN sizes  s            ON s.size_id     = pv.size_id
LEFT JOIN materials mat       ON mat.material_id   = pv.material_id
LEFT JOIN neck_types nt       ON nt.neck_type_id   = pv.neck_type_id
LEFT JOIN sleeve_types st     ON st.sleeve_type_id = pv.sleeve_type_id
LEFT JOIN fits ft             ON ft.fit_id         = pv.fit_id
LEFT JOIN patterns pat        ON pat.pattern_id    = pv.pattern_id
{where}
GROUP BY
    p.product_id, p.title, p.url, p.platform_item_id, p.image, p.material,
    p.neck_type, p.sleeve_type, p.fit, p.pattern, p.care, p.scraped_at,
    pl.name, pl.display_name, b.name, cat.name, cat.gender,
    r.rating_avg, r.review_count,
    r.stars_1_pct, r.stars_2_pct, r.stars_3_pct, r.stars_4_pct, r.stars_5_pct
ORDER BY r.review_count DESC NULLS LAST
"""


def load_products(platform: str = None, category: str = None) -> pd.DataFrame:
    db = _session()
    try:
        conditions, params = [], {}
        if platform:
            conditions.append("pl.name = :platform")
            params["platform"] = platform
        if category:
            conditions.append("cat.name = :category")
            params["category"] = category

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = db.execute(text(_LOAD_SQL.format(where=where)), params).mappings().fetchall()
        if not rows:
            return pd.DataFrame()

        records = []
        for r in rows:
            rec = dict(r)
            if "image" in rec:
                rec["image"] = _pickle_safe_image(rec.get("image"))
            for col in ("current_price", "original_price", "discount_pct", "rating"):
                v = rec.get(col)
                rec[col] = float(v) if v is not None else None
            rec["review_count"] = _clean_review_count(rec.get("review_count"))
            records.append(rec)

        return pd.DataFrame(records)
    finally:
        db.close()


_VARIANT_SQL = """
WITH current_variants AS (
    SELECT DISTINCT ON (product_id, color_id, size_id)
        *
    FROM product_variants
    ORDER BY product_id, color_id, size_id, scraped_at DESC, variant_id DESC
)
SELECT
    pv.variant_id,
    pv.product_id,
    CONCAT(pl.name, '-', p.product_id, '-', pv.variant_id) AS sku_code,
    p.title,
    p.url,
    p.platform_item_id,
    p.image,
    COALESCE(mat.name, p.material)       AS material,
    COALESCE(nt.name, p.neck_type)       AS neck_type,
    COALESCE(st.name, p.sleeve_type)     AS sleeve_type,
    COALESCE(ft.name, p.fit)             AS fit,
    COALESCE(pat.name, p.pattern)        AS pattern,
    p.scraped_at       AS product_scraped_at,
    pl.name            AS platform,
    pl.display_name    AS platform_display,
    b.name             AS brand,
    cat.name           AS category,
    cat.gender,
    c.name             AS color,
    c.color_family,
    s.label            AS size,
    pv.is_available,
    pv.price           AS current_price,
    pv.original_price,
    pv.discount_pct,
    pv.currency,
    pv.low_stock,
    pv.stock_note,
    pv.scraped_at      AS variant_scraped_at,
    r.rating_avg       AS rating,
    r.review_count,
    r.fit_feedback,
    r.pros,
    r.cons,
    r.stars_1_pct,
    r.stars_2_pct,
    r.stars_3_pct,
    r.stars_4_pct,
    r.stars_5_pct
FROM current_variants pv
JOIN products p          ON p.product_id    = pv.product_id
JOIN platforms pl        ON pl.id           = p.platform_id
LEFT JOIN brands b       ON b.brand_id      = p.brand_id
LEFT JOIN categories cat ON cat.category_id = p.category_id
LEFT JOIN colors c       ON c.color_id      = pv.color_id
LEFT JOIN sizes s        ON s.size_id       = pv.size_id
LEFT JOIN materials mat  ON mat.material_id = pv.material_id
LEFT JOIN neck_types nt  ON nt.neck_type_id = pv.neck_type_id
LEFT JOIN sleeve_types st ON st.sleeve_type_id = pv.sleeve_type_id
LEFT JOIN fits ft        ON ft.fit_id       = pv.fit_id
LEFT JOIN patterns pat   ON pat.pattern_id  = pv.pattern_id
LEFT JOIN LATERAL (
    SELECT rating_avg, review_count, fit_feedback, pros, cons,
           stars_1_pct, stars_2_pct, stars_3_pct, stars_4_pct, stars_5_pct
    FROM reviews
    WHERE product_id = p.product_id
    ORDER BY scraped_at DESC
    LIMIT 1
) r ON TRUE
{where}
ORDER BY r.review_count DESC NULLS LAST, pv.variant_id
"""


def load_variant_skus(platform: str = None, category: str = None) -> pd.DataFrame:
    """Return one row per saved product variant/SKU."""
    db = _session()
    try:
        conditions, params = [], {}
        if platform:
            conditions.append("pl.name = :platform")
            params["platform"] = platform
        if category:
            conditions.append("cat.name = :category")
            params["category"] = category

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = db.execute(text(_VARIANT_SQL.format(where=where)), params).mappings().fetchall()
        if not rows:
            return pd.DataFrame()

        records = []
        for r in rows:
            rec = dict(r)
            if "image" in rec:
                rec["image"] = _pickle_safe_image(rec.get("image"))
            for col in ("current_price", "original_price", "discount_pct", "rating"):
                v = rec.get(col)
                rec[col] = float(v) if v is not None else None
            rec["review_count"] = _clean_review_count(rec.get("review_count"))
            records.append(rec)
        return pd.DataFrame(records)
    finally:
        db.close()


# ── KPI helpers ───────────────────────────────────────────────────────────────

def get_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total": 0, "avg_price": 0, "avg_rating": 0,
                "total_reviews": 0, "platforms": 0, "brands": 0}
    return {
        "total":         len(df),
        "avg_price":     round(float(df["current_price"].dropna().mean()), 2)
                         if "current_price" in df.columns else 0,
        "avg_rating":    round(float(df["rating"].dropna().mean()), 2)
                         if "rating" in df.columns else 0,
        "total_reviews": int(df["review_count"].fillna(0).sum()),
        "platforms":     df["platform"].nunique() if "platform" in df.columns else 0,
        "brands":        df["brand"].nunique() if "brand" in df.columns else 0,
    }


def attribute_counts(df: pd.DataFrame, col: str, top_n: int = 10) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return pd.DataFrame(columns=[col, "count"])
    counts = (
        df[col].dropna()
        .str.split(r",\s*")
        .explode()
        .str.strip()
        .value_counts()
        .head(top_n)
    )
    return pd.DataFrame({col: counts.index.tolist(), "count": counts.values.tolist()})


def price_bands(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "current_price" not in df.columns:
        return pd.DataFrame()
    bins   = [0, 25, 50, 75, 100, 150, 200, 9999]
    labels = ["<$25", "$25-50", "$50-75", "$75-100", "$100-150", "$150-200", "$200+"]
    cut = pd.cut(df["current_price"].dropna(), bins=bins, labels=labels)
    counts = cut.value_counts().sort_index()
    return pd.DataFrame({"band": counts.index.astype(str), "count": counts.values.tolist()})


def platform_comparison(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby("platform")
        .agg(
            products     =("url",           "count"),
            avg_price    =("current_price", "mean"),
            avg_rating   =("rating",        "mean"),
            total_reviews=("review_count",  "sum"),
            brands       =("brand",         "nunique"),
        )
        .round(2)
        .reset_index()
    )


def top_products(df: pd.DataFrame, by: str = "review_count", n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = ["title", "brand", "platform", "category",
            "current_price", "rating", "review_count", "url"]
    cols = [c for c in cols if c in df.columns]
    return df[cols].dropna(subset=[by]).nlargest(n, by).reset_index(drop=True)


def color_family_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Products per color family, useful for the sidebar filter and charts."""
    return attribute_counts(df, "color_family", top_n=15)


def save_feedback(recommendation_text: str, action: str,
                  category: str = None, modified_text: str = None):
    db = _session()
    try:
        db.execute(
            text("""INSERT INTO recommendation_feedback
                    (recommendation_text, category, action, modified_text)
                    VALUES (:t, :c, :a, :m)"""),
            {"t": recommendation_text, "c": category, "a": action, "m": modified_text},
        )
        db.commit()
    finally:
        db.close()


# ── Trend scores & recommendations ───────────────────────────────────────────

def load_trend_scores(category: str = None, platform: str = None,
                      attr_key: str = None) -> pd.DataFrame:
    db = _session()
    try:
        conditions, params = [], {}
        if category and category != "All":
            conditions.append("category = :category")
            params["category"] = category
        if platform and platform != "All":
            conditions.append("platform = :platform")
            params["platform"] = platform
        if attr_key:
            conditions.append("attr_key = :attr_key")
            params["attr_key"] = attr_key
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = db.execute(
            text(f"SELECT * FROM trend_scores {where} ORDER BY momentum_score DESC"),
            params,
        ).mappings().fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        for col in ("momentum_score", "avg_rating", "category_avg_rating",
                    "rating_delta", "review_growth_pct", "latest_week_share",
                    "previous_week_share"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "weeks_observed" in df.columns:
            df["weeks_observed"] = pd.to_numeric(df["weeks_observed"], errors="coerce").fillna(0).astype(int)
        return df
    finally:
        db.close()


def load_recommendations(category: str = None, platform: str = None,
                         status: str = None, limit: int = 30) -> list[dict]:
    db = _session()
    try:
        conditions, params = [], {"limit": limit}
        if category and category != "All":
            conditions.append("category = :category")
            params["category"] = category
        if platform and platform != "All":
            conditions.append("platform ILIKE :platform")
            params["platform"] = f"%{platform}%"
        if status:
            conditions.append("status = :status")
            params["status"] = status
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = db.execute(
            text(f"""SELECT * FROM recommendations {where}
                     ORDER BY generated_at DESC LIMIT :limit"""),
            params,
        ).mappings().fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def update_recommendation_status(rec_id: int, status: str,
                                  modified_text: str = None) -> None:
    db = _session()
    try:
        db.execute(
            text("""UPDATE recommendations
                    SET status = :status, modified_text = :mt, actioned_at = NOW()
                    WHERE rec_id = :rid"""),
            {"status": status, "mt": modified_text, "rid": rec_id},
        )
        db.commit()
    finally:
        db.close()


def load_review_velocity() -> list[dict]:
    """Return category-platform weekly review time series for Tab 3 chart."""
    db = _session()
    try:
        rows = db.execute(text("""
            SELECT
                cat.name                               AS category,
                pl.name                                AS platform,
                DATE_TRUNC('week', r.scraped_at)::date AS week,
                SUM(r.review_count)                    AS total_reviews
            FROM reviews r
            JOIN products p     ON p.product_id    = r.product_id
            JOIN categories cat ON cat.category_id = p.category_id
            JOIN platforms  pl  ON pl.id           = p.platform_id
            GROUP BY cat.name, pl.name, DATE_TRUNC('week', r.scraped_at)
            ORDER BY cat.name, pl.name, week
        """)).mappings().fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def data_summary_for_llm(df: pd.DataFrame) -> str:
    if df.empty:
        return "No product data available."

    kpis = get_kpis(df)
    lines = [
        f"Total products: {kpis['total']}",
        f"Platforms: {', '.join(df['platform'].value_counts().to_dict().keys())} "
        f"({', '.join(f'{k}: {v}' for k, v in df['platform'].value_counts().items())})",
        f"Categories: {', '.join(df['category'].dropna().value_counts().to_dict().keys())}",
        f"Avg price: ${kpis['avg_price']}",
        f"Avg rating: {kpis['avg_rating']} / 5",
        f"Total reviews: {kpis['total_reviews']:,}",
    ]

    for col, label in [
        ("color_family", "Top color families"),
        ("color",        "Top colors"),
        ("pattern",      "Top patterns"),
        ("material",     "Top materials"),
        ("neck_type",    "Top neck types"),
        ("fit",          "Top fits"),
    ]:
        counts = attribute_counts(df, col, top_n=5)
        if not counts.empty:
            items = ", ".join(f"{r[col]} ({r['count']})" for _, r in counts.iterrows())
            lines.append(f"{label}: {items}")

    pb = price_bands(df)
    if not pb.empty:
        band_str = ", ".join(f"{r.iloc[0]}: {int(r.iloc[1])}" for _, r in pb.iterrows())
        lines.append(f"Price bands: {band_str}")

    pc = platform_comparison(df)
    if not pc.empty:
        for _, row in pc.iterrows():
            lines.append(
                f"{row['platform'].title()}: {int(row['products'])} products, "
                f"avg ${row['avg_price']:.0f}, avg rating {row['avg_rating']:.1f}"
            )

    return "\n".join(lines)
