-- Add weekly trend lifecycle fields used by predictive intelligence.
ALTER TABLE trend_scores
    ADD COLUMN IF NOT EXISTS lifecycle_stage VARCHAR(20),
    ADD COLUMN IF NOT EXISTS retailer_action TEXT,
    ADD COLUMN IF NOT EXISTS lifecycle_explanation TEXT,
    ADD COLUMN IF NOT EXISTS weeks_observed INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS latest_week_share NUMERIC(6, 4),
    ADD COLUMN IF NOT EXISTS previous_week_share NUMERIC(6, 4);

CREATE INDEX IF NOT EXISTS idx_trend_scores_lifecycle_stage
    ON trend_scores (lifecycle_stage);
