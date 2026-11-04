CREATE TABLE IF NOT EXISTS analytics_schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_sessions (
    id UUID PRIMARY KEY,
    token_digest BYTEA NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    platform TEXT,
    language TEXT,
    event_count INTEGER NOT NULL DEFAULT 0 CHECK (event_count >= 0),
    visit_count INTEGER NOT NULL DEFAULT 1 CHECK (visit_count >= 1),
    CHECK (platform IS NULL OR platform IN ('desktop', 'tablet', 'mobile', 'unknown')),
    CHECK (language IS NULL OR language IN ('en', 'es', 'fr', 'ar', 'zh-CN'))
);

CREATE INDEX IF NOT EXISTS analytics_sessions_expires_at
    ON analytics_sessions (expires_at);
CREATE INDEX IF NOT EXISTS analytics_sessions_started_at
    ON analytics_sessions (started_at);
CREATE INDEX IF NOT EXISTS analytics_sessions_last_seen_at
    ON analytics_sessions (last_seen_at);

CREATE TABLE IF NOT EXISTS analytics_events (
    event_id UUID PRIMARY KEY,
    session_id UUID REFERENCES analytics_sessions(id) ON DELETE SET NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    request_id UUID,
    attempt SMALLINT CHECK (attempt IS NULL OR attempt IN (1, 2)),
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms BETWEEN 0 AND 600000),
    outcome TEXT,
    reason TEXT,
    value INTEGER CHECK (value IS NULL OR value BETWEEN 0 AND 1000000),
    interaction_kind TEXT,
    response_action TEXT,
    grounding_mode TEXT,
    capability TEXT,
    component TEXT,
    state TEXT,
    inference_state TEXT,
    product TEXT,
    surface TEXT,
    platform TEXT,
    language TEXT,
    product_target TEXT,
    destination TEXT,
    clarification_reason TEXT
);

CREATE INDEX IF NOT EXISTS analytics_events_occurred_at
    ON analytics_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS analytics_events_type_time
    ON analytics_events (event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS analytics_events_session_time
    ON analytics_events (session_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS analytics_events_request_time
    ON analytics_events (request_id, occurred_at DESC)
    WHERE request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS analytics_daily_metrics (
    day DATE NOT NULL,
    metric TEXT NOT NULL,
    count BIGINT NOT NULL DEFAULT 0 CHECK (count >= 0),
    duration_count BIGINT NOT NULL DEFAULT 0 CHECK (duration_count >= 0),
    duration_sum BIGINT NOT NULL DEFAULT 0 CHECK (duration_sum >= 0),
    value_sum BIGINT NOT NULL DEFAULT 0 CHECK (value_sum >= 0),
    PRIMARY KEY (day, metric)
);

CREATE TABLE IF NOT EXISTS analytics_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics_dropped_events (
    day DATE NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('queue_overflow', 'database_unavailable', 'shutdown')),
    count BIGINT NOT NULL CHECK (count > 0),
    PRIMARY KEY (day, reason)
);
