from sqlalchemy import Column, Integer, SmallInteger, String, Text, Numeric, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from database.connection import Base

GENDER_ID = {"men": 1, "women": 2, "unisex": 3}


class Platform(Base):
    __tablename__ = "platforms"
    id           = Column(SmallInteger, primary_key=True, index=True)
    name         = Column(String(50),  nullable=False, unique=True)
    display_name = Column(String(100), nullable=True)
    base_url     = Column(Text,        nullable=False)

    def __repr__(self):
        return f"<Platform {self.name}>"


class Brand(Base):
    __tablename__ = "brands"
    brand_id = Column(Integer, primary_key=True, index=True)
    name     = Column(String(200), nullable=False, unique=True)

    def __repr__(self):
        return f"<Brand {self.name}>"


class Category(Base):
    __tablename__ = "categories"
    category_id = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False, unique=True)
    gender      = Column(String(20), nullable=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Color(Base):
    __tablename__ = "colors"
    color_id     = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False, unique=True)
    color_family = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<Color {self.name} / {self.color_family}>"


class Size(Base):
    __tablename__ = "sizes"
    size_id     = Column(Integer, primary_key=True, index=True)
    label       = Column(String(50), nullable=False, unique=True)
    sort_order  = Column(Integer, nullable=False, default=999)
    size_system = Column(String(20), nullable=False, default="alpha")

    def __repr__(self):
        return f"<Size {self.label}>"


class Product(Base):
    __tablename__ = "products"
    product_id       = Column(Integer, primary_key=True, index=True)
    platform_id      = Column(SmallInteger, ForeignKey("platforms.id"), nullable=False)
    brand_id         = Column(Integer, ForeignKey("brands.brand_id"), nullable=True)
    category_id      = Column(Integer, ForeignKey("categories.category_id"), nullable=True)
    title            = Column(Text, nullable=False)
    url              = Column(Text, nullable=False, unique=True)
    platform_item_id = Column(String(100), nullable=True)
    material         = Column(Text, nullable=True)
    neck_type        = Column(String(100), nullable=True)
    sleeve_type      = Column(String(100), nullable=True)
    fit              = Column(String(100), nullable=True)
    pattern          = Column(String(100), nullable=True)
    care             = Column(Text, nullable=True)
    scraped_at       = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Product {self.title[:40]}>"


class ProductVariant(Base):
    __tablename__ = "product_variants"
    variant_id     = Column(Integer, primary_key=True, index=True)
    product_id     = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    color_id       = Column(Integer, ForeignKey("colors.color_id"), nullable=True)
    size_id        = Column(Integer, ForeignKey("sizes.size_id"), nullable=True)
    is_available   = Column(Boolean, nullable=False, default=True)
    price          = Column(Numeric(10, 2), nullable=True)
    original_price = Column(Numeric(10, 2), nullable=True)
    discount_pct   = Column(Numeric(5, 2), nullable=True)
    currency       = Column(String(3), nullable=False, default="USD")
    low_stock      = Column(Boolean, nullable=False, default=False)
    stock_note     = Column(String(200), nullable=True)
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
