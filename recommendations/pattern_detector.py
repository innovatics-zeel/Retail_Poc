"""
pattern_detector.py — Rules engine that finds actionable patterns in trend_scores.

Pattern types:
  1. emerging_star       — high momentum + high rating + above-avg review count
  2. declining_attribute — negative momentum + below-avg rating
  3. underserved_niche   — high rating but low product count (opportunity gap)
  4. review_leader       — review count >> category average (validated attribute)
  5. cross_platform_gap  — trending on one platform, absent/weak on the other
  6. rating_outlier      — avg_rating >= 0.5 pts above/below the category mean
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

import pandas as pd
from loguru import logger
from sqlalchemy import text

from database.connection import SessionLocal


def load_trend_scores() -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT * FROM trend_scores ORDER BY momentum_score DESC")
        ).mappings().fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        for col in ("momentum_score", "avg_rating", "category_avg_rating",
                    "rating_delta", "review_growth_pct", "new_product_share"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    finally:
        db.close()


def detect_patterns(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    patterns: list[dict] = []

    # ── 1. Emerging Star ──────────────────────────────────────────
    stars = df[
        (df["momentum_score"] > 0.20) &
        (df["avg_rating"] >= 4.2) &
        (df["review_count"] > df["review_count"].quantile(0.5))
    ]
    for _, r in stars.head(3).iterrows():
        patterns.append(_make(r, "emerging_star", {
            "momentum_score": float(r["momentum_score"]),
            "avg_rating":     float(r["avg_rating"]),
            "review_count":   int(r["review_count"]),
            "rating_delta":   float(r["rating_delta"]),
            "explanation":    r.get("explanation") or "",
        }))

    # ── 2. Declining Attribute ─────────────────────────────────────
    declining = df[
        (df["momentum_score"] < -0.10) &
        (df["avg_rating"] < df["category_avg_rating"].fillna(df["avg_rating"]))
    ]
    for _, r in declining.head(2).iterrows():
        patterns.append(_make(r, "declining_attribute", {
            "momentum_score":      float(r["momentum_score"]),
            "avg_rating":          float(r["avg_rating"]),
            "category_avg_rating": float(r.get("category_avg_rating") or 0),
            "explanation":         r.get("explanation") or "",
        }))

    # ── 3. Underserved Niche ───────────────────────────────────────
    underserved = df[
        (df["avg_rating"] >= 4.3) &
        (df["product_count"] <= df["product_count"].quantile(0.25)) &
        (df["product_count"] >= 1)
    ]
    for _, r in underserved.head(2).iterrows():
        patterns.append(_make(r, "underserved_niche", {
            "avg_rating":    float(r["avg_rating"]),
            "product_count": int(r["product_count"]),
            "explanation":   r.get("explanation") or "",
        }))

    # ── 4. Review Leader ──────────────────────────────────────────
    cat_avg = df.groupby("category")["review_count"].mean()
    df_aug = df.copy()
    df_aug["cat_avg_reviews"] = df_aug["category"].map(cat_avg)
    leaders = df_aug[df_aug["review_count"] > df_aug["cat_avg_reviews"] * 2].nlargest(2, "review_count")
    for _, r in leaders.iterrows():
        patterns.append(_make(r, "review_leader", {
            "review_count":      int(r["review_count"]),
            "cat_avg_reviews":   round(float(r["cat_avg_reviews"]), 1),
            "avg_rating":        float(r["avg_rating"]),
            "explanation":       r.get("explanation") or "",
        }))

    # ── 5. Cross-Platform Gap ─────────────────────────────────────
    if df["platform"].nunique() >= 2:
        for attr_key in df["attr_key"].unique():
            sub = df[df["attr_key"] == attr_key]
            for category in sub["category"].unique():
                cat_sub = sub[sub["category"] == category]
                for attr_val in cat_sub["attr_value"].unique():
                    val_rows = cat_sub[cat_sub["attr_value"] == attr_val]
                    if len(val_rows) < 2:
                        continue
                    scores_by_plat = val_rows.set_index("platform")["momentum_score"]
                    gap = float(scores_by_plat.max() - scores_by_plat.min())
                    if gap > 0.30:
                        strong = scores_by_plat.idxmax()
                        weak = scores_by_plat.idxmin()
                        patterns.append({
                            "pattern_type": "cross_platform_gap",
                            "category":     category,
                            "platform":     f"{strong} vs {weak}",
                            "attr_key":     attr_key,
                            "attr_value":   attr_val,
                            "evidence": {
                                "strong_platform": strong,
                                "strong_score":    round(float(scores_by_plat[strong]), 3),
                                "weak_platform":   weak,
                                "weak_score":      round(float(scores_by_plat[weak]), 3),
                                "score_gap":       round(gap, 3),
                            },
                        })

    # ── 6. Rating Outlier ─────────────────────────────────────────
    outliers = df[df["rating_delta"].abs() >= 0.50].sort_values("rating_delta", ascending=False)
    for _, r in outliers.head(2).iterrows():
        patterns.append(_make(r, "rating_outlier", {
            "avg_rating":          float(r["avg_rating"]),
            "category_avg_rating": float(r.get("category_avg_rating") or 0),
            "rating_delta":        float(r["rating_delta"]),
            "explanation":         r.get("explanation") or "",
        }))

    # Deduplicate
    seen: set[tuple] = set()
    unique: list[dict] = []
    for p in patterns:
        key = (p["pattern_type"], p["category"], str(p["platform"]),
               p["attr_key"], p["attr_value"])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    logger.info(f"pattern_detector: found {len(unique)} patterns")
    return unique


def _make(row: pd.Series, pattern_type: str, evidence: dict) -> dict:
    return {
        "pattern_type": pattern_type,
        "category":     str(row.get("category", "")),
        "platform":     str(row.get("platform", "")),
        "attr_key":     str(row.get("attr_key", "")),
        "attr_value":   str(row.get("attr_value", "")),
        "evidence":     evidence,
    }
