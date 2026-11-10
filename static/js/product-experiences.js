const copy = Object.freeze({
    chaseingreen: Object.freeze({
        "1D": "1D · Constructive, mixed confirmation",
        "1W": "1W · Range holding, momentum cooling",
        "1M": "1M · Trend positive, risk still matters",
    }),
    lottovate: Object.freeze({
        freemium: "Start with daily regular predictions and keep favorite numbers together.",
        premium: "Open more prediction tools, accuracy trends, rewards and community leaderboards.",
    }),
});

const lottovatePanels = Object.freeze({
    freemium: '<div class="membership-demo__summary"><b>Four daily prediction lanes</b><span>Midday and evening · 3D and 4D</span></div><ul><li>Regular predictions</li><li>Favorites, with sign-in for syncing</li><li>Historical results and number analysis</li></ul>',
    premium: '<div class="membership-demo__summary"><b>Expanded prediction workspace</b><span>Up to 6 tickets per platform input · up to 12 Easy Picks</span></div><ul><li>Accuracy trends displayed as percentages from recorded results</li><li>XP and tokens returned by eligible play activity</li><li>Shared-favorites feed and wins, tokens and weekly leaderboards</li></ul>',
});

const journeys = Object.freeze({
    sportfolio: Object.freeze([
        "The observation enters the event record with its source attached.",
        "Independent sources can agree—or preserve a discrepancy for review.",
        "A verified result updates the player record without erasing its history.",
    ]),
    drinkswithfriendz: Object.freeze([
        "Start with an authorized location or a place the user chooses.",
        "Browse nearby venues on an interactive map.",
        "Review venue details, photos, ratings and hours where available.",
        "Continue to directions or contact options.",
    ]),
});

function setPressed(group, selected) {
    group.querySelectorAll("[data-demo-choice]").forEach((button) => {
        button.setAttribute("aria-pressed", String(button === selected));
    });
}

function handleChoice(button) {
    const demo = button.closest("[data-product-demo]");
    const values = copy[demo?.dataset.productDemo];
    if (!demo || !values || !(button.dataset.demoChoice in values)) return;
    setPressed(demo, button);
    const output = demo.querySelector("[data-demo-output]");
    if (output) output.textContent = values[button.dataset.demoChoice];
    if (demo.dataset.productDemo === "lottovate") {
        const panel = demo.querySelector("[data-membership-panel]");
        if (panel) panel.innerHTML = lottovatePanels[button.dataset.demoChoice];
    }
}

function handleAdvance(button) {
    const demo = button.closest("[data-product-demo]");
    const steps = demo?.querySelectorAll("ol li");
    const messages = journeys[demo?.dataset.productDemo];
    if (!demo || !steps?.length || !messages) return;
    const current = [...steps].findIndex((step) => step.classList.contains("is-current"));
    const next = (current + 1) % steps.length;
    steps.forEach((step, index) => step.classList.toggle("is-current", index === next));
    const output = demo.querySelector("[data-demo-output]");
    if (output) output.textContent = messages[next];
}

export function initializeProductExperiences(root = document) {
    root.addEventListener("click", (event) => {
        const choice = event.target.closest("[data-demo-choice]");
        if (choice) handleChoice(choice);
        const advance = event.target.closest("[data-demo-advance]");
        if (advance) handleAdvance(advance);
    });
}
