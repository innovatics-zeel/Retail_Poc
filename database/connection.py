"""
connection.py
─────────────────────────────────────────────────────────
Local PostgreSQL connection using SQLAlchemy.
No Docker, no cloud — just your local pgAdmin instance.

Before running:
  1. Open pgAdmin → create database  : Innovatics_Retail
  2. Copy .env.example → .env        : fill in DB_USER / DB_PASSWORD
  3. Run:  python -c "from database.connection import run_migrations"
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.settings import settings

# ── Engine — single local connection ──────────────────────────
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # drops stale connections automatically
    echo=False,           # set True to print every SQL query
)

# ── Session factory ────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── ORM base ──────────────────────────────────────────────────
Base = declarative_base()


def get_db():
    """Yield a DB session, always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """Returns True if local PostgreSQL is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"✅ Connected to PostgreSQL → {settings.db_name} @ {settings.db_host}:{settings.db_port}")
        return True
    except Exception as e:
        logger.error(f"❌ Cannot connect to PostgreSQL: {e}")
        logger.error(f"   Check your .env — DB_HOST={settings.db_host} DB_USER={settings.db_user} DB_NAME={settings.db_name}")
        return False


# Maps each migration filename to the DB table it creates.
# Used to bootstrap the tracking table when it's introduced to an existing DB.
_MIGRATION_TABLE = {
    "001_create_sku_listings.sql":    "sku_listings",
    "002_create_sku_attributes.sql":  "sku_attributes",
    "003_create_price_snapshots.sql": "price_snapshots",
    "004_create_review_signals.sql":  "review_signals",
    "005_create_platforms.sql":       "platforms",
    "008_create_nordstrom_mens_tshirts.sql": "nordstrom_mens_tshirts",
    "009_create_amazon_womens_dresses.sql": "amazon_womens_dresses",
    "010_create_amazon_mens_tshirts.sql": "amazon_mens_tshirts",
}

_REQUIRED_SCHEMA = {
    "nordstrom_mens_tshirts": {
        "id",
        "platform",
        "url",
        "title",
        "brand",
        "description",
        "category",
        "gender",
        "sub_category",
        "current_price",
        "discount_price",
        "actual_price",
        "original_price",
        "discount_percent",
        "price_text",
        "discount_text",
        "currency",
        "color",
        "size",
        "stock_json",
        "pattern",
        "material",
        "neck_type",
        "sleeve_type",
        "fit",
        "dress_length",
        "occasion",
        "closure_type",
        "care_instructions",
        "rating",
        "review_count",
        "review_fit",
        "star_distribution_json",
        "review_pros_json",
        "review_cons_json",
        "review_details_json",
        "raw_attributes_json",
        "data_label",
        "poc_run_id",
        "is_active",
        "scraped_at",
        "updated_at",
    },
    "amazon_womens_dresses": {
        "id",
        "platform",
        "url",
        "title",
        "brand",
        "asin",
        "category",
        "gender",
        "unit_count",
        "variants_json",
        "attributes_json",
        "reviews_json",
        "raw_attributes_json",
        "data_label",
        "poc_run_id",
        "is_active",
        "scraped_at",
        "updated_at",
    },
    "amazon_mens_tshirts": {
        "id",
        "platform",
        "url",
        "title",
        "brand",
        "asin",
        "category",
        "gender",
        "unit_count",
        "variants_json",
        "attributes_json",
        "reviews_json",
        "raw_attributes_json",
        "data_label",
        "poc_run_id",
        "is_active",
        "scraped_at",
        "updated_at",
    },
}

_REQUIRED_COLUMN_TYPES = {
    ("nordstrom_mens_tshirts", "url"): "text",
    ("nordstrom_mens_tshirts", "description"): "text",
    ("nordstrom_mens_tshirts", "color"): "text",
    ("nordstrom_mens_tshirts", "size"): "text",
    ("nordstrom_mens_tshirts", "stock_json"): "text",
    ("nordstrom_mens_tshirts", "review_details_json"): "text",
    ("amazon_womens_dresses", "url"): "text",
    ("amazon_womens_dresses", "variants_json"): "text",
    ("amazon_womens_dresses", "attributes_json"): "text",
    ("amazon_womens_dresses", "reviews_json"): "text",
    ("amazon_womens_dresses", "raw_attributes_json"): "text",
    ("amazon_mens_tshirts", "url"): "text",
    ("amazon_mens_tshirts", "variants_json"): "text",
    ("amazon_mens_tshirts", "attributes_json"): "text",
    ("amazon_mens_tshirts", "reviews_json"): "text",
    ("amazon_mens_tshirts", "raw_attributes_json"): "text",
}


def _table_exists(conn, table_name: str) -> bool:
    return conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = :t
        )
    """), {"t": table_name}).scalar()


