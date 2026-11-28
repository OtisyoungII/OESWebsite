BEGIN;

CREATE SCHEMA IF NOT EXISTS android_interest;
CREATE TABLE IF NOT EXISTS android_interest.registrations (
    email text PRIMARY KEY CHECK (char_length(email) BETWEEN 3 AND 254 AND email = lower(email)),
    consent_version text NOT NULL CHECK (consent_version = 'android-interest-v1'),
    registered_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW android_interest.daily_demand AS
SELECT (registered_at AT TIME ZONE 'UTC')::date AS day_utc, count(*) AS unique_registrations
FROM android_interest.registrations
GROUP BY 1;

REVOKE ALL ON SCHEMA android_interest FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA android_interest FROM PUBLIC;
COMMIT;
