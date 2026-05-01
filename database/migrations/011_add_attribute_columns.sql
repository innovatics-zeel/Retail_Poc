-- Migration 011: add individual attribute columns to both product tables
-- Flat columns enable direct SQL filtering/grouping on key fields.
-- JSON blobs are kept for full structured detail.

-- ── nordstrom_womens_dresses ──────────────────────────────────────────────────
ALTER TABLE nordstrom_womens_dresses
    ADD COLUMN IF NOT EXISTS color            VARCHAR(200),
    ADD COLUMN IF NOT EXISTS neck_type        VARCHAR(150),
    ADD COLUMN IF NOT EXISTS dress_length     VARCHAR(150),
    ADD COLUMN IF NOT EXISTS occasion         VARCHAR(150),
    ADD COLUMN IF NOT EXISTS fit              VARCHAR(150),
    ADD COLUMN IF NOT EXISTS pattern          VARCHAR(150),
    ADD COLUMN IF NOT EXISTS closure_type     VARCHAR(150),
    ADD COLUMN IF NOT EXISTS material         TEXT,
    ADD COLUMN IF NOT EXISTS care_instructions TEXT,
    ADD COLUMN IF NOT EXISTS sleeve_type      VARCHAR(150);

-- ── nordstrom_mens_tshirts ────────────────────────────────────────────────────
ALTER TABLE nordstrom_mens_tshirts
    ADD COLUMN IF NOT EXISTS color            VARCHAR(200),
    ADD COLUMN IF NOT EXISTS size             TEXT,
    ADD COLUMN IF NOT EXISTS neck_type        VARCHAR(150),
    ADD COLUMN IF NOT EXISTS fit              VARCHAR(150),
    ADD COLUMN IF NOT EXISTS pattern          VARCHAR(150),
    ADD COLUMN IF NOT EXISTS material         TEXT,
    ADD COLUMN IF NOT EXISTS care_instructions TEXT,
    ADD COLUMN IF NOT EXISTS sleeve_type      VARCHAR(150);
