# Customer onboarding release

## AquaFunded

Only the website channel from `public_destinations.py` appears on public pages.
The owner reported a successful website visitor attribution. The other seven
assignments need individual verification by their channel owner. The app channel
is reserved for separate compliance review. AquaFunded is authoritative for
attributed purchases and commissions.

The public provider help center and terms supply program rules. Avoid copying
short-lived offers, editable fees or plan-specific thresholds into evergreen copy.
The guide is educational and does not attest to a released app integration.

## Visual references

The expected private location is
`%USERPROFILE%\Documents\OES\References\Razer_Website_References\`.
If missing, extract the supplied archive there, outside this repository.
The archive inventory is 4 marketing, 4 challenge configuration, 2 checkout,
and 9 dashboard/platform images. None is cleared for public use here.
For a later publishing pass, obtain permission and create redacted derivatives:
marketing needs usage approval, configuration needs rule/date verification,
and checkout/dashboard images need individual review for account, payment and
identity data. Keep originals out of Git. The guide currently uses the existing
public App Store screenshot for the ChaseInGreen step and textual instructions
plus official walkthroughs for provider steps.

## Private measurement

Existing product/session telemetry remains unchanged. New optional counts are
disabled without `OES_MARKETING_METRICS_DSN`. Apply
`migrations/marketing_metrics_001.sql` on an approved private PostgreSQL target
and verify TLS and user permissions before configuring the DSN. Grant schema
USAGE and only the INSERT/SELECT/UPDATE permissions required for the aggregate
upsert to a dedicated web role. Give a separate admin reporting role schema
USAGE and SELECT on `oes_marketing.daily`; do not give it to visitors.

The table stores UTC day, fixed page, fixed action and count. It stores no visits
as identities, referrer URLs, IP addresses, emails or user-agent strings. Step
counts represent step-link activations, not completed steps. Outbound clicks
are not purchases, installs, subscriptions or completed referrals. Browser
events can be lost, repeated or fabricated and are operational estimates only.
Android demand is read separately from the private registration aggregate.
Run the retention and permission tests before opening either collector.

## Release gate

Review this branch and merge through the normal GitHub workflow only after
approval. Allow the existing Render auto-deploy, verify the deployed SHA and
health, follow both homepage and ChaseInGreen links to the guide, check the
mobile layout, and inspect the exact affiliate href without generating a fake
visitor attribution. Roll back to the prior verified main revision if the
release fails. Leave Android email collection and private metrics disabled until
their respective database, notice and retention gates are approved.
