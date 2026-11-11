import { oesContent } from "../shared/content.js";

const APP_STORE_URL = "https://apps.apple.com/us/app/chaseingreen/id6770096789";
const configuredSportfolioUrl = document.body.dataset.sportfolioUrl || "";
const SPORTFOLIO_URL = (() => {
  try {
    const url = new URL(configuredSportfolioUrl);
    return url.protocol === "https:" ? url.href : "https://sportfolio-api-ktd5.onrender.com/";
  } catch {
    return "https://sportfolio-api-ktd5.onrender.com/";
  }
})();
const baseProducts = oesContent.products.map((product) => ({ ...product, features: [...product.features], actions: product.actions.map((action) => ({ ...action })) }));
const chase = baseProducts.find((product) => product.id === "chaseingreen");
chase.status = "Live on the App Store";
chase.description = "See market context, plan risk and keep a clearer record of your decisions—all in one trading companion. ChaseInGreen is not a brokerage, exchange, wallet or financial institution.";
chase.actions = [
  { label: "Get ChaseINGreen on the App Store", href: APP_STORE_URL, primary: true },
  { label: "Join ChaseInGreen Discord", href: "https://discord.gg/YjKFkdnj3" },
  { label: "ChaseInGreen Privacy Policy", href: "/privacy" },
];
chase.note = "Trading involves risk. ChaseInGreen supports research and planning; it does not guarantee outcomes.";

const sportfolio = baseProducts.find((product) => product.id === "sportfolio");
sportfolio.actions = [
  { label: "Try Sportfolio Web", href: SPORTFOLIO_URL, primary: true },
  { label: "iOS TestFlight — Coming Soon", disabled: true },
];

const lottovate = baseProducts.find((product) => product.id === "lottovate");
lottovate.status = "Public TestFlight";
const drinks = baseProducts.find((product) => product.id === "drinkswithfriendz");
drinks.status = "Public TestFlight Beta";

const products = baseProducts.filter((product) => product.id !== "drinkswithfriendz");
const clientProjects = [drinks];

const disciplines = ["Artificial intelligence", "Native mobile", "Web platforms", "Data systems", "Trading technology", "Sports technology", "Location services", "Public interface"];
const productDisciplines = {
  chaseingreen: ["Artificial intelligence", "Data systems", "Trading technology"],
  lottovate: ["Artificial intelligence", "Native mobile", "Data systems"],
  sportfolio: ["Native mobile", "Web platforms", "Data systems", "Sports technology"],
};

