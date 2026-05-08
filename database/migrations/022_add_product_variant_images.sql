-- Store per-color product photos on normalized product variants.
-- image keeps the downloaded jpg/jpeg bytes; image_url keeps the original CDN URL.

ALTER TABLE product_variants
    ADD COLUMN IF NOT EXISTS image BYTEA,
    ADD COLUMN IF NOT EXISTS image_url TEXT;
