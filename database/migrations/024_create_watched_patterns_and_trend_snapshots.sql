-- 024: Watched patterns watchlist + Google Trends historical snapshots

CREATE TABLE IF NOT EXISTS watched_patterns (
    id           SERIAL PRIMARY KEY,
    rec_id       INTEGER REFERENCES recommendations(rec_id) ON DELETE SET NULL,
    pattern_name VARCHAR(500) NOT NULL,
    attr_key     VARCHAR(100),
    category     VARCHAR(100),
    platform     VARCHAR(200),
    stage        VARCHAR(50),
    change_pct   NUMERIC(8, 2),
    confidence   VARCHAR(20),
    action       TEXT,
    note         TEXT,
    watched_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wp_rec_id     ON watched_patterns(rec_id);
CREATE INDEX IF NOT EXISTS idx_wp_watched_at ON watched_patterns(watched_at DESC);

CREATE TABLE IF NOT EXISTS google_trend_snapshots (
    id          SERIAL PRIMARY KEY,
    query       VARCHAR(500) NOT NULL,
    geo         VARCHAR(10)  NOT NULL DEFAULT 'US',
    date_window VARCHAR(50)  NOT NULL DEFAULT 'today 3-m',
    score       INTEGER,
    delta_pct   INTEGER,
    points      INTEGER,
    category    VARCHAR(100),
    platform    VARCHAR(100),
    fetched_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gts_query      ON google_trend_snapshots(query);
CREATE INDEX IF NOT EXISTS idx_gts_fetched_at ON google_trend_snapshots(fetched_at DESC);
