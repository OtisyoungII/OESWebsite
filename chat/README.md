# Eyeball public chat v1

Browser → POST `/api/chat` → validation → ChatService → ChatProvider →
OllamaProvider → normalized SSE events → safe text transcript.

`providers.py` owns inference HTTP details. Add future adapters behind
`ChatProvider.stream(messages)`; never expose provider configuration to the client.
No tools, retrieval, private documents, persistent storage or admin actions are
available to the model. Hosted credentials stay exclusively in the HTTP adapter. History stays in browser memory and is
bounded again by the server. Assistant history is untrusted, not verified facts.

## Local run (PowerShell, repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install Flask
ollama list
# Run `ollama serve` in another terminal only if Ollama is not already running.
# Run `ollama pull llama3.2` only if that model is missing.
$env:OES_CHAT_PROVIDER = 'ollama'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'llama3.2'
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 and click the Eyeball. `.env.example` is documentation;
the application does not load `.env` automatically. Flask is already a declared
project dependency. No new HTTP library or model SDK is needed.

## Tests

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
Get-Content static/js/eyeball-chat.js -Raw | node --input-type=module --check
git diff --check
```

Backend tests use fake providers and mocked HTTP; Ollama is not required.
Manually test casual banter, an enterprise/security documentation request, Stop,
close/Escape, reopening, sphere dragging, and recovery when Ollama is unavailable.

## Policy and limits

`policy.py` separates identity, reviewed homepage facts, and serious-topic policy.
The small keyword detector includes bounded conversation history. Serious-topic
model output is a selection of approved fact IDs: software renders the facts and
an explicit unconfirmed-information notice. Invalid selections fall back to that
notice and contact information. Raw serious-topic model prose is never streamed.
This was necessary because live llama3.2 testing invented controls despite strong
prompt instructions. Casual text streams normally and can still be inaccurate;
keyword classification is not a universal factuality or prompt-injection guarantee.

Requests: 64 KiB, 4,000-character message, at most 10 history items (4,000 characters
each and 12,000 total); allowlisted observation values only. Response: at most
16,000 characters, Ollama generation cap of 600 tokens. HTTP read timeout is 30
seconds; the generation deadline is 120 seconds, checked between reads (an active
read can extend it by up to the socket timeout). Provider exceptions are replaced
with a generic error. No prompts, transcripts or provider exceptions are logged by
the chat package. The web server may still log request metadata.

AbortController stops the browser stream. Generator cleanup closes the upstream
response when the WSGI server detects a disconnect; this is not guaranteed immediate
model cancellation while an upstream read is blocked. Closing chat also aborts.
Interrupted answers are not added to request history.

## Situation Intelligence

`situation.py` derives an immutable SituationState from the validated message,
bounded in-request history and allowlisted observations. No state is accepted from
the browser or persisted. Continuity retains at most three recent assistant texts
inside the existing history bounds, and classifies recent tone without asserting
visitor intent. `certainty` describes classification confidence, not factual truth.

Serious policy wins over playful tone, including serious history and sensitive
business terms. The approved-fact renderer remains unchanged. Ordinary replies
stream normally. Short playful replies are buffered and checked for length,
first-person voice, generic disclaimers, repeated four-word phrases/openings and
some obvious repeated joke structures. One regeneration is allowed; two invalid
drafts produce the existing safe error, not a canned joke. The validator is a
bounded heuristic, not a universal semantic repetition or factuality guarantee.

Flask debug mode logs only interaction_kind, tone, serious, facts_required,
grounding_mode, response_action and certainty. It logs no message or draft text.

## Website observation context (v2)

`eyeball-observations.js` holds page-memory observations only and resets on reload.
It consumes section awareness without changing it. Project selection means a click
or keyboard focus within a known product card, not inferred intent or passive hover.
Section dwell accumulates only while the document is visible. Details openings count
only actual native `details` opening events within a product; the current homepage
has no such expanders, so that count currently remains zero. TestFlight clicks match
the three existing published CTA paths. Counts never imply emotion or purchase intent.

Fields: section, project, device, interaction_mode, time_on_section_seconds (0–3600),
product_interaction_count and details_opened_count (0–20 each, reset on project/section change), testflight_clicked
(page-wide boolean), chat_open_count (0–20), chat_message_count (0–100). Server-side
types and enums are checked; finite numeric values are clamped. No state/inference
overrides are accepted. `observations.py` keeps ObservationState separate from
InferenceState: possible_interest, needs_guidance, engagement_level, confidence,
source_observations. Confidence is heuristic, not a calibrated probability;
needs_guidance remains unknown because these observations cannot establish need.

`POST /api/chat/initiation` is a same-origin, deterministic, 4 KiB decision endpoint;
it never calls inference providers. It offers help only in products/client-work,
with an observed project AND either 45s dwell plus two explicit product interactions at least 3s apart (or two future details openings) OR 90s
dwell after a project selection. It stays silent after TestFlight is clicked, any
manual chat use, dismissal, a prior offer in the visit, a repeated project suggestion,
or within a 180s cooldown. It does not produce TestFlight suggestions. Other proactive
actions (ask_question/mention_product) are intentionally not enabled.

The client performs a one-shot eligibility check after qualifying interactions,
not repeated polling. It rechecks restraint and section revision after the decision
arrives. It never auto-opens the drawer, moves focus, or auto-sends chat
text: it reveals a validated model-worded optional invitation using the existing chat-opening event.
Closing chat or dismissing the invitation suppresses all invitations until reload.
A section reentry is a new meaningful visit only after 15s away; duplicate suggestions
remain suppressed across those visits. Requests after a declined/failed decision are
not retried for that project/visit. Page-memory restraint is a UX rule, not an
authentication boundary against a client forging requests.

In Flask debug mode, the initiation endpoint and chat service log only the specified observation,
inference and action/reason summaries; no messages, identifiers or inferred sensitive
traits. Chat additionally retains its existing allowlisted situation debug fields;
its initiation decision is always stay_silent because user requests take precedence.

Client state tests (no dependencies):

```powershell
node --preserve-symlinks --preserve-symlinks-main tests/test_observation_client.cjs
```

## Controlled initiative (v3)

`initiative.py` derives a frozen `InitiationIntent`: action, target, reason,
allowed_observations, allowed_public_facts, forbidden_inferences, tone, max_words
and certainty. Only offer_help is enabled, with light_helpful tone, an 18-word cap
and moderate classification certainty. Allowed facts contain only the product name.
Observations never establish visitor motives. Details expanders are not required.

After deterministic permission, `POST /api/chat/invitation` independently validates
context, restraint, bounded history and at most three recent invitations (240
characters each). The request limit is 8 KiB. Authorization is rechecked before
provider construction. Browser-supplied intent/action/tone overrides are rejected.
Serious/problem history, any prior conversation or uncertain target means silence.
Normal `/api/chat` generation and the provider abstraction remain unchanged.

`ChatService.invitation` buffers wording and validates length, optional help,
detectable inferences, unsupported claims, pressure, disclaimers, serious language
and repetition. One correction attempt is permitted; a second rejection or provider
failure means silence. No canned production response is substituted. Validation is
heuristic, not a universal semantic factuality guarantee.

The browser retains wording only in page memory, rechecks eligibility and section
revision before display, discards late responses after user interaction, and inserts
accepted text with textContent. Clicks/keyboard focus use existing product cards and
the client-work spotlight; paired focus/click events are deduped. Restraint, cooldown,
dismissal, prior chat and TestFlight suppression remain software controlled.

Debug-only v3 logs contain initiation action/target/reason and generation
attempt/status/validator_reason, without visitor text or generated drafts.
Browser observations and flags are not attestations: forged requests can fabricate
eligibility. These UX controls do not replace server-side abuse limits. Browser
abort does not guarantee immediate cancellation of an in-flight provider request.
There is no persistence, new authentication or tool execution.

## Production runtime v1

The audit found no hosting vendor/deployment manifest or hosted-provider convention.
`requirements.txt` already declares Flask and Gunicorn; no SDK or additional package
is needed. The former development-only factory, missing kill switches/readiness,
and unthrottled public inference were production blockers. `python app.py` remains
a local development command; it defaults to loopback and debug on. OES_DEV_DEBUG=false
turns off its debugger. HOST and PORT can override its development binding.

### Provider selection

`OES_CHAT_PROVIDER=ollama` retains local development at OLLAMA_BASE_URL and OLLAMA_MODEL.
Do not expose Ollama's port publicly or use a laptop tunnel as production hosting.
`OES_CHAT_PROVIDER=openai_compatible` uses OES_AI_BASE_URL, OES_AI_API_KEY and OES_AI_MODEL.
All three are required. The base is the API root (for example a provider's `/v1`);
the adapter appends `/chat/completions`. There is no default hosted vendor or model.
Configure credentials through environment/host secret management, never browser code
or committed files. Environment is loaded at process startup, not from .env files.

The hosted adapter sends Chat Completions SSE with max_tokens=600 and accepts text
choice 0, a normal stop finish, then [DONE]. It does not send tools, retry HTTP failures,
or expose upstream error bodies. Only normalized delta/done events reach the service.
Adapters requiring another token parameter, non-SSE output, different authentication
or another API shape are not yet supported; test the chosen provider before launch.
HTTPS is mandatory; credentials-in-URL, query/fragment, obvious private/local addresses
and all redirects are rejected. DNS is controlled by the server operator; this is
not a general-purpose SSRF proxy or a DNS-pinning mechanism. No browser payload can
supply provider configuration. Existing serious rendering and invitation validators
remain authoritative and unchanged.

### Switches and health

OES_EYEBALL_ENABLED=false disables all intelligent APIs. OES_AI_CHAT_ENABLED=false
returns the existing safe 503 message for manual chat and silence for proactive paths.
OES_PROACTIVE_ENABLED=false silences initiation/invitation without affecting manual
chat. Switches default true for local compatibility; only true enables them (invalid
values fail closed). Changing process environment requires restart/redeploy. They
do not change Core/Three.js/motion or hide/redesign the drawer.

GET /api/chat/health validates configuration without network calls or generation.
It returns only enabled/disabled/ready/unavailable/configured/unconfigured states and
reachability=unchecked. Valid configuration is NOT evidence of provider availability,
valid credentials, sufficient quota or acceptable model quality. Missing configuration
returns 503 when chat is enabled. Responses are no-store and omit URLs, model names,
keys and prompts. Production must explicitly set OES_CHAT_PROVIDER; `wsgi.py` does
not fall back to local Ollama if that variable is absent.

### Limits, timeouts and failure

Existing body caps remain 64 KiB chat / 4 KiB initiation / 8 KiB invitation. Messages
are <=4000 characters; history <=10 entries / 12000 total characters. Output is
<=16000 characters, with stricter existing playful/invitation validation. Both
providers request at most 600 tokens and cap upstream bytes at 1 MiB, line/frame
size at 64 KiB, socket operations at 30s and generation reading at 120s per attempt.
Chunk reading prevents continuously trickled lines from evading deadline checks.
A blocked read can extend an attempt by up to a socket timeout. DNS resolution is
subject to the operating system resolver; these are not hard real-time guarantees.
There are no HTTP retries. Existing policy permits at most one regeneration, so a
request may use two calls. The browser gives up after 330s and clears busy state;
Stop and stale-request checks remain effective. Provider error/timeout/malformed
stream produces the existing safe error; rejected invitations stay silent.

`runtime.py` applies process-local locked admission control:
- OES_API_RATE_LIMIT=60 requests/client/minute across POST APIs, including invalid requests.
- OES_CHAT_RATE_LIMIT=12 generation requests/client/minute (manual and proactive combined).
- OES_PROACTIVE_RATE_LIMIT=3 generation requests/client/10 minutes.
- Fixed 30 generation requests/process/minute, each allowing at most two existing policy attempts.
- OES_AI_MAX_CONCURRENCY=2 generation requests, held through retries and streaming cleanup.
- At most 2048 recently active client buckets; capacity exhaustion fails closed.

Limits return safe 429/503 with Retry-After; there is no queue. Release is idempotent
and handles completion, exceptions, client disconnect and unstarted closed responses.
Addresses are keyed using an ephemeral process HMAC; message contents are not stored
by the limiter. Buckets expire after inactivity; all limits reset on restart/deploy
and multiply with worker/replica count. NAT users share limits. These are small-beta
protections, not distributed bot defense, billing controls or authentication. Set
provider-side spending caps and configure edge protections before public launch.

Buffered invitation requests can finish after browser cancellation. Normal streamed
requests close upstream when the WSGI server detects disconnection, which may wait
for the next provider read/yield. Slow downstream clients can retain a worker slot;
proxy read/send/client-body timeouts are required. There is no persistent account
system, new tool permission, private data access or motion control from model output.

### Production server and reverse proxy

On a Linux host with requirements installed:

```sh
gunicorn -c gunicorn.conf.py wsgi:app
```

`wsgi.py` forces debug/testing off. The supplied beta profile uses one gthread worker,
eight threads, a 360s worker timeout and a 30s graceful shutdown. Gunicorn is a Unix
server; this Windows session verifies Flask/provider behavior, not a Linux launch.
HOST defaults to 127.0.0.1 and PORT to 8000; a container platform may require
HOST=0.0.0.0 and an injected PORT. Do not expose the development server in production.

SSE responses set X-Accel-Buffering=no and Cache-Control=no-store, no-transform.
These headers alone do not prove proxy/CDN compatibility. Configure `/api/chat`
streaming with response buffering/caching/compression disabled and upstream read
and client send timeouts sufficient for the 330s browser budget (or choose a host
supporting it). For nginx, use proxy_buffering off and proxy_read_timeout 360s;
set appropriate request-body/client timeouts and preserve the public Host header.
Do not enable proxy_ignore_client_abort. Validate actual chunk arrival and Stop
through the deployed proxy; some serverless hosts impose shorter hard deadlines.
See [Gunicorn deployment guidance](https://gunicorn.org/deploy/) and
[worker guidance](https://gunicorn.org/design/).

By default forwarded client IP/scheme headers are ignored. Set
OES_TRUSTED_PROXY_HOPS only after verifying the exact number (0�2) of trusted,
header-sanitizing proxies, and firewall the origin against direct public traffic.
It enables ProxyFix for client IP and scheme only. An incorrect value permits
spoofed client identity/rate-limit bypass; leaving it zero behind a proxy groups
visitors under the proxy's address and may reject HTTPS Origin checks. Configure
TLS, public host validation, access-log retention and secret injection at the host.

### Verification and launch boundary

The complete suite includes tests/test_runtime.py (mocked hosted HTTP, no credentials)
and existing policy/motion tests. tests/test_runtime_browser.cjs uses running local
servers on 5055 (enabled) and 5057 (chat disabled); its Stop/timeout checks use explicit
transport fixtures. PLAYWRIGHT_MODULE can select an already-installed Playwright.
No test installs dependencies or invokes a paid hosted API by default.

Real local Ollama verification passed for manual casual chat, serious fabricated
certification grounding and proactive generation. Proactive-off preserved manual
chat, chat-off failed gracefully, and enabled configuration restored responses.
Hosted HTTP is tested with fixtures only: no hosted credentials were available.

Before a cellular/public test, Otis must supply the hosting target/OS/start command,
public domain/TLS and proxy/CDN topology, hosted API root/model and securely injected
key, provider quota/spending limits, and expected beta traffic/retention requirements.
Then verify Linux startup, provider authentication/model behavior, proxy streaming,
client-IP attribution and cancellation from an external network. The repository is
host-compatible but is NOT a deployed, publicly verified service and is not ready
for Gooch until those checks pass. Keep approved public facts explicitly reviewed;
no repository scraping or private-document ingestion occurs.
