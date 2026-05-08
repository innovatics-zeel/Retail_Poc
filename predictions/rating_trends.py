"""
rating_trends.py — Linear rating trend per (category, platform, attr_key, attr_value).

Uses scipy.stats.linregress when available, falls back to numpy.polyfit.
With a single scrape snapshot all slopes will be 0; the rating delta vs the
category average is still informative.
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy import text

from database.connection import SessionLocal

_RATING_SQL = """
SELECT
    r.product_id,
    r.rating_avg,
    r.review_count,
    r.scraped_at,
    cat.name    AS category,
    pl.name     AS platform,
    COALESCE(pat.name, p.pattern)        AS pattern,
    COALESCE(mat.name, p.material)       AS material,
    COALESCE(ft.name, p.fit)             AS fit,
    COALESCE(nt.name, p.neck_type)       AS neck_type,
    COALESCE(st.name, p.sleeve_type)     AS sleeve_type,
    c.color_family
FROM reviews r
JOIN products p     ON p.product_id    = r.product_id
JOIN categories cat ON cat.category_id = p.category_id
JOIN platforms  pl  ON pl.id           = p.platform_id
LEFT JOIN product_variants pv ON pv.product_id = p.product_id
LEFT JOIN colors c            ON c.color_id    = pv.color_id
LEFT JOIN materials mat       ON mat.material_id   = pv.material_id
LEFT JOIN neck_types nt       ON nt.neck_type_id   = pv.neck_type_id
LEFT JOIN sleeve_types st     ON st.sleeve_type_id = pv.sleeve_type_id
LEFT JOIN fits ft             ON ft.fit_id         = pv.fit_id
LEFT JOIN patterns pat        ON pat.pattern_id    = pv.pattern_id
WHERE r.rating_avg IS NOT NULL
"""


def _load_history() -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = db.execute(text(_RATING_SQL)).mappings().fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
        df["rating_avg"] = pd.to_numeric(df["rating_avg"], errors="coerce")
        return df
    finally:
        db.close()


def _linregress(y: np.ndarray, x: np.ndarray) -> dict:
    n = len(y)
    intercept_val = float(np.mean(y)) if n > 0 else 0.0
    _zero = {"slope": 0.0, "intercept": intercept_val, "r_squared": 0.0,
             "p_value": 1.0, "significant": False}

    if n < 2:
        return _zero
    # All timestamps identical (single scrape run) — slope is undefined
    if np.unique(x).size == 1:
        return _zero
    try:
        from scipy.stats import linregress as sp_linregress
        slope, intercept, r, p, _ = sp_linregress(x, y)
        return {"slope": round(float(slope), 6), "intercept": round(float(intercept), 4),
                "r_squared": round(float(r ** 2), 4), "p_value": round(float(p), 4),
                "significant": float(p) < 0.05}
    except (ImportError, ValueError):
        try:
            coeffs = np.polyfit(x, y, 1)
            return {"slope": round(float(coeffs[0]), 6), "intercept": round(float(coeffs[1]), 4),
                    "r_squared": 0.0, "p_value": 1.0, "significant": False}
        except Exception:
            return _zero


def _trends_for_attr(df: pd.DataFrame, attr_key: str) -> list[dict]:
    work = df.dropna(subset=[attr_key]).copy()

    if attr_key != "color_family":
        work[attr_key] = work[attr_key].astype(str).str.split(r",\s*")
        work = work.explode(attr_key)
        work[attr_key] = work[attr_key].str.strip()

    work = work[work[attr_key].astype(str).str.len() > 0]
    if work.empty:
        return []

    results = []
    for (cat, plat, attr_val), grp in work.groupby(["category", "platform", attr_key]):
        if not attr_val or str(attr_val).lower() in ("nan", "none", ""):
            continue

        ratings = grp["rating_avg"].dropna().values
        if len(ratings) == 0:
            continue

        t = (grp["scraped_at"] - grp["scraped_at"].min()).dt.total_seconds().values / 86400
        trend = _linregress(ratings, t)

        results.append({
            "category":        str(cat),
            "platform":        str(plat),
            "attr_key":        attr_key,
            "attr_value":      str(attr_val),
            "avg_rating":      round(float(grp["rating_avg"].mean()), 2),
            "slope":           trend["slope"],
            "r_squared":       trend["r_squared"],
            "p_value":         trend["p_value"],
            "significant":     trend["significant"],
            "n_observations":  len(grp),
        })

    return results


def compute_all() -> list[dict]:
    df = _load_history()
    if df.empty:
        logger.warning("rating_trends: no rating history found")
        return []

    attr_keys = ["color_family", "pattern", "material", "fit", "neck_type", "sleeve_type"]
    all_results: list[dict] = []
    for key in attr_keys:
        if key in df.columns:
            all_results.extend(_trends_for_attr(df, key))

    logger.info(f"rating_trends: computed {len(all_results)} attribute-group trends")
    return all_results
