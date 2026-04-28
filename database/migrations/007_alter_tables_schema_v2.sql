-- Migration 007: align existing tables to v2 schema (models.py update)
-- Safe to run on any existing DB — all operations check before altering.

-- ── sku_listings ──────────────────────────────────────────────────────────────

-- New columns
ALTER TABLE sku_listings ADD COLUMN IF NOT EXISTS gender        VARCHAR(30);
ALTER TABLE sku_listings ADD COLUMN IF NOT EXISTS description   TEXT;
ALTER TABLE sku_listings ADD COLUMN IF NOT EXISTS current_price NUMERIC(10,2);
ALTER TABLE sku_listings ADD COLUMN IF NOT EXISTS currency      VARCHAR(10) NOT NULL DEFAULT 'USD';
ALTER TABLE sku_listings ADD COLUMN IF NOT EXISTS rating        NUMERIC(3,2);
ALTER TABLE sku_listings ADD COLUMN IF NOT EXISTS review_count  INTEGER NOT NULL DEFAULT 0;

-- is_available → is_active
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sku_listings' AND column_name = 'is_available'
    ) THEN
        ALTER TABLE sku_listings RENAME COLUMN is_available TO is_active;
    END IF;
END $$;

-- Drop sku_id (url is the unique key in v2)
ALTER TABLE sku_listings DROP COLUMN IF EXISTS sku_id;
ALTER TABLE sku_listings DROP CONSTRAINT IF EXISTS sku_listings_platform_sku_id_key;

-- Add unique constraint on url if missing
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'sku_listings'::regclass AND conname = 'sku_listings_url_key'
    ) THEN
        ALTER TABLE sku_listings ADD CONSTRAINT sku_listings_url_key UNIQUE (url);
    END IF;
END $$;

-- Drop old timestamp columns
ALTER TABLE sku_listings DROP COLUMN IF EXISTS created_at;
ALTER TABLE sku_listings DROP COLUMN IF EXISTS updated_at;

-- New indexes
CREATE INDEX IF NOT EXISTS idx_sku_listings_gender      ON sku_listings(gender);
CREATE INDEX IF NOT EXISTS idx_sku_listings_platform_id ON sku_listings(platform_id);


-- ── sku_attributes ────────────────────────────────────────────────────────────

-- listing_id → sku_id
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sku_attributes' AND column_name = 'listing_id'
    ) THEN
        ALTER TABLE sku_attributes RENAME COLUMN listing_id TO sku_id;
    END IF;
END $$;

-- New columns
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS size                TEXT;
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS dress_length        VARCHAR(150);
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS occasion            VARCHAR(150);
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS closure_type        VARCHAR(150);
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS care_instructions   TEXT;
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS stock_json          TEXT;
ALTER TABLE sku_attributes ADD COLUMN IF NOT EXISTS raw_attributes_json TEXT;

-- Widen existing columns to match v2
ALTER TABLE sku_attributes ALTER COLUMN size      TYPE TEXT;
ALTER TABLE sku_attributes ALTER COLUMN color     TYPE TEXT;
ALTER TABLE sku_attributes ALTER COLUMN pattern   TYPE VARCHAR(150);
ALTER TABLE sku_attributes ALTER COLUMN material  TYPE TEXT;
ALTER TABLE sku_attributes ALTER COLUMN neck_type TYPE VARCHAR(150);
ALTER TABLE sku_attributes ALTER COLUMN sleeve_type TYPE VARCHAR(150);
ALTER TABLE sku_attributes ALTER COLUMN fit       TYPE VARCHAR(150);

-- Drop normalised columns removed in v2
ALTER TABLE sku_attributes DROP COLUMN IF EXISTS color_family;
ALTER TABLE sku_attributes DROP COLUMN IF EXISTS material_family;
ALTER TABLE sku_attributes DROP COLUMN IF EXISTS gender;
ALTER TABLE sku_attributes DROP COLUMN IF EXISTS size_range;

