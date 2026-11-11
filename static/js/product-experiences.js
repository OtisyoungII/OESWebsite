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
    freemium: '<div class="membership-demo__summary"><b>Six daily prediction lanes</b><span>Midday and evening · 3D, 4D and 5D</span></div><ul><li>Regular daily predictions</li><li>Favorites, with sign-in for syncing</li><li>Recorded results and number exploration</li></ul>',
    premium: '<div class="membership-demo__summary"><b>Expanded prediction workspace</b><span>Platform Picks, Easy Picks and performance tools</span></div><ul><li>Additional analytics and performance cards</li><li>XP, tokens and eligible rewards activity</li><li>Community activity and leaderboards</li></ul>',
});

const chaseMarketStates = Object.freeze({
    "1D": Object.freeze({ state: "Constructive", pressure: "Balanced", risk: "Defined" }),
    "1W": Object.freeze({ state: "Range holding", pressure: "Cooling", risk: "Watch support" }),
    "1M": Object.freeze({ state: "Trend positive", pressure: "Mixed", risk: "Plan exposure" }),
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
        demo.classList.remove("is-number-reacting");
        void demo.offsetWidth;
        demo.classList.add("is-number-reacting");
        window.setTimeout(() => demo.classList.remove("is-number-reacting"), 720);
    }
    if (demo.dataset.productDemo === "chaseingreen") {
        const state = chaseMarketStates[button.dataset.demoChoice];
        if (!state) return;
        demo.querySelector("[data-market-state]").textContent = state.state;
        demo.querySelector("[data-market-pressure]").textContent = state.pressure;
        demo.querySelector("[data-market-risk]").textContent = state.risk;
        const display = demo.querySelector("[data-market-display]");
        display?.classList.remove("is-refreshing");
        void display?.offsetWidth;
        display?.classList.add("is-refreshing");
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
