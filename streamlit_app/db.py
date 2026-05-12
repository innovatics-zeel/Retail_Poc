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
    """Return category-platform daily review time series for Tab 3 chart."""
    db = _session()
    try:
        rows = db.execute(text("""
            SELECT
                cat.name                               AS category,
                pl.name                                AS platform,
                DATE_TRUNC('day', r.scraped_at)::date  AS day,
                SUM(r.review_count)                    AS total_reviews
            FROM product_review_snapshots r
            JOIN products p     ON p.product_id    = r.product_id
            JOIN categories cat ON cat.category_id = p.category_id
            JOIN platforms  pl  ON pl.id           = p.platform_id
            GROUP BY cat.name, pl.name, DATE_TRUNC('day', r.scraped_at)
            ORDER BY cat.name, pl.name, day
        """)).mappings().fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def _scope_where(platform: str = None, category: str = None, alias: str = "pl") -> tuple[str, dict]:
    conditions, params = [], {}
    if platform and platform != "All":
        conditions.append(f"{alias}.name = :platform")
        params["platform"] = platform
    if category and category != "All":
        conditions.append("cat.name = :category")
        params["category"] = category
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def _pct_change(current: float, previous: float) -> float:
    if previous is None or previous <= 0:
        return 0.0 if current <= 0 else 100.0
    return round((current - previous) / previous * 100, 1)


def _linear_forecast(values: list[float], periods: int = 7) -> tuple[list[float], float]:
    if not values:
        return [], 0.0
    current = float(values[-1])
    if len(values) < 2:
        return [current] * periods, 0.0
    slope = (float(values[-1]) - float(values[0])) / max(len(values) - 1, 1)
    forecast = [max(0.0, current + slope * (i + 1)) for i in range(periods)]
    return forecast, round(slope, 2)


def _confidence(points: int, magnitude: float) -> str:
    if points >= 5 and abs(magnitude) >= 8:
        return "High"
    if points >= 3 or abs(magnitude) >= 8:
        return "Med"
    return "Low"


def _finite_float(value, default: float = 0.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if pd.notna(value) else default


def load_review_velocity_forecast(platform: str = None, category: str = None) -> list[dict]:
    """Daily review velocity forecast for the active filter."""
    where, params = _scope_where(platform, category)
    db = _session()
    try:
        rows = db.execute(text(f"""
            SELECT
                r.product_id,
                DATE_TRUNC('day', r.scraped_at)::date AS day,
                MAX(r.review_count)                   AS review_count,
                cat.name                              AS category,
                pl.name                               AS platform
            FROM product_review_snapshots r
            JOIN products p      ON p.product_id    = r.product_id
            JOIN categories cat  ON cat.category_id = p.category_id
            JOIN platforms pl    ON pl.id           = p.platform_id
            {where}
            GROUP BY r.product_id, DATE_TRUNC('day', r.scraped_at), cat.name, pl.name
            ORDER BY cat.name, pl.name, day
        """), params).mappings().fetchall()
    finally:
        db.close()

    if not rows:
        return []

    df = pd.DataFrame([dict(r) for r in rows])
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0)

    out = []
    for (cat, plat), grp in df.groupby(["category", "platform"]):
        daily = grp.groupby("day")["review_count"].sum().sort_index()
        if daily.empty:
            continue
        hist_vals = [float(v) for v in daily.tail(14).values]
        forecast, slope = _linear_forecast(hist_vals, 30)
        current = hist_vals[-1]
        previous = hist_vals[-2] if len(hist_vals) >= 2 else current
        actual_pct = _pct_change(current, previous)
        projected_pct = _pct_change(forecast[-1] if forecast else current, current)
        out.append({
            "category": str(cat),
            "platform": str(plat),
            "name": f"{str(plat).title()} · {str(cat).replace('_', ' ').title()}",
            "current_reviews": int(current),
            "actual_change_pct": actual_pct,
            "projected_change_pct": projected_pct,
            "slope": slope,
            "hist_days": [str(d.date()) for d in daily.tail(14).index],
            "hist_vals": hist_vals,
            "future_vals": [round(v, 1) for v in forecast],
            "confidence": _confidence(len(hist_vals), projected_pct),
        })
    return sorted(out, key=lambda r: r["projected_change_pct"], reverse=True)


