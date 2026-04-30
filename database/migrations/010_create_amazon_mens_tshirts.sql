-- Migration 010: Amazon men's T-shirts
-- One denormalized row per canonical Amazon ASIN/product URL.

CREATE TABLE IF NOT EXISTS amazon_mens_tshirts (
    id                       SERIAL PRIMARY KEY,

    platform                 VARCHAR(50)  NOT NULL DEFAULT 'amazon',
    url                      TEXT         NOT NULL UNIQUE,
    title                    TEXT         NOT NULL,
    brand                    VARCHAR(200),
    asin                     VARCHAR(50) UNIQUE,

    category                 VARCHAR(100) NOT NULL DEFAULT 'mens_tshirt',
    gender                   VARCHAR(30)  NOT NULL DEFAULT 'men',
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

CREATE INDEX IF NOT EXISTS idx_amazon_mens_tshirts_brand
    ON amazon_mens_tshirts(brand);

CREATE INDEX IF NOT EXISTS idx_amazon_mens_tshirts_asin
    ON amazon_mens_tshirts(asin);

CREATE INDEX IF NOT EXISTS idx_amazon_mens_tshirts_scraped_at
    ON amazon_mens_tshirts(scraped_at);

CREATE INDEX IF NOT EXISTS idx_amazon_mens_tshirts_poc_run_id
    ON amazon_mens_tshirts(poc_run_id);
