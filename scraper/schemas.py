# from pydantic import BaseModel, field_validator
# from typing import Optional
# from decimal import Decimal


# class MensTshirtData(BaseModel):
#     platform:     str
#     url:          str
#     title:        str
#     brand:        Optional[str]    = None
#     price:        Optional[Decimal] = None
#     size:         Optional[str]    = None
#     color:        Optional[str]    = None
#     neck_type:    Optional[str]    = None
#     fit:          Optional[str]    = None
#     material:     Optional[str]    = None
#     rating:       Optional[Decimal] = None
#     review_count: int = 0

#     @field_validator("platform")
#     @classmethod
#     def validate_platform(cls, v):
#         allowed = {"amazon", "nordstrom", "walmart"}
#         if v.lower() not in allowed:
#             raise ValueError(f"Platform must be one of {allowed}")
#         return v.lower()

#     @field_validator("rating")
#     @classmethod
#     def validate_rating(cls, v):
#         if v is not None and not (0 <= float(v) <= 5):
#             raise ValueError("Rating must be between 0 and 5")
#         return v


# class WomensDressData(BaseModel):
#     """Placeholder schema — women's dresses will be implemented next."""
#     platform:     str
#     url:          str
#     title:        str
#     brand:        Optional[str]    = None
#     price:        Optional[Decimal] = None
#     size:         Optional[str]    = None
#     color:        Optional[str]    = None
#     neck_type:    Optional[str]    = None
#     fit:          Optional[str]    = None
#     material:     Optional[str]    = None
#     rating:       Optional[Decimal] = None
#     review_count: int = 0

#     @field_validator("platform")
#     @classmethod
#     def validate_platform(cls, v):
#         allowed = {"amazon", "nordstrom", "walmart"}
#         if v.lower() not in allowed:
#             raise ValueError(f"Platform must be one of {allowed}")
#         return v.lower()
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Optional
from decimal import Decimal


# ── Raw JSON schemas — validate the exact payload produced by the scraper ──────

class SizeEntry(BaseModel):
    size: str
    available: bool = True
    stock_text: Optional[str] = None
    price_text: Optional[str] = None
    original_price_text: Optional[str] = None
    discount_text: Optional[str] = None
    discount_percent: Optional[float] = None
    currency: str = "USD"


class ColorVariant(BaseModel):
    color: Optional[str] = None
    sizes: list[SizeEntry] = Field(default_factory=list)


class DressAttributes(BaseModel):
    neck_type: Optional[str] = None
    dress_length: Optional[str] = None
    occasion: Optional[str] = None
    fit: Optional[str] = None
    pattern: Optional[str] = None
    closure_type: Optional[str] = None
    material: Optional[str] = None
    care_instructions: Optional[str] = None
    sleeve_type: Optional[str] = None
    details_text: Optional[str] = None


class ReviewSummary(BaseModel):
    rating: Optional[float] = None
    review_count: int = 0
    fit: Optional[str] = None
    star_distribution: dict = Field(default_factory=dict)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class RawWomensDressPayload(BaseModel):
    """Validates the raw JSON produced by NordstromWomensDressScraper._parse_product."""
    platform: str = "nordstrom"
    url: str
    title: str
    brand: Optional[str] = None
    category: str = "womens_dresses"
    gender: str = "women"
    attributes: DressAttributes = Field(default_factory=DressAttributes)
    stock_variants: list[ColorVariant] = Field(default_factory=list)
    review: ReviewSummary = Field(default_factory=ReviewSummary)

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        data = dict(values)
        # scraper writes "stock_price"; accept both
        if "stock_variants" not in data and "stock_price" in data:
            data["stock_variants"] = data["stock_price"]
        return data

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v.lower() != "nordstrom":
            raise ValueError("platform must be 'nordstrom'")
        return v.lower()

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v.lower() != "womens_dresses":
            raise ValueError("category must be 'womens_dresses'")
        return v.lower()

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v.lower() != "women":
            raise ValueError("gender must be 'women'")
        return v.lower()


