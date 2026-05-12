"""
ingest_normalized.py
Writes scraped data to the normalized 8-table schema.
Called automatically from ingest_batch — no scraper changes needed.

Table write order:
  platforms (pre-seeded) → brands → categories → colors → sizes → attribute masters
  → products → product_variants → reviews
"""
import json
import re
from datetime import datetime, timezone
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import (
    Brand, Category, Color, Size, Material, NeckType, SleeveType, Fit, Pattern,
    Platform, Product, ProductVariant, Review,
)

MAX_REALISTIC_REVIEW_COUNT = 1_000_000

PLATFORM_SEEDS = [
    (1, "amazon", "Amazon", "https://www.amazon.com"),
    (2, "nordstrom", "Nordstrom", "https://www.nordstrom.com"),
    (3, "walmart", "Walmart", "https://www.walmart.com"),
]

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


def _ensure_platforms(db: Session) -> None:
    """Keep platform FK seeds present even if an older DB missed the seed migration."""
    for platform_id, name, display_name, base_url in PLATFORM_SEEDS:
        platform = db.query(Platform).filter_by(name=name).first()
        if platform:
            platform.display_name = platform.display_name or display_name
            platform.base_url = platform.base_url or base_url
            continue
        db.add(Platform(
            id=platform_id,
            name=name,
            display_name=display_name,
            base_url=base_url,
        ))
    db.flush()


def _resolve_platform_id(db: Session, requested_id: Optional[int]) -> Optional[int]:
    if requested_id and db.query(Platform.id).filter_by(id=requested_id).scalar():
        return requested_id
    for seed_id, name, _display_name, _base_url in PLATFORM_SEEDS:
        if requested_id == seed_id:
            return db.query(Platform.id).filter_by(name=name).scalar()
    return requested_id


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


def _clean_master_name(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(name)).strip()
    if not cleaned or cleaned.lower() in {"none", "nan", "unknown", "n/a"}:
        return None
    return cleaned[:200]


def _get_or_create_master(db: Session, model, id_attr: str, name: Optional[str]) -> Optional[int]:
    cleaned = _clean_master_name(name)
    if not cleaned:
        return None
    obj = db.query(model).filter_by(name=cleaned).first()
    if not obj:
        obj = model(name=cleaned)
        db.add(obj)
        db.flush()
    return getattr(obj, id_attr)


def _get_or_create_product(
    db: Session,
    values: dict,
    brand_id: Optional[int],
    category_id: Optional[int],
) -> int:
    image = values.get("image")
    obj = db.query(Product).filter_by(url=values["url"]).first()
    if obj:
        obj.platform_id = values.get("platform_id") or obj.platform_id
        obj.brand_id = brand_id
        obj.category_id = category_id
        obj.title = values["title"]
        if isinstance(image, bytes):
            obj.image = image
        obj.material = values.get("material")
        obj.neck_type = values.get("neck_type")
        obj.sleeve_type = values.get("sleeve_type")
        obj.fit = values.get("fit")
        obj.pattern = values.get("pattern")
        obj.care = values.get("care_instructions")
        obj.scraped_at = datetime.now(timezone.utc)
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
        image=image if isinstance(image, bytes) else None,
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

