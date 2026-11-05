# OES Product Intelligence v1

This first slice extends the existing content-free OES telemetry contract. Render validates
fixed browser events, the authenticated outbound relay carries them, and OES Core persists
them in its existing bounded SQLite store. No public analytics endpoint exposes the local
database.

## Definitions

- **Website session:** one server-issued, session-cookie-scoped browser session observed by
  the current web-service process. Tabs in the same browser session share it. The public
  runtime counter resets when the service process restarts. The opaque cookie is held only
  in the browser and bounded Render memory; it is never written to telemetry.
- **Visit:** not measured separately in v1. The UI therefore does not label sessions as
  unique people or durable visits.
- **Tap/activation:** one completed DOM `click` on an explicitly instrumented action. Native
  mouse click, touch tap, and keyboard activation all converge on that single event. Pointer
  down, hover, focus, movement, scrolling, coordinates, and key contents are not counted.
- **Interaction:** one accepted fixed-schema product event. A session, Eyeball open, message
  submission, language selection, and link activation are different event types and must not
  be combined as “users.”
- **Returning session/person:** not measured. There is no durable browser identifier or
  fingerprint.
- **Visit:** initial session creation or the first page initialization after at least 30
  minutes without a page initialization. Concurrent requests carrying the same cookie are
  serialized by PostgreSQL so only one request advances the visit count.
- **Page view:** one successful page initialization reported as a fixed page category. The
  system stores no URL or referrer.
- **Product-card activation:** one completed click within an explicitly instrumented product
  card, excluding a nested link that has its own more-specific activation event.

## Fixed contract

Persisted events use the shared telemetry envelope: schema version, random event ID, server
timestamp, fixed event type, optional fixed outcome, and allowlisted dimensions. Product
events add only bounded `product`, `surface`, `platform`, `language`, `product_target`, and
`destination` categories. They contain no session identifier or free-form browser text.

The first measured events are `website_session_started`, `eyeball_opened`,
`eyeball_closed`, `eyeball_message_submitted`, `eyeball_language_changed`,
`testflight_link_activated`, `web_app_link_activated`,
`external_product_link_activated`, and `contact_action_activated`.
Phase 1B.2 adds `website_visit_started`, `website_page_viewed`, and real
`product_card_activated` events. Sessions, visits, page views, and activations are separate
metrics and must never be presented as interchangeable users.

Existing authoritative server events remain the source for completed Eyeball responses,
SAFE_ERROR, grounding, capability use, inference attempts, and response latency. The browser
does not duplicate or claim those outcomes.

## Storage and retention

OES Core retains detailed validated events for 30 days and preserves daily aggregate rows
within the bounded database. The database ceiling remains 50 MiB. The first accepted website
session records a separate product-intelligence start timestamp; periods before that date are
not treated as zero-usage history.

## Public counter

The footer shows **SESSIONS THIS SERVICE RUN**. Its number is maintained by the server and is
never accepted from browser JSON. It is real but intentionally process-local and may reset on
deployment or restart. It is not a count of people, lifetime visits, or unique devices.

## Privacy boundary

The system does not collect prompts, responses, Tavily queries or evidence, coordinates, IP
addresses, raw user-agent strings, screen dimensions, keystrokes, cursor positions, emails,
names, URLs, credentials, signatures, or browser fingerprints. Platform and language are
fixed coarse categories reported by the public client and should be treated as approximate.
Geography is not collected in v1 because no existing trusted coarse-region signal was found.

## Future products and model access

Sportfolio and other OES products can later send the same fixed envelope through a
product-specific authenticated ingestion boundary, for example `product=sportfolio`,
`surface=web`, `event=session_started`. Each new event and dimension value must be added to
the shared allowlists; products may not submit arbitrary names or prose.

Public Eyeball must never query telemetry tables. A future public analytics capability may
return reviewed aggregates only. Private Scout may receive a separately authorized,
least-privilege aggregate capability; it must not gain direct database access from this work.

## Optional PostgreSQL persistence foundation

The Phase 1B.1 foundation can copy the same server-validated telemetry events into fixed
PostgreSQL columns. It is disabled by default with
`OES_PERSISTENT_ANALYTICS_ENABLED=false`; `OES_ANALYTICS_DATABASE_URL` is read only on the
server. Migrations are explicit and never run from a public request:

```
python -m persistent_analytics.migrate
```

Migration execution additionally requires `OES_ANALYTICS_EXPECTED_DATABASE` and/or
`OES_ANALYTICS_SCHEMA`. The command verifies `current_database()` and `current_schema()`
before analytics DDL. Schema names are restricted identifiers and cannot be `public`,
`pg_catalog`, or `information_schema`. Runtime analytics connections use the same fixed
search path. This permits a dedicated schema on an existing PostgreSQL instance without
granting access to another application's tables. A separate logical database remains the
preferred boundary when the managed role permits it.

