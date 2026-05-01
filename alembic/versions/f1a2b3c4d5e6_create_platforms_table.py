"""Create platforms table (if it doesn't already exist from legacy SQL migrations)

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'f1a2b3c4d5e6'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    exists = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'platforms'
        )
    """)).scalar()

    if not exists:
        op.create_table(
            'platforms',
            sa.Column('id',           sa.SmallInteger(), nullable=False),
            sa.Column('name',         sa.String(50),     nullable=False),
            sa.Column('display_name', sa.String(100),    nullable=True),
            sa.Column('base_url',     sa.Text(),         nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
        )
        op.create_index('ix_platforms_id', 'platforms', ['id'], unique=False)

        op.execute("""
            INSERT INTO platforms (id, name, display_name, base_url) VALUES
            (1, 'amazon',    'Amazon',    'https://www.amazon.com'),
            (2, 'nordstrom', 'Nordstrom', 'https://www.nordstrom.com')
            ON CONFLICT DO NOTHING
        """)


def downgrade():
    op.drop_index('ix_platforms_id', table_name='platforms', if_exists=True)
    op.drop_table('platforms')
