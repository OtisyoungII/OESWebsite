# Eyeball behavioral motion v1

## Movement ownership audit (before implementation)

- `static/js/oes-core-companion.js`: `applyPosition` alone writes portal x/y CSS variables; `applySize` writes size. `animateToPosition` interpolates automatic travel, interest avoidance, manual API moves and docking. `enterCompanionMode`/`restoreCoreToOriginalStage` reparent the existing Core and set floating placement. `moveToCurrentSection`, `handleResize`, hero/viewport observers and public move/dock/reset APIs initiate placement. `beginMovementDrag`/`continueMovementDrag`/`endMovementDrag` own outer-handle capture and dragging; direct drag position updates bypass automatic motion policy.
- `static/js/section-awareness.js`: `activateInterest` dispatches `oes:interestchange` after hover/focus/click; section observation dispatches section changes. It writes awareness colors/classes, not portal position.
- `static/js/oes-core.js`: independent window pointer tracking and Core interaction listeners own visual state, gaze variables, blinking and activation. No floating portal position writes.
- `static/js/oes-core-3d.js`: independent global/Core pointer listeners own gaze and drag-to-spin. Its animation loop owns scene-object transforms; setup/cleanup also owns Core button transform. Companion CSS deliberately overrides the nested button transform while floating. Portal and scene transforms are distinct layers.
- `static/js/eyeball-chat.js`: independent Core pointer listeners distinguish click from >=5px drag and use `oes:chatrequest`. Native dialog focus/open state changes, no portal position writes.
- `static/js/eyeball-observations.js`: invitation visibility and restraint; no Core transforms.
- `static/js/detroit-scene.js`, `ambient-effects.js`, `card-effects.js`, `product-effects.js` and page CSS: background parallax, ambient effects and card transforms. Card transforms affect measured target geometry but do not write companion position. Existing hero/floating CSS owns layout, breathing and scale.

Root cause: `handleInterestChange` previously chose the side opposite every interest element and animated there, without verifying actionable overlap, pointer approach, pointerdown or chat state. Repeated hover interest events could request repeated relocations. There is no separate cursor-distance avoidance physics to rewrite.

## Arbitration

`static/js/eyeball-motion.js` supplies a pure `MotionArbiter` and a small DOM adapter. It never writes transforms or calls an AI service. Only one previous pointer point is retained. The adapter uses actual element geometry and native UI state, not request context or generated text. Software-derived scores are tentative, not assertions of visitor intent.

Automatic movement enters the gate in `animateToPosition`; in-flight animation checks engagement before another position write. Interest moves additionally require the same observed actionable target. The adapter can request the existing interest movement when a pointer heads into a partially obstructed actionable element. Existing physics, timing, destination selection, manual dragging/docking and viewport safety remain owned by the companion. Hero restore/fallback remain authoritative lifecycle operations.

Thresholds:
- Pointer sample interval <=250ms, displacement >=1px; scores expire after 300ms.
- Near = half the larger Core dimension +120px.
- Approach score >=0.65 holds automatic relocation for 900ms; being over Core also holds.
- Avoidance requires >=20% target-area overlap, pointer within 240px of target center, trajectory score >=0.8, and approach score <0.65.
- Every automatic relocation starts a 3000ms cooldown. Following the new location also establishes an approach hold.
- Core/handle pointerdown locks until matching up/cancel/lost capture; blur clears pointer capture observations. Native chat, visible invitation and Core/handle focus suppress automatic moves. Hidden document and government/privacy section state also suppress discretionary moves.

States: observing, available, approached, engaged, avoiding, suppressed, serious. Explicit drag/dock/API commands and viewport clamping are exceptions to discretionary relocation locks. Invitation dismissal does not trigger motion or reset the existing invitation restraint. No persistent state is added.

Flask DEBUG renders `data-motion-debug`; diagnostics are transition-only, at most twice a second, with state, pointer_distance, approach_score, obstruction_score, movement_allowed and movement_reason. No raw trail logging. Changing local JavaScript is not a security boundary, but no AI-context field or model output controls this policy.

## Verification

`node --preserve-symlinks --preserve-symlinks-main tests/test_motion_client.cjs` runs 14 pure-policy checks. Existing Python and observation client tests remain required. Browser verification uses real Edge pointer events, floating WebGL Core, existing activation, center spin and movement handle. The obstruction fixture positions the real Core over an existing privacy link using the existing public movement API; it does not introduce an artificial button or alter physics.

Limitations: conservative overlap/trajectory heuristics may choose to stay put for ambiguous targets, especially fully covered targets. Touch proximity has no inferred avoidance; pointerdown and existing touch dragging remain authoritative. Serious state here uses observable page sections/native chat presence, not private server conversation classification. An interrupted automatic move holds its current position until another legitimate placement event; it does not schedule retries.

Browser regression: tests/test_motion_browser.cjs requires an existing Flask server and Playwright (PLAYWRIGHT_MODULE may select an existing installation; OES_TEST_URL defaults to loopback port 5055). No dependencies are installed by the test. A malformed package.json above this repository required running a scratch copy with an absolute Playwright import during this session. The browser check also verifies the obstructed link can be clicked after relocation, and uses a visible-invitation fixture for the motion-only precedence check.
