"""
review_velocity.py — Review-count velocity forecasting per (category, platform).

Groups review snapshots by (product_id, scrape day) → aggregates by (category, platform, day)
→ linear regression → 7-day forecast with confidence interval.

When only one day of data exists, the current count is returned as the flat forecast.
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from loguru import logger
from sqlalchemy import text

from database.connection import SessionLocal

_REVIEW_SQL = """
SELECT
    r.product_id,
    DATE_TRUNC('day', r.scraped_at)::date  AS day,
    MAX(r.review_count)                    AS review_count,
    cat.name                               AS category,
    pl.name                                AS platform
FROM product_review_snapshots r
JOIN products p   ON p.product_id   = r.product_id
JOIN categories cat ON cat.category_id = p.category_id
JOIN platforms  pl  ON pl.id           = p.platform_id
GROUP BY r.product_id, DATE_TRUNC('day', r.scraped_at), cat.name, pl.name
ORDER BY r.product_id, day
"""


def load_review_timeseries() -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = db.execute(text(_REVIEW_SQL)).mappings().fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        df["day"] = pd.to_datetime(df["day"])
        df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0)
        return df
    finally:
        db.close()


def _forecast_series(daily: pd.Series, days_ahead: int = 7) -> dict:
    n = len(daily)
    current = float(daily.iloc[-1])

    if n == 1:
        return {
            "current": current,
            "slope": 0.0,
            "forecast_vals": [current] * days_ahead,
            "lower_ci": [max(0, current * 0.9)] * days_ahead,
            "upper_ci": [current * 1.1] * days_ahead,
            "days_of_data": 1,
        }

    x = np.arange(n, dtype=float)
    y = daily.values.astype(float)
    coeffs = np.polyfit(x, y, 1)
    slope = float(coeffs[0])

    y_pred = np.polyval(coeffs, x)
    std = float(np.std(y - y_pred)) if n > 2 else abs(slope)

    forecast_vals = [max(0.0, float(np.polyval(coeffs, n + i))) for i in range(days_ahead)]
    lower = [max(0.0, v - 1.96 * std) for v in forecast_vals]
    upper = [v + 1.96 * std for v in forecast_vals]

    return {
        "current": current,
        "slope": round(slope, 2),
        "forecast_vals": [round(v, 1) for v in forecast_vals],
        "lower_ci": [round(v, 1) for v in lower],
        "upper_ci": [round(v, 1) for v in upper],
        "days_of_data": n,
    }


def compute_category_velocity(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    results = []
    for (category, platform), grp in df.groupby(["category", "platform"]):
        daily = (
            grp.groupby("day")["review_count"]
            .sum()
            .sort_index()
        )

        fc = _forecast_series(daily, days_ahead=7)

        last_day = daily.index[-1]
        future_days = [
            str((last_day + pd.Timedelta(days=i + 1)).date())
            for i in range(7)
        ]

        results.append({
            "category":        str(category),
            "platform":        str(platform),
            "hist_days":       [str(d.date()) for d in daily.index],
            "hist_vals":       daily.values.tolist(),
            "future_days":     future_days,
            "future_vals":     fc["forecast_vals"],
            "lower_ci":        fc["lower_ci"],
            "upper_ci":        fc["upper_ci"],
            "slope":           fc["slope"],
            "current_reviews": fc["current"],
            "days_of_data":    fc["days_of_data"],
        })

    return results


def compute_all() -> list[dict]:
    df = load_review_timeseries()
    if df.empty:
        logger.warning("review_velocity: no review data found")
        return []
    results = compute_category_velocity(df)
    logger.info(f"review_velocity: computed forecasts for {len(results)} category-platform pairs")
    return results
