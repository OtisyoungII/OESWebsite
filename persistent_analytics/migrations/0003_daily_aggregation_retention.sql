ALTER TABLE analytics_dropped_events
    DROP CONSTRAINT IF EXISTS analytics_dropped_events_reason_check;

ALTER TABLE analytics_dropped_events
    ADD CONSTRAINT analytics_dropped_events_reason_check
    CHECK (reason IN ('queue_overflow', 'database_unavailable', 'shutdown',
                      'late_after_finalization'));

CREATE TABLE IF NOT EXISTS analytics_aggregation_days (
    day DATE PRIMARY KEY,
    source_event_count BIGINT NOT NULL CHECK (source_event_count >= 0),
    source_drop_count BIGINT NOT NULL CHECK (source_drop_count >= 0),
    telemetry_gap_count BIGINT NOT NULL CHECK (telemetry_gap_count >= 0),
    aggregated_at TIMESTAMPTZ NOT NULL,
    finalized_at TIMESTAMPTZ,
    CHECK (finalized_at IS NULL OR finalized_at >= aggregated_at)
);

CREATE INDEX IF NOT EXISTS analytics_aggregation_days_finalized
    ON analytics_aggregation_days (finalized_at, day);
