"""add attribute master tables

Revision ID: b7c8d9e0f1a2
Revises: 374a50606fd4
Create Date: 2026-05-04 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "374a50606fd4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "materials",
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("material_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_materials_material_id"), "materials", ["material_id"], unique=False)

    op.create_table(
        "neck_types",
        sa.Column("neck_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("neck_type_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_neck_types_neck_type_id"), "neck_types", ["neck_type_id"], unique=False)

    op.create_table(
        "sleeve_types",
        sa.Column("sleeve_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("sleeve_type_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_sleeve_types_sleeve_type_id"), "sleeve_types", ["sleeve_type_id"], unique=False)

    op.create_table(
        "fits",
        sa.Column("fit_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("fit_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_fits_fit_id"), "fits", ["fit_id"], unique=False)

    op.create_table(
        "patterns",
        sa.Column("pattern_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("pattern_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_patterns_pattern_id"), "patterns", ["pattern_id"], unique=False)

    op.add_column("product_variants", sa.Column("material_id", sa.Integer(), nullable=True))
    op.add_column("product_variants", sa.Column("neck_type_id", sa.Integer(), nullable=True))
    op.add_column("product_variants", sa.Column("sleeve_type_id", sa.Integer(), nullable=True))
    op.add_column("product_variants", sa.Column("fit_id", sa.Integer(), nullable=True))
    op.add_column("product_variants", sa.Column("pattern_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_product_variants_material_id_materials",
        "product_variants", "materials", ["material_id"], ["material_id"],
    )
    op.create_foreign_key(
        "fk_product_variants_neck_type_id_neck_types",
        "product_variants", "neck_types", ["neck_type_id"], ["neck_type_id"],
    )
    op.create_foreign_key(
        "fk_product_variants_sleeve_type_id_sleeve_types",
        "product_variants", "sleeve_types", ["sleeve_type_id"], ["sleeve_type_id"],
    )
    op.create_foreign_key(
        "fk_product_variants_fit_id_fits",
        "product_variants", "fits", ["fit_id"], ["fit_id"],
    )
    op.create_foreign_key(
        "fk_product_variants_pattern_id_patterns",
        "product_variants", "patterns", ["pattern_id"], ["pattern_id"],
    )

    op.create_index(op.f("ix_product_variants_material_id"), "product_variants", ["material_id"], unique=False)
    op.create_index(op.f("ix_product_variants_neck_type_id"), "product_variants", ["neck_type_id"], unique=False)
    op.create_index(op.f("ix_product_variants_sleeve_type_id"), "product_variants", ["sleeve_type_id"], unique=False)
    op.create_index(op.f("ix_product_variants_fit_id"), "product_variants", ["fit_id"], unique=False)
    op.create_index(op.f("ix_product_variants_pattern_id"), "product_variants", ["pattern_id"], unique=False)

    # Backfill from the legacy product text columns so existing scraped data remains queryable.
    op.execute("""
        INSERT INTO materials (name)
        SELECT DISTINCT TRIM(material)
        FROM products
        WHERE NULLIF(TRIM(material), '') IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO neck_types (name)
        SELECT DISTINCT TRIM(neck_type)
        FROM products
        WHERE NULLIF(TRIM(neck_type), '') IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO sleeve_types (name)
        SELECT DISTINCT TRIM(sleeve_type)
        FROM products
        WHERE NULLIF(TRIM(sleeve_type), '') IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO fits (name)
        SELECT DISTINCT TRIM(fit)
        FROM products
        WHERE NULLIF(TRIM(fit), '') IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO patterns (name)
        SELECT DISTINCT TRIM(pattern)
        FROM products
        WHERE NULLIF(TRIM(pattern), '') IS NOT NULL
        ON CONFLICT (name) DO NOTHING
    """)

    op.execute("""
        UPDATE product_variants pv
        SET material_id = m.material_id
        FROM products p
        JOIN materials m ON m.name = TRIM(p.material)
        WHERE p.product_id = pv.product_id
          AND NULLIF(TRIM(p.material), '') IS NOT NULL
    """)
    op.execute("""
        UPDATE product_variants pv
        SET neck_type_id = nt.neck_type_id
        FROM products p
        JOIN neck_types nt ON nt.name = TRIM(p.neck_type)
        WHERE p.product_id = pv.product_id
          AND NULLIF(TRIM(p.neck_type), '') IS NOT NULL
    """)
    op.execute("""
        UPDATE product_variants pv
        SET sleeve_type_id = st.sleeve_type_id
        FROM products p
        JOIN sleeve_types st ON st.name = TRIM(p.sleeve_type)
        WHERE p.product_id = pv.product_id
          AND NULLIF(TRIM(p.sleeve_type), '') IS NOT NULL
    """)
    op.execute("""
        UPDATE product_variants pv
        SET fit_id = f.fit_id
        FROM products p
        JOIN fits f ON f.name = TRIM(p.fit)
        WHERE p.product_id = pv.product_id
          AND NULLIF(TRIM(p.fit), '') IS NOT NULL
    """)
    op.execute("""
        UPDATE product_variants pv
        SET pattern_id = pat.pattern_id
        FROM products p
        JOIN patterns pat ON pat.name = TRIM(p.pattern)
        WHERE p.product_id = pv.product_id
          AND NULLIF(TRIM(p.pattern), '') IS NOT NULL
    """)


def downgrade():
    op.drop_index(op.f("ix_product_variants_pattern_id"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_fit_id"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_sleeve_type_id"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_neck_type_id"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_material_id"), table_name="product_variants")

    op.drop_constraint("fk_product_variants_pattern_id_patterns", "product_variants", type_="foreignkey")
    op.drop_constraint("fk_product_variants_fit_id_fits", "product_variants", type_="foreignkey")
    op.drop_constraint("fk_product_variants_sleeve_type_id_sleeve_types", "product_variants", type_="foreignkey")
    op.drop_constraint("fk_product_variants_neck_type_id_neck_types", "product_variants", type_="foreignkey")
    op.drop_constraint("fk_product_variants_material_id_materials", "product_variants", type_="foreignkey")

    op.drop_column("product_variants", "pattern_id")
    op.drop_column("product_variants", "fit_id")
    op.drop_column("product_variants", "sleeve_type_id")
    op.drop_column("product_variants", "neck_type_id")
    op.drop_column("product_variants", "material_id")

    op.drop_index(op.f("ix_patterns_pattern_id"), table_name="patterns")
    op.drop_table("patterns")
    op.drop_index(op.f("ix_fits_fit_id"), table_name="fits")
    op.drop_table("fits")
    op.drop_index(op.f("ix_sleeve_types_sleeve_type_id"), table_name="sleeve_types")
    op.drop_table("sleeve_types")
    op.drop_index(op.f("ix_neck_types_neck_type_id"), table_name="neck_types")
    op.drop_table("neck_types")
    op.drop_index(op.f("ix_materials_material_id"), table_name="materials")
    op.drop_table("materials")
