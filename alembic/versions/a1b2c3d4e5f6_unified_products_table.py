"""Unified products table — replaces nordstrom_mens_tshirts and nordstrom_womens_dresses

Revision ID: a1b2c3d4e5f6
Revises: e986b170af86
Create Date: 2026-04-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'e986b170af86'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old platform-specific tables
    op.drop_index('ix_nordstrom_womens_dresses_id', table_name='nordstrom_womens_dresses', if_exists=True)
    op.drop_table('nordstrom_womens_dresses')

    op.drop_index('ix_nordstrom_mens_tshirts_id', table_name='nordstrom_mens_tshirts', if_exists=True)
    op.drop_table('nordstrom_mens_tshirts')

    # Create unified products table
    op.create_table(
        'products',
        sa.Column('id',               sa.Integer(),      nullable=False),
        sa.Column('platform',         sa.String(50),     nullable=False),
        sa.Column('platform_id',      sa.Integer(),      nullable=True),
        sa.Column('url',              sa.Text(),         nullable=False),
        sa.Column('asin',             sa.String(20),     nullable=True),
        sa.Column('title',            sa.Text(),         nullable=False),
        sa.Column('brand',            sa.String(200),    nullable=True),
        sa.Column('description',      sa.Text(),         nullable=True),
        sa.Column('category',         sa.String(100),    nullable=False),
        sa.Column('gender',           sa.String(30),     nullable=False),
        sa.Column('sub_category',     sa.String(150),    nullable=True),
        sa.Column('currency',         sa.String(10),     nullable=True),
        sa.Column('current_price',    sa.Numeric(10, 2), nullable=True),
        sa.Column('original_price',   sa.Numeric(10, 2), nullable=True),
        sa.Column('discount_percent', sa.Numeric(5, 2),  nullable=True),
        sa.Column('rating',           sa.Numeric(3, 2),  nullable=True),
        sa.Column('review_count',     sa.Integer(),      nullable=True),
        sa.Column('attributes_json',  sa.Text(),         nullable=True),
        sa.Column('price_json',       sa.Text(),         nullable=True),
        sa.Column('review_json',      sa.Text(),         nullable=True),
        sa.Column('raw_json',         sa.Text(),         nullable=True),
        sa.Column('data_label',       sa.String(100),    nullable=True),
        sa.Column('poc_run_id',       sa.String(100),    nullable=True),
        sa.Column('is_active',        sa.Boolean(),      nullable=True),
        sa.Column('scraped_at',       sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at',       sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url'),
    )
    op.create_index('ix_products_id',               'products', ['id'],                   unique=False)
    op.create_index('ix_products_platform_category','products', ['platform', 'category'], unique=False)
    op.create_index('ix_products_category_price',   'products', ['category', 'current_price'], unique=False)
    op.create_index('ix_products_category_rating',  'products', ['category', 'rating'],   unique=False)
    op.create_index('ix_products_scraped_at',       'products', ['scraped_at'],            unique=False)

    # Create recommendation_feedback table
    op.create_table(
        'recommendation_feedback',
        sa.Column('id',                   sa.Integer(), nullable=False),
        sa.Column('recommendation_text',  sa.Text(),    nullable=False),
        sa.Column('category',             sa.String(100), nullable=True),
        sa.Column('action',               sa.String(20),  nullable=False),
        sa.Column('modified_text',        sa.Text(),    nullable=True),
        sa.Column('created_at',           sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recommendation_feedback_id', 'recommendation_feedback', ['id'], unique=False)


def downgrade():
    op.drop_index('ix_recommendation_feedback_id', table_name='recommendation_feedback')
    op.drop_table('recommendation_feedback')

    op.drop_index('ix_products_scraped_at',        table_name='products')
    op.drop_index('ix_products_category_rating',   table_name='products')
    op.drop_index('ix_products_category_price',    table_name='products')
    op.drop_index('ix_products_platform_category', table_name='products')
    op.drop_index('ix_products_id',                table_name='products')
    op.drop_table('products')
