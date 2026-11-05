import { oesContent } from "../shared/content.js";

const APP_STORE_URL = "https://apps.apple.com/us/app/chaseingreen/id6770096789";
const SPORTFOLIO_URL = "https://sportfolio-api-ktd5.onrender.com/";
const baseProducts = oesContent.products.map((product) => ({ ...product, features: [...product.features], actions: product.actions.map((action) => ({ ...action })) }));
const chase = baseProducts.find((product) => product.id === "chaseingreen");
chase.status = "Live on the App Store";
chase.description = "ChaseInGreen is an OES-built trading companion now live on the Apple App Store. It brings market context, planning, risk tools, journaling and trader workspace features together without acting as a brokerage, exchange, wallet or financial institution.";
chase.actions = [
  { label: "Get ChaseINGreen on the App Store", href: APP_STORE_URL, primary: true },
  { label: "Join ChaseInGreen Discord", href: "https://discord.gg/YjKFkdnj3" },
  { label: "ChaseInGreen Privacy Policy", href: "/privacy" },
];
chase.note = "The App Store listing is the current public release destination. OES does not claim download counts, ratings, rankings or guaranteed trading outcomes.";

const sportfolio = baseProducts.find((product) => product.id === "sportfolio");
sportfolio.actions = [
  { label: "Try Sportfolio Web", href: SPORTFOLIO_URL, primary: true },
  { label: "iOS TestFlight — Coming Soon", disabled: true },
];

const lottovate = baseProducts.find((product) => product.id === "lottovate");
lottovate.status = "Public TestFlight";
const drinks = baseProducts.find((product) => product.id === "drinkswithfriendz");
drinks.status = "Public TestFlight Beta";

const products = [...baseProducts, {
  id: "eyeball", name: "Eyeball / OES Core", category: "Public Intelligence Interface", status: "Public Website Interface",
  description: "Eyeball is represented by the animated OES Core on the public website. It provides a public intelligence interface with an explicit safety notice and localized interface text.",
  features: ["Existing OES website interaction", "Public AI-assistant safety notice", "Localized interface text in English, Spanish, French, Arabic and Simplified Chinese", "Optional product invitations and clarification controls", "Existing runtime remains outside this visual prototype"],
  actions: [{ label: "View the existing OES website", href: "/", primary: true }, { label: "Read OES Privacy Policy", href: "/privacy" }],
  note: "This showroom reserves a place for Eyeball but does not call the chat service, launch the native renderer or claim private access."
}];

const disciplines = ["Artificial intelligence", "Native mobile", "Web platforms", "Data systems", "Trading technology", "Sports technology", "Location services", "Public interface"];
const productDisciplines = {
  chaseingreen: ["Artificial intelligence", "Data systems", "Trading technology"],
  lottovate: ["Artificial intelligence", "Native mobile", "Data systems"],
  sportfolio: ["Native mobile", "Web platforms", "Data systems", "Sports technology"],
  drinkswithfriendz: ["Native mobile", "Location services"],
  eyeball: ["Artificial intelligence", "Web platforms", "Public interface"],
};

const escapeHtml = (value) => String(value).replace(/[&<>"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
const external = (href = "") => href.startsWith("http") ? ' target="_blank" rel="noopener noreferrer"' : "";
const actionMarkup = (action) => action.disabled
  ? `<span class="alloy-button" aria-disabled="true">${escapeHtml(action.label)}</span>`
  : `<a class="alloy-button${action.primary ? " alloy-button--solid" : ""}" href="${escapeHtml(action.href)}"${external(action.href)}>${escapeHtml(action.label)}</a>`;

const spine = document.querySelector("[data-product-spine]");
const stage = document.querySelector("[data-product-stage]");
const disciplineMap = document.querySelector("[data-discipline-map]");
let activeIndex = 0;

function renderSpine() {
  spine.innerHTML = products.map((product, index) => `
    <button class="spine__button" type="button" role="tab" id="product-tab-${escapeHtml(product.id)}" aria-controls="product-panel-${escapeHtml(product.id)}" aria-selected="${index === activeIndex}" tabindex="${index === activeIndex ? 0 : -1}" data-product-index="${index}">
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
  stage.innerHTML = `<article class="product-focus" role="tabpanel" id="product-panel-${escapeHtml(product.id)}" aria-labelledby="product-tab-${escapeHtml(product.id)}" tabindex="0">
    <div class="product-focus__topline"><span class="product-focus__category">${escapeHtml(product.category)}</span><span class="status-pill"><span class="signal"></span>${escapeHtml(product.status)}</span></div>
    <h3>${escapeHtml(product.name)}</h3>${product.tagline ? `<p class="product-focus__tagline">${escapeHtml(product.tagline)}</p>` : ""}
    <p class="product-focus__description">${escapeHtml(product.description)}</p>
    <div class="product-focus__actions">${product.actions.map(actionMarkup).join("")}</div>
    <details class="dossier" ${new URLSearchParams(location.search).get("details") === "1" ? "open" : ""}>
      <summary><span><span class="dossier-label">Development and technical dossier</span><br>Show all documented details</span></summary>
      <div class="dossier__body"><p><strong>Current verified state:</strong> ${escapeHtml(product.status)}.</p><ul>${product.features.map((feature) => `<li>${escapeHtml(feature)}</li>`).join("")}</ul></div>
    </details>
    ${product.note ? `<p class="product-focus__note">${escapeHtml(product.note)}</p>` : ""}
    ${isChase ? `<p class="product-focus__note"><strong>Official release destination:</strong> Apple App Store product ID 6770096789.</p>` : ""}
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
document.querySelector("[data-government-intro]").innerHTML = oesContent.government.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
document.querySelector("[data-government-capabilities]").innerHTML = oesContent.government.capabilities.map(([title, text]) => `<article class="vault-panel"><p class="eyebrow">Verified capability</p><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></article>`).join("");
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

const eyeballButton = document.querySelector("[data-eyeball-preview]");
const eyeballNote = document.querySelector("#eyeball-note");
eyeballButton.addEventListener("click", () => {
  const open = eyeballButton.getAttribute("aria-expanded") !== "true";
  eyeballButton.setAttribute("aria-expanded", String(open));
  eyeballNote.hidden = !open;
});
