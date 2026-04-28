-- Migration 003: price_snapshots
-- Time-series price data — one row per scrape per SKU

CREATE TABLE IF NOT EXISTS price_snapshots (
    id               SERIAL         PRIMARY KEY,
    sku_id           INTEGER        NOT NULL REFERENCES sku_listings(id) ON DELETE CASCADE,

    price            NUMERIC(10,2)  NOT NULL,
    original_price   NUMERIC(10,2),                   -- pre-discount / strikethrough price
    discount_percent NUMERIC(5,2),                    -- 0 – 100
    price_text       TEXT,                            -- rendered PDP price string/range
    discount_text    TEXT,                            -- rendered PDP discount string
    currency         VARCHAR(10)    NOT NULL DEFAULT 'USD',
    price_band       VARCHAR(50),                     -- auto-assigned by trigger below

    captured_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- Price band bucketing function
CREATE OR REPLACE FUNCTION assign_price_band(price NUMERIC)
RETURNS VARCHAR(50) AS $$
BEGIN
    RETURN CASE
        WHEN price < 15   THEN 'under_15'
        WHEN price < 30   THEN '15_30'
        WHEN price < 50   THEN '30_50'
        WHEN price < 75   THEN '50_75'
        WHEN price < 100  THEN '75_100'
        ELSE                   '100_plus'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION trg_set_price_band()
RETURNS TRIGGER AS $$
BEGIN
    NEW.price_band := assign_price_band(NEW.price);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_price_band_trigger ON price_snapshots;
CREATE TRIGGER set_price_band_trigger
    BEFORE INSERT OR UPDATE ON price_snapshots
    FOR EACH ROW EXECUTE FUNCTION trg_set_price_band();

CREATE INDEX IF NOT EXISTS idx_price_snap_sku_id      ON price_snapshots(sku_id);
CREATE INDEX IF NOT EXISTS idx_price_snap_captured_at ON price_snapshots(captured_at);
CREATE INDEX IF NOT EXISTS idx_price_snap_price_band  ON price_snapshots(price_band);

COMMENT ON TABLE price_snapshots IS 'Time-series price snapshots per SKU. Price band auto-assigned on insert.';
