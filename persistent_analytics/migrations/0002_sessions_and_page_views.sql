ALTER TABLE analytics_events
    ADD COLUMN IF NOT EXISTS page TEXT;

ALTER TABLE analytics_events
    DROP CONSTRAINT IF EXISTS analytics_events_page_allowed;

ALTER TABLE analytics_events
    ADD CONSTRAINT analytics_events_page_allowed
    CHECK (page IS NULL OR page IN ('home', 'privacy', 'drinks_with_friendz_privacy', 'other'));
