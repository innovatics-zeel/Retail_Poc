-- Migration 013: platform-based tables + genders lookup
-- One table per platform. category column distinguishes mens_tshirts / womens_dresses.

CREATE TABLE IF NOT EXISTS genders (
    id   SMALLINT     PRIMARY KEY,
    name VARCHAR(30)  NOT NULL UNIQUE
);
INSERT INTO genders (id, name) VALUES (1, 'men'), (2, 'women'), (3, 'unisex')
ON CONFLICT (id) DO NOTHING;

-- ── Nordstrom ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nordstrom (
    id               SERIAL      PRIMARY KEY,
    platform_id      SMALLINT    NOT NULL REFERENCES platforms(id) DEFAULT 2,
    gender_id        SMALLINT    NOT NULL REFERENCES genders(id),
    category         VARCHAR(100) NOT NULL,
    url              TEXT        NOT NULL UNIQUE,
    title            TEXT        NOT NULL,
    brand            VARCHAR(200),
    description      TEXT,
    sub_category     VARCHAR(150),
    currency         VARCHAR(10) NOT NULL DEFAULT 'USD',
    current_price    NUMERIC(10,2),
    original_price   NUMERIC(10,2),
    discount_percent NUMERIC(5,2),
    rating           NUMERIC(3,2),
    review_count     INTEGER     NOT NULL DEFAULT 0,
    -- individual attribute columns
    color            TEXT,
    size             TEXT,
    neck_type        VARCHAR(150),
    dress_length     VARCHAR(150),
    occasion         VARCHAR(150),
    fit              VARCHAR(150),
    pattern          VARCHAR(150),
    closure_type     VARCHAR(150),
    material         TEXT,
    care_instructions TEXT,
    sleeve_type      VARCHAR(150),
    -- full structured blobs
    attributes_json      TEXT,
    stock_variants_json  TEXT,
    review_json          TEXT,
    raw_json             TEXT,
    -- meta
    data_label       VARCHAR(100) DEFAULT 'demonstration_data',
    poc_run_id       VARCHAR(100),
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    scraped_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nordstrom_category    ON nordstrom(category);
CREATE INDEX IF NOT EXISTS idx_nordstrom_gender_id   ON nordstrom(gender_id);
CREATE INDEX IF NOT EXISTS idx_nordstrom_brand       ON nordstrom(brand);
CREATE INDEX IF NOT EXISTS idx_nordstrom_price       ON nordstrom(current_price);
CREATE INDEX IF NOT EXISTS idx_nordstrom_scraped_at  ON nordstrom(scraped_at);

-- ── Amazon ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS amazon (
    id               SERIAL      PRIMARY KEY,
    platform_id      SMALLINT    NOT NULL REFERENCES platforms(id) DEFAULT 1,
    gender_id        SMALLINT    NOT NULL REFERENCES genders(id),
    category         VARCHAR(100) NOT NULL,
    url              TEXT        NOT NULL UNIQUE,
    title            TEXT        NOT NULL,
    brand            VARCHAR(200),
    description      TEXT,
    sub_category     VARCHAR(150),
    currency         VARCHAR(10) NOT NULL DEFAULT 'USD',
    current_price    NUMERIC(10,2),
    original_price   NUMERIC(10,2),
    discount_percent NUMERIC(5,2),
    rating           NUMERIC(3,2),
    review_count     INTEGER     NOT NULL DEFAULT 0,
    -- individual attribute columns
    color            TEXT,
    size             TEXT,
    neck_type        VARCHAR(150),
    dress_length     VARCHAR(150),
    occasion         VARCHAR(150),
    fit              VARCHAR(150),
    pattern          VARCHAR(150),
    closure_type     VARCHAR(150),
    material         TEXT,
    care_instructions TEXT,
    sleeve_type      VARCHAR(150),
    -- full structured blobs
    attributes_json      TEXT,
    stock_variants_json  TEXT,
    review_json          TEXT,
    raw_json             TEXT,
    -- meta
    data_label       VARCHAR(100) DEFAULT 'demonstration_data',
    poc_run_id       VARCHAR(100),
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    scraped_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_amazon_category   ON amazon(category);
CREATE INDEX IF NOT EXISTS idx_amazon_gender_id  ON amazon(gender_id);
CREATE INDEX IF NOT EXISTS idx_amazon_brand      ON amazon(brand);
CREATE INDEX IF NOT EXISTS idx_amazon_price      ON amazon(current_price);
CREATE INDEX IF NOT EXISTS idx_amazon_scraped_at ON amazon(scraped_at);
