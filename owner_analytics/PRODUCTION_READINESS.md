# Owner analytics production readiness

The dashboard remains disabled by default. This document records the Phase 1B.5 local
rehearsal; it is not authorization to configure Render or production PostgreSQL.

## Rehearsal checklist (2026-11-04)

| Check | Result | Evidence / remaining action |
|---|---|---|
| PostgreSQL 17 migrations 1–4 | PASS | Applied and replayed on isolated PostgreSQL 17.11 as a non-superuser database owner. |
| Existing analytics integration suite | PASS | Seven original real-database tests passed. |
| Owner session creation/digests | PASS | Real PostgreSQL stores keyed token and CSRF digests only. |
| Idle/absolute expiry and revocation | PASS | Real PostgreSQL tests cover 30-minute idle, eight-hour absolute expiry, and deletion. |
| TOTP replay prevention | PASS | Eight concurrent consumers accepted one counter exactly once. |
| Disabled/misconfigured routes | PASS | Blueprint is absent and every owner URL is 404. |
| Anonymous/authenticated route matrix | PASS | Login, dashboard, and logout access and CSRF behavior tested. |
| Secure cookies/proxy metadata | PASS (code) | Secure, HttpOnly, Strict and path attributes are server-controlled even with spoofed forwarded scheme. |
| Public availability during database outage | PASS | Homepage and `/healthz` remain responsive while persistence fails. |
| Multi-worker brute-force limit | FAIL / BLOCKER | Limiter is intentionally process-local. Configure an edge rule before enabling. |
| Render trusted-proxy behavior | NOT TESTED | Verify against the actual Render/edge chain without guessing proxy hops. |
| Disposable backup and restore | PASS | Custom-format dump restored to a second isolated database with migrations 1–4 and all analytics tables. |
| Production backup and restore | NOT TESTED | Complete an encrypted production-environment restore rehearsal before activation. |
| Production MFA enrollment/recovery | NOT TESTED | Requires owner-controlled secrets and authenticator enrollment. |
| Production database least-privilege roles | NOT TESTED | Provision separate runtime/maintenance roles and verify grants. |

## Required edge protection

Gunicorn workers do not share Python memory. With `N` workers, a client can receive up to
`N × 5` attempts per 15 minutes before every worker-local limiter is saturated. Before
activation, configure the existing trusted edge to rate-limit `POST /owner/analytics/login`
across all instances. The rule must key on an edge-verified client signal, permit normal MFA
use, return 429, and must not trust browser-supplied forwarding headers. Keep the in-process
limiter as defense in depth.

## Migration, recovery and rollback

1. Take a verified encrypted PostgreSQL backup before migration.
2. Disable owner analytics and persistent ingestion during a schema restore.
3. Apply `python -m persistent_analytics.migrate`; migration history checksums reject edited
   history and PostgreSQL transactions roll back a failed migration pass.
4. Validate schema versions, aggregate counts, owner authentication and `/healthz` before
   enabling the dashboard.
5. Roll back application code by disabling `OES_OWNER_ANALYTICS_ENABLED` first. Migration 4
   is additive; leave its tables in place during application rollback. Do not drop analytics
   data as an automated rollback step.
6. If recovery is required, restore into a new isolated database, run integrity checks, then
   switch only after owner approval. Never test a restore over the sole production copy.

Backups must include schema migrations, events, sessions, aggregates, aggregation status,
metadata, drop counts, owner auth state and owner sessions. Encrypt backups, restrict access,
define retention, and test restoration regularly. Owner sessions may be deliberately omitted
only if recovery procedure explicitly requires every session to be revoked.

## Secret rotation and account recovery

- Password: generate a new PBKDF2 hash offline, replace the server secret, and restart all
  workers. Never store or transmit the plaintext password in Git or logs.
- TOTP: disable the dashboard, enroll a newly generated owner-controlled secret, replace the
  server secret, reset `last_totp_counter` through an approved administrative procedure, and
  re-enable only after verification.
- Session secret: disable the dashboard, replace the secret, delete all rows from
  `analytics_owner_sessions`, restart all workers, and require fresh login. Never rotate it
  partially across workers.
- Lost owner access: disable the dashboard first, verify owner identity out of band, rotate
  password, TOTP and session secrets, revoke all sessions, document the recovery, then test
  login before re-enabling. There is intentionally no public self-service recovery route.
