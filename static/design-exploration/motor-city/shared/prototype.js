import { oesContent as c } from "./content.js";

const root = document.querySelector("[data-prototype]");
const concept = root?.dataset.concept || "a";
const external = (href) => href?.startsWith("http") ? ' target="_blank" rel="noopener noreferrer"' : "";
const actions = (items = []) => items.map((item) => item.disabled
  ? `<span class="action is-disabled" aria-disabled="true">${item.label}</span>`
  : `<a class="action" href="${item.href}"${external(item.href)}>${item.label}</a>`).join("");
const product = (p, index) => `
  <article class="product product--${p.id}" id="product-${p.id}">
    <div class="product__index" aria-hidden="true">0${index + 1}</div>
    <div class="product__summary">
      <p class="kicker">${p.category}</p><h3>${p.name}</h3>
      <p class="status"><span></span>${p.status}</p>${p.tagline ? `<p class="tagline">${p.tagline}</p>` : ""}
    </div>
    <details class="product__detail" ${index === 0 ? "open" : ""}>
      <summary>Explore verified product details</summary>
      <div class="detail-body"><p>${p.description}</p>
        <ul>${p.features.map((f) => `<li>${f}</li>`).join("")}</ul>
        <div class="actions">${actions(p.actions)}</div>${p.note ? `<p class="note">${p.note}</p>` : ""}
      </div>
    </details>
  </article>`;
const card = (title, text, extra = "") => `<article class="info-card"><h3>${title}</h3><p>${text}</p>${extra}</article>`;

