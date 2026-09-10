# Eyeball public chat v1

Browser → POST `/api/chat` → validation → ChatService → ChatProvider →
OllamaProvider → normalized SSE events → safe text transcript.

`providers.py` owns inference HTTP details. Add future adapters behind
`ChatProvider.stream(messages)`; never expose provider configuration to the client.
No tools, retrieval, credentials, private documents, persistent storage or admin
actions are available to the model. History stays in browser memory and is
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
details_opened_count (0–20, reset on project/section change), testflight_clicked
(page-wide boolean), chat_open_count (0–20), chat_message_count (0–100). Server-side
types and enums are checked; finite numeric values are clamped. No state/inference
overrides are accepted. `observations.py` keeps ObservationState separate from
InferenceState: possible_interest, needs_guidance, engagement_level, confidence,
source_observations. Confidence is heuristic, not a calibrated probability;
needs_guidance remains unknown because these observations cannot establish need.

`POST /api/chat/initiation` is a same-origin, deterministic, 4 KiB decision endpoint;
it never calls inference providers. It offers help only in products/client-work,
with an observed project AND either 45s dwell plus two real details openings OR 90s
dwell after a project selection. It stays silent after TestFlight is clicked, any
manual chat use, dismissal, a prior offer in the visit, a repeated project suggestion,
or within a 180s cooldown. It does not produce TestFlight suggestions. Other proactive
actions (ask_question/mention_product) are intentionally not enabled.

The client performs a one-shot eligibility check after qualifying interactions,
not repeated polling. It rechecks restraint and section revision after the decision
arrives. It never auto-opens the drawer, moves focus, or generates unsolicited model
text: it reveals a small optional invitation using the existing chat-opening event.
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

## Deployment boundary

Loopback defaults and `python app.py` are local development settings. This pass
does not establish production readiness: shared rate/concurrency limits, spending
controls, HTTPS, production WSGI/proxy streaming and timeout configuration, and
privacy/retention review remain deployment work. Origin checks are not user
authentication or bot protection. Do not expose the development debug server.
Review approved facts explicitly when website content changes; no repository
scraping or automatic context ingestion occurs.