def _table_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :t
    """), {"t": table_name})
    return {row[0] for row in rows}


def _column_type(conn, table_name: str, column_name: str) -> str | None:
    return conn.execute(text("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :t
          AND column_name = :c
    """), {"t": table_name, "c": column_name}).scalar()


def verify_schema() -> bool:
    """Check that the manually managed DB schema matches the current ORM model."""
    try:
        with engine.connect() as conn:
            missing_tables = []
            missing_columns = {}

            for table_name, required_columns in _REQUIRED_SCHEMA.items():
                if not _table_exists(conn, table_name):
                    missing_tables.append(table_name)
                    continue

                existing_columns = _table_columns(conn, table_name)
                missing = sorted(required_columns - existing_columns)
                if missing:
                    missing_columns[table_name] = missing

            wrong_types = {}
            for (table_name, column_name), required_type in _REQUIRED_COLUMN_TYPES.items():
                existing_type = _column_type(conn, table_name, column_name)
                if existing_type and existing_type != required_type:
                    wrong_types[f"{table_name}.{column_name}"] = existing_type

            if missing_tables or missing_columns or wrong_types:
                if missing_tables:
                    logger.error(f"Missing tables: {', '.join(missing_tables)}")
                for table_name, columns in missing_columns.items():
                    logger.error(f"Missing columns in {table_name}: {', '.join(columns)}")
                for column_name, existing_type in wrong_types.items():
                    logger.error(f"Wrong type for {column_name}: {existing_type} (expected text)")
                return False

        logger.info("Database schema matches the current scraper model.")
        return True
    except Exception as e:
        logger.error(f"Cannot verify database schema: {e}")
        return False


def run_migrations():
    """
    Executes pending SQL migration files in database/migrations/ in order.
    Tracks applied migrations in schema_migrations — skips already-run files.
    On first use, bootstraps the tracking table from tables that already exist.
    """
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    sql_files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        conn.commit()

        # Bootstrap: schema_migrations is new and empty, but tables may already exist.
        # Mark pre-existing migrations as applied so they are not re-run.
        row_count = conn.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar()
        if row_count == 0:
            bootstrapped = False
            for fname, table in _MIGRATION_TABLE.items():
                if fname in sql_files and _table_exists(conn, table):
                    conn.execute(
                        text("INSERT INTO schema_migrations (filename) VALUES (:f) ON CONFLICT DO NOTHING"),
                        {"f": fname},
                    )
                    logger.info(f"  ⏭  {fname} (already applied — bootstrapped)")
                    bootstrapped = True
            if bootstrapped:
                conn.commit()

        applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_migrations"))}
        pending = [f for f in sql_files if f not in applied]

        if not pending:
            logger.info("All migrations already applied — nothing to run.")
            return

        logger.info(f"Running {len(pending)} new migration(s)...")
        for fname in pending:
            fpath = os.path.join(migrations_dir, fname)
            with open(fpath, "r") as f:
                sql = f.read()
            try:
                conn.execute(text(sql))
                conn.execute(
                    text("INSERT INTO schema_migrations (filename) VALUES (:f)"),
                    {"f": fname},
                )
                conn.commit()
                logger.info(f"  ✅ {fname}")
            except Exception as e:
                conn.rollback()
                logger.warning(f"  ⚠️  {fname} — {e}")
    logger.info("Migrations complete.")


if __name__ == "__main__":
    # Quick test — run: python database/connection.py
    if test_connection():
        run_migrations()
