from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database.connection import Base

GENDER_ID = {"men": 1, "women": 2, "unisex": 3}


class Platform(Base):
    __tablename__ = "platforms"
    id           = Column(SmallInteger, primary_key=True, index=True)
    name         = Column(String(50),  nullable=False, unique=True)
    display_name = Column(String(100), nullable=True)
    base_url     = Column(Text,        nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Platform {self.name}>"


class Brand(Base):
    __tablename__ = "brands"
    brand_id = Column(Integer, primary_key=True, index=True)
    name     = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Brand {self.name}>"


class Category(Base):
    __tablename__ = "categories"
    category_id = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False, unique=True)
    gender      = Column(String(20), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Category {self.name}>"


class Color(Base):
    __tablename__ = "colors"
    color_id     = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False, unique=True)
    color_family = Column(String(50), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Color {self.name} / {self.color_family}>"


class Size(Base):
    __tablename__ = "sizes"
    size_id     = Column(Integer, primary_key=True, index=True)
    label       = Column(String(50), nullable=False, unique=True)
    sort_order  = Column(Integer, nullable=False, default=999)
    size_system = Column(String(20), nullable=False, default="alpha")
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Size {self.label}>"


class Material(Base):
    __tablename__ = "materials"
    material_id = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False, unique=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Material {self.name}>"


class NeckType(Base):
    __tablename__ = "neck_types"
    neck_type_id = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False, unique=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NeckType {self.name}>"


class SleeveType(Base):
    __tablename__ = "sleeve_types"
    sleeve_type_id = Column(Integer, primary_key=True, index=True)
    name           = Column(String(100), nullable=False, unique=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SleeveType {self.name}>"


class Fit(Base):
    __tablename__ = "fits"
    fit_id = Column(Integer, primary_key=True, index=True)
    name   = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Fit {self.name}>"


class Pattern(Base):
    __tablename__ = "patterns"
    pattern_id = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Pattern {self.name}>"


class Product(Base):
    __tablename__ = "products"
    product_id       = Column(Integer, primary_key=True, index=True)
    platform_id      = Column(SmallInteger, ForeignKey("platforms.id"), nullable=False)
    brand_id         = Column(Integer, ForeignKey("brands.brand_id"), nullable=True)
    category_id      = Column(Integer, ForeignKey("categories.category_id"), nullable=True)
    title            = Column(Text, nullable=False)
    url              = Column(Text, nullable=False, unique=True)
    platform_item_id = Column(String(100), nullable=True)
    image            = Column(LargeBinary, nullable=True)
    material         = Column(Text, nullable=True)
    neck_type        = Column(String(100), nullable=True)
    sleeve_type      = Column(String(100), nullable=True)
    fit              = Column(String(100), nullable=True)
    pattern          = Column(String(100), nullable=True)
    care             = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    scraped_at       = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Product {self.title[:40]}>"


class ProductVariant(Base):
    __tablename__ = "product_variants"
    variant_id     = Column(Integer, primary_key=True, index=True)
    product_id     = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    color_id       = Column(Integer, ForeignKey("colors.color_id"), nullable=True)
    size_id        = Column(Integer, ForeignKey("sizes.size_id"), nullable=True)
    material_id    = Column(Integer, ForeignKey("materials.material_id"), nullable=True)
    neck_type_id   = Column(Integer, ForeignKey("neck_types.neck_type_id"), nullable=True)
    sleeve_type_id = Column(Integer, ForeignKey("sleeve_types.sleeve_type_id"), nullable=True)
    fit_id         = Column(Integer, ForeignKey("fits.fit_id"), nullable=True)
    pattern_id     = Column(Integer, ForeignKey("patterns.pattern_id"), nullable=True)
    is_available   = Column(Boolean, nullable=False, default=True)
    price          = Column(Numeric(10, 2), nullable=True)
    original_price = Column(Numeric(10, 2), nullable=True)
    discount_pct   = Column(Numeric(5, 2), nullable=True)
    currency       = Column(String(3), nullable=False, default="USD")
    image           = Column(LargeBinary, nullable=True)
    image_url       = Column(Text, nullable=True)
    low_stock      = Column(Boolean, nullable=False, default=False)
    stock_note     = Column(String(200), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    scraped_at     = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ProductVariant product={self.product_id} color={self.color_id} size={self.size_id}>"


class Review(Base):
    __tablename__ = "reviews"
    review_id    = Column(Integer, primary_key=True, index=True)
    product_id   = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    rating_avg   = Column(Numeric(3, 1), nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    fit_feedback = Column(String(100), nullable=True)
    stars_1_pct  = Column(SmallInteger, nullable=True)
    stars_2_pct  = Column(SmallInteger, nullable=True)
    stars_3_pct  = Column(SmallInteger, nullable=True)
    stars_4_pct  = Column(SmallInteger, nullable=True)
    stars_5_pct  = Column(SmallInteger, nullable=True)
    pros         = Column(JSON, nullable=True)
    cons         = Column(JSON, nullable=True)
    comment_json  = Column(JSONB, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    scraped_at   = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Review product={self.product_id} rating={self.rating_avg}>"


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    id                  = Column(Integer,     primary_key=True, index=True)
    recommendation_text = Column(Text,        nullable=False)
    category            = Column(String(100), nullable=True)
    action              = Column(String(20),  nullable=False)
    modified_text       = Column(Text,        nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<RecommendationFeedback {self.action} | {self.recommendation_text[:40]}>"


class TrendScore(Base):
    __tablename__ = "trend_scores"
    score_id            = Column(Integer,      primary_key=True, index=True)
    category            = Column(String(100),  nullable=True)
    platform            = Column(String(50),   nullable=True)
    attr_key            = Column(String(50),   nullable=True)
    attr_value          = Column(String(100),  nullable=True)
    review_count        = Column(Integer,       nullable=False, default=0)
    review_growth_pct   = Column(Numeric(12, 2),nullable=True)
    avg_rating          = Column(Numeric(3, 1),nullable=True)
    category_avg_rating = Column(Numeric(3, 1),nullable=True)
    rating_delta        = Column(Numeric(4, 2),nullable=True)
    product_count       = Column(Integer,      nullable=False, default=0)
    new_product_share   = Column(Numeric(6, 4),nullable=True)
    momentum_score      = Column(Numeric(8, 4),nullable=True)
    trend_direction     = Column(String(20),   nullable=True)
    lifecycle_stage     = Column(String(20),   nullable=True)
    retailer_action     = Column(Text,         nullable=True)
    lifecycle_explanation = Column(Text,       nullable=True)
    weeks_observed      = Column(Integer,      nullable=False, default=0)
    latest_week_share   = Column(Numeric(6, 4),nullable=True)
    previous_week_share = Column(Numeric(6, 4),nullable=True)
    explanation         = Column(Text,         nullable=True)
    computed_at         = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TrendScore {self.attr_key}={self.attr_value} score={self.momentum_score}>"


class Recommendation(Base):
    __tablename__ = "recommendations"
    rec_id              = Column(Integer,      primary_key=True, index=True)
    category            = Column(String(100),  nullable=True)
    platform            = Column(String(100),  nullable=True)
    pattern_type        = Column(String(100),  nullable=True)
    evidence            = Column(JSONB,        nullable=True)
    recommendation_text = Column(Text,         nullable=False)
    observation         = Column(Text,         nullable=True)
    action              = Column(Text,         nullable=True)
    impact              = Column(Text,         nullable=True)
    confidence          = Column(String(20),   nullable=True)
    status              = Column(String(20),   nullable=False, default="pending")
    modified_text       = Column(Text,         nullable=True)
    generated_at        = Column(DateTime(timezone=True), server_default=func.now())
    actioned_at         = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Recommendation {self.pattern_type} | {self.status}>"


# class VariantSnapshot(Base):
#     __tablename__ = "variant_snapshots"
#     id             = Column(Integer,         primary_key=True, index=True)
#     variant_id     = Column(Integer,         ForeignKey("product_variants.variant_id"), nullable=False, index=True)
#     price          = Column(Numeric(10, 2),  nullable=True)
#     original_price = Column(Numeric(10, 2),  nullable=True)
#     discount_pct   = Column(Numeric(5, 2),   nullable=True)
#     is_available   = Column(Boolean,         nullable=False, default=True)
#     low_stock      = Column(Boolean,         nullable=False, default=False)
#     stock_note     = Column(String(200),     nullable=True)
#     scraped_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

#     def __repr__(self):
#         return f"<VariantSnapshot variant={self.variant_id} price={self.price} at={self.scraped_at}>"


# class ProductReviewSnapshot(Base):
#     __tablename__ = "product_review_snapshots"
#     id           = Column(Integer,        primary_key=True, index=True)
#     product_id   = Column(Integer,        ForeignKey("products.product_id"), nullable=False, index=True)
#     rating_avg   = Column(Numeric(3, 1),  nullable=True)
#     review_count = Column(Integer,        nullable=False, default=0)
#     fit_feedback = Column(String(100),    nullable=True)
#     stars_1_pct  = Column(SmallInteger,   nullable=True)
#     stars_2_pct  = Column(SmallInteger,   nullable=True)
#     stars_3_pct  = Column(SmallInteger,   nullable=True)
#     stars_4_pct  = Column(SmallInteger,   nullable=True)
#     stars_5_pct  = Column(SmallInteger,   nullable=True)
#     scraped_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

#     def __repr__(self):
#         return f"<ProductReviewSnapshot product={self.product_id} rating={self.rating_avg} at={self.scraped_at}>"
