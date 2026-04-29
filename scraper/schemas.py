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
from pydantic import BaseModel, field_validator, model_validator
from typing import Any, Optional
from decimal import Decimal


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
        if not isinstance(values, dict):
            return values
        data = dict(values)
        data.setdefault("platform", "nordstrom")
        data.setdefault("category", "womens_dresses")
        data.setdefault("gender", "women")
        data.setdefault("currency", "USD")
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

