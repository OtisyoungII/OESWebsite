# Motor City — Liquid Alloy

Concept D refines the selected Concept C direction without changing Concepts A, B or C. It remains a buildless design prototype isolated from Flask production templates and runtime services.

## Content-preservation matrix

| Original content | Original location | Concept D location | Exposure | Link preservation / factual change |
| --- | --- | --- | --- | --- |
| OES identity, Detroit location and “Ideas into execution” | `templates/base.html` header/footer | Machined masthead and site footer | Immediate | Existing logo and legal routes retained |
| Homepage positioning and belief | `templates/index.html#home` | Layered Liquid Alloy hero | Immediate | Copy preserved; headline is art direction, not a new company claim |
| ChaseInGreen description, boundaries, features, Discord and privacy | `templates/index.html#products` | First Liquid Alloy spine product and foreground dossier | Status/description immediate; features expandable | TestFlight action replaced by verified App Store listing; status updated to “Live on the App Store” |
| Lottovate description, features, no-guarantee boundary, TestFlight and Discord | `templates/index.html#products` | Second spine product and dossier | Status/description immediate; features expandable | Existing destinations retained; status phrased “Public TestFlight” from its public TestFlight destination |
| Sportfolio description, baseball-first scope, features, web testing and iOS future state | `templates/index.html#products`, `app.py`, approved public facts | Third spine product and dossier | Status/description immediate; features expandable | Documented public web URL retained; iOS TestFlight remains coming soon |
| Drinks With Friendz client attribution, phase, features, site, TestFlight and privacy | `templates/index.html#client-work` | Dedicated Client Work bay and expandable delivery dossier | Ownership/status/description immediate; delivered capabilities expandable | Client attribution and all destinations retained; explicitly excluded from the OES-owned product spine |
| Eyeball / OES Core representation, public notice and localization | `templates/index.html`, `templates/partials/eyeball_chat.html`, `static/js/eyeball-localization.js`, approved public facts | Dedicated Eyeball platform dock with a truthful asset-review gate | Platform identity and boundary immediate | Existing localization statement retained; prototype performs no chat or native-renderer call and does not pass off the flat logo/procedural prototype as premium 3D art |
| Eight OES services | `templates/index.html#services` | Flowing capability river | Immediate | Every title and description preserved |
| Active SAM registration, UEI, CAGE, eligibility language and six capabilities | `templates/index.html#government` | Elevated federal plate and capability vault | Immediate | Exact identifiers and cautious eligibility language retained |
| Apple Developer Academy, TechTown, Black Tech Saturdays, Crossroads, mentorship and OES belief | `templates/index.html#community` | Detroit network nodes | Immediate | All existing public destinations retained; no partnership claims added |
| Research explanation and six state-labeled initiatives | `templates/index.html#research` | Research instrument | Immediate | Status labels and descriptions preserved; no fake telemetry |
| Company story | `templates/index.html#about` | Detroit identity bay | Immediate | All three original paragraphs preserved |
| Contact scope, email and ChaseInGreen action | `templates/index.html#contact` | Contact forge | Immediate | Email retained; Chase action updated to App Store |
| OES and Drinks With Friendz privacy policies | `/privacy`, `/drinks-with-friendz/privacy` | Footer and product actions | Immediate links | Existing Flask routes retained; legal text not duplicated or altered |
| Product Intelligence | `static/js/product-intelligence.js` | Production-integration note only | Not active in prototype | Prototype emits no analytics; final integration must reuse validated events |
| Accessibility and reduced-motion behavior | Existing semantic templates/CSS | Skip link, tablist, native details, focus states, compact navigation, reduced-motion media query | Immediate | Keyboard, touch and screen-reader semantics included |

## ChaseInGreen release verification

The repository contained only the prior public TestFlight destination. Public Apple App Store verification on November 5, 2026 located the official U.S. listing:

- Product: ChaseINGreen
- App Store product ID: `6770096789`
- URL: `https://apps.apple.com/us/app/chaseingreen/id6770096789`
- Developer shown by Apple: Otis Young
- Copyright shown by Apple: © 2026 Otis Execution Systems LLC

Concept D changes only the prototype’s release state and action. It does not alter production product policy, Chat grounding facts or production templates.

## Interaction model

The Liquid Alloy Navigation Spine is a real `tablist` limited to the three OES-owned products. Click, touch, Enter/Space and arrow keys select a product. The selected system becomes the foreground surface while the discipline panel changes to documented shared OES disciplines. Native `details` exposes the development and technical dossier without hover dependence. Drinks With Friendz occupies a visibly separate client-delivery bay with an explicit ownership plate.

The connected-system map is deliberately constrained: it visualizes disciplines supported by each existing product description, not data exchange, customer deployments or product integrations.

## Layer system

1. **Foundation:** fixed graphite atmosphere, sparse engineering mesh and large alloy contours.
2. **Structure:** masthead, spine, system lines and relationship map.
3. **Elevated content:** physically separated product, public-sector, community and research surfaces using directional shadows and edge highlights.
4. **Controls:** product tabs, dossier disclosures, mobile navigation, calls to action and the showroom switcher.

## Concept C comparison

Concept C uses a disciplined flat command matrix. Concept D retains its systems-thinking and technical typography, then adds a materially different spatial language: irregular machined contours, a vertical/horizontal adaptive product spine, one focused product surface instead of repeated records, directional elevation, satin metal, optical reflections and a warmer Detroit manufacturing accent. It is not a recolor of Concept C.

## Local preview

The original showroom may remain on port 5000. From the Liquid Alloy worktree, launch a second loopback-only process on an available port with debug, workers and analytics disabled, then open:

`/static/design-exploration/motor-city/concept-d/index.html`

No production navigation or runtime route points to Concept D.

## Current review captures

- `docs/design-previews/liquid-alloy/concept-d-v2-desktop.png` — 1440 × 1000 desktop hero and navigation.
- `docs/design-previews/liquid-alloy/concept-d-v2-mobile-500.png` — 500 × 844 compact/mobile hero with the responsive menu and controls.

These captures show the revised ownership navigation and visual direction. They do
not represent owner acceptance of the final website or a completed 3D character.

## Known limitations and owner questions

- The prototype uses installed system typography (`Bahnschrift`, Segoe UI and Consolas) rather than adding a webfont dependency.
- Eyeball placement is interactive only as a truthful integration note; it does not open production chat. Blender and CMake are not installed on the validated Windows node, and no approved `.blend`/glTF asset exists, so the dock intentionally shows an asset gate rather than fake finished 3D artwork.
- Product history has no verified dated milestones in the source site. The dossier preserves documented current state and features rather than inventing a timeline.
- Formal assistive-technology testing with a screen reader remains an owner-selection follow-up.
- Owner selection is needed on the balance between the sculptural hero object and product-first content density before production-template work.
