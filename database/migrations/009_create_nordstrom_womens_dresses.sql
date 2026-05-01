-- Migration 009: single-table Nordstrom women's dresses
-- One denormalized row per product URL.
-- JSON blobs store full structured detail; flat scalar columns enable fast SQL filtering.

CREATE TABLE IF NOT EXISTS nordstrom_womens_dresses (
    id                   SERIAL PRIMARY KEY,

    platform             VARCHAR(50)   NOT NULL DEFAULT 'nordstrom',
    platform_id          INTEGER,
    url                  TEXT          NOT NULL UNIQUE,
    title                TEXT          NOT NULL,
    brand                VARCHAR(200),
    description          TEXT,
    category             VARCHAR(100)  NOT NULL DEFAULT 'womens_dresses',
    gender               VARCHAR(30)   NOT NULL DEFAULT 'women',
    sub_category         VARCHAR(150),

    -- flat price scalars — fast aggregation and range filters
    current_price        NUMERIC(10,2),
    original_price       NUMERIC(10,2),
    discount_percent     NUMERIC(5,2),
    currency             VARCHAR(10)   NOT NULL DEFAULT 'USD',

    -- flat review scalars — fast sorting
    rating               NUMERIC(3,2),
    review_count         INTEGER       NOT NULL DEFAULT 0,

    -- JSON blobs — full structured payload
    attributes_json      TEXT,   -- DressAttributes: neck_type, dress_length, material, etc.
    stock_variants_json  TEXT,   -- list of {color, sizes:[{size, available, price_text, …}]}
    review_json          TEXT,   -- {rating, review_count, fit, star_distribution, pros, cons}
    raw_json             TEXT,   -- complete raw scraper payload

    data_label           VARCHAR(100)  DEFAULT 'demonstration_data',
    poc_run_id           VARCHAR(100),
    is_active            BOOLEAN       NOT NULL DEFAULT TRUE,
    scraped_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nordstrom_womens_dresses_brand
    ON nordstrom_womens_dresses(brand);

CREATE INDEX IF NOT EXISTS idx_nordstrom_womens_dresses_current_price
    ON nordstrom_womens_dresses(current_price);

CREATE INDEX IF NOT EXISTS idx_nordstrom_womens_dresses_rating
    ON nordstrom_womens_dresses(rating);

CREATE INDEX IF NOT EXISTS idx_nordstrom_womens_dresses_scraped_at
    ON nordstrom_womens_dresses(scraped_at);
