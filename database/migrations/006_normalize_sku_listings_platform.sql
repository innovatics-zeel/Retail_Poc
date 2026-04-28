-- Migration 006: normalize platform column on sku_listings
-- Adds platform_id FK referencing platforms(id) and backfills from existing text values

ALTER TABLE sku_listings
    ADD COLUMN IF NOT EXISTS platform_id SMALLINT REFERENCES platforms(id);

-- Backfill platform_id from the existing free-text platform column
UPDATE sku_listings sl
SET    platform_id = p.id
FROM   platforms p
WHERE  sl.platform = p.name
AND    sl.platform_id IS NULL;

-- Replace the old text-based index with a FK index
DROP INDEX IF EXISTS idx_sku_listings_platform;

CREATE INDEX IF NOT EXISTS idx_sku_listings_platform_id ON sku_listings(platform_id);

COMMENT ON COLUMN sku_listings.platform_id IS 'FK to platforms.id — normalized replacement for the platform text column.';