def _band_edges_for_prices(prices: pd.Series) -> list[tuple[str, float | None]]:
    clean = pd.to_numeric(prices, errors="coerce").dropna()
    median = float(clean.median()) if not clean.empty else 40.0
    if median >= 75:
        return [("<$50", 50), ("$50-100", 100), ("$100-150", 150),
                ("$150-250", 250), ("$250-400", 400), (">$400", None)]
    return [("<$20", 20), ("$20-24", 24), ("$24-32", 32),
            ("$32-45", 45), ("$45-60", 60), (">$60", None)]


def _band_label(price, bands: list[tuple[str, float | None]]) -> str:
    try:
        price = float(price)
    except (TypeError, ValueError):
        return "Unknown"
    for label, upper in bands:
        if upper is None or price < upper:
            return label
    return bands[-1][0]


def _variant_history(platform: str = None, category: str = None) -> pd.DataFrame:
    where, params = _scope_where(platform, category)
    db = _session()
    try:
        rows = db.execute(text(f"""
            SELECT
                pv.variant_id,
                pv.product_id,
                pv.color_id,
                pv.size_id,
                vs.price,
                vs.is_available,
                vs.scraped_at AS observed_at,
                DATE_TRUNC('day', vs.scraped_at)::date AS day,
                cat.name AS category,
                pl.name AS platform,
                c.color_family,
                c.name AS color,
                s.label AS size,
                COALESCE(mat.name, p.material) AS material,
                COALESCE(ft.name, p.fit) AS fit,
                COALESCE(nt.name, p.neck_type) AS neck_type,
                COALESCE(st.name, p.sleeve_type) AS sleeve_type,
                COALESCE(pat.name, p.pattern) AS pattern,
                r.rating_avg AS rating,
                r.review_count
            FROM variant_snapshots vs
            JOIN product_variants pv ON pv.variant_id = vs.variant_id
            JOIN products p      ON p.product_id    = pv.product_id
            JOIN platforms pl    ON pl.id           = p.platform_id
            LEFT JOIN categories cat ON cat.category_id = p.category_id
            LEFT JOIN colors c       ON c.color_id      = pv.color_id
            LEFT JOIN sizes s        ON s.size_id       = pv.size_id
            LEFT JOIN materials mat  ON mat.material_id = pv.material_id
            LEFT JOIN fits ft        ON ft.fit_id       = pv.fit_id
            LEFT JOIN neck_types nt  ON nt.neck_type_id = pv.neck_type_id
            LEFT JOIN sleeve_types st ON st.sleeve_type_id = pv.sleeve_type_id
            LEFT JOIN patterns pat   ON pat.pattern_id  = pv.pattern_id
            LEFT JOIN LATERAL (
                SELECT rating_avg, review_count
                FROM product_review_snapshots
                WHERE product_id = p.product_id
                  AND scraped_at <= vs.scraped_at + INTERVAL '1 day'
                ORDER BY scraped_at DESC
                LIMIT 1
            ) r ON TRUE
            {where}
            ORDER BY vs.scraped_at, pv.variant_id
        """), params).mappings().fetchall()
    finally:
        db.close()

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df["observed_at"] = pd.to_datetime(df["observed_at"], errors="coerce")
    for col in ("price", "rating", "review_count"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values(["observed_at", "variant_id"])
    return df.drop_duplicates(
        subset=["product_id", "color_id", "size_id", "day"],
        keep="last",
    )


def load_price_band_momentum(platform: str = None, category: str = None) -> list[dict]:
    """Daily price-band momentum based on variant observations."""
    df = _variant_history(platform, category)
    if df.empty or "price" not in df.columns:
        return []
    df = df.dropna(subset=["price", "day"]).copy()
    if df.empty:
        return []

    out = []
    for (cat, plat), scope in df.groupby(["category", "platform"]):
        bands = _band_edges_for_prices(scope["price"])
        band_order = [b[0] for b in bands]
        scope = scope.copy()
        scope["band"] = scope["price"].apply(lambda p: _band_label(p, bands))

        totals = scope.groupby("day")["variant_id"].nunique().sort_index()
        daily = (
            scope.groupby(["day", "band"])
            .agg(
                variant_count=("variant_id", "nunique"),
                avg_price=("price", "mean"),
                avg_rating=("rating", "mean"),
                review_count=("review_count", "sum"),
            )
            .reset_index()
        )

        for band in band_order:
            grp = daily[daily["band"] == band].set_index("day").sort_index()
            if grp.empty:
                continue
            shares = (grp["variant_count"] / totals.reindex(grp.index).fillna(1).clip(lower=1)).fillna(0)
            latest_share = float(shares.iloc[-1])
            previous_share = float(shares.iloc[-2]) if len(shares) >= 2 else latest_share
            change = round((latest_share - previous_share) * 100, 1)
            forecast, slope = _linear_forecast([float(v) for v in shares.tail(14).values], 30)
            projected_change = round(((forecast[-1] if forecast else latest_share) - latest_share) * 100, 1)
            momentum = change if abs(change) >= abs(projected_change) else projected_change
            stage = "accelerating" if momentum >= 3 else "declining" if momentum <= -3 else "plateau"
            action = (
                "Expand buy depth in this price corridor"
                if stage == "accelerating" else
                "Reduce exposure or markdown test"
                if stage == "declining" else
                "Maintain and monitor daily"
            )
            out.append({
                "category": str(cat),
                "platform": str(plat),
                "name": band,
                "change": int(round(momentum)),
                "stage": stage,
                "action": action,
                "confidence": _confidence(len(shares), momentum),
                "latest_share": round(latest_share, 4),
                "previous_share": round(previous_share, 4),
                "avg_price": round(_finite_float(grp["avg_price"].iloc[-1]), 2),
                "review_count": int(grp["review_count"].fillna(0).iloc[-1]),
            })
    return sorted(out, key=lambda r: r["change"], reverse=True)


def load_whitespace_scores(platform: str = None, category: str = None) -> list[dict]:
    """Find high-demand, low-saturation attribute pockets from latest variant data."""
    df = _variant_history(platform, category)
    if df.empty:
        return []
    latest_day = df["day"].dropna().max()
    if pd.isna(latest_day):
        return []
    current = df[df["day"] == latest_day].copy()
    previous_day = df[df["day"] < latest_day]["day"].dropna().max()
    previous = df[df["day"] == previous_day].copy() if pd.notna(previous_day) else pd.DataFrame()

    attrs = ["color_family", "material", "fit", "pattern", "neck_type", "sleeve_type"]
    out = []
    total_variants = max(current["variant_id"].nunique(), 1)
    avg_reviews = _finite_float(current["review_count"].fillna(0).mean())
    avg_rating = _finite_float(current["rating"].dropna().mean())

    for attr in attrs:
        if attr not in current.columns:
            continue
        work = current.dropna(subset=[attr]).copy()
        if work.empty:
            continue
        work[attr] = work[attr].astype(str).str.split(r",\s*")
        work = work.explode(attr)
        work[attr] = work[attr].astype(str).str.strip()
        work = work[(work[attr] != "") & (work[attr].str.lower() != "nan")]
        if work.empty:
            continue

        prev_counts = pd.Series(dtype=float)
        if not previous.empty and attr in previous.columns:
            prev_work = previous.dropna(subset=[attr]).copy()
            prev_work[attr] = prev_work[attr].astype(str).str.split(r",\s*")
            prev_work = prev_work.explode(attr)
            prev_work[attr] = prev_work[attr].astype(str).str.strip()
            prev_total = max(prev_work["variant_id"].nunique(), 1)
            prev_counts = prev_work.groupby(attr)["variant_id"].nunique() / prev_total

        grouped = (
            work.groupby(attr)
            .agg(
                variant_count=("variant_id", "nunique"),
                product_count=("product_id", "nunique"),
                avg_rating=("rating", "mean"),
                avg_reviews=("review_count", "mean"),
            )
            .reset_index()
        )
        for _, row in grouped.iterrows():
            name = str(row[attr])
            share = float(row["variant_count"]) / total_variants
            prev_share = float(prev_counts.get(name, share)) if not prev_counts.empty else share
            change = round((share - prev_share) * 100, 1)
            row_rating = _finite_float(row["avg_rating"], avg_rating)
            row_reviews = _finite_float(row["avg_reviews"])
            rating_score = max(0.0, (row_rating - max(avg_rating, 1)) / 1.5)
            review_score = (row_reviews / max(avg_reviews, 1)) - 1
            demand = max(0.0, min(1.0, 0.55 + rating_score * 0.25 + review_score * 0.20))
            saturation = int(round(share * 100))
            whitespace = demand * (1 - min(share, 0.95))
            rol = max(0.1, whitespace * 4)
            if float(row["variant_count"]) < 1:
                continue
            out.append({
                "attr_key": attr,
                "name": name,
                "change": int(round(change)),
                "saturation": saturation,
                "new_listing_rol": round(rol, 1),
                "demand_score": round(demand, 3),
                "variant_count": int(row["variant_count"]),
                "avg_rating": round(row_rating, 2),
                "avg_reviews": round(row_reviews, 1),
            })

    return sorted(
        out,
        key=lambda r: (r["new_listing_rol"], -r["saturation"], r["change"]),
        reverse=True,
    )


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
