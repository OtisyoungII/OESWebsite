# ChaseInGreen Android interest list

Android is not released. The registration page is disabled unless
`OES_ANDROID_INTEREST_DSN` is configured. Do not enable it until the owner
approves the notice, retention/deletion schedule and registration service.

Apply `migrations/android_interest_001.sql` as the database owner to an approved
private PostgreSQL target. Use a dedicated runtime role with schema USAGE and
column INSERT on email and consent_version. Use a separate read-only reporting
role with schema USAGE and SELECT on android_interest.daily_demand only.
Keep the owner and reporting credentials out of the web application. Verify
TLS hostname and CA trust, encrypted storage and backups, restore procedures,
role isolation, and an abuse rate limit at the edge before activation.

The public POST collects one normalized email address and affirmative,
versioned consent. The database primary key deduplicates concurrent submissions.
New and duplicate submissions get the same response. The page never accepts
broker credentials, and registration addresses do not enter analytics.

For the owner report, connect privately using the reporting role and select
day_utc and unique_registrations from android_interest.daily_demand. No website
route exposes this report. Counts represent unique registrants who remain on
the list, not verified email ownership, downloads or subscriptions. Arrange
owner-only deletion on withdrawal and enforce the approved retention schedule
before collecting real addresses. The current release does not send email.
