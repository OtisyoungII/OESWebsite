# OES Eyeball public beta release-candidate evidence

Date: 2026-09-15
Base commit: `24ba540929c426fe0836e4b6d4ce565e356a6e88` (`Add secure outbound Eyeball inference worker`)
Branch: `main`
Candidate state: uncommitted bounded character/grounding changes plus this report
Decision: **PUBLIC BETA CANDIDATE — GO**; personality safe-failure rate accepted as a beta limitation

## Scope and architecture exercised

The review exercised Browser → Flask routes → `ChatService` → provider abstraction →
local Ollama, software-controlled serious/public-fact rendering, bounded observations,
initiative policy, runtime admission controls, outbound-worker protocol tests, browser
Stop behavior, Core/chat UI and motion arbitration. It did not activate proactive AI,
start the production worker, deploy, push, or use production credentials.

Local model: `llama3.2:latest`
Model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`

## Candidate changes

- Character-directed banter receives a bounded contract, small greeting/presence/activity/trust
  hint, validation and at most one regeneration. No hint contains canned response wording.
- Approved public facts cover OES, ChaseInGreen, Lottovate and Drinks With Friendz.
- OES/product answers use model fact-ID selection and software-rendered approved text.
- Unsupported customer, agency, revenue, user-count, guarantee, credential, private-data and
  internal-instruction requests use the strict serious-output boundary.
- Unknown visitor motive is not inferred; software returns a bounded clarification without
  calling the provider.
- Explicit approved-fact selection omits untrusted conversation history after serious
  precedence and situation analysis have already run.

## Deterministic verification

- Final complete Python suite: **143 passed**.
- Final focused suite counts: situation **19**; chat **29**.
- Observation client assertions: passed.
- Motion policy: **14 passed**.
- Runtime browser: **4 passed**.
- Motion browser: **9 passed**.
- JavaScript module syntax: **16 files passed** using stdin module checking.
- CommonJS syntax: **4 files passed**.
- Python source compilation: **29 files passed** without writing bytecode.
- `git diff --check`: passed.

Direct Node module checking is obstructed by a malformed pre-existing
`C:\Users\baseb\package.json`. The unchanged browser tests ran with a synthetic filename
outside that package scope and the installed Codex Playwright runtime.

## Real-model character results

Ten specified prompts were run three times through real `ChatService` and local
`llama3.2`, retaining the one-retry validator. Latest result:

- accepted: **20/30**
- safe error after two rejected drafts: **10/30**
- requests using the one allowed regeneration: **24/30**

Representative accepted outputs: “Not again.”, “Indeed I am.”, “You've spotted me.”,
“Still pretty smart, I think.”, and “Right on cue.”

Rejected/problematic drafts included technology explanations, claimed reboot/background
activity, visitor observation, invented prior activity and unsupported trust claims. Rejected
drafts were not released. The remaining safe-error rate is accepted for the first public beta
because rejected drafts fail safely.

Final multi-turn checks preserved character continuity and transitioned to exact
software-rendered OES and ChaseInGreen facts. One appearance-teasing turn exhausted both
attempts and returned the safe error.

## Grounding, context and adversarial results

- Approved facts for all four named OES/product subjects were server-rendered.
- Unsupported agency, Fortune 500 customer, certification, encryption, revenue, Pentagon,
  profit-guarantee and million-user claims did not escape after the fixes.
- Project context can authorize relevant fact selection without asserting visitor motive.
- “Why am I looking at this?” no longer reaches the model or infers intent.
- Direct, misspelled, developer-message, hidden-text, repeat-last, credential and API-key
  requests entered the strict software-rendered boundary in final focused checks.
- Browser-supplied situation/authority overrides remain rejected by deterministic tests.

The meta-request detector is heuristic, not a universal prompt-injection proof. Anonymous
users gain no tool, administrative, private-document or action authority.

## Failure, cancellation and recovery

Unit and browser suites verified provider/factory failure, malformed streams, bounded timeouts,
concurrency release, rate budgets, client disconnect cleanup, worker cancellation/upstream close,
worker disappearance, model mismatch, disabled modes, Stop/stale-response suppression and UI
recovery. Website/Core liveness remains independent of provider and worker health.

## Findings

### P0

No known P0 remains in the tested candidate diff. Public fact hallucination, visitor-motive
inference and internal-policy disclosure were observed during testing and then closed with
software-controlled boundaries and regression tests.

The previously identified untrusted state of the intended Razer worker host remains an external
operational blocker. Do not place production credentials on it or start the production worker
until that host is independently remediated or replaced.

### Accepted beta limitation

Real `llama3.2` character reliability produced 10/30 safe failures after both attempts. The
business owner explicitly accepted this for the first beta; safe failure remains preferable to
releasing fabricated or policy-breaking output.

### P2

- Fact selection may include an extra relevant-but-unnecessary approved fact; it cannot add
  model prose or an unapproved fact.
- The meta-request detector is heuristic defense in depth.
- Direct Node tooling remains affected by the malformed user-level package file.

### P3 / deferred

RAG, tools, agents, persistent history, accounts, voice, lead scoring, admin mode, model routing,
new providers and distributed scaling remain intentionally outside this candidate.

## Initial-beta feature state

Proactive AI, production worker activation, private tools, persistent conversation storage and
administrative actions remain disabled/not activated. No production secret was generated or used.
