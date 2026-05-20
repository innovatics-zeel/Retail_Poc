-- 025: Add snoozed_until to watched_patterns

ALTER TABLE watched_patterns
    ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMP WITH TIME ZONE;
