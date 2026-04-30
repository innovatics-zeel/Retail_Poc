from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    DateTime,
    Boolean,
)
from sqlalchemy.sql import func

from database.connection import Base


class NordstromMensTshirt(Base):
    __tablename__ = "nordstrom_mens_tshirts"

    id = Column(Integer, primary_key=True, index=True)

    platform = Column(String(50), nullable=False, default="nordstrom")
    url = Column(Text, nullable=False, unique=True)

    title = Column(Text, nullable=False)
    brand = Column(String(200))
    description = Column(Text)
    category = Column(String(100), nullable=False, default="mens_tshirts")
    gender = Column(String(30), nullable=False, default="men")
    sub_category = Column(String(150))

    current_price = Column(Numeric(10, 2))
    discount_price = Column(Numeric(10, 2))
    actual_price = Column(Numeric(10, 2))
    original_price = Column(Numeric(10, 2))
    discount_percent = Column(Numeric(5, 2))
    price_text = Column(Text)
    discount_text = Column(Text)
    currency = Column(String(10), default="USD")

    color = Column(Text)
    size = Column(Text)
    stock_json = Column(Text)
    pattern = Column(String(150))
    material = Column(Text)
    neck_type = Column(String(150))
    sleeve_type = Column(String(150))
    fit = Column(String(150))
    dress_length = Column(String(150))
    occasion = Column(String(150))
    closure_type = Column(String(150))
    care_instructions = Column(Text)

    rating = Column(Numeric(3, 2))
    review_count = Column(Integer, default=0)
    review_fit = Column(Text)
    star_distribution_json = Column(Text)
    review_pros_json = Column(Text)
    review_cons_json = Column(Text)
    review_details_json = Column(Text)

    raw_attributes_json = Column(Text)
    data_label = Column(String(100), default="demonstration_data")
    poc_run_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<NordstromMensTshirt {self.brand} | {self.title[:40]}>"


class AmazonWomensDress(Base):
    __tablename__ = "amazon_womens_dresses"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="amazon")
    url = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=False)
    brand = Column(String(200))
    asin = Column(String(50), unique=True)
    category = Column(String(100), nullable=False, default="women_dresses")
    gender = Column(String(30), nullable=False, default="women")
    unit_count = Column(Integer, nullable=False, default=1)

    # Variants JSON: color, size, current_price, original_price,
    # discount_price, discount_percent, currency.
    variants_json = Column(Text)

    # Attributes JSON: occasion, apparel_silhouette, neck_style,
    # sleeve_type, seasons, style, closure, back_style, strap_type,
    # pattern, waist_style, collar_type, material_type.
    attributes_json = Column(Text)

    # Reviews JSON: rating, review_count, review_summary,
    # star_distribution, review_details.
    reviews_json = Column(Text)

    raw_attributes_json = Column(Text)
    data_label = Column(String(100), default="demonstration_data")
    poc_run_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AmazonWomensDress {self.brand} | {self.title[:40]}>"


class AmazonMensTshirt(Base):
    __tablename__ = "amazon_mens_tshirts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="amazon")
    url = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=False)
    brand = Column(String(200))
    asin = Column(String(50), unique=True)
    category = Column(String(100), nullable=False, default="mens_tshirt")
    gender = Column(String(30), nullable=False, default="men")
    unit_count = Column(Integer, nullable=False, default=1)

    # Variants JSON: color, size, current_price, original_price,
    # discount_price, discount_percent, currency.
    variants_json = Column(Text)

    # Attributes JSON: occasion, cuff_type, neck_style, sleeve_type,
    # seasons, style, closure, pattern, collar_type, fit_type,
    # material_type, care_instructions.
    attributes_json = Column(Text)

    # Reviews JSON: rating, review_count, review_summary,
    # star_distribution, review_details.
    reviews_json = Column(Text)

    raw_attributes_json = Column(Text)
    data_label = Column(String(100), default="demonstration_data")
    poc_run_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AmazonMensTshirt {self.brand} | {self.title[:40]}>"
