"""
recommendation_store.py — DB persistence layer for the recommendations table.

Public API:
    save_recommendations(recs)          → int (rows inserted)
    get_recommendations(...)            → list[dict]
    update_status(rec_id, status, text) → None
"""
from __future__ import annotations
import sys
import json
sys.path.insert(0, ".")

from loguru import logger
from sqlalchemy import text

from database.connection import SessionLocal


def save_recommendations(recommendations: list[dict]) -> int:
    if not recommendations:
        return 0
    db = SessionLocal()
    try:
        count = 0
        for rec in recommendations:
            db.execute(
                text("""
                    INSERT INTO recommendations
                        (category, platform, pattern_type, evidence,
                         recommendation_text, observation, action, impact, confidence)
                    VALUES
                        (:category, :platform, :pattern_type, CAST(:evidence AS JSONB),
                         :rec_text, :observation, :action, :impact, :confidence)
                """),
                {
                    "category":     rec.get("category"),
                    "platform":     str(rec.get("platform", "")),
                    "pattern_type": rec.get("pattern_type"),
                    "evidence":     json.dumps(rec.get("evidence", {})),
                    "rec_text":     rec.get("recommendation_text", ""),
                    "observation":  rec.get("observation", ""),
                    "action":       rec.get("action", ""),
                    "impact":       rec.get("impact", ""),
                    "confidence":   rec.get("confidence", "Medium"),
                },
            )
            count += 1
        db.commit()
        logger.info(f"recommendation_store: saved {count} recommendations")
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_recommendations(
    category: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    limit: int = 30,
) -> list[dict]:
    db = SessionLocal()
    try:
        conditions: list[str] = []
        params: dict = {"limit": limit}

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
            text(f"""
                SELECT * FROM recommendations
                {where}
                ORDER BY generated_at DESC
                LIMIT :limit
            """),
            params,
        ).mappings().fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def update_status(rec_id: int, status: str, modified_text: str | None = None) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text("""
                UPDATE recommendations
                SET status       = :status,
                    modified_text = :modified_text,
                    actioned_at  = NOW()
                WHERE rec_id = :rec_id
            """),
            {"status": status, "modified_text": modified_text, "rec_id": rec_id},
        )
        db.commit()
        logger.info(f"recommendation_store: rec {rec_id} → {status}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
