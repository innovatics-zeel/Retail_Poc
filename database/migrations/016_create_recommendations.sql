CREATE TABLE IF NOT EXISTS recommendations (
    rec_id               SERIAL PRIMARY KEY,
    category             VARCHAR(100),
    platform             VARCHAR(100),
    pattern_type         VARCHAR(100),
    evidence             JSONB,
    recommendation_text  TEXT             NOT NULL,
    observation          TEXT,
    action               TEXT,
    impact               TEXT,
    confidence           VARCHAR(20),
    status               VARCHAR(20)      NOT NULL DEFAULT 'pending',
    modified_text        TEXT,
    generated_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    actioned_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recommendations_category     ON recommendations (category);
CREATE INDEX IF NOT EXISTS idx_recommendations_status       ON recommendations (status);
CREATE INDEX IF NOT EXISTS idx_recommendations_pattern_type ON recommendations (pattern_type);
CREATE INDEX IF NOT EXISTS idx_recommendations_generated_at ON recommendations (generated_at DESC);
