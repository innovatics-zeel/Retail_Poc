"""
ingest_normalized.py
Writes scraped data to the normalized 8-table schema.
Called automatically from ingest_batch — no scraper changes needed.

Table write order:
  platforms (pre-seeded) → brands → categories → colors → sizes
  → products → product_variants → reviews
"""
import json
import re
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Brand, Category, Color, Size, Product, ProductVariant, Review

# ── Color-family mapping ──────────────────────────────────────────────────────
# Keywords are matched as substrings (case-insensitive) in the color name.
_COLOR_FAMILY_MAP = [
    (["black", "onyx", "jet", "ebony", "noir", "graphite"], "Black"),
    (["white", "ivory", "cream", "off-white", "eggshell", "snow", "alabaster"], "White"),
    (["red", "crimson", "scarlet", "cardinal", "ruby", "garnet",
      "maroon", "wine", "burgundy", "berry", "cherry"], "Red"),
    (["navy", "sapphire", "cobalt", "azure", "indigo", "denim",
      "royal blue", "powder blue", "steel blue", "blue"], "Blue"),
    (["teal", "aqua", "turquoise", "cyan", "seafoam", "bright aqua"], "Teal/Aqua"),
    (["green", "emerald", "forest", "sage", "olive", "mint",
      "lime", "hunter", "moss", "fern", "jade"], "Green"),
    (["pink", "rose", "blush", "mauve", "dusty rose",
      "hot pink", "fuchsia", "magenta"], "Pink"),
    (["yellow", "gold", "mustard", "lemon", "amber", "canary", "sunshine"], "Yellow"),
    (["orange", "coral", "peach", "tangerine", "apricot",
      "rust", "burnt orange", "terra cotta"], "Orange"),
    (["purple", "violet", "lavender", "lilac", "plum",
      "grape", "orchid", "eggplant"], "Purple"),
    (["brown", "tan", "camel", "beige", "taupe", "sand",
      "khaki", "mocha", "chocolate", "espresso", "walnut", "cognac"], "Brown/Beige"),
    (["grey", "gray", "charcoal", "dove", "silver", "slate", "ash", "heather"], "Grey"),
    (["multi", "multicolor", "print", "mixed", "colorblock",
      "color block", "patterned", "tie dye"], "Multi"),
]


def _color_family(name: str) -> str:
    low = (name or "").lower()
    for keywords, family in _COLOR_FAMILY_MAP:
        if any(kw in low for kw in keywords):
            return family
    return "Other"


# ── get-or-create helpers ─────────────────────────────────────────────────────

def _get_or_create_brand(db: Session, name: Optional[str]) -> Optional[int]:
    if not name:
        return None
    obj = db.query(Brand).filter_by(name=name).first()
    if not obj:
        obj = Brand(name=name)
        db.add(obj)
        db.flush()
    return obj.brand_id


def _get_or_create_category(db: Session, name: str, gender: Optional[str] = None) -> Optional[int]:
    if not name:
        return None
    obj = db.query(Category).filter_by(name=name).first()
    if not obj:
        obj = Category(name=name, gender=gender)
        db.add(obj)
        db.flush()
    return obj.category_id


def _get_or_create_color(db: Session, name: str) -> Optional[int]:
    if not name:
        return None
    obj = db.query(Color).filter_by(name=name).first()
    if not obj:
        obj = Color(name=name, color_family=_color_family(name))
        db.add(obj)
        db.flush()
    return obj.color_id


def _get_or_create_size(db: Session, label: str) -> Optional[int]:
    if not label:
        return None
    obj = db.query(Size).filter_by(label=label).first()
    if not obj:
        obj = Size(label=label, sort_order=999, size_system="alpha")
        db.add(obj)
        db.flush()
    return obj.size_id


def _get_or_create_product(
    db: Session,
    values: dict,
    brand_id: Optional[int],
    category_id: Optional[int],
) -> int:
    obj = db.query(Product).filter_by(url=values["url"]).first()
    if obj:
        return obj.product_id

    url = values.get("url", "")
    platform_item_id = None
    asin_m = re.search(r"/dp/([A-Z0-9]{10})", url)
    if asin_m:
        platform_item_id = asin_m.group(1)
    else:
        item_m = re.search(r"/s/[^/]+/(\d+)", url)
        if item_m:
            platform_item_id = item_m.group(1)

    obj = Product(
        platform_id=values.get("platform_id") or 1,
        brand_id=brand_id,
        category_id=category_id,
        title=values["title"],
        url=url,
        platform_item_id=platform_item_id,
        material=values.get("material"),
        neck_type=values.get("neck_type"),
        sleeve_type=values.get("sleeve_type"),
        fit=values.get("fit"),
        pattern=values.get("pattern"),
        care=values.get("care_instructions"),
    )
    db.add(obj)
    db.flush()
    return obj.product_id


# ── Variant / review writers ──────────────────────────────────────────────────

