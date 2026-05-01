"""Restore nordstrom_mens_tshirts and nordstrom_womens_dresses with 3-JSON schema

Revision ID: c3d4e5f6a7b8
Revises: 2881141dffd3
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = '2881141dffd3'
branch_labels = None
depends_on = None

_COMMON = [
    sa.Column('id',               sa.Integer(),       nullable=False),
    sa.Column('platform',         sa.String(50),      nullable=False),
    sa.Column('platform_id',      sa.Integer(),       nullable=True),
    sa.Column('url',              sa.Text(),          nullable=False),
    sa.Column('title',            sa.Text(),          nullable=False),
    sa.Column('brand',            sa.String(200),     nullable=True),
    sa.Column('description',      sa.Text(),          nullable=True),
    sa.Column('category',         sa.String(100),     nullable=False),
    sa.Column('gender',           sa.String(30),      nullable=False),
    sa.Column('sub_category',     sa.String(150),     nullable=True),
    sa.Column('currency',         sa.String(10),      nullable=True),
    sa.Column('current_price',    sa.Numeric(10, 2),  nullable=True),
    sa.Column('original_price',   sa.Numeric(10, 2),  nullable=True),
    sa.Column('discount_percent', sa.Numeric(5, 2),   nullable=True),
    sa.Column('rating',           sa.Numeric(3, 2),   nullable=True),
    sa.Column('review_count',     sa.Integer(),       nullable=True),
    sa.Column('attributes_json',  sa.Text(),          nullable=True),
    sa.Column('price_json',       sa.Text(),          nullable=True),
    sa.Column('review_json',      sa.Text(),          nullable=True),
    sa.Column('raw_json',         sa.Text(),          nullable=True),
    sa.Column('data_label',       sa.String(100),     nullable=True),
    sa.Column('poc_run_id',       sa.String(100),     nullable=True),
    sa.Column('is_active',        sa.Boolean(),       nullable=True),
    sa.Column('scraped_at',       sa.DateTime(timezone=True),
              server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at',       sa.DateTime(timezone=True),
              server_default=sa.text('now()'), nullable=True),
]


def upgrade():
    # Drop the unified products table (from the previous migration path)
    op.drop_index('ix_products_id', table_name='products', if_exists=True)
    op.drop_table('products')

    # Recreate nordstrom_mens_tshirts with clean 3-JSON schema
    op.create_table(
        'nordstrom_mens_tshirts',
        *_COMMON,
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )
    op.create_index('ix_nordstrom_mens_tshirts_id', 'nordstrom_mens_tshirts', ['id'], unique=False)

    # Recreate nordstrom_womens_dresses with clean 3-JSON schema
    op.create_table(
        'nordstrom_womens_dresses',
        *_COMMON,
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )
    op.create_index('ix_nordstrom_womens_dresses_id', 'nordstrom_womens_dresses', ['id'], unique=False)


def downgrade():
    op.drop_index('ix_nordstrom_womens_dresses_id', table_name='nordstrom_womens_dresses')
    op.drop_table('nordstrom_womens_dresses')

    op.drop_index('ix_nordstrom_mens_tshirts_id', table_name='nordstrom_mens_tshirts')
    op.drop_table('nordstrom_mens_tshirts')

    # Recreate products table for downgrade
    op.create_table(
        'products',
        sa.Column('id',               sa.Integer(),       nullable=False),
        sa.Column('platform',         sa.String(50),      nullable=False),
        sa.Column('platform_id',      sa.Integer(),       nullable=True),
        sa.Column('url',              sa.Text(),          nullable=False),
        sa.Column('title',            sa.Text(),          nullable=False),
        sa.Column('brand',            sa.String(200),     nullable=True),
        sa.Column('description',      sa.Text(),          nullable=True),
        sa.Column('category',         sa.String(100),     nullable=False),
        sa.Column('gender',           sa.String(30),      nullable=False),
        sa.Column('sub_category',     sa.String(150),     nullable=True),
        sa.Column('currency',         sa.String(10),      nullable=True),
        sa.Column('current_price',    sa.Numeric(10, 2),  nullable=True),
        sa.Column('original_price',   sa.Numeric(10, 2),  nullable=True),
        sa.Column('discount_percent', sa.Numeric(5, 2),   nullable=True),
        sa.Column('rating',           sa.Numeric(3, 2),   nullable=True),
        sa.Column('review_count',     sa.Integer(),       nullable=True),
        sa.Column('attributes_json',  sa.Text(),          nullable=True),
        sa.Column('price_json',       sa.Text(),          nullable=True),
        sa.Column('review_json',      sa.Text(),          nullable=True),
        sa.Column('raw_json',         sa.Text(),          nullable=True),
        sa.Column('data_label',       sa.String(100),     nullable=True),
        sa.Column('poc_run_id',       sa.String(100),     nullable=True),
        sa.Column('is_active',        sa.Boolean(),       nullable=True),
        sa.Column('scraped_at',       sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at',       sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )
    op.create_index('ix_products_id', 'products', ['id'], unique=False)
