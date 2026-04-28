-- Migration 002: sku_attributes
-- Apparel-specific attributes — one row per SKU listing

CREATE TABLE IF NOT EXISTS sku_attributes (
    id                  SERIAL      PRIMARY KEY,
    sku_id              INTEGER     NOT NULL UNIQUE REFERENCES sku_listings(id) ON DELETE CASCADE,

    -- Core apparel attributes
    size                TEXT,                          -- scraped option lists can be long
    color               TEXT,
    pattern             VARCHAR(150),                  -- 'solid' | 'graphic' | 'striped' | 'floral'
    material            TEXT,                          -- '100% Cotton', 'Polyester Blend', 'hemp-cotton'
    neck_type           VARCHAR(150),                  -- 'crewneck' | 'v-neck' | 'round' | 'square'
    sleeve_type         VARCHAR(150),                  -- 'short sleeve' | 'long sleeve' | 'sleeveless'
    fit                 VARCHAR(150),                  -- 'slim' | 'regular' | 'relaxed' | 'bodycon' | 'a-line'

    -- Extended apparel fields
    dress_length        VARCHAR(150),                  -- 'mini' | 'midi' | 'maxi'
    occasion            VARCHAR(150),                  -- 'casual' | 'work' | 'party'
    closure_type        VARCHAR(150),
    care_instructions   TEXT,
    stock_json          TEXT,                          -- color-size availability JSON
    raw_attributes_json TEXT,                          -- original scraped attribute blob (JSON string)

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sku_attr_pattern    ON sku_attributes(pattern);
CREATE INDEX IF NOT EXISTS idx_sku_attr_fit        ON sku_attributes(fit);
CREATE INDEX IF NOT EXISTS idx_sku_attr_neck_type  ON sku_attributes(neck_type);

COMMENT ON TABLE sku_attributes IS 'Apparel attributes extracted from listing pages — color, material, fit, neck type, etc.';