The existing authenticated relay and OES Core SQLite store remain operational regardless of
PostgreSQL state. When enabled, a bounded daemon queue isolates database latency and outages
from Flask and Eyeball streaming. Queue overflow and failed batches increment fixed drop
categories. Those counters are written after database recovery when possible; if the process
terminates while PostgreSQL remains unavailable, unflushed events and drop counters are lost.
This is an intentional availability-first limitation, not a claim of lossless analytics.

Phase 1B.1 does not switch browser sessions to PostgreSQL, expose analytics publicly, or
enable owner access. The `analytics_sessions` table is reserved for a separately reviewed
durable-session phase.

Phase 1B.2 uses that table only when optional persistence is enabled and both server-only
database and digest-key configuration are present. The browser retains a random cookie; the
database stores only its HMAC-SHA256 digest under `OES_ANALYTICS_SESSION_DIGEST_KEY`. The raw
cookie, digest key, IP address, user agent, and browser fingerprint are not stored as event
data. Session expiry remains a sliding 12 hours. PostgreSQL unavailability falls back to the
bounded in-process behavior, so the website remains available but durable continuity and
exact visit classification can be temporarily unavailable.

## Offline aggregation and retention (Phase 1B.3)

Daily maintenance is a separate explicit process and never runs in Flask request handling.
It remains disabled unless `OES_ANALYTICS_MAINTENANCE_ENABLED=true` and is invoked with:

```
python -m persistent_analytics.maintenance
```

Phase 1B.6 also supports a disabled-by-default zero-additional-service mode with
`OES_ANALYTICS_INPROCESS_MAINTENANCE_ENABLED=true`. It starts a low-frequency daemon on the
existing always-on web service, waits 60 seconds after process startup, and attempts a pass
hourly even when no visitor arrives. Each pass is limited to 32 historical days and uses the
same PostgreSQL advisory transaction lock, so restarts, duplicate Gunicorn processes, and
overlapping attempts remain idempotent. Missed work catches up after the next process start.
Database failure never affects public routes or `/healthz`. This is appropriate for the
current beta but is not an external scheduler SLA; a supervised cron remains the stronger
paid option if strict daily completion guarantees become necessary.

The job uses one PostgreSQL advisory transaction lock, aggregates only completed UTC days,
and replaces each provisional day's seven fixed metrics from persisted source rows. This
makes retries and historical backfill idempotent. Sessions, visits, page views, product-card
activations, Eyeball interactions, operational analytics drops, and telemetry-gap values are
kept distinct. A browser session spanning midnight contributes each event to the UTC day on
which that event occurred.

Completed days remain provisional and are recomputed while their detailed events are
retained. A day becomes final only after the 30-day detail window. Events presented after
that finalization boundary are rejected from detail storage and counted under the fixed
`late_after_finalization` drop category; they cannot silently rewrite a finalized total.
The per-day source-event, drop, and telemetry-gap counts record known completeness limits.

Detailed events are retained for 30 days. Session rows are eligible for deletion 30 days
after their sliding expiry. Daily metrics and finalization records are retained for 13
months. `analytics_metadata.earliest_available_date` is recalculated after retention and
records the earliest currently available legitimate session, event, drop, or aggregate
date; the job never invents pre-telemetry history. PostgreSQL failure produces a content-free operational failure and does not affect
the website, Eyeball, or `/healthz`.

## Private owner dashboard (Phase 1B.4)

The owner dashboard is an independent Flask blueprint and is absent unless
`OES_OWNER_ANALYTICS_ENABLED=true` and every owner configuration value is valid. It does not
use Auth0, add a public analytics API, or grant Eyeball database access. Authentication
requires a PBKDF2-SHA256 password hash and TOTP. TOTP counters are consumed atomically to
prevent replay. Random owner-session and CSRF tokens are stored only as keyed digests in
PostgreSQL; browser cookies are `HttpOnly`, `SameSite=Strict`, path-scoped, secure by default,
idle-expiring after 30 minutes, and absolutely bounded to eight hours. Logout deletes the
server-side session. Login attempts receive both bounded in-process limiting and an atomic
PostgreSQL-backed limiter keyed only by an HMAC digest. The database limiter works across
Gunicorn workers and instances. `OES_OWNER_CANONICAL_HOST` is mandatory when owner routes
are enabled, and alternate Render hostnames receive 404. Edge limiting remains useful
defense in depth but is no longer the only distributed boundary.

Authenticated views under `/owner/analytics/` query fixed aggregates and aggregate metadata
only. They expose no prompts, responses, cookies, visitor identifiers, IP addresses, or raw
event exports. Reporting uses UTC with fixed 7-day, 30-day, 90-day and 13-month ranges.
Database failure renders an accurate unavailable state while public routes remain
independent. Owner responses disable caching and framing and apply a narrow content security
policy.