const escapeHtml = (value) => String(value).replace(/[&<>"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
const external = (href = "") => href.startsWith("http") ? ' target="_blank" rel="noopener noreferrer"' : "";
const analyticsAttributes = (action, product) => {
  if (!action.href || !product) return "";
  const event = action.href.includes("testflight.apple.com") ? "testflight_link_activated"
    : action.href === SPORTFOLIO_URL ? "web_app_link_activated"
      : action.href.startsWith("mailto:") ? "contact_action_activated"
        : action.href.startsWith("http") ? "external_product_link_activated" : "";
  return event ? ` data-product-event="${event}" data-product-target="${escapeHtml(product.id)}"` : "";
};
const actionMarkup = (action, product) => action.disabled
  ? `<span class="alloy-button" aria-disabled="true">${escapeHtml(action.label)}</span>`
  : `<a class="alloy-button${action.primary ? " alloy-button--solid" : ""}" href="${escapeHtml(action.href)}"${external(action.href)}${analyticsAttributes(action, product)}>${escapeHtml(action.label)}</a>`;

const experienceMarkup = (product) => {
  const demos = {
    chaseingreen: `<section class="product-demo product-demo--chase" data-product-demo="chaseingreen" aria-labelledby="demo-chase-title">
      <div class="chase-brand"><img src="/static/images/chaseingreen/chaseingreen-bull-bear-sculpted.webp" alt="Sculpted gold bull and bear emblem for ChaseInGreen" width="768" height="768" loading="lazy" decoding="async"><div class="product-demo__heading"><span>Illustrative market workspace</span><strong id="demo-chase-title">Read context, plan risk.</strong><small>Explore how timeframe, pressure and risk context can support a trading plan.</small></div></div>
      <div class="market-display" data-market-display>
        <div class="market-display__toolbar"><span>MARKET CONTEXT · DEMONSTRATION</span><span class="market-display__status">Illustrative data</span></div>
        <svg viewBox="0 0 600 240" preserveAspectRatio="none" role="img" aria-label="Illustrative market trend rising unevenly across the selected timeframe"><defs><linearGradient id="chase-chart-gradient" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#38bdf8"></stop><stop offset="55%" stop-color="#22c55e"></stop><stop offset="100%" stop-color="#f4c66a"></stop></linearGradient></defs><polyline class="market-display__glow" points="0,190 45,180 85,197 130,135 170,151 225,92 275,122 330,69 380,91 432,45 485,70 540,28 600,42"></polyline><polyline class="market-display__line" points="0,190 45,180 85,197 130,135 170,151 225,92 275,122 330,69 380,91 432,45 485,70 540,28 600,42" stroke="url(#chase-chart-gradient)"></polyline></svg>
        <div class="market-display__metrics"><span>Market state<strong data-market-state>Constructive</strong></span><span>Pressure<strong data-market-pressure>Balanced</strong></span><span>Risk context<strong data-market-risk>Defined</strong></span></div>
      </div>
      <div class="demo-tabs" role="group" aria-label="Illustrative market timeframe"><button type="button" data-demo-choice="1D" aria-pressed="true">1D</button><button type="button" data-demo-choice="1W" aria-pressed="false">1W</button><button type="button" data-demo-choice="1M" aria-pressed="false">1M</button></div>
      <div class="demo-readout" aria-live="polite"><span>Context summary</span><strong data-demo-output>1D · Constructive, mixed confirmation</strong></div>
      <div class="tier-boundary"><span><b>Free</b> Essential market context and planning tools.</span><span><b>Gold</b> Expanded AI market tools, additional alerts and deeper analytics.</span></div>
      <small>Demonstration only. Values are illustrative—not live market data and not financial advice.</small>
    </section>`,
    lottovate: `<section class="product-demo membership-demo product-demo--lottovate" data-product-demo="lottovate" aria-labelledby="demo-lotto-title">
      <div class="product-identity product-identity--lottovate"><img src="/static/images/lottovate/lottovate-icon.png" alt="Lottovate app icon" width="1024" height="1024" loading="lazy" decoding="async"><div class="product-demo__heading"><span>Lottery analysis workspace</span><strong id="demo-lotto-title">Organize picks. Explore recorded results.</strong><small>Use prediction-assistance tools without treating any number as a promise.</small></div></div>
      <div class="lottery-display" aria-label="Decorative lottery balls moving through an illustrative scan"><div class="lottery-display__grid" aria-hidden="true"></div><div class="lottery-ball lottery-ball--one" aria-hidden="true">7</div><div class="lottery-ball lottery-ball--two" aria-hidden="true">0</div><div class="lottery-ball lottery-ball--three" aria-hidden="true">3</div><div class="lottery-ball lottery-ball--four" aria-hidden="true">9</div><div class="lottery-display__scan" aria-hidden="true"></div><p class="lottery-display__status">ILLUSTRATIVE NUMBER EXPLORATION · ACTIVE TESTFLIGHT</p></div>
      <div class="demo-tabs" role="group" aria-label="Lottovate membership level"><button type="button" data-demo-choice="freemium" aria-pressed="true">Freemium</button><button type="button" data-demo-choice="premium" aria-pressed="false">Premium</button></div>
      <div class="membership-demo__panel" data-membership-panel><div class="membership-demo__summary"><b>Six daily prediction lanes</b><span>Midday and evening · 3D, 4D and 5D</span></div><ul><li>Regular daily predictions</li><li>Favorites, with sign-in for syncing</li><li>Recorded results and number exploration</li></ul></div><p class="demo-readout" data-demo-output aria-live="polite">Start with daily regular predictions and keep favorite numbers together.</p><small>Predictions and historical patterns do not guarantee future results.</small>
    </section>`,
    sportfolio: `<section class="product-demo product-demo--sportfolio" data-product-demo="sportfolio" aria-labelledby="demo-sport-title">
      <div class="product-identity product-identity--sportfolio"><img src="/static/images/sportfolio/sportfolio-approved-master.webp" alt="Sportfolio approved artwork featuring its full athlete and stadium composition" width="1254" height="1254" loading="lazy" decoding="async"><div class="product-demo__heading"><span>Baseball field test</span><strong id="demo-sport-title">Record, compare and verify the game.</strong><small>The first live implementation connects game state to a persistent athlete record.</small></div></div>
      <div class="sportfolio-display" aria-label="Illustrative baseball scoreboard showing Detroit leading the visitors four to three in the top of the seventh inning"><div class="sportfolio-display__header"><span>FIELD TEST</span><strong>BASEBALL · LIVE WORKFLOW</strong></div><div class="sportfolio-display__score"><span class="sportfolio-display__team">DET</span><strong>4</strong><span class="sportfolio-display__inning">TOP 7</span><strong>3</strong><span class="sportfolio-display__team">VIS</span></div><div class="sportfolio-display__diamond" aria-label="Runners shown on first, second and third base"><span></span><span></span><span></span></div><div class="sportfolio-display__metrics"><span>Pitch count<strong>72</strong></span><span>Lineup<strong>Verified</strong></span><span>Game record<strong>Auditable</strong></span></div></div>
      <ol class="play-pipeline"><li class="is-current"><b>01</b><span>Play recorded<small>Single to center</small></span></li><li><b>02</b><span>Sources compared<small>Team scorer · official</small></span></li><li><b>03</b><span>Record updated<small>History retained</small></span></li></ol><button class="demo-advance" type="button" data-demo-advance>Advance illustrative play</button><p class="demo-readout" data-demo-output aria-live="polite">The observation enters the event record with its source attached.</p>
    </section>`,
  };
  return demos[product.id] || "";
};

const spine = document.querySelector("[data-product-spine]");
const stage = document.querySelector("[data-product-stage]");
const disciplineMap = document.querySelector("[data-discipline-map]");
let activeIndex = 0;

function renderSpine() {
  spine.innerHTML = products.map((product, index) => `
    <button class="spine__button" type="button" role="tab" id="product-tab-${escapeHtml(product.id)}" aria-controls="product-panel-${escapeHtml(product.id)}" aria-selected="${index === activeIndex}" tabindex="${index === activeIndex ? 0 : -1}" data-product-index="${index}" data-product-event="product_card_activated" data-product-target="${escapeHtml(product.id)}">
      <span class="spine__number">${String(index + 1).padStart(2, "0")}</span><span>${escapeHtml(product.name)}<small>${escapeHtml(product.status)}</small></span>
    </button>`).join("");
}

function renderDisciplines(product) {
  const active = new Set(productDisciplines[product.id] || []);
  disciplineMap.innerHTML = disciplines.map((name) => `<span class="discipline${active.has(name) ? " is-active" : ""}">${escapeHtml(name)}</span>`).join("");
}

function renderProduct({ focus = false } = {}) {
  const product = products[activeIndex];
  const isChase = product.id === "chaseingreen";
  stage.innerHTML = `<article class="product-focus" data-product="${escapeHtml(product.id)}" role="tabpanel" id="product-panel-${escapeHtml(product.id)}" aria-labelledby="product-tab-${escapeHtml(product.id)}" tabindex="0">
    <div class="product-focus__topline"><span class="product-focus__category">${escapeHtml(product.category)}</span><span class="status-pill"><span class="signal"></span>${escapeHtml(product.status)}</span></div>
    <h3>${escapeHtml(product.name)}</h3>${product.tagline ? `<p class="product-focus__tagline">${escapeHtml(product.tagline)}</p>` : ""}
    <p class="product-focus__description">${escapeHtml(product.description)}</p>
    ${experienceMarkup(product)}
    <div class="product-focus__actions">${product.actions.map((action) => actionMarkup(action, product)).join("")}</div>
    <details class="dossier" ${new URLSearchParams(location.search).get("details") === "1" ? "open" : ""}>
      <summary><span><span class="dossier-label">See how it works</span><br>Features and availability</span></summary>
      <div class="dossier__body"><p><strong>Available now:</strong> ${escapeHtml(product.status)}.</p><ul>${product.features.map((feature) => `<li>${escapeHtml(feature)}</li>`).join("")}</ul></div>
    </details>
    ${product.note ? `<p class="product-focus__note">${escapeHtml(product.note)}</p>` : ""}
    ${isChase ? `<p class="product-focus__note"><strong>Available on the Apple App Store.</strong></p>` : ""}
  </article>`;
  renderDisciplines(product);
  renderSpine();
  const url = new URL(location.href);
  url.searchParams.set("product", product.id);
  history.replaceState({}, "", url);
  if (focus) stage.querySelector(".product-focus")?.focus();
}

function selectProduct(index, { focus = false } = {}) {
  activeIndex = Math.max(0, Math.min(products.length - 1, index));
  renderProduct({ focus });
}

const requestedProduct = new URLSearchParams(location.search).get("product");
const requestedIndex = products.findIndex((product) => product.id === requestedProduct);
if (requestedIndex >= 0) activeIndex = requestedIndex;
renderProduct();

spine.addEventListener("click", (event) => {
  const button = event.target.closest("[data-product-index]");
  if (button) selectProduct(Number(button.dataset.productIndex), { focus: false });
});
spine.addEventListener("keydown", (event) => {
  const button = event.target.closest("[data-product-index]");
  if (!button) return;
  const current = Number(button.dataset.productIndex);
  const keys = { ArrowDown: current + 1, ArrowRight: current + 1, ArrowUp: current - 1, ArrowLeft: current - 1, Home: 0, End: products.length - 1 };
  if (!(event.key in keys)) return;
  event.preventDefault();
  selectProduct((keys[event.key] + products.length) % products.length);
  spine.querySelector(`[data-product-index="${activeIndex}"]`)?.focus();
});

document.querySelector("[data-services]").innerHTML = oesContent.services.map(([title, text], index) => `<article class="service-ribbon"><span class="service-ribbon__number">${String(index + 1).padStart(2, "0")}</span><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></article>`).join("");
const dwfLogoMarkup = document.querySelector("#dwf-logo-template")?.innerHTML || "";
document.querySelector("[data-client-work]").innerHTML = clientProjects.map((project, index) => `<article class="client-project" data-product="${escapeHtml(project.id)}">
  <div class="client-project__rail"><span>${String(index + 1).padStart(2, "0")}</span><span>IPHONE APP</span></div>
  <div class="client-project__body"><div class="product-focus__topline"><span class="product-focus__category">${escapeHtml(project.category)}</span><span class="status-pill"><span class="signal"></span>${escapeHtml(project.status)}</span></div>
  <div class="client-brand-story"><div class="client-brand-story__visual" id="dwf-logo-showcase">${dwfLogoMarkup}</div><div class="client-brand-story__copy"><h3>${escapeHtml(project.name)}</h3><p>${escapeHtml(project.description)}</p><p class="client-brand-story__note">Discover nearby places, compare useful venue details and continue from the map to directions or contact options.</p></div></div><section class="product-demo product-demo--journey" data-product-demo="drinkswithfriendz" aria-label="Illustrative venue discovery journey"><div class="product-demo__heading"><span>Venue journey demonstration</span><strong>From an area to the next stop.</strong></div><ol class="venue-journey"><li class="is-current"><b>01</b><span>Choose an area</span></li><li><b>02</b><span>Explore nearby venues</span></li><li><b>03</b><span>Open details</span></li><li><b>04</b><span>Get directions</span></li></ol><button class="demo-advance" type="button" data-demo-advance>Walk through the experience</button><p class="demo-readout" data-demo-output aria-live="polite">Start with an authorized location or a place the user chooses.</p></section><div class="product-focus__actions">${project.actions.map((action) => actionMarkup(action, project)).join("")}</div>
  <details class="dossier"><summary><span><span class="dossier-label">What OES delivered</span><br>See the app features</span></summary><div class="dossier__body"><ul>${project.features.map((feature) => `<li>${escapeHtml(feature)}</li>`).join("")}</ul></div></details></div>
  <aside class="client-project__ownership"><span>CLIENT WORK</span><strong>Built for Drinks With Friendz</strong><p>OES designed and developed this iPhone experience for a client-owned brand.</p></aside>
</article>`).join("");
document.querySelector("[data-government-intro]").innerHTML = oesContent.government.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
document.querySelector("[data-government-capabilities]").innerHTML = oesContent.government.capabilities.map(([title, text]) => `<article class="vault-panel"><p class="eyebrow">What OES builds</p><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></article>`).join("");
document.querySelector("[data-community]").innerHTML = oesContent.community.map((item) => `<article class="detroit-node"><p class="detroit-node__type">${escapeHtml(item.type)}</p><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.text)}${item.detail ? ` ${escapeHtml(item.detail)}` : ""}</p>${item.links ? item.links.map(([label, href]) => `<a class="text-link" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`).join("") : ""}</article>`).join("");
document.querySelector("[data-research-intro]").innerHTML = oesContent.research.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
document.querySelector("[data-research-lines]").innerHTML = oesContent.research.lines.map(([status, name]) => `<div class="research-line"><strong>${escapeHtml(status)}</strong><span>${escapeHtml(name)}</span></div>`).join("");
document.querySelector("[data-about]").innerHTML = oesContent.about.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
document.querySelector("[data-contact-copy]").textContent = oesContent.contact.text;

const menu = document.querySelector("[data-menu]");
menu.addEventListener("click", () => {
  const open = menu.getAttribute("aria-expanded") !== "true";
  menu.setAttribute("aria-expanded", String(open));
  document.querySelector("[data-nav]").classList.toggle("is-open", open);
});
document.querySelector("[data-nav]").addEventListener("click", () => {
  menu.setAttribute("aria-expanded", "false");
  document.querySelector("[data-nav]").classList.remove("is-open");
});
