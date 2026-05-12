-- Migration 023: daily snapshots for stable normalized product variants/reviews
-- Current tables keep one latest row per SKU/product; snapshot tables keep daily history.

CREATE TABLE IF NOT EXISTS variant_snapshots (
    id             SERIAL PRIMARY KEY,
    variant_id     INT NOT NULL REFERENCES product_variants(variant_id) ON DELETE CASCADE,
    price          NUMERIC(10,2),
    original_price NUMERIC(10,2),
    discount_pct   NUMERIC(5,2),
    is_available   BOOLEAN NOT NULL DEFAULT TRUE,
    low_stock      BOOLEAN NOT NULL DEFAULT FALSE,
    stock_note     VARCHAR(200),
    scraped_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_variant_snapshots_variant_id
    ON variant_snapshots(variant_id);
CREATE INDEX IF NOT EXISTS idx_variant_snapshots_scraped_at
    ON variant_snapshots(scraped_at);
CREATE INDEX IF NOT EXISTS idx_variant_snapshots_variant_day
    ON variant_snapshots(variant_id, scraped_at);

CREATE TABLE IF NOT EXISTS product_review_snapshots (
    id           SERIAL PRIMARY KEY,
    product_id   INT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    rating_avg   NUMERIC(3,1),
    review_count INT NOT NULL DEFAULT 0,
    fit_feedback VARCHAR(100),
    stars_1_pct  SMALLINT,
    stars_2_pct  SMALLINT,
    stars_3_pct  SMALLINT,
    stars_4_pct  SMALLINT,
    stars_5_pct  SMALLINT,
    scraped_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_review_snapshots_product_id
    ON product_review_snapshots(product_id);
CREATE INDEX IF NOT EXISTS idx_product_review_snapshots_scraped_at
    ON product_review_snapshots(scraped_at);
CREATE INDEX IF NOT EXISTS idx_product_review_snapshots_product_day
    ON product_review_snapshots(product_id, scraped_at);

INSERT INTO variant_snapshots (
    variant_id, price, original_price, discount_pct,
    is_available, low_stock, stock_note, scraped_at
)
SELECT
    pv.variant_id, pv.price, pv.original_price, pv.discount_pct,
    pv.is_available, pv.low_stock, pv.stock_note, pv.scraped_at
FROM product_variants pv
WHERE NOT EXISTS (
    SELECT 1
    FROM variant_snapshots vs
    WHERE vs.variant_id = pv.variant_id
      AND vs.scraped_at = pv.scraped_at
);

INSERT INTO product_review_snapshots (
    product_id, rating_avg, review_count, fit_feedback,
    stars_1_pct, stars_2_pct, stars_3_pct, stars_4_pct, stars_5_pct,
    scraped_at
)
SELECT
    r.product_id, r.rating_avg, r.review_count, r.fit_feedback,
    r.stars_1_pct, r.stars_2_pct, r.stars_3_pct, r.stars_4_pct, r.stars_5_pct,
    r.scraped_at
FROM reviews r
WHERE NOT EXISTS (
    SELECT 1
    FROM product_review_snapshots prs
    WHERE prs.product_id = r.product_id
      AND prs.scraped_at = r.scraped_at
);
