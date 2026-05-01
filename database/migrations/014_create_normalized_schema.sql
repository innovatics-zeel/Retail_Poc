-- Migration 014: normalized retail data model
-- Creates master lookups + normalized product / variant / review tables.
-- The flat nordstrom and amazon tables are untouched — scrapers keep writing there.
-- Existing flat `products` table (migration 010) renamed to products_legacy.

-- ── Rename old flat products table ───────────────────────────────────────────
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'products'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products'
          AND column_name = 'product_id'
    ) THEN
        ALTER TABLE products RENAME TO products_legacy;
    END IF;
END $$;

-- ── Master lookup tables ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS brands (
    brand_id SERIAL      PRIMARY KEY,
    name     VARCHAR(200) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL      PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,   -- 'mens_tshirts', 'womens_dresses'
    gender      VARCHAR(20)                      -- 'men', 'women', 'unisex'
);

INSERT INTO categories (name, gender) VALUES
    ('mens_tshirts',   'men'),
    ('womens_dresses', 'women')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS colors (
    color_id     SERIAL      PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,  -- 'Black', 'Dove Grey', 'Bright Aqua'
    color_family VARCHAR(50)                     -- 'Black', 'Grey', 'Blue'
);

CREATE TABLE IF NOT EXISTS sizes (
    size_id     SERIAL      PRIMARY KEY,
    label       VARCHAR(50)  NOT NULL UNIQUE,   -- 'Small', 'X-Large', '32x30'
    sort_order  INT          NOT NULL DEFAULT 999,
    size_system VARCHAR(20)  NOT NULL DEFAULT 'alpha'  -- 'alpha', 'numeric', 'waist-inseam'
);

INSERT INTO sizes (label, sort_order, size_system) VALUES
    ('XXS',     1, 'alpha'), ('XS',      2, 'alpha'),
    ('S',       3, 'alpha'), ('Small',   3, 'alpha'),
    ('M',       4, 'alpha'), ('Medium',  4, 'alpha'),
    ('L',       5, 'alpha'), ('Large',   5, 'alpha'),
    ('XL',      6, 'alpha'), ('X-Large', 6, 'alpha'),
    ('XXL',     7, 'alpha'), ('2XL',     7, 'alpha'),
    ('XXXL',    8, 'alpha'), ('3XL',     8, 'alpha'),
    ('4XL',     9, 'alpha')
ON CONFLICT (label) DO NOTHING;

-- ── Normalized products table ─────────────────────────────────────────────────
-- One row per listing URL.

CREATE TABLE IF NOT EXISTS products (
    product_id       SERIAL      PRIMARY KEY,
    platform_id      SMALLINT    NOT NULL REFERENCES platforms(id),
    brand_id         INT         REFERENCES brands(brand_id),
    category_id      INT         REFERENCES categories(category_id),
    title            TEXT        NOT NULL,
    url              TEXT        NOT NULL UNIQUE,
    platform_item_id VARCHAR(100),             -- ASIN for Amazon, item ID for Nordstrom
    material         TEXT,
    neck_type        VARCHAR(100),
    sleeve_type      VARCHAR(100),
    fit              VARCHAR(100),
    pattern          VARCHAR(100),
    care             TEXT,
    scraped_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_platform_id  ON products(platform_id);
CREATE INDEX IF NOT EXISTS idx_products_brand_id     ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_products_category_id  ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_scraped_at   ON products(scraped_at);

-- ── Variants — one row per (product × color × size × scrape date) ─────────────
-- This is the main fact table; new rows on every scrape give price / availability history.

CREATE TABLE IF NOT EXISTS product_variants (
    variant_id     SERIAL      PRIMARY KEY,
    product_id     INT         NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    color_id       INT         REFERENCES colors(color_id),
    size_id        INT         REFERENCES sizes(size_id),
    is_available   BOOLEAN     NOT NULL DEFAULT TRUE,
    price          NUMERIC(10,2),
    original_price NUMERIC(10,2),
    discount_pct   NUMERIC(5,2),
    currency       CHAR(3)     NOT NULL DEFAULT 'USD',
    low_stock      BOOLEAN     NOT NULL DEFAULT FALSE,
    stock_note     VARCHAR(200),
    scraped_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pv_product_id  ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_pv_color_id    ON product_variants(color_id);
CREATE INDEX IF NOT EXISTS idx_pv_size_id     ON product_variants(size_id);
CREATE INDEX IF NOT EXISTS idx_pv_scraped_at  ON product_variants(scraped_at);
CREATE INDEX IF NOT EXISTS idx_pv_price       ON product_variants(price);

-- ── Reviews — one row per (product × scrape date) ─────────────────────────────

CREATE TABLE IF NOT EXISTS reviews (
    review_id    SERIAL      PRIMARY KEY,
    product_id   INT         NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    rating_avg   NUMERIC(3,1),
    review_count INT         NOT NULL DEFAULT 0,
    fit_feedback VARCHAR(100),
    stars_1_pct  SMALLINT,
    stars_2_pct  SMALLINT,
    stars_3_pct  SMALLINT,
    stars_4_pct  SMALLINT,
    stars_5_pct  SMALLINT,
    pros         JSONB,
    cons         JSONB,
    scraped_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_product_id  ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_scraped_at  ON reviews(scraped_at);
