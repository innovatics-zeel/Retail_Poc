CREATE TABLE IF NOT EXISTS trend_scores (
    score_id             SERIAL PRIMARY KEY,
    category             VARCHAR(100),
    platform             VARCHAR(50),
    attr_key             VARCHAR(50),
    attr_value           VARCHAR(100),
    review_count         INTEGER          DEFAULT 0,
    review_growth_pct    NUMERIC(8, 2),
    avg_rating           NUMERIC(3, 1),
    category_avg_rating  NUMERIC(3, 1),
    rating_delta         NUMERIC(4, 2),
    product_count        INTEGER          DEFAULT 0,
    new_product_share    NUMERIC(6, 4),
    momentum_score       NUMERIC(8, 4),
    trend_direction      VARCHAR(20),
    explanation          TEXT,
    computed_at          TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trend_scores_category  ON trend_scores (category);
CREATE INDEX IF NOT EXISTS idx_trend_scores_platform  ON trend_scores (platform);
CREATE INDEX IF NOT EXISTS idx_trend_scores_attr_key  ON trend_scores (attr_key);
CREATE INDEX IF NOT EXISTS idx_trend_scores_momentum  ON trend_scores (momentum_score DESC);
