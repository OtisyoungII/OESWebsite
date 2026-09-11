# Outbound worker beta: disabled pending activation review

## Deployment boundary

Owner-confirmed: Render Starter, repository root, main, auto-deploy on commit,
current `gunicorn app:app`, no HTTP health path. Public GETs show a working Gunicorn
website but do not prove deployed SHA, resolved startup configuration, instance
count or trusted proxy chain. Retrieve those from Render; never guess
OES_TRUSTED_PROXY_HOPS. No dashboard, DNS, firewall or Cloudflare changes are made.

Gunicorn normally discovers gunicorn.conf.py in its working directory even without
`-c`. The old entry point loads policy and Admission but skips wsgi.py's explicit
provider selection and optional proxy setup. Neither import runs app.py's dev main.

Eventual Render start command:

```sh
gunicorn -c gunicorn.conf.py --bind "0.0.0.0:$PORT" wsgi:app
```

`GET /healthz` returns only `{"status":"ok"}`, HTTP 200, without external work or AI
dependencies. Use it as Render's health path after deployment. Never use
`/api/chat/health` as website liveness: that endpoint is optional AI/runtime health.

Production wsgi defaults AI chat and proactive off; an absent provider stays
unconfigured. Worker defaults off in every entry point. Local `python app.py`
retains direct Ollama behavior. No automatic .env loading is implemented.

## Authority

Browser -> existing OES API -> policy/ChatService -> OutboundWorkerProvider ->
one ephemeral relay job -> outbound HTTPS worker -> loopback Ollama -> signed
result batches -> existing OES response controls -> existing browser SSE.

The Razer executes `python -m worker`. It creates no listening socket. Its fixed
local endpoints are `http://127.0.0.1:11434/api/tags` (digest readiness) and
`/api/chat` (inference). Its only remote origin is trusted OES_WORKER_RELAY_URL:
HTTPS, no userinfo/query/fragment/path, verified certificates and hostname.
Redirects and environment HTTP proxies are disabled. Payloads cannot set a URL,
model, provider, tool, file or shell command. No arbitrary Ollama forwarding exists.

This process is not an OS sandbox. Use a restricted Windows identity with only
runtime/code and protected worker credentials. Do not inherit broker, repository
tokens or administrative credentials. Python/model runtime files remain readable;
there is no filesystem API. No router forwarding, inbound firewall rule or public
Ollama binding is needed. Render remains the policy and knowledge authority.

## Protocol v1

POST JSON endpoints under `/api/worker/v1/`:

| Operation | Exact body fields | Success response |
| --- | --- | --- |
| connect | boot, ollama | epoch, lease |
| poll | epoch, boot, lease | job:null OR job,messages,seconds |
| heartbeat | epoch, boot, lease, job, ollama | active,health |
| result | epoch, boot, lease, job, seq, text, done, error | accepted,active |

Canonical JSON: sorted keys, ASCII escapes, no whitespace, duplicate keys or
NaN/Infinity. Maximum body 256 KiB. Unknown fields/operations fail. Authentication
precedes session/job allocation and long-poll waits; body reading/hashing is bounded.
`ollama` is ready/unavailable. Heartbeat job can be null. Identifiers are bounded.
Result seq starts at integer zero; booleans are not sequence numbers. Advance only
after an accepted batch. Text <=1,024 characters/batch and <=16,000/job; an error
result must be terminal and contain no text. Tool/malformed model events fail.

One live worker boot owns a process-random epoch and random lease. A different boot
cannot replace it before expiry. Expired sessions cannot revive an old job.

## Authentication and replay

Headers: X-OES-Worker, X-OES-Key, X-OES-Time, X-OES-Nonce, X-OES-Signature.
HMAC-SHA256 signs newline-separated:

```text
oes-worker-v1
request OR response
POST
exact path
fixed worker ID
key ID
integer Unix timestamp
unique nonce
SHA256(canonical body)
```

Responses are signed and bound to the request nonce/time/path. Verify before
decoding jobs. Key: 32 random bytes as 64 lowercase hex characters. Comparisons are
constant-time. Timestamp tolerance 30 seconds. Monotonic nonce cache: 120 seconds,
2,048 entries, fail closed at capacity. Synchronize clocks.

Process restart resets the ephemeral cache but changes the epoch. Replayed connect
cannot itself execute inference; old job/lease requests fail across epochs.
Signatures are domain-separated by protocol/direction/path, not hostname: never
reuse the credential across deployments. Compromise of either credential-holding
host can expose prompts or impersonate the worker. Rotation/revocation is required.

## Bounds and cancellation

- One admitted job, no waiting inference queue, one local generation. The worker
  independently enforces serialization during deployment overlap.
- One system message <=16,000 characters, <=10 history user/assistant messages,
  each <=4,000 and total <=12,000, final user <=4,000.
- Conservative UTF-8 byte/template budget must fit 8,192 context tokens plus 600
  output tokens. Over-budget jobs fail; policy is never truncated. This rejects
  some otherwise valid maximum browser histories. Digest must match the approved
  local llama3.2:latest. Context capacity still needs a sustained GPU test.
- Relay deadline 100 seconds; delivered inference budget <=90 seconds. Lease 15
  seconds; heartbeat every 3; long poll <=10. Poll owns at most one waiting slot.
- Local Ollama socket timeout 10 seconds plus overall bounded stream/wire parsing.
  A blocking read can extend a deadline by up to its socket timeout.
