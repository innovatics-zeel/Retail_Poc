-- Store product image bytes directly on products.
-- Add a nullable reviews.review_json column for a later review-specific flow.
-- The variant history/snapshot/insight tables are removed from this simplified flow.

ALTER TABLE products
    DROP COLUMN IF EXISTS image_url,
    ADD COLUMN IF NOT EXISTS image BYTEA;

ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS review_json JSONB;

DROP TABLE IF EXISTS product_variant_insights CASCADE;
DROP TABLE IF EXISTS product_variant_history CASCADE;
DROP TABLE IF EXISTS product_variant_snapshots CASCADE;