def _parse_price_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
    return round(float(m.group(0)), 2) if m else None


def _insert_variant(
    db: Session,
    product_id: int,
    color_id: Optional[int],
    size_id: Optional[int],
    entry: dict,
) -> None:
    price = entry.get("current_price") or entry.get("price")
    if price is None:
        price = _parse_price_text(entry.get("price_text"))

    orig_price = entry.get("original_price")
    if orig_price is None:
        orig_price = _parse_price_text(entry.get("original_price_text"))

    stock_text = entry.get("stock_text") or entry.get("stock_note") or ""
    is_available = entry.get("available")
    if is_available is None:
        is_available = True

    low_stock = bool(stock_text and re.search(r"\bonly\s+\d+\s+left\b", stock_text, re.I))

    discount_pct = entry.get("discount_percent")
    if discount_pct is None and price and orig_price and orig_price > price:
        discount_pct = round((orig_price - price) / orig_price * 100, 2)

    db.add(ProductVariant(
        product_id=product_id,
        color_id=color_id,
        size_id=size_id,
        is_available=bool(is_available),
        price=price,
        original_price=orig_price,
        discount_pct=discount_pct,
        currency="USD",
        low_stock=low_stock,
        stock_note=stock_text[:200] if stock_text else None,
    ))


def _insert_review(db: Session, product_id: int, review_data: dict) -> None:
    star = review_data.get("star_distribution", {})
    pros = review_data.get("pros")
    cons = review_data.get("cons")

    db.add(Review(
        product_id=product_id,
        rating_avg=review_data.get("rating"),
        review_count=min(int(review_data.get("review_count") or 0), 2_147_483_647),
        fit_feedback=review_data.get("fit"),
        stars_1_pct=star.get("1") or star.get(1),
        stars_2_pct=star.get("2") or star.get(2),
        stars_3_pct=star.get("3") or star.get(3),
        stars_4_pct=star.get("4") or star.get(4),
        stars_5_pct=star.get("5") or star.get(5),
        pros=pros if isinstance(pros, list) else None,
        cons=cons if isinstance(cons, list) else None,
    ))


# ── Core writer — called per record from ingest.py ───────────────────────────

def write_normalized(db: Session, values: dict) -> None:
    """
    Write one to_db_values() dict to the normalized tables.
    Uses the same session as the caller — caller owns commit/rollback.
    """
    gender_map = {1: "men", 2: "women", 3: "unisex"}
    gender = gender_map.get(values.get("gender_id") or 0, "unisex")
    category_name = values.get("category", "")

    brand_id    = _get_or_create_brand(db, values.get("brand"))
    category_id = _get_or_create_category(db, category_name, gender)
    product_id  = _get_or_create_product(db, values, brand_id, category_id)

    # ── Parse stock_variants_json → variants ──────────────────────────────────
    sv_json = values.get("stock_variants_json")
    if sv_json:
        try:
            stock_variants = json.loads(sv_json)
        except (json.JSONDecodeError, TypeError):
            stock_variants = []

        for variant in stock_variants:
            color_name = variant.get("color")
            color_id   = _get_or_create_color(db, color_name) if color_name else None

            sizes = variant.get("sizes")
            if sizes:
                # Nordstrom style — nested sizes list
                for size_entry in sizes:
                    label   = size_entry.get("size")
                    size_id = _get_or_create_size(db, label) if label else None
                    _insert_variant(db, product_id, color_id, size_id, size_entry)
            else:
                # Amazon style — flat variant; size may be a comma-sep string
                size_str    = variant.get("size") or ""
                size_labels = [s.strip() for s in size_str.split(",") if s.strip()]
                if size_labels:
                    for label in size_labels:
                        size_id = _get_or_create_size(db, label)
                        _insert_variant(db, product_id, color_id, size_id, variant)
                else:
                    _insert_variant(db, product_id, color_id, None, variant)

    # ── Parse review_json → review ────────────────────────────────────────────
    review_json = values.get("review_json")
    if review_json:
        try:
            _insert_review(db, product_id, json.loads(review_json))
        except (json.JSONDecodeError, TypeError):
            pass


# ── Standalone entry point (used when calling outside ingest_batch) ───────────

def ingest_normalized(db_values_list: list[dict]) -> dict:
    summary = {"total": len(db_values_list), "success": 0, "failed": 0}
    db = SessionLocal()
    try:
        for values in db_values_list:
            if not values or not values.get("url"):
                continue
            try:
                write_normalized(db, values)
                db.commit()
                summary["success"] += 1
            except Exception as e:
                db.rollback()
                logger.warning(f"  Normalized ingest failed {values.get('url', '?')}: {e}")
                summary["failed"] += 1
    finally:
        db.close()

    logger.info(
        f"📥 Normalized — ✅ {summary['success']} | ❌ {summary['failed']} of {summary['total']}"
    )
    return summary