root.innerHTML = `
  <a class="skip-link" href="#main">Skip to main content</a>
  <header class="site-head">
    <a class="brand" href="#top"><img src="/static/images/oes-logo.svg" alt=""><span><strong>OTIS EXECUTION SYSTEMS</strong><small>DETROIT, MICHIGAN</small></span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav" aria-label="Prototype navigation"><a href="#products">Products</a><a href="#capabilities">Capabilities</a><a href="#public-sector">Public sector</a><a href="#detroit">Detroit</a><a href="#research">Research</a><a href="#contact">Contact</a></nav>
  </header>
  <main id="main">
    <section class="hero" id="top"><div class="hero__grid" aria-hidden="true"></div><div class="hero__copy">
      <p class="kicker">${c.identity.heroEyebrow}</p><h1>${c.identity.heroTitle}</h1><p class="lede">${c.identity.heroIntroduction}</p><p>${c.identity.heroBelief}</p>
      <div class="actions"><a class="action action--primary" href="#products">Explore the OES ecosystem</a><a class="action" href="#contact">Build with OES</a></div>
    </div><button class="eyeball" type="button" aria-expanded="false" aria-controls="eyeball-panel"><img src="/static/images/oes-logo.svg" alt=""><span>Ask Eyeball</span></button></section>
    <aside class="eyeball-panel" id="eyeball-panel" hidden><button type="button" data-close-eyeball>Close</button><p class="kicker">OES EYEBALL</p><h2>Intelligence stays in the experience.</h2><p>This concept preserves the existing Eyeball chat trigger and runtime. The design preview does not call the production chat service.</p></aside>
    <section class="section products" id="products"><header class="section__head"><p class="kicker">OES Product Ecosystem</p><h2>Built to help people recognize, decide and execute.</h2><p>OES designs, builds and tests real software systems: a trading companion, a lottery assistant, a multi-sport platform and client applications moving toward public release.</p></header><div class="product-stage">${c.products.map(product).join("")}</div></section>
    <section class="section capabilities" id="capabilities"><header class="section__head"><p class="kicker">Build With OES</p><h2>From an unfinished idea to a working platform.</h2><p>OES delivers native iOS apps, backend APIs, integrations, data systems, dashboards and automation for entrepreneurs, organizations, agencies and growing businesses.</p></header><div class="card-grid">${c.services.map(([a,b], i) => card(`${String(i+1).padStart(2,"0")} · ${a}`, b)).join("")}</div></section>
    <section class="section government" id="public-sector"><div class="registration"><p class="kicker">${c.government.status}</p><strong>SAM.gov: Active</strong><span>Unique Entity ID: ${c.government.uei}</span><span>CAGE Code: ${c.government.cage}</span><p>${c.government.note}</p></div><header class="section__head"><p class="kicker">Government and Public Sector</p><h2>${c.government.title}</h2>${c.government.paragraphs.map(p=>`<p>${p}</p>`).join("")}</header><div class="card-grid">${c.government.capabilities.map(([a,b])=>card(a,b)).join("")}</div><a class="action" href="#contact">Discuss public-sector work</a></section>
    <section class="section detroit" id="detroit"><header class="section__head"><p class="kicker">Detroit Is Part of the System</p><h2>Technology grows when more people can participate.</h2><p>OES is shaped by Detroit technology education, entrepreneurship, community service, youth mentorship and organizations creating more pathways into the future.</p></header><div class="community-track">${c.community.map((x)=>card(x.name, `${x.text}${x.detail ? ` ${x.detail}` : ""}`, `<p class="kicker">${x.type}</p>${x.links ? `<div class="actions">${x.links.map(([l,h])=>`<a class="text-link" href="${h}" target="_blank" rel="noopener noreferrer">${l}</a>`).join("")}</div>` : ""}`)).join("")}</div></section>
    <section class="section research" id="research"><header class="section__head"><p class="kicker">OES Research Lab</p><h2>${c.research.title}</h2>${c.research.paragraphs.map(p=>`<p>${p}</p>`).join("")}</header><div class="research-list">${c.research.lines.map(([s,n])=>`<div><strong>${s}</strong><span>${n}</span></div>`).join("")}</div></section>
    <section class="section about" id="about"><img src="/static/images/oes-logo.svg" alt="Otis Execution Systems logo"><div><p class="kicker">About OES</p><h2>${c.about.title}</h2>${c.about.paragraphs.map(p=>`<p>${p}</p>`).join("")}</div></section>
    <section class="section contact" id="contact"><div><p class="kicker">Start the Conversation</p><h2>${c.contact.title}</h2><p>${c.contact.text}</p></div><div class="actions"><a class="action action--primary" href="mailto:${c.contact.email}">Start a project conversation</a><a class="action" href="https://testflight.apple.com/join/nPjjyDSf" target="_blank" rel="noopener noreferrer">Test ChaseInGreen on TestFlight</a></div></section>
  </main>
  <footer><a class="brand" href="#top"><img src="/static/images/oes-logo.svg" alt="Otis Execution Systems logo"><span><strong>${c.identity.name}</strong><small>${c.identity.tagline}</small></span></a><nav aria-label="Legal"><a href="/privacy">Privacy Policy</a><a href="/drinks-with-friendz/privacy">Drinks With Friendz Privacy</a></nav><p>© 2026 Otis Execution Systems LLC. All rights reserved.</p><p>Detroit built. Future focused.</p></footer>`;

document.title = `${c.identity.name} — Concept ${concept.toUpperCase()}`;
const toggle = document.querySelector(".nav-toggle");
toggle?.addEventListener("click", () => { const open = toggle.getAttribute("aria-expanded") !== "true"; toggle.setAttribute("aria-expanded", String(open)); document.querySelector("#nav")?.classList.toggle("is-open", open); });
const eye = document.querySelector(".eyeball");
const panel = document.querySelector("#eyeball-panel");
const setEye = (open) => { eye?.setAttribute("aria-expanded", String(open)); if (panel) panel.hidden = !open; if (open) panel?.querySelector("button")?.focus(); else eye?.focus(); };
eye?.addEventListener("click", () => setEye(true));
panel?.querySelector("[data-close-eyeball]")?.addEventListener("click", () => setEye(false));
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && panel && !panel.hidden) setEye(false); });