- Relay RPC socket timeout 12 seconds and read-loop deadline 15 seconds; a blocked
  read can extend that deadline by up to 12 seconds. A 27-second caller deadline
  also covers OS DNS stalls; at most two outstanding transport threads are allowed.
  A late transport result is discarded, and occupied slots fail closed. An OS
  operation may outlive caller cancellation but cannot create unlimited threads.
  Model-readiness parsing is bounded too. No unlimited trickle read.
- Eight result batches buffered. Full buffer returns accepted:false without
  advancing seq. Only that explicitly unaccepted batch can be resubmitted after
  a brief wait. Ambiguous HTTP failure never replays an inference.
- Outbound manual chat uses an eight-event pump and content-free existing start
  frames every two seconds. WSGI can notice disconnects while policy buffers model
  output, cancel the job and close the stream. No unvalidated text is released.
- Worker heartbeat or rejected late result causes local HTTP stream closure.
  A blocked read can delay cancellation by ten seconds. GPU cessation after HTTP
  close is best effort, not instantaneous or guaranteed by Python.
- After a claimed job ends, new work waits for the worker to acknowledge idle;
  cancellation cannot immediately reassign work while the old stream is closing.
- Proactive requests remain disabled for beta. They retain buffered validation and
  bounded deadlines; immediate proactive HTTP-disconnect detection is not promised.

No disk queue, conversation storage, paid fallback or automatic inference replay.
The existing restrained AI error remains; Core/UI behavior is independent.

## Instances, health and logs

Use one Gunicorn worker and one steady-state Render instance. State is per process.
During overlapping deployments, wrong-epoch results fail closed; tolerate brief
AI downtime instead of assuming sticky routing or duplicating a job. A shared
multi-instance queue is not implemented. Worker serialization remains independent.

Authenticated heartbeat health dimensions:

- WEB_SERVICE_HEALTH: application is serving the request.
- EYEBALL_CORE_HEALTH: client_observed_only; server cannot certify browser motion.
- AI_FEATURE_HEALTH: disabled/ready/unavailable.
- LOCAL_WORKER_HEALTH: LOCAL_WORKER_HEALTHY, LOCAL_WORKER_DEGRADED (including busy),
  LOCAL_WORKER_OFFLINE.
- OLLAMA_HEALTH: worker-reported ready/unavailable, unknown when worker absent.

Public health reveals only coarse AI availability. Worker logs fixed outcome codes,
not prompts, responses, secrets, auth headers or raw exceptions. Host/edge logging
and general denial-of-service protections still require deployment review. A
health endpoint alone cannot prevent arbitrary internet traffic exhausting threads.

## Configuration and later activation

Render non-secret: OES_CHAT_PROVIDER=outbound_worker, OES_WORKER_ENABLED=false,
OES_EYEBALL_ENABLED=true, OES_AI_CHAT_ENABLED=false, OES_PROACTIVE_ENABLED=false,
OES_AI_MAX_CONCURRENCY=1, OES_API_RATE_LIMIT=60, OES_CHAT_RATE_LIMIT=12,
OES_PROACTIVE_RATE_LIMIT=3, OES_WORKER_ID, OES_WORKER_KEY_ID. Render supplies PORT.
Verify OES_TRUSTED_PROXY_HOPS with actual HTTPS Origin and spoofed forwarding tests.

Razer non-secret: OES_WORKER_ID, OES_WORKER_KEY_ID, OES_WORKER_RELAY_URL,
OES_WORKER_MODEL_DIGEST, OLLAMA_BASE_URL=http://127.0.0.1:11434,
OLLAMA_MODEL=llama3.2. Shared secret: OES_WORKER_SHARED_KEY on both. No additional
Render-only, Razer-only, Cloudflare or hosted-model credential is needed.

Later secret procedure, only after activation approval:

1. Generate secrets.token_hex(32) on a trusted machine. PowerShell can capture it
   without displaying it:
   `$env:OES_WORKER_SHARED_KEY = python -c "import secrets; print(secrets.token_hex(32))"`.
   Avoid transcription, screen recording and debug logging.
2. Transfer through a trusted secret manager into Render and protected Windows
   service storage. Never paste into chat, source, command arguments or committed
   .env files. If using a clipboard, clear it after entry.
3. Assign matching worker/key IDs. To rotate, disable AI/worker, replace key/key ID
   on both, restart to invalidate leases, verify readiness, then re-enable.
4. Never reuse the test harness credential. No production key is generated here.

Activation sequence: review code/tests -> separately authorize commit/push ->
deploy with AI/worker/proactive off -> verify successful SHA and /healthz -> apply
documented start command and /healthz check -> verify proxy/origin handling ->
configure restricted Razer worker and secrets -> enable worker only -> verify
signed readiness -> separately enable manual AI -> real failure/cancellation and
controlled capacity tests -> invite testers. Keep proactive false.

## Local verification

```sh
python -B -m unittest discover -s tests
node tests/test_observation_client.cjs
node tests/test_motion_client.cjs
python -B tools/verify_outbound_worker.py --openssl /path/to/openssl --browser
git diff --check
```

Integration is opt-in and requires already-installed OpenSSL, Ollama/llama3.2 and,
for --browser, Playwright/Edge (PLAYWRIGHT_MODULE may point to an existing install).
It creates temporary test-only TLS credentials, binds only loopback ports 5055,
5057 and 5443, runs a separate real worker and actual model, and cleans up.
Its printed synthetic test responses are intentional verification output, not
production logging. Unit tests use public fixture keys and do not access a model.
Windows checks do not establish Linux/Gunicorn/Render deployment behavior.
