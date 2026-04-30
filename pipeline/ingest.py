"""
ingest.py
Generic ingest pipeline — validates raw scraper dicts and upserts into the database.

Adding a new scraper requires NO changes here. The registry discovers the right
SCHEMA_CLASS, DB_MODEL, and to_db_values() from the scraper class automatically.
"""
import sys
from loguru import logger
from sqlalchemy.orm import Session

sys.path.append("..")

from database.connection import SessionLocal
from scraper.registry import get_by_category


def ingest_batch(raw_records: list[dict], category: str) -> dict:
    """Validate and upsert a list of raw scraper dicts for the given category."""
    summary = {"total": len(raw_records), "success": 0, "failed": 0, "skipped": 0}

    scraper_cls = get_by_category(category)
    schema_cls = scraper_cls.SCHEMA_CLASS
    db_model = scraper_cls.DB_MODEL

    db = SessionLocal()
    try:
        for raw in raw_records:
            if not raw:
                summary["skipped"] += 1
                continue

            try:
                raw.setdefault("category", category)
                data = schema_cls(**raw)
                values = scraper_cls.to_db_values(data)
                _upsert(db, db_model, values)
                db.commit()
                summary["success"] += 1

            except Exception as e:
                db.rollback()
                logger.warning(f"  ⚠️  Failed {raw.get('url', '?')}: {e}")
                summary["failed"] += 1

    finally:
        db.close()

    logger.info(
        f"📥 Ingest [{category}] — "
        f"✅ {summary['success']} | ❌ {summary['failed']} | ⏭ {summary['skipped']} "
        f"of {summary['total']}"
    )
    return summary


def _upsert(db: Session, model, values: dict) -> None:
    record = db.query(model).filter_by(url=values["url"]).first()
    if record:
        for key, value in values.items():
            setattr(record, key, value)
        logger.debug(f"  ↻ Updated: {values['url']}")
    else:
        db.add(model(**values))
        logger.debug(f"  + New: {values.get('title', values['url'])[:50]}")
