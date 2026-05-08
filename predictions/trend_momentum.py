"""
trend_momentum.py — Computes momentum scores for attribute combinations.

For each (category, platform, attr_key, attr_value):
  - avg_rating vs category_avg_rating  → rating_delta
  - review count vs category mean      → review velocity signal
  - product share within category      → new_product_share
  - weekly attribute share curve        → lifecycle stage + retailer action

Momentum score is a weighted composite in [-1, 1]:
  0.40 × rating_component + 0.35 × velocity_component + 0.25 × share_component

Score threshold: >0.15 = Rising, <-0.10 = Falling, else Stable
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy import text

from database.connection import SessionLocal

ATTR_KEYS = ["color_family", "pattern", "material", "fit", "neck_type", "sleeve_type"]

RETAIL_ACTIONS = {
    "emerging":     "Test buy: small qty, fast turn",
    "accelerating": "Load up",
    "peak":         "Maintain, prepare exit",
    "plateau":      "Maintain core qty, monitor weekly",
    "declining":    "Mark down, clear",
    "dead":         "Stop reorder, liquidate residual stock",
}

_WEIGHTS = {"rating": 0.40, "velocity": 0.35, "share": 0.25}

_LOAD_SQL = """
WITH current_variants AS (
    SELECT DISTINCT ON (product_id, color_id, size_id)
        *
    FROM product_variants
    ORDER BY product_id, color_id, size_id, scraped_at DESC, variant_id DESC
)
SELECT
    p.product_id,
    COALESCE(pat.name, p.pattern)        AS pattern,
    COALESCE(mat.name, p.material)       AS material,
    COALESCE(nt.name, p.neck_type)       AS neck_type,
    COALESCE(st.name, p.sleeve_type)     AS sleeve_type,
    COALESCE(ft.name, p.fit)             AS fit,
    COALESCE(pv.scraped_at, p.scraped_at) AS observed_at,
    pl.name          AS platform,
    cat.name         AS category,
    r.rating_avg     AS rating,
    r.review_count,
    c.color_family
