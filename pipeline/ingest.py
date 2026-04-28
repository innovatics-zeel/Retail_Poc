"""
ingest.py
Validates raw scraper dicts and inserts them into the database.
Writes one row per Nordstrom men's T-shirt.
"""
import json
import sys
from loguru import logger
from sqlalchemy.orm import Session

sys.path.append("..")
from database.connection import SessionLocal
from database.models import NordstromMensTshirt
from scraper.schemas import ProductData


def ingest_batch(raw_records: list[dict], category: str) -> dict:
    """Validate and insert a list of raw scraper dicts for the given category."""
    summary = {"total": len(raw_records), "success": 0, "failed": 0, "skipped": 0}
    db = SessionLocal()

    try:
        for raw in raw_records:
            if not raw:
                summary["skipped"] += 1
                continue

            try:
                raw.setdefault("category", category)
                data = ProductData(**raw)

                if data.category != category:
                    logger.warning(
                        f"Category mismatch '{category}' vs '{data.category}' for {data.url} - using payload value"
                    )

                if data.platform != "nordstrom" or data.category != "mens_tshirts":
                    logger.warning(f"Unknown category '{category}' — skipping")
                    summary["skipped"] += 1
                    continue

                _upsert(db, data)
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


def _upsert(db: Session, data: ProductData) -> None:
    """Insert or refresh one denormalized Nordstrom men's T-shirt row."""
    product = db.query(NordstromMensTshirt).filter_by(url=data.url).first()
    review_details = _json_loads(data.review_details_json)

    values = {
        "platform": data.platform,
        "url": data.url,
        "title": data.title,
        "brand": data.brand,
        "description": data.description,
        "category": data.category,
        "gender": data.gender,
        "sub_category": data.sub_category,
        "current_price": data.current_price,
        "discount_price": data.current_price,
        "actual_price": data.original_price,
        "original_price": data.original_price,
        "discount_percent": data.discount_percent,
        "price_text": data.price_text,
        "discount_text": data.discount_text,
        "currency": data.currency,
        "color": data.color,
        "size": data.size,
        "stock_json": data.stock_json,
        "pattern": data.pattern,
        "material": data.material,
        "neck_type": data.neck_type,
        "sleeve_type": data.sleeve_type,
        "fit": data.fit,
        "care_instructions": data.care_instructions,
        "rating": data.rating,
        "review_count": data.review_count,
        "review_fit": review_details.get("fit"),
        "star_distribution_json": json.dumps(review_details.get("star_distribution") or {}, ensure_ascii=True),
        "review_pros_json": json.dumps(review_details.get("pros") or [], ensure_ascii=True),
        "review_cons_json": json.dumps(review_details.get("cons") or [], ensure_ascii=True),
        "review_details_json": data.review_details_json,
        "data_label": data.data_label,
        "poc_run_id": data.poc_run_id,
        "is_active": True,
    }

    if product:
        for key, value in values.items():
            setattr(product, key, value)
        logger.debug(f"  ↻ Updated: {data.url}")
    else:
        db.add(NordstromMensTshirt(**values))
        logger.debug(f"  + New: {data.title[:50]}")


def _json_loads(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
