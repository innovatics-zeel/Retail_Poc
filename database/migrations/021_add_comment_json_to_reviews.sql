-- Compatibility migration in case an older 020 migration already ran.
-- This only ensures the intended column exists; it does not populate it.

ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS comment_json JSONB;
