"""add created_at audit columns

Revision ID: c8d9e0f1a2b3
Revises: 1cdf2c149c33
Create Date: 2026-05-04 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c8d9e0f1a2b3"
down_revision = "1cdf2c149c33"
branch_labels = None
depends_on = None


_TABLES = [
    "platforms",
    "brands",
    "categories",
    "colors",
    "sizes",
    "materials",
    "neck_types",
    "sleeve_types",
    "fits",
    "patterns",
    "products",
    "product_variants",
    "reviews",
]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in _TABLES:
        columns = {col["name"] for col in inspector.get_columns(table_name)}
        if "created_at" not in columns:
            op.add_column(
                table_name,
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=True,
                ),
            )

    indexes = {
        table: {idx["name"] for idx in inspector.get_indexes(table)}
        for table in ("products", "product_variants", "reviews")
    }
    if "ix_products_created_at" not in indexes["products"]:
        op.create_index("ix_products_created_at", "products", ["created_at"], unique=False)
    if "ix_product_variants_created_at" not in indexes["product_variants"]:
        op.create_index("ix_product_variants_created_at", "product_variants", ["created_at"], unique=False)
    if "ix_reviews_created_at" not in indexes["reviews"]:
        op.create_index("ix_reviews_created_at", "reviews", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_reviews_created_at", table_name="reviews")
    op.drop_index("ix_product_variants_created_at", table_name="product_variants")
    op.drop_index("ix_products_created_at", table_name="products")

    for table_name in reversed(_TABLES):
        op.drop_column(table_name, "created_at")
