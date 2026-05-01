-- Migration 012: widen color/size columns to TEXT — scrapers store all values comma-separated
ALTER TABLE nordstrom_mens_tshirts
    ALTER COLUMN color  TYPE TEXT,
    ALTER COLUMN size   TYPE TEXT;

ALTER TABLE nordstrom_womens_dresses
    ALTER COLUMN color  TYPE TEXT;
