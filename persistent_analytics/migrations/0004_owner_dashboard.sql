CREATE TABLE IF NOT EXISTS analytics_owner_sessions (
    token_digest BYTEA PRIMARY KEY,
    csrf_digest BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    absolute_expires_at TIMESTAMPTZ NOT NULL,
    CHECK (expires_at <= absolute_expires_at)
);

CREATE INDEX IF NOT EXISTS analytics_owner_sessions_expires_at
    ON analytics_owner_sessions (expires_at);

CREATE TABLE IF NOT EXISTS analytics_owner_auth_state (
    owner_id TEXT PRIMARY KEY CHECK (owner_id = 'owner'),
    last_totp_counter BIGINT NOT NULL DEFAULT -1
);

INSERT INTO analytics_owner_auth_state(owner_id,last_totp_counter)
VALUES('owner',-1) ON CONFLICT(owner_id) DO NOTHING;