def _parse_review_date(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    cleaned = re.sub(r"^Reviewed\s+.*?\s+on\s+", "", str(text).strip(), flags=re.I)
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _format_review_date(text: Optional[str]) -> str:
    parsed = _parse_review_date(text)
    return parsed.strftime("%d-%m-%Y") if parsed else (str(text).strip() if text else "")


def _comment_key(comment: dict) -> tuple[str, str, str]:
    return (
        _format_review_date(comment.get("date")).lower(),
        re.sub(r"\s+", " ", str(comment.get("title", ""))).strip().lower(),
        re.sub(r"\s+", " ", str(comment.get("description", ""))).strip().lower(),
    )


def _merge_review_comments(existing_comments: list[dict], incoming_comments: list[dict]) -> list[dict]:
    """
    Keep the saved comments and append only unseen comments from the scraper.
    Scraped Amazon reviews are newest-first, so dates older than the latest saved
    comment are ignored unless there is no saved date yet.
    """
    existing = [c for c in existing_comments if isinstance(c, dict)]
    incoming = [c for c in incoming_comments if isinstance(c, dict)]
    latest_existing = max(
        (date for date in (_parse_review_date(c.get("date")) for c in existing) if date),
        default=None,
    )

    merged: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def add_comment(comment: dict) -> None:
        key = _comment_key(comment)
        if key in seen:
            return
        seen.add(key)
        merged.append({
            "date": _format_review_date(comment.get("date")),
            "title": comment.get("title", ""),
            "description": comment.get("description", ""),
            "color": comment.get("color"),
            "size": comment.get("size"),
        })

    for comment in existing:
        add_comment(comment)

    for comment in incoming:
        comment_date = _parse_review_date(comment.get("date"))
        if latest_existing and comment_date and comment_date < latest_existing:
            continue
        add_comment(comment)

    merged.sort(key=lambda c: _parse_review_date(c.get("date")) or datetime.min, reverse=True)
    for idx, comment in enumerate(merged, start=1):
        comment["comment_count"] = idx
    return merged

def _parse_price_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
    return round(float(m.group(0)), 2) if m else None


def _normalize_price(
    value: Optional[float],
    platform_id: Optional[int],
    category_name: Optional[str] = None,
) -> Optional[float]:
    if value is None:
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    # Amazon sometimes exposes whole/cents DOM text as a shifted value
    # (e.g. 4695.62 for an apparel price around 46.96). Correct the
    # obvious apparel outliers at ingest time.
    if platform_id == 1 and price > 500:
        price = price / 100
    if platform_id == 1 and category_name == "mens_tshirts" and price > 150:
        price = price / 10
    return round(price, 2)


def _insert_variant(
    db: Session,
    product_id: int,
    color_id: Optional[int],
    size_id: Optional[int],
    attr_ids: dict,
    entry: dict,
) -> None:
    price = entry.get("current_price") or entry.get("price")
    if price is None:
        price = _parse_price_text(entry.get("price_text"))

    orig_price = entry.get("original_price")
    if orig_price is None:
        orig_price = _parse_price_text(entry.get("original_price_text"))

    platform_id, category_name = (
        db.query(Product.platform_id, Category.name)
        .outerjoin(Category, Category.category_id == Product.category_id)
        .filter(Product.product_id == product_id)
        .one()
    )
    price = _normalize_price(price, platform_id, category_name)
    orig_price = _normalize_price(orig_price, platform_id, category_name)

    stock_text = entry.get("stock_text") or entry.get("stock_note") or ""
    is_available = entry.get("available")
    if is_available is None:
        is_available = True

    low_stock = bool(stock_text and re.search(r"\bonly\s+\d+\s+left\b", stock_text, re.I))

    discount_pct = entry.get("discount_percent")
    if discount_pct is None and price and orig_price and orig_price > price:
        discount_pct = round((orig_price - price) / orig_price * 100, 2)

    image = entry.get("image")
    image_url = entry.get("image_url")

    values = {
        "product_id": product_id,
        "color_id": color_id,
        "size_id": size_id,
        "material_id": attr_ids.get("material_id"),
        "neck_type_id": attr_ids.get("neck_type_id"),
        "sleeve_type_id": attr_ids.get("sleeve_type_id"),
        "fit_id": attr_ids.get("fit_id"),
        "pattern_id": attr_ids.get("pattern_id"),
        "is_available": bool(is_available),
        "price": price,
        "original_price": orig_price,
        "discount_pct": discount_pct,
        "currency": "USD",
        "low_stock": low_stock,
        "stock_note": stock_text[:200] if stock_text else None,
        "scraped_at": datetime.now(timezone.utc),
    }
    if isinstance(image, bytes):
        values["image"] = image
    if isinstance(image_url, str) and image_url:
        values["image_url"] = image_url[:1000]

    # Keep one observation per scrape. Current-product queries already select
    # the latest row per product/color/size, while predictions need history.
    db.add(ProductVariant(**values))
    db.flush()


def _upsert_review(db: Session, product_id: int, review_data: dict) -> None:
    star = review_data.get("star_distribution", {})
    pros = review_data.get("pros")
    cons = review_data.get("cons")
    comments = review_data.get("comments") or review_data.get("comment_json")
    try:
        review_count = int(review_data.get("review_count") or 0)
    except (TypeError, ValueError):
        review_count = 0
    if review_count < 0 or review_count >= MAX_REALISTIC_REVIEW_COUNT:
        review_count = 0

    db.add(Review(
        product_id=product_id,
        rating_avg=review_data.get("rating"),
        review_count=review_count,
        fit_feedback=review_data.get("fit"),
        stars_1_pct=star.get("1") or star.get(1),
        stars_2_pct=star.get("2") or star.get(2),
        stars_3_pct=star.get("3") or star.get(3),
        stars_4_pct=star.get("4") or star.get(4),
        stars_5_pct=star.get("5") or star.get(5),
        pros=pros if isinstance(pros, list) else None,
        cons=cons if isinstance(cons, list) else None,
        comment_json=comments if isinstance(comments, (list, dict)) else None,
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

    _ensure_platforms(db)
    values["platform_id"] = _resolve_platform_id(db, values.get("platform_id")) or values.get("platform_id")
    brand_id    = _get_or_create_brand(db, values.get("brand"))
    category_id = _get_or_create_category(db, category_name, gender)
    product_id  = _get_or_create_product(db, values, brand_id, category_id)
    variant_image_map = {
        item.get("color"): item
        for item in values.get("variant_images", [])
        if isinstance(item, dict)
    }
    fallback_variant_image = variant_image_map.get(None) or next(iter(variant_image_map.values()), {})
    attr_ids = {
        "material_id":    _get_or_create_master(db, Material, "material_id", values.get("material")),
        "neck_type_id":   _get_or_create_master(db, NeckType, "neck_type_id", values.get("neck_type")),
        "sleeve_type_id": _get_or_create_master(db, SleeveType, "sleeve_type_id", values.get("sleeve_type")),
        "fit_id":         _get_or_create_master(db, Fit, "fit_id", values.get("fit")),
        "pattern_id":     _get_or_create_master(db, Pattern, "pattern_id", values.get("pattern")),
    }

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
            variant_image = variant_image_map.get(color_name) or fallback_variant_image

            sizes = variant.get("sizes")
            if sizes:
                # Nordstrom style — nested sizes list
                for size_entry in sizes:
                    label   = size_entry.get("size")
                    size_id = _get_or_create_size(db, label) if label else None
                    entry = dict(size_entry)
                    entry.setdefault("image_url", variant.get("image_url") or variant_image.get("image_url"))
                    if variant_image.get("image"):
                        entry["image"] = variant_image["image"]
                    _insert_variant(db, product_id, color_id, size_id, attr_ids, entry)
            else:
                # Amazon style — flat variant; size may be a comma-sep string
                entry = dict(variant)
                entry.setdefault("image_url", variant_image.get("image_url"))
                if variant_image.get("image"):
                    entry["image"] = variant_image["image"]
                size_str    = variant.get("size") or ""
                size_labels = [s.strip() for s in size_str.split(",") if s.strip()]
                if size_labels:
                    for label in size_labels:
                        size_id = _get_or_create_size(db, label)
                        _insert_variant(db, product_id, color_id, size_id, attr_ids, entry)
                else:
                    _insert_variant(db, product_id, color_id, None, attr_ids, entry)

    # ── Parse review_json → review ────────────────────────────────────────────
    review_json = values.get("review_json")
    if review_json:
        try:
            _upsert_review(db, product_id, json.loads(review_json))
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
