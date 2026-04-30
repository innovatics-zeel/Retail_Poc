-- Migration 009: Amazon women's dresses
-- One denormalized row per canonical Amazon ASIN/product URL.

CREATE TABLE IF NOT EXISTS amazon_womens_dresses (
    id                       SERIAL PRIMARY KEY,

    platform                 VARCHAR(50)  NOT NULL DEFAULT 'amazon',
    url                      TEXT         NOT NULL UNIQUE,
    title                    TEXT         NOT NULL,
    brand                    VARCHAR(200),
    asin                     VARCHAR(50) UNIQUE,

    category                 VARCHAR(100) NOT NULL DEFAULT 'women_dresses',
    gender                   VARCHAR(30)  NOT NULL DEFAULT 'women',
    unit_count               INTEGER      NOT NULL DEFAULT 1,

    variants_json            TEXT,
    attributes_json          TEXT,
    reviews_json             TEXT,
    raw_attributes_json      TEXT,

    data_label               VARCHAR(100) DEFAULT 'demonstration_data',
    poc_run_id               VARCHAR(100),
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    scraped_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_amazon_womens_dresses_brand
    ON amazon_womens_dresses(brand);

CREATE INDEX IF NOT EXISTS idx_amazon_womens_dresses_asin
    ON amazon_womens_dresses(asin);

CREATE INDEX IF NOT EXISTS idx_amazon_womens_dresses_scraped_at
    ON amazon_womens_dresses(scraped_at);

CREATE INDEX IF NOT EXISTS idx_amazon_womens_dresses_poc_run_id
    ON amazon_womens_dresses(poc_run_id);
