# OES Motor City Premium Design Exploration

This exploration is isolated from production templates and runtime behavior. It is based on unified integration checkpoint `bb27e9207fe67c9a7f346e10349693c98fbdff5d` and uses the existing OES logo and verified website copy.

## Content-preservation map

| Existing source | Existing information | Concept A | Concept B | Concept C |
| --- | --- | --- | --- | --- |
| `templates/base.html` | OES identity, Detroit location, primary navigation, footer, contact, privacy | Sticky industrial masthead and footer | Editorial masthead and footer | System masthead and footer |
| `templates/index.html#home` | Hero positioning, company introduction, OES belief, two primary calls to action | Machined assembly-bay hero | 313 editorial district cover | Command-center system entry |
| `templates/index.html#products` | ChaseInGreen, Lottovate, Sportfolio descriptions, statuses, features, links and cautions | Product bays with accessible detail disclosures | Product dossier grid | Selectable-looking system records with detail disclosures |
| `templates/index.html#client-work` | Drinks With Friendz client attribution, description, phase, features, website, TestFlight and privacy | Fourth product bay, explicitly client work | Fourth project dossier, explicitly client work | Fourth system record, explicitly client work |
| `templates/index.html#services` | Eight OES service descriptions | Stamped capability plates | Two-column campus program blocks | Capability matrix |
| `templates/index.html#government` | Active SAM status, UEI, CAGE, eligibility language, two explanatory paragraphs, six capabilities and CTA | Compliance plate and capability grid | Civic-red public-sector chapter | Bounded public-sector system panel |
| `templates/index.html#community` | Apple Developer Academy, TechTown Detroit, Black Tech Saturdays, Crossroads, mentorship and OES belief | Horizontal Detroit production line | Urban editorial story blocks | Connected-node records |
| `templates/index.html#research` | Two research paragraphs and six truthful status lines | Test-cell ledger | Research editorial chapter | Live-looking, non-live research status table |
| `templates/index.html#about` | Company scope, multidisciplinary approach and imperfection belief | Industrial identity plate | Dark editorial interlude | Identity subsystem |
| `templates/index.html#contact` | Contact scope, email CTA and ChaseInGreen TestFlight CTA | Amber action plate | High-contrast civic action band | Command action panel |
| `templates/partials/eyeball_chat.html` plus Eyeball scripts | Existing chat trigger and UI/runtime | Mechanical console trigger | Editorial black-square trigger | Luminous system-node trigger |
| `static/js/product-intelligence.js` | Existing validated Product Intelligence events | No runtime duplication; production integration would retain existing attributes/events | Same | Same |
| `templates/privacy.html` | OES privacy policy | Working `/privacy` link to existing route | Same | Same |
| `templates/drinks_with_friendz_privacy.html` | Drinks With Friendz privacy policy | Working `/drinks-with-friendz/privacy` link | Same | Same |
| `static/js/eyeball-localization.js` | Eyeball UI languages: English, Spanish, French, Arabic, Chinese | Runtime remains untouched; concept changes only placement | Same | Same |
| Existing responsive CSS and semantic markup | Mobile navigation, readable layout, skip link and reduced motion | New responsive rules and accessible disclosures | Same, with editorial reflow | Same, with command panels stacked |

No product fact has been added. Sportfolio’s public web URL remains visibly pending because the source template only enables it when `SPORTFOLIO_WEB_URL` is configured. Community organizations remain ecosystem connections, not claimed partnerships.

## Concept A — Motor City Industrial Future

An automotive engineering language without literal car decoration. Precision grid lines, stamped indices, dark machined surfaces, warm inspection amber and restrained cyan instrumentation organize the experience into product bays. Product detail expands in place, keeping the overview fast while preserving every verified feature and action.

Typography uses condensed-feeling uppercase system forms for display and highly readable Segoe UI for body copy. Motion should feel like controlled machinery: short, direct, damped and never ornamental. Mobile collapses each product bay into a single-column service record.

## Concept B — Detroit Innovation District

An editorial, civic and architectural direction. Warm paper, brick red, ink blue, a large “313” field and an asymmetric story grid make OES feel embedded in a living innovation ecosystem without claiming partnerships. Products read like project dossiers; community material has equal visual dignity instead of becoming an afterthought.

Typography pairs Georgia’s editorial authority with Segoe UI’s clarity. Motion should resemble wayfinding and page composition: gentle reveals and deliberate shifts. On mobile, asymmetric grids resolve into a clear reading order.

## Concept C — OES Digital Command Center

A dense but disciplined system environment. Visitors see OES as a connected portfolio: products, capabilities, research, public-sector readiness and Detroit context are system records rather than disconnected cards. Cyan is functional signal color, not decorative neon. The layout uses a persistent information rail on desktop and straightforward stacked panels on mobile.

Typography uses Consolas for system metadata and Segoe UI for persuasive content. Motion should communicate state and selection only. Reduced-motion mode removes all nonessential transitions.

## Product-discovery model

All three concepts use the same two-level pattern:

1. A first-time visitor sees product name, category and verified current status immediately.
2. A native `details` disclosure exposes the complete description, feature list, caveats and working actions on demand.

The disclosure is keyboard-operable, works without hover and remains useful without animation. It avoids inventing a roadmap: the source site does not provide verified historical stage dates, so the prototypes label current state rather than fabricating a timeline.

## Visual identity system

| System | A — Industrial | B — District | C — Command Center |
| --- | --- | --- | --- |
| Primary type | Segoe UI, uppercase display | Georgia display + Segoe UI body | Segoe UI display + Consolas metadata |
| Palette | Graphite, steel, inspection amber, restrained cyan | Warm paper, ink blue, brick red, civic yellow | Near-black, ice cyan, muted green |
| Grid | Assembly bays and production lines | Asymmetric editorial blocks | Information rails and system matrices |
| Detroit motif | Manufacturing precision | 313, architecture, civic print | Network node / systems operations |
| Eyeball role | Mechanical control console | Editorial interruption / guide | Persistent intelligence node |
| Motion | Damped machine movement | Wayfinding and editorial reveal | State transitions and signal changes |

## Accessibility observations

- Each prototype begins with a keyboard-visible skip link.
- Navigation uses real links; the mobile menu is a button with `aria-expanded`.
- Product detail uses native `details`/`summary`, not hover.
- The Eyeball design-preview panel is keyboard operable, Escape-closeable and returns focus to its trigger.
- External links use `noopener noreferrer`; unavailable product destinations are non-links with `aria-disabled`.
- Responsive breakpoints cover compact phone, tablet and desktop layouts.
- `prefers-reduced-motion: reduce` disables smooth scrolling and collapses transition/animation time.
- The prototypes use high-contrast text/background pairs, but formal WCAG color measurement remains part of final-direction implementation.

## Known limitations

- These are buildless design prototypes, not replacements for Flask templates.
- The preview Eyeball panel demonstrates placement only and deliberately does not call `/api/chat`.
- Product Intelligence is not emitted by the prototypes; final integration must reuse the existing validated event schema and attributes.
- Sportfolio’s environment-configured public URL cannot be represented in a static file, so its action truthfully remains pending.
- Legal pages remain the existing Flask pages and are linked rather than duplicated.
- No new photography, third-party marks or unverified Detroit partnership claims were added.

## Local preview

From the repository worktree:

```powershell
.venv\Scripts\python.exe app.py
```

Then open:

`http://127.0.0.1:5000/static/design-exploration/motor-city/index.html`

The concept switcher remains visible in every prototype. This exploration must not be routed from production navigation or deployed before owner selection.
