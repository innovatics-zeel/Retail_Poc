-- Migration 004: review_signals
-- Review metrics and velocity per SKU per scrape

CREATE TABLE IF NOT EXISTS review_signals (
    id                   SERIAL        PRIMARY KEY,
    sku_id               INTEGER       NOT NULL REFERENCES sku_listings(id) ON DELETE CASCADE,

    rating               NUMERIC(3,2),                -- 0.00 – 5.00
    review_count         INTEGER       NOT NULL DEFAULT 0,
    review_velocity_30d  INTEGER       NOT NULL DEFAULT 0,  -- reviews gained in last 30 days
    sentiment_score      NUMERIC(5,2),                -- optional NLP-derived score
    reviewer_region      VARCHAR(100),                -- dominant reviewer region
    review_details_json  TEXT,                        -- star distribution, fit, pros, cons

    captured_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_sig_sku_id      ON review_signals(sku_id);
CREATE INDEX IF NOT EXISTS idx_review_sig_captured_at ON review_signals(captured_at);
CREATE INDEX IF NOT EXISTS idx_review_sig_rating      ON review_signals(rating);

COMMENT ON TABLE review_signals IS 'Review count, rating, and velocity metrics per SKU per scrape cycle.';
