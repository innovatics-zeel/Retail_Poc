-- Widen columns that can legitimately hold large values.
-- review_count sums can exceed INT range when one product has a corrupted INT_MAX value.
-- review_growth_pct with a single scrape can produce extreme ratios (>999%).
ALTER TABLE trend_scores
    ALTER COLUMN review_count     TYPE BIGINT,
    ALTER COLUMN review_growth_pct TYPE NUMERIC(12, 2);
