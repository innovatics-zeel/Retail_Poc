-- Migration 008: single-table Nordstrom men's T-shirts
-- One denormalized row per product URL.

CREATE TABLE IF NOT EXISTS nordstrom_mens_tshirts (
    id                       SERIAL PRIMARY KEY,

    platform                 VARCHAR(50)  NOT NULL DEFAULT 'nordstrom',
    url                      TEXT         NOT NULL UNIQUE,
    title                    TEXT         NOT NULL,
    brand                    VARCHAR(200),
    description              TEXT,
    category                 VARCHAR(100) NOT NULL DEFAULT 'mens_tshirts',
    gender                   VARCHAR(30)  NOT NULL DEFAULT 'men',
    sub_category             VARCHAR(150),

    current_price            NUMERIC(10,2),
    discount_price           NUMERIC(10,2),
    actual_price             NUMERIC(10,2),
    original_price           NUMERIC(10,2),
    discount_percent         NUMERIC(5,2),
    price_text               TEXT,
    discount_text            TEXT,
    currency                 VARCHAR(10) NOT NULL DEFAULT 'USD',

    color                    TEXT,
    size                     TEXT,
    stock_json               TEXT,
    pattern                  VARCHAR(150),
    material                 TEXT,
    neck_type                VARCHAR(150),
    sleeve_type              VARCHAR(150),
    fit                      VARCHAR(150),
    dress_length             VARCHAR(150),
    occasion                 VARCHAR(150),
    closure_type             VARCHAR(150),
    care_instructions        TEXT,

    rating                   NUMERIC(3,2),
    review_count             INTEGER NOT NULL DEFAULT 0,
    review_fit               TEXT,
    star_distribution_json   TEXT,
    review_pros_json         TEXT,
    review_cons_json         TEXT,
    review_details_json      TEXT,

    raw_attributes_json      TEXT,
    data_label               VARCHAR(100) DEFAULT 'demonstration_data',
    poc_run_id               VARCHAR(100),
    is_active                BOOLEAN NOT NULL DEFAULT TRUE,
    scraped_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nordstrom_mens_tshirts_brand
    ON nordstrom_mens_tshirts(brand);

CREATE INDEX IF NOT EXISTS idx_nordstrom_mens_tshirts_sub_category
    ON nordstrom_mens_tshirts(sub_category);

CREATE INDEX IF NOT EXISTS idx_nordstrom_mens_tshirts_scraped_at
    ON nordstrom_mens_tshirts(scraped_at);

CREATE INDEX IF NOT EXISTS idx_nordstrom_mens_tshirts_current_price
    ON nordstrom_mens_tshirts(current_price);
