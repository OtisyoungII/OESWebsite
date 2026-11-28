BEGIN;
CREATE SCHEMA IF NOT EXISTS oes_marketing;
CREATE TABLE IF NOT EXISTS oes_marketing.daily (
    day_utc date NOT NULL,
    page text NOT NULL CHECK (char_length(page) BETWEEN 1 AND 32),
    action text NOT NULL CHECK (char_length(action) BETWEEN 1 AND 32),
    total bigint NOT NULL CHECK (total > 0),
    PRIMARY KEY (day_utc, page, action)
);
REVOKE ALL ON SCHEMA oes_marketing FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA oes_marketing FROM PUBLIC;
COMMIT;