DROP INDEX IF EXISTS idx_sku_attr_color_family;
DROP INDEX IF EXISTS idx_sku_attr_material_family;

CREATE INDEX IF NOT EXISTS idx_sku_attr_neck_type ON sku_attributes(neck_type);
CREATE INDEX IF NOT EXISTS idx_sku_attr_fit       ON sku_attributes(fit);
CREATE INDEX IF NOT EXISTS idx_sku_attr_pattern   ON sku_attributes(pattern);


-- ── price_snapshots ───────────────────────────────────────────────────────────

-- listing_id → sku_id
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'price_snapshots' AND column_name = 'listing_id'
    ) THEN
        ALTER TABLE price_snapshots RENAME COLUMN listing_id TO sku_id;
    END IF;
END $$;

-- discount_pct → discount_percent
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'price_snapshots' AND column_name = 'discount_pct'
    ) THEN
        ALTER TABLE price_snapshots RENAME COLUMN discount_pct TO discount_percent;
    END IF;
END $$;

-- snapshot_at → captured_at
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'price_snapshots' AND column_name = 'snapshot_at'
    ) THEN
        ALTER TABLE price_snapshots RENAME COLUMN snapshot_at TO captured_at;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_price_snap_listing_id;
DROP INDEX IF EXISTS idx_price_snap_snapshot_at;

CREATE INDEX IF NOT EXISTS idx_price_snap_sku_id      ON price_snapshots(sku_id);
CREATE INDEX IF NOT EXISTS idx_price_snap_captured_at ON price_snapshots(captured_at);

ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS price_text    TEXT;
ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS discount_text TEXT;

-- Recreate trigger with DROP IF EXISTS so re-runs are safe
DROP TRIGGER IF EXISTS set_price_band_trigger ON price_snapshots;
CREATE TRIGGER set_price_band_trigger
    BEFORE INSERT OR UPDATE ON price_snapshots
    FOR EACH ROW EXECUTE FUNCTION trg_set_price_band();


-- ── review_signals ────────────────────────────────────────────────────────────

-- listing_id → sku_id
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'review_signals' AND column_name = 'listing_id'
    ) THEN
        ALTER TABLE review_signals RENAME COLUMN listing_id TO sku_id;
    END IF;
END $$;

-- velocity_30d → review_velocity_30d
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'review_signals' AND column_name = 'velocity_30d'
    ) THEN
        ALTER TABLE review_signals RENAME COLUMN velocity_30d TO review_velocity_30d;
    END IF;
END $$;

-- snapshot_at → captured_at
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'review_signals' AND column_name = 'snapshot_at'
    ) THEN
        ALTER TABLE review_signals RENAME COLUMN snapshot_at TO captured_at;
    END IF;
END $$;

-- New columns
ALTER TABLE review_signals ADD COLUMN IF NOT EXISTS sentiment_score  NUMERIC(5,2);
ALTER TABLE review_signals ADD COLUMN IF NOT EXISTS reviewer_region  VARCHAR(100);
ALTER TABLE review_signals ADD COLUMN IF NOT EXISTS review_details_json TEXT;

-- Drop removed columns
ALTER TABLE review_signals DROP COLUMN IF EXISTS review_count_delta;
ALTER TABLE review_signals DROP COLUMN IF EXISTS velocity_7d;
ALTER TABLE review_signals DROP COLUMN IF EXISTS reviewer_locations;

DROP INDEX IF EXISTS idx_review_sig_listing_id;
DROP INDEX IF EXISTS idx_review_sig_snapshot_at;
DROP INDEX IF EXISTS idx_review_sig_velocity;

CREATE INDEX IF NOT EXISTS idx_review_sig_sku_id      ON review_signals(sku_id);
CREATE INDEX IF NOT EXISTS idx_review_sig_captured_at ON review_signals(captured_at);
CREATE INDEX IF NOT EXISTS idx_review_sig_rating      ON review_signals(rating);