class ProductData(BaseModel):
    platform: str
    platform_id: Optional[int] = None
    url: str
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None

    category: str
    gender: str
    sub_category: Optional[str] = None

    current_price: Optional[Decimal] = None
    currency: str = "USD"
    rating: Optional[Decimal] = None
    review_count: int = 0

    size: Optional[str] = None
    color: Optional[str] = None
    pattern: Optional[str] = None
    material: Optional[str] = None
    neck_type: Optional[str] = None
    sleeve_type: Optional[str] = None
    fit: Optional[str] = None
    care_instructions: Optional[str] = None
    stock_json: Optional[str] = None

    original_price: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    price_text: Optional[str] = None
    discount_text: Optional[str] = None
    review_details_json: Optional[str] = None

    data_label: str = "demonstration_data"
    poc_run_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_scraper_keys(cls, values: Any):
        if not isinstance(values, dict):
            return values

        data = dict(values)
        if "current_price" not in data and "price" in data:
            data["current_price"] = data["price"]
        if "discount_percent" not in data and "discount_pct" in data:
            data["discount_percent"] = data["discount_pct"]
        if data.get("category") == "womens_casual_dresses":
            data["category"] = "womens_dresses"
        # cap review_count to PostgreSQL INTEGER max to prevent overflow
        if "review_count" in data:
            try:
                data["review_count"] = min(int(data["review_count"] or 0), 2_147_483_647)
            except (TypeError, ValueError):
                data["review_count"] = 0
        return data

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v):
        allowed = {"amazon", "nordstrom", "walmart"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Platform must be one of {allowed}")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        allowed = {"men", "women", "unisex"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Gender must be one of {allowed}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed = {"mens_tshirts", "womens_dresses"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"Category must be one of {allowed}")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and not (0 <= float(v) <= 5):
            raise ValueError("Rating must be between 0 and 5")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        return v.upper()



# ── Amazon schemas ─────────────────────────────────────────────────────────────

class AmazonVariant(BaseModel):
    color: Optional[str] = None
    size: Optional[str] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_price: Optional[float] = None
    discount_percent: Optional[float] = None
    currency: str = "USD"


class AmazonTshirtAttributes(BaseModel):
    occasion: Optional[str] = None
    apparel_silhouette: Optional[str] = None
    neck_style: Optional[str] = None
    sleeve_type: Optional[str] = None
    seasons: Optional[str] = None
    style: Optional[str] = None
    closure: Optional[str] = None
    back_style: Optional[str] = None
    strap_type: Optional[str] = None
    pattern: Optional[str] = None
    collar_type: Optional[str] = None
    fit_type: Optional[str] = None
    material_type: Optional[str] = None


class AmazonDressAttributes(AmazonTshirtAttributes):
    waist_style: Optional[str] = None
    dress_length: Optional[str] = None


class AmazonReview(BaseModel):
    rating: Optional[float] = None
    review_count: int = 0
    review_summary: Optional[str] = None
    star_distribution: dict = Field(default_factory=dict)
    review_details: list = Field(default_factory=list)


def _normalize_amazon_flat(data: dict) -> dict:
    """Map old flat amazon_scraper.py output into variants/attributes/review structure."""
    if "variants" not in data and ("price" in data or "current_price" in data):
        data["variants"] = [{
            "color": data.get("color"),
            "size": data.get("size_range") or data.get("size"),
            "current_price": data.get("current_price") or data.get("price"),
            "original_price": data.get("original_price"),
            "discount_percent": data.get("discount_percent") or data.get("discount_pct"),
            "currency": data.get("currency", "USD"),
        }]
    if "attributes" not in data:
        data["attributes"] = {
            "neck_style": data.get("neck_type"),
            "sleeve_type": data.get("sleeve_type"),
            "pattern": data.get("pattern"),
            "fit_type": data.get("fit"),
            "material_type": data.get("material"),
        }
    if "review" not in data:
        data["review"] = {
            "rating": data.get("rating"),
            "review_count": data.get("review_count", 0),
        }
    if isinstance(data.get("review"), dict):
        try:
            data["review"]["review_count"] = min(
                int(data["review"].get("review_count") or 0), 2_147_483_647
            )
        except (TypeError, ValueError):
            data["review"]["review_count"] = 0
    return data


class RawAmazonMensTshirtPayload(BaseModel):
    platform: str = "amazon"
    url: str
    title: str
    brand: Optional[str] = None
    category: str = "mens_tshirts"
    gender: str = "men"
    asin: Optional[str] = None
    variants: list[AmazonVariant] = Field(default_factory=list)
    attributes: AmazonTshirtAttributes = Field(default_factory=AmazonTshirtAttributes)
    review: AmazonReview = Field(default_factory=AmazonReview)
    data_label: str = "demonstration_data"
    poc_run_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        return _normalize_amazon_flat(dict(values))

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v.lower() != "amazon":
            raise ValueError("platform must be 'amazon'")
        return v.lower()


class RawAmazonWomensDressPayload(BaseModel):
    platform: str = "amazon"
    url: str
    title: str
    brand: Optional[str] = None
    category: str = "womens_dresses"
    gender: str = "women"
    asin: Optional[str] = None
    variants: list[AmazonVariant] = Field(default_factory=list)
    attributes: AmazonDressAttributes = Field(default_factory=AmazonDressAttributes)
    review: AmazonReview = Field(default_factory=AmazonReview)
    data_label: str = "demonstration_data"
    poc_run_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        return _normalize_amazon_flat(dict(values))

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v.lower() != "amazon":
            raise ValueError("platform must be 'amazon'")
        return v.lower()


# ── Legacy Nordstrom schema ────────────────────────────────────────────────────

class WomensDressData(BaseModel):
    platform: str = "nordstrom"
    platform_id: Optional[int] = None
    url: str
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    category: str = "womens_dresses"
    gender: str = "women"
    currency: str = "USD"

    stock_price_json: Optional[str] = None
    attributes_json: Optional[str] = None
    review_json: Optional[str] = None
    raw_product_json: Optional[str] = None
    json_file_path: Optional[str] = None

    data_label: str = "demonstration_data"
    poc_run_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_keys(cls, values: Any):
        import json as _json
        if not isinstance(values, dict):
            return values
        data = dict(values)
        data.setdefault("platform", "nordstrom")
        data.setdefault("category", "womens_dresses")
        data.setdefault("gender", "women")
        data.setdefault("currency", "USD")

        # handle raw dict/list fields from JSON file format
        for raw_key, json_key in [
            ("stock_variants", "stock_price_json"),
            ("stock_price",    "stock_price_json"),
            ("attributes",     "attributes_json"),
            ("review",         "review_json"),
        ]:
            if raw_key in data and json_key not in data:
                val = data[raw_key]
                if isinstance(val, (dict, list)):
                    data[json_key] = _json.dumps(val, ensure_ascii=False)
        return data

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v):
        v = v.lower()
        if v != "nordstrom":
            raise ValueError("Platform must be nordstrom")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        v = v.lower()
        if v != "women":
            raise ValueError("Gender must be women")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        v = v.lower()
        if v != "womens_dresses":
            raise ValueError("Category must be womens_dresses")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        return v.upper()

