-- Migration 001: sku_listings
-- Core product listing — one row per scraped SKU per platform

CREATE TABLE IF NOT EXISTS platforms (
    id           SMALLINT     PRIMARY KEY,
    name         VARCHAR(50)  NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    base_url     TEXT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO platforms (id, name, display_name, base_url) VALUES
    (1, 'amazon',    'Amazon',    'https://www.amazon.com'),
    (2, 'nordstrom', 'Nordstrom', 'https://www.nordstrom.com'),
    (3, 'walmart',   'Walmart',   'https://www.walmart.com')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS sku_listings (
    id              SERIAL          PRIMARY KEY,

    -- Marketplace identity
    platform_id     SMALLINT        REFERENCES platforms(id),
    platform        VARCHAR(50)     NOT NULL,           -- 'amazon' | 'nordstrom' | 'walmart'
    url             TEXT            NOT NULL UNIQUE,

    -- Product identity
    title           TEXT            NOT NULL,
    brand           VARCHAR(200),
    description     TEXT,
    category        VARCHAR(100)    NOT NULL,           -- 'mens_tshirts' | 'womens_casual_dresses'
    gender          VARCHAR(30)     NOT NULL,           -- 'men' | 'women' | 'unisex'
    sub_category    VARCHAR(150),                      -- 'crewneck' | 'graphic' | 'casual dress'

    -- Current snapshot values (denormalised for quick reads)
    current_price   NUMERIC(10,2),
    currency        VARCHAR(10)     NOT NULL DEFAULT 'USD',
    rating          NUMERIC(3,2),
    review_count    INTEGER         NOT NULL DEFAULT 0,

    -- Demo / pipeline tracking
    data_label      VARCHAR(100)    NOT NULL DEFAULT 'demonstration_data',
    poc_run_id      VARCHAR(100),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    scraped_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sku_listings_platform    ON sku_listings(platform);
CREATE INDEX IF NOT EXISTS idx_sku_listings_platform_id ON sku_listings(platform_id);
CREATE INDEX IF NOT EXISTS idx_sku_listings_category    ON sku_listings(category);
CREATE INDEX IF NOT EXISTS idx_sku_listings_gender      ON sku_listings(gender);
CREATE INDEX IF NOT EXISTS idx_sku_listings_scraped_at  ON sku_listings(scraped_at);

COMMENT ON TABLE sku_listings IS 'Core product listings scraped from US marketplaces.';
