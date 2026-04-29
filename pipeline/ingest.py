"""
ingest.py
Validates raw scraper dicts and inserts them into the database.

Supports:
  • Nordstrom men's T-shirts  -> nordstrom_mens_tshirts
  • Nordstrom women's dresses -> nordstrom_womens_dresses

Women's dresses are stored without redundancy:
  • stock_price_json
  • attributes_json
  • review_json
  • raw_product_json
"""
import json
import sys
from loguru import logger
from sqlalchemy.orm import Session

sys.path.append("..")

from database.connection import SessionLocal
from database.models import NordstromMensTshirt, NordstromWomensDress

from scraper.schemas import ProductData,WomensDressData



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

                if category == "mens_tshirts":
                    data = ProductData(**raw)

                    if data.platform != "nordstrom" or data.category != "mens_tshirts":
                        logger.warning(f"Unknown category '{category}' — skipping")
                        summary["skipped"] += 1
                        continue

                    _upsert_mens_tshirt(db, data)

                elif category == "womens_dresses":
                    data = WomensDressData(**raw)

                    if data.platform != "nordstrom" or data.category != "womens_dresses":
                        logger.warning(f"Unknown category '{category}' — skipping")
                        summary["skipped"] += 1
                        continue

                    _upsert_womens_dress(db, data)

                else:
                    logger.warning(f"Unsupported category '{category}' — skipping")
                    summary["skipped"] += 1
                    continue

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


def _upsert_mens_tshirt(db: Session, data: ProductData) -> None:
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
        "actual_price": data.original_price or data.current_price,
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
        "star_distribution_json": json.dumps(
            review_details.get("star_distribution") or {},
            ensure_ascii=True,
        ),
        "review_pros_json": json.dumps(
            review_details.get("pros") or [],
            ensure_ascii=True,
        ),
        "review_cons_json": json.dumps(
            review_details.get("cons") or [],
            ensure_ascii=True,
        ),
        "review_details_json": data.review_details_json,

        "data_label": data.data_label,
        "poc_run_id": data.poc_run_id,
        "is_active": True,
    }

    if product:
        for key, value in values.items():
            setattr(product, key, value)
        logger.debug(f"  ↻ Updated mens_tshirt: {data.url}")
    else:
        db.add(NordstromMensTshirt(**values))
        logger.debug(f"  + New mens_tshirt: {data.title[:50]}")


def _upsert_womens_dress(db: Session, data: WomensDressData) -> None:
    """Insert or refresh one clean Nordstrom women's dress row."""
    product = db.query(NordstromWomensDress).filter_by(url=data.url).first()

    raw_product_json = data.raw_product_json
    if not raw_product_json:
        raw_product_json = json.dumps(
            {
                "platform": data.platform,
                "platform_id": data.platform_id,
                "url": data.url,
                "title": data.title,
                "brand": data.brand,
                "description": data.description,
                "category": data.category,
                "gender": data.gender,
                "currency": data.currency,
                "stock_price": _json_loads_list_or_dict(data.stock_price_json),
                "attributes": _json_loads_list_or_dict(data.attributes_json),
                "review": _json_loads_list_or_dict(data.review_json),
            },
            ensure_ascii=False,
        )

    values = {
        "platform": data.platform,
        "platform_id": data.platform_id,
        "url": data.url,
        "title": data.title,
        "brand": data.brand,
        "description": data.description,
        "category": data.category,
        "gender": data.gender,
        "currency": data.currency,

        # Clean non-redundant JSON columns
        "stock_price_json": data.stock_price_json,
        "attributes_json": data.attributes_json,
        "review_json": data.review_json,

        # Full managed product JSON + optional file path
        "raw_product_json": raw_product_json,
        "json_file_path": data.json_file_path,

        "data_label": data.data_label,
        "poc_run_id": data.poc_run_id,
        "is_active": True,
    }

    if product:
        for key, value in values.items():
            setattr(product, key, value)
        logger.debug(f"  ↻ Updated womens_dress: {data.url}")
    else:
        db.add(NordstromWomensDress(**values))
        logger.debug(f"  + New womens_dress: {data.title[:50]}")


def _json_loads(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _json_loads_list_or_dict(value: str | None):
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        if isinstance(parsed, (dict, list)):
            return parsed
        return {}
    except json.JSONDecodeError:
        return {}
