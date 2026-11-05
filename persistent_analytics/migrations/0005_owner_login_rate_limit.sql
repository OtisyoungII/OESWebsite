CREATE TABLE IF NOT EXISTS analytics_owner_login_attempts (
    fingerprint_digest BYTEA PRIMARY KEY,
    window_started_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL CHECK (attempts > 0),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS analytics_owner_login_attempts_expires_at
    ON analytics_owner_login_attempts (expires_at);
