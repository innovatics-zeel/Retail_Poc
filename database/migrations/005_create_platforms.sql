-- Migration 005: platforms
-- Lookup table for marketplace platforms — normalizes the free-text platform column

CREATE TABLE IF NOT EXISTS platforms (
    id           SMALLINT     PRIMARY KEY,
    name         VARCHAR(50)  NOT NULL UNIQUE,   -- internal key: 'amazon', 'nordstrom', 'walmart'
    display_name VARCHAR(100) NOT NULL,           -- human label: 'Amazon', 'Nordstrom', 'Walmart'
    base_url     TEXT,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO platforms (id, name, display_name, base_url) VALUES
    (1, 'amazon',    'Amazon',    'https://www.amazon.com'),
    (2, 'nordstrom', 'Nordstrom', 'https://www.nordstrom.com'),
    (3, 'walmart',   'Walmart',   'https://www.walmart.com')
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE platforms IS 'Lookup table for supported marketplace platforms.';
