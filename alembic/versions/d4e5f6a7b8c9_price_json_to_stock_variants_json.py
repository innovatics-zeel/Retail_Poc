"""Replace price_json with stock_variants_json on both platform tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-30
"""
from alembic import op

revision = 'd4e5f6a7b8c9'
down_revision = '075dd146dd06'
branch_labels = None
depends_on = None

_TABLES = ["nordstrom_mens_tshirts", "nordstrom_womens_dresses"]


def upgrade():
    for t in _TABLES:
        op.alter_column(t, "price_json", new_column_name="stock_variants_json")


def downgrade():
    for t in _TABLES:
        op.alter_column(t, "stock_variants_json", new_column_name="price_json")
