-- Migration 010: unified products table
-- Single table for all platforms and categories.
-- Replaces separate nordstrom_mens_tshirts / nordstrom_womens_dresses tables.

CREATE TABLE IF NOT EXISTS products (
    id                   SERIAL PRIMARY KEY,

    platform             VARCHAR(50)   NOT NULL,
    platform_id          INTEGER,
    url                  TEXT          NOT NULL UNIQUE,
    title                TEXT          NOT NULL,
    brand                VARCHAR(200),
    description          TEXT,
    category             VARCHAR(100)  NOT NULL,
    gender               VARCHAR(30)   NOT NULL,
    sub_category         VARCHAR(150),

    current_price        NUMERIC(10,2),
    original_price       NUMERIC(10,2),
    discount_percent     NUMERIC(5,2),
    currency             VARCHAR(10)   NOT NULL DEFAULT 'USD',

    rating               NUMERIC(3,2),
    review_count         INTEGER       NOT NULL DEFAULT 0,

    attributes_json      TEXT,
    stock_variants_json  TEXT,
    review_json          TEXT,
    raw_json             TEXT,

    data_label           VARCHAR(100)  DEFAULT 'demonstration_data',
    poc_run_id           VARCHAR(100),
    is_active            BOOLEAN       NOT NULL DEFAULT TRUE,
    scraped_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_platform    ON products(platform);
CREATE INDEX IF NOT EXISTS idx_products_category    ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand       ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_current_price ON products(current_price);
CREATE INDEX IF NOT EXISTS idx_products_rating      ON products(rating);
CREATE INDEX IF NOT EXISTS idx_products_scraped_at  ON products(scraped_at);
