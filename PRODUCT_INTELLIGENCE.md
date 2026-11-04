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