FROM products p
JOIN platforms pl        ON pl.id           = p.platform_id
JOIN categories cat      ON cat.category_id = p.category_id
LEFT JOIN LATERAL (
    SELECT rating_avg, review_count
    FROM reviews WHERE product_id = p.product_id
    ORDER BY scraped_at DESC LIMIT 1
) r ON TRUE
LEFT JOIN current_variants pv ON pv.product_id = p.product_id
LEFT JOIN colors c            ON c.color_id    = pv.color_id
LEFT JOIN materials mat       ON mat.material_id   = pv.material_id
LEFT JOIN neck_types nt       ON nt.neck_type_id   = pv.neck_type_id
LEFT JOIN sleeve_types st     ON st.sleeve_type_id = pv.sleeve_type_id
LEFT JOIN fits ft             ON ft.fit_id         = pv.fit_id
LEFT JOIN patterns pat        ON pat.pattern_id    = pv.pattern_id
"""


def _load_df() -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = db.execute(text(_LOAD_SQL)).mappings().fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        for col in ("rating", "review_count"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["observed_at"] = pd.to_datetime(df["observed_at"], errors="coerce", utc=True)
        df["observed_week"] = df["observed_at"].dt.tz_convert(None).dt.to_period("W").dt.start_time
        # Deduplicate product × color × week; product_variants can fan out by size.
        df = df.drop_duplicates(subset=["product_id", "color_family", "observed_week"])
        return df
    finally:
        db.close()


def _clip_norm(val: float, lo: float, hi: float) -> float:
    """Scale val from [lo, hi] to [-1, 1]."""
    if hi == lo:
        return 0.0
    return max(-1.0, min(1.0, 2 * (val - lo) / (hi - lo) - 1))


def _attr_frame(df: pd.DataFrame, attr_key: str) -> pd.DataFrame:
    cols = [
        "product_id", "category", "platform", "observed_week",
        attr_key, "rating", "review_count",
    ]
    exploded = df[[c for c in cols if c in df.columns]].copy()
    exploded = exploded.dropna(subset=[attr_key])

    if attr_key != "color_family":
        exploded[attr_key] = exploded[attr_key].astype(str).str.split(r",\s*")
        exploded = exploded.explode(attr_key)
        exploded[attr_key] = exploded[attr_key].str.strip()
    else:
        exploded[attr_key] = exploded[attr_key].astype(str).str.strip()

    exploded = exploded[exploded[attr_key].str.len() > 0]
    return exploded


def _weekly_lifecycle(df: pd.DataFrame, attr_key: str) -> dict[tuple, dict]:
    if "observed_week" not in df.columns or df["observed_week"].isna().all():
        return {}

    attr_df = _attr_frame(df, attr_key)
    if attr_df.empty:
        return {}

    totals = (
        df.dropna(subset=["observed_week"])
        .drop_duplicates(subset=["product_id", "category", "platform", "observed_week"])
        .groupby(["category", "platform", "observed_week"])["product_id"]
        .nunique()
        .rename("total_products")
        .reset_index()
    )

    weekly = (
        attr_df.dropna(subset=["observed_week"])
        .drop_duplicates(subset=["product_id", "category", "platform", attr_key, "observed_week"])
        .groupby(["category", "platform", attr_key, "observed_week"])["product_id"]
        .nunique()
        .rename("product_count")
        .reset_index()
        .merge(totals, on=["category", "platform", "observed_week"], how="left")
    )
    if weekly.empty:
        return {}

    weekly["share"] = weekly["product_count"] / weekly["total_products"].clip(lower=1)
    out: dict[tuple, dict] = {}

    for key, group in weekly.groupby(["category", "platform", attr_key]):
        group = group.sort_values("observed_week")
        weeks = sorted(
            totals[
                (totals["category"] == key[0]) &
                (totals["platform"] == key[1])
            ]["observed_week"].dropna().unique()
        )
        if len(weeks) < 2:
            # A single scrape is a baseline rather than a lifecycle curve.
            # Let current momentum classify the action until weekly history exists.
            continue
        series = (
            group.set_index("observed_week")["share"]
            .reindex(weeks, fill_value=0.0)
            .astype(float)
        )
        if len(weeks) < 3:
            out[(key[0], key[1], attr_key, str(key[2]))] = _two_week_lifecycle(series)
        else:
            out[(key[0], key[1], attr_key, str(key[2]))] = _classify_lifecycle(series)

    return out


def _snapshot_lifecycle(direction: str, momentum: float, new_product_share: float) -> dict:
    if direction == "Falling":
        stage = "declining"
    elif momentum >= 0.35 and new_product_share >= 0.12:
        stage = "accelerating"
    elif direction == "Rising":
        stage = "emerging"
    else:
        stage = "plateau"

    return {
        "lifecycle_stage":       stage,
        "retailer_action":       RETAIL_ACTIONS[stage],
        "lifecycle_explanation": (
            "Snapshot baseline from scraped_at: fewer than 3 weekly scrape points are available, "
            "so stage is inferred from current momentum, rating, review, and share signals."
        ),
        "weeks_observed":        1,
        "latest_week_share":     round(new_product_share, 4),
        "previous_week_share":   0.0,
    }


def _two_week_lifecycle(series: pd.Series) -> dict:
    latest = float(series.iloc[-1])
    previous = float(series.iloc[-2])
    growth = latest - previous

    if latest <= 0 and previous > 0:
        stage = "dead"
    elif growth <= -0.03:
        stage = "declining"
    elif previous <= 0 and latest > 0:
        stage = "emerging"
    elif growth >= 0.03:
        stage = "accelerating"
    else:
        stage = "plateau"

    return {
        "lifecycle_stage":       stage,
        "retailer_action":       RETAIL_ACTIONS[stage],
        "lifecycle_explanation": (
            f"Two-week comparison from scraped_at: current scrape week share is {latest:.1%} "
            f"vs {previous:.1%} in the previous scrape week. Full lifecycle curve starts after 3 weeks."
        ),
        "weeks_observed":        int((series > 0).sum()),
        "latest_week_share":     round(latest, 4),
        "previous_week_share":   round(previous, 4),
    }


def _classify_lifecycle(series: pd.Series) -> dict:
    series = series.dropna()
    if series.empty:
        stage = "dead"
        latest = previous = peak = growth = 0.0
        weeks_observed = 0
    else:
        latest = float(series.iloc[-1])
        previous = float(series.iloc[-2]) if len(series) >= 2 else 0.0
        peak = float(series.max())
        growth = latest - previous
        weeks_observed = int((series > 0).sum())
        recent = series.tail(3)
        recent_std = float(recent.std()) if len(recent) >= 2 else 0.0
        near_peak = peak > 0 and latest >= peak * 0.9

        if latest <= 0 and peak > 0:
            stage = "dead"
        elif growth <= -0.03 or (peak >= 0.08 and latest <= peak * 0.55):
            stage = "declining"
        elif weeks_observed <= 2 and latest > 0:
            stage = "emerging"
        elif growth >= 0.03 and latest < max(peak * 0.9, 0.20):
            stage = "accelerating"
        elif len(recent) >= 3 and recent_std <= 0.02:
            stage = "plateau"
        elif near_peak and (growth >= -0.02 or latest >= 0.25):
            stage = "peak"
        elif growth > 0:
            stage = "accelerating"
        else:
            stage = "plateau"

    explanation = (
        f"Current scrape week share is {latest:.1%} vs {previous:.1%} in the previous scrape week; "
        f"historical peak is {peak:.1%} across {weeks_observed} active week(s)."
    )
    return {
        "lifecycle_stage":      stage,
        "retailer_action":      RETAIL_ACTIONS[stage],
        "lifecycle_explanation": explanation,
        "weeks_observed":       weeks_observed,
        "latest_week_share":    round(latest, 4),
        "previous_week_share":  round(previous, 4),
    }


def _compute_scores(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    cat_stats = (
        df.dropna(subset=["rating", "category"])
        .groupby("category")
        .agg(cat_avg_rating=("rating", "mean"), cat_avg_reviews=("review_count", "mean"))
    )

    scores: list[dict] = []
    lifecycle_by_key: dict[tuple, dict] = {}
    for attr_key in ATTR_KEYS:
        if attr_key in df.columns:
            lifecycle_by_key.update(_weekly_lifecycle(df, attr_key))

    for attr_key in ATTR_KEYS:
        if attr_key not in df.columns:
            continue

        exploded = _attr_frame(df, attr_key)

        # Deduplicate per (product_id, attr_value) before summing review_count
        # — the LEFT JOIN on product_variants fans out one row per variant,
        # so without dedup the review_count is multiplied by the variant count.
        exploded_dedup = exploded.drop_duplicates(subset=["product_id", attr_key])

        grouped = (
            exploded_dedup
            .groupby(["category", "platform", attr_key])
            .agg(
                product_count=("product_id", "nunique"),
                avg_rating=("rating", "mean"),
                avg_reviews=("review_count", "mean"),
                total_reviews=("review_count", "sum"),
            )
            .reset_index()
        )

        for _, row in grouped.iterrows():
            cat = row["category"]
            plat = row["platform"]
            attr_val = str(row[attr_key])
            avg_rating = float(row["avg_rating"]) if pd.notna(row["avg_rating"]) else 0.0
            avg_reviews = float(row["avg_reviews"]) if pd.notna(row["avg_reviews"]) else 0.0
            total_reviews = int(row["total_reviews"]) if pd.notna(row["total_reviews"]) else 0
            product_count = int(row["product_count"])

            cat_row = cat_stats.loc[cat] if cat in cat_stats.index else None
            cat_avg_rating = float(cat_row["cat_avg_rating"]) if cat_row is not None else avg_rating
            cat_avg_reviews = float(cat_row["cat_avg_reviews"]) if cat_row is not None else avg_reviews or 1.0

            rating_delta = avg_rating - cat_avg_rating
            velocity_ratio = (avg_reviews / max(cat_avg_reviews, 1)) - 1.0

            total_cat_prods = len(df[df["category"] == cat]["product_id"].unique())
            new_product_share = product_count / max(total_cat_prods, 1)

            rating_component = _clip_norm(rating_delta, -1.5, 1.5)
            velocity_component = _clip_norm(velocity_ratio, -0.5, 2.0)
            share_component = _clip_norm(new_product_share, 0.0, 0.4)

            momentum = (
                _WEIGHTS["rating"]   * rating_component +
                _WEIGHTS["velocity"] * velocity_component +
                _WEIGHTS["share"]    * share_component
            )

            if momentum > 0.15:
                direction = "Rising"
            elif momentum < -0.10:
                direction = "Falling"
            else:
                direction = "Stable"

            lifecycle = lifecycle_by_key.get(
                (cat, plat, attr_key, attr_val),
                _snapshot_lifecycle(direction, momentum, new_product_share),
            )

            scores.append({
                "category":            cat,
                "platform":            plat,
                "attr_key":            attr_key,
                "attr_value":          attr_val,
                "review_count":        total_reviews,
                "review_growth_pct":   round(velocity_ratio * 100, 2),
                "avg_rating":          round(avg_rating, 2),
                "category_avg_rating": round(cat_avg_rating, 2),
                "rating_delta":        round(rating_delta, 2),
                "product_count":       product_count,
                "new_product_share":   round(new_product_share, 4),
                "momentum_score":      round(momentum, 4),
                "trend_direction":     direction,
                **lifecycle,
            })

    return scores


def _safe(s: dict) -> dict:
    """Clamp values to safe DB ranges before inserting."""
    out = dict(s)
    # review_count: cap at 10M (review_count = INT_MAX signals a scrape error)
    out["review_count"] = min(int(out.get("review_count") or 0), 10_000_000)
    # review_growth_pct: clamp to [-100, 500] — extreme ratios from single-scrape baseline
    pct = float(out.get("review_growth_pct") or 0)
    out["review_growth_pct"] = max(-100.0, min(500.0, round(pct, 2)))
    return out


def _ensure_lifecycle_columns(db) -> None:
    db.execute(text("""
        ALTER TABLE trend_scores
            ADD COLUMN IF NOT EXISTS lifecycle_stage VARCHAR(20),
            ADD COLUMN IF NOT EXISTS retailer_action TEXT,
            ADD COLUMN IF NOT EXISTS lifecycle_explanation TEXT,
            ADD COLUMN IF NOT EXISTS weeks_observed INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS latest_week_share NUMERIC(6, 4),
            ADD COLUMN IF NOT EXISTS previous_week_share NUMERIC(6, 4)
    """))


def write_scores(scores: list[dict]) -> int:
    if not scores:
        return 0
    db = SessionLocal()
    try:
        _ensure_lifecycle_columns(db)
        db.execute(text("DELETE FROM trend_scores"))
        for s in scores:
            db.execute(
                text("""
                    INSERT INTO trend_scores
                        (category, platform, attr_key, attr_value,
                         review_count, review_growth_pct, avg_rating,
                         category_avg_rating, rating_delta, product_count,
                         new_product_share, momentum_score, trend_direction,
                         lifecycle_stage, retailer_action, lifecycle_explanation,
                         weeks_observed, latest_week_share, previous_week_share,
                         explanation)
                    VALUES
                        (:category, :platform, :attr_key, :attr_value,
                         :review_count, :review_growth_pct, :avg_rating,
                         :category_avg_rating, :rating_delta, :product_count,
                         :new_product_share, :momentum_score, :trend_direction,
                         :lifecycle_stage, :retailer_action, :lifecycle_explanation,
                         :weeks_observed, :latest_week_share, :previous_week_share,
                         NULL)
                """),
                _safe(s),
            )
        db.commit()
        return len(scores)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def compute_all() -> list[dict]:
    df = _load_df()
    if df.empty:
        logger.warning("trend_momentum: no product data found, skipping")
        return []
    scores = _compute_scores(df)
    written = write_scores(scores)
    logger.info(f"trend_momentum: wrote {written} scores")
    return scores
