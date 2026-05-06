"""
explainability.py — Generates plain-English explanations for each trend score.

Reads all rows in trend_scores where explanation IS NULL and writes a sentence
like: "Navy is trending up because average rating (4.6) is 0.4 points above the
category average and review volume grew 34% vs the category baseline."
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

from loguru import logger
from sqlalchemy import text

from database.connection import SessionLocal


def _build_explanation(row: dict) -> str:
    attr_val   = row.get("attr_value", "?")
    direction  = (row.get("trend_direction") or "Stable").lower()
    avg_rating = float(row.get("avg_rating") or 0)
    delta      = float(row.get("rating_delta") or 0)
    growth_pct = float(row.get("review_growth_pct") or 0)
    reviews    = int(row.get("review_count") or 0)
    platform   = row.get("platform", "")
    category   = (row.get("category") or "").replace("_", " ")
    stage      = (row.get("lifecycle_stage") or "").replace("_", " ")
    action     = row.get("retailer_action") or ""

    evidence: list[str] = []

    if abs(delta) >= 0.1:
        word = "above" if delta > 0 else "below"
        evidence.append(
            f"average rating ({avg_rating:.1f}) is {abs(delta):.1f} pts {word} "
            f"the {category} category average"
        )

    if abs(growth_pct) >= 5:
        word = "grew" if growth_pct > 0 else "declined"
        evidence.append(f"review volume {word} {abs(growth_pct):.0f}% vs category baseline")

    if reviews > 0 and len(evidence) < 2:
        evidence.append(f"backed by {reviews:,} reviews on {platform}")

    if not evidence:
        n_products = int(row.get("product_count") or 0)
        evidence.append(f"based on {n_products} products in this attribute group")

    if direction == "rising":
        verb = "is trending up"
    elif direction == "falling":
        verb = "is trending down"
    else:
        verb = "is holding steady"

    joined = " and ".join(evidence[:2])
    if len(evidence) > 2:
        joined += f", {evidence[2]}"

    suffix = f" Lifecycle stage: {stage}; retailer action: {action}." if stage and action else ""
    return f"{attr_val} {verb} because {joined}.{suffix}"


def generate_all() -> int:
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT * FROM trend_scores WHERE explanation IS NULL")
        ).mappings().fetchall()

        count = 0
        for row in rows:
            row_dict = dict(row)
            explanation = _build_explanation(row_dict)
            db.execute(
                text("UPDATE trend_scores SET explanation = :e WHERE score_id = :sid"),
                {"e": explanation, "sid": row_dict["score_id"]},
            )
            count += 1

        db.commit()
        logger.info(f"explainability: generated {count} explanations")
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
