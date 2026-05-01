"""
ingest.py
Generic ingest pipeline — validates raw scraper dicts and writes to the
normalized 8-table schema (brands, categories, colors, sizes, products,
product_variants, reviews).

The old flat nordstrom/amazon tables are no longer used.
Adding a new scraper requires NO changes here.
"""
import sys
from loguru import logger
from sqlalchemy.orm import Session

sys.path.append("..")

from database.connection import SessionLocal
from scraper.registry import get_scraper, get_by_category
from pipeline.ingest_normalized import write_normalized


def ingest_batch(raw_records: list[dict], category: str, platform: str = None) -> dict:
    """Validate raw scraper dicts and write to the normalized schema."""
    summary = {"total": len(raw_records), "success": 0, "failed": 0, "skipped": 0}

    # Prefer explicit platform; fall back to reading it from the first record
    if not platform:
        for r in raw_records:
            if r and isinstance(r, dict) and r.get("platform"):
                platform = r["platform"]
                break

    try:
        scraper_cls = get_scraper(platform, category) if platform else get_by_category(category)
    except ValueError:
        scraper_cls = get_by_category(category)
    schema_cls = scraper_cls.SCHEMA_CLASS

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
                write_normalized(db, values)
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
