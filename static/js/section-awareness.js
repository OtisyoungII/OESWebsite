/*
===============================================================================
FILE: static/js/section-awareness.js

PURPOSE:
    Gives the Otis Execution Systems website awareness of what the visitor is
    viewing, hovering, focusing on, and repeatedly exploring.

UPDATED:
    July 15, 2026

RESPONSIBILITIES:
    [x] Detect the currently visible homepage section
    [x] Detect focused and hovered cards, links, and content
    [x] Update the OES Core message based on visitor attention
    [x] Change page-level awareness classes
    [x] Track repeated interest without storing personal information
    [x] Suggest relevant actions after meaningful engagement
    [x] Dispatch reusable OES awareness events
    [x] Support mouse, keyboard, touch, and reduced-motion users
    [x] Avoid interfering with normal navigation
    [x] Reset temporary reactions safely

PRIVACY:
    [x] No cookies
    [x] No local storage
    [x] No external analytics
    [x] No personally identifiable information
    [x] Interest tracking exists only during the current page visit

CUSTOM EVENTS:
    oes:sectionchange

    detail:
        {
            sectionId,
            sectionElement,
            message,
            accent,
            visitCount
        }

    oes:interestchange

    detail:
        {
            interest,
            element,
            message,
            accent,
            interactionCount
        }

    oes:coremessage

    detail:
        {
            message,
            source,
            accent,
            priority,
            duration
        }

    oes:awarenessreset

IMPORTANT SELECTORS:
    [data-oes-core-stage]
    [data-core-message]
    [data-awareness]
    [data-product]
    .section
    .service-card
    .capability-card
    .community-card
    .client-spotlight
    .research-line

IMPORTANT RULES:
    [x] This module must not directly control OES Core movement
    [x] OES Core movement remains inside oes-core.js
    [x] This module communicates through classes, CSS variables, and events
    [x] Missing optional elements must never break the page
    [x] Repeated hover events must not create message flicker
===============================================================================
*/

/* ==========================================================================
   CONFIGURATION
============================================================================ */

const SECTION_CONFIG = {
    home: {
        message: "OES systems online. Detroit is building.",
        accent: "blue"
    },

    products: {
        message: "Two OES products. Different problems. One execution system.",
        accent: "green"
    },

    "client-work": {
        message: "Client development mode. Real businesses. Working software.",
        accent: "pink"
    },

    services: {
        message: "Choose a capability. OES can help define, build, test and launch it.",
        accent: "blue"
    },

    government: {
        message: "Public-sector capabilities loaded.",
        accent: "government"
    },

    community: {
        message: "Detroit technology, education and community pathways connected.",
        accent: "community"
    },

    research: {
        message: "OES Research Lab active. Exploring what comes next.",
        accent: "purple"
    },

    about: {
        message: "Detroit built. Purpose driven. Execution focused.",
        accent: "blue"
    },

    contact: {
        message: "Ready when you are. Bring OES the idea.",
        accent: "green"
    }
};

const INTEREST_CONFIG = {
    chaseingreen: {
        message: "ChaseInGreen: market awareness, risk control and personal trading intelligence.",
        repeatedMessage: "Trading keeps your attention. Open the ChaseInGreen beta when you are ready.",
        accent: "green"
    },

    lottovate: {
        message: "Lottovate: Daily 3 and Daily 4 data made easier to explore.",
        repeatedMessage: "Watching Lottovate? The next iOS beta is being rebuilt.",
        accent: "yellow"
    },

    client: {
        message: "OES builds native applications for businesses with real growth plans.",
        repeatedMessage: "Planning an app? OES can help turn the idea into a working product.",
        accent: "pink"
    },

    ai: {
        message: "Applied AI should perform a clear job, not exist only as a buzzword.",
        repeatedMessage: "Interested in AI? Start with the problem the system must solve.",
        accent: "purple"
    },

    mobile: {
        message: "Native mobile development: product planning, SwiftUI, testing and launch preparation.",
        repeatedMessage: "Thinking mobile? OES can help define the first version before development begins.",
        accent: "blue"
    },

    web: {
        message: "Web systems can support customers, staff, operations and long-term business growth.",
        repeatedMessage: "A website can be more than a brochure. It can become part of the operation.",
        accent: "blue"
    },

    data: {
        message: "Data becomes valuable when people can understand and act on it.",
        repeatedMessage: "OES can turn raw information into dashboards, patterns and clearer decisions.",
        accent: "green"
    },

    saas: {
        message: "SaaS development connects accounts, product tiers, cloud services and recurring value.",
        repeatedMessage: "Building a platform? Start with the smallest version people will consistently use.",
        accent: "purple"
    },

    automation: {
        message: "Automation should remove repetitive work without hiding important decisions.",
        repeatedMessage: "Repeated manual steps may be a strong opportunity for automation.",
        accent: "green"
    },

    consulting: {
        message: "Strong development begins with scope, architecture and realistic priorities.",
        repeatedMessage: "Before building everything, define what Version 1 must prove.",
        accent: "blue"
    },

    training: {
        message: "OES teaches AI and technology through practical, accessible experiences.",
        repeatedMessage: "Technology confidence grows when people can use the tools for real tasks.",
        accent: "community"
    },

    government: {
        message: "OES supports clearly defined public needs with practical technology.",
        repeatedMessage: "Public-sector interest detected. Focus on the outcome, users and workflow.",
        accent: "government"
    },

    prototype: {
        message: "Prototype development tests whether an idea works before larger investment.",
        repeatedMessage: "A smaller working prototype can reveal more than a larger untested plan.",
        accent: "government"
    },

    academy: {
        message: "Apple Developer Academy: product thinking, Swift development and human-centered design.",
        repeatedMessage: "The Academy helped shape how OES turns human needs into working software.",
        accent: "community"
    },

    techtown: {
        message: "TechTown Detroit connects founders with resources, programs and business support.",
        repeatedMessage: "TechTown events can open doors to Detroit's entrepreneurial ecosystem.",
        accent: "community"
    },

    "black-tech": {
        message: "Black Tech Saturdays expands access, visibility and connection in technology.",
        repeatedMessage: "Detroit technology grows stronger when more builders can participate.",
        accent: "community"
    },

    crossroads: {
        message: "Crossroads of Michigan connects service, community and practical technology support.",
        repeatedMessage: "Technology matters most when it helps people solve real problems.",
        accent: "community"
    },

    mentorship: {
        message: "OES connects technology, athletics, education and life preparation.",
        repeatedMessage: "Discipline learned through sports can create opportunities far beyond the field.",
        accent: "community"
    },

    research: {
        message: "OES research is visible inside its products and interactive systems.",
        repeatedMessage: "You are exploring the lab. These systems connect behavior, prediction and execution.",
        accent: "purple"
    },

    contact: {
        message: "Bring OES the idea. The next step is defining what should be built first.",
        repeatedMessage: "Ready to start? Send the problem, goal and current stage of the idea.",
        accent: "green"
    }
};

const ACCENT_VALUES = {
    blue: {
        primary: "#38bdf8",
        secondary: "#2563eb",
        glow: "rgba(56, 189, 248, 0.52)"
    },

    green: {
        primary: "#22c55e",
        secondary: "#38bdf8",
        glow: "rgba(34, 197, 94, 0.5)"
    },

    yellow: {
        primary: "#facc15",
        secondary: "#a855f7",
        glow: "rgba(250, 204, 21, 0.46)"
    },

    pink: {
        primary: "#ec4899",
        secondary: "#a855f7",
        glow: "rgba(236, 72, 153, 0.46)"
    },

    purple: {
        primary: "#a855f7",
        secondary: "#38bdf8",
        glow: "rgba(168, 85, 247, 0.48)"
    },

    government: {
        primary: "#60a5fa",
        secondary: "#2563eb",
        glow: "rgba(96, 165, 250, 0.48)"
    },

    community: {
        primary: "#34d399",
        secondary: "#f59e0b",
        glow: "rgba(52, 211, 153, 0.44)"
    }
};

const DEFAULT_MESSAGE = "Move. Touch. Explore.";

const MESSAGE_CHANGE_DELAY = 90;
const HOVER_INTENT_DELAY = 180;
const DEFAULT_TEMPORARY_DURATION = 4200;
const REPEATED_INTEREST_THRESHOLD = 3;

/* ==========================================================================
   STATE
============================================================================ */

let initialized = false;

let currentSectionId = "home";
let currentInterest = null;

let messageTimer = null;
let hoverIntentTimer = null;
let temporaryResetTimer = null;
let sectionScrollFrame = null;

const sectionVisits = new Map();
const interestInteractions = new Map();

const observedSections = new Map();

let coreStage = null;
let coreMessage = null;
let pageRoot = null;

/* ==========================================================================
   GENERAL HELPERS
============================================================================ */

function prefersReducedMotion() {
    return window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;
}

function normalizeText(value) {
    return String(value || "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
}

function incrementMapValue(map, key) {
    const nextValue = (map.get(key) || 0) + 1;

    map.set(key, nextValue);

    return nextValue;
}

function clearTimer(timerId) {
    if (timerId) {
        window.clearTimeout(timerId);
    }
}

function escapeAttributeValue(value) {
    if (
        window.CSS &&
        typeof window.CSS.escape === "function"
    ) {
        return window.CSS.escape(value);
    }

    return String(value)
        .replace(/\\/g, "\\\\")
        .replace(/"/g, '\\"');
}

function getSectionById(sectionId) {
    if (!sectionId) {
        return null;
    }

    return document.querySelector(
        `#${escapeAttributeValue(sectionId)}`
    );
}

/* ==========================================================================
   EVENT HELPERS
============================================================================ */

function dispatchOESCustomEvent(name, detail) {
    document.dispatchEvent(
        new CustomEvent(name, {
            detail
        })
    );
}

function dispatchCoreMessage({
    message,
    source = "section-awareness",
    accent = "blue",
    priority = "normal",
    duration = DEFAULT_TEMPORARY_DURATION
}) {
    dispatchOESCustomEvent(
        "oes:coremessage",
        {
            message,
            source,
            accent,
            priority,
            duration
        }
    );
}

/* ==========================================================================
   ACCENT SYSTEM
============================================================================ */

function applyAccent(accentName = "blue") {
    const accent =
        ACCENT_VALUES[accentName] ||
        ACCENT_VALUES.blue;

    document.documentElement.style.setProperty(
        "--awareness-primary",
        accent.primary
    );

    document.documentElement.style.setProperty(
        "--awareness-secondary",
        accent.secondary
    );

    document.documentElement.style.setProperty(
        "--awareness-glow",
        accent.glow
    );

    if (pageRoot) {
        pageRoot.dataset.awarenessAccent =
            accentName;
    }

    if (coreStage) {
        coreStage.dataset.awarenessAccent =
            accentName;
    }
}

/* ==========================================================================
   CORE MESSAGE SYSTEM
============================================================================ */

function updateCoreMessage(
    message,
    {
        accent = "blue",
        source = "section-awareness",
        priority = "normal",
        duration = 0,
        announce = true
    } = {}
) {
    if (!message) {
        return;
    }

    applyAccent(accent);

    clearTimer(messageTimer);
    clearTimer(temporaryResetTimer);

    if (!coreMessage) {
        dispatchCoreMessage({
            message,
            source,
            accent,
            priority,
            duration
        });

        return;
    }

    coreMessage.classList.add(
        "core-message--changing"
    );

    messageTimer = window.setTimeout(
        () => {
            coreMessage.textContent = message;

            coreMessage.dataset.messageSource =
                source;

            coreMessage.dataset.messagePriority =
                priority;

            coreMessage.classList.remove(
                "core-message--changing"
            );

            if (announce) {
                coreMessage.setAttribute(
                    "aria-live",
                    priority === "high"
                        ? "assertive"
                        : "polite"
                );
            }

            dispatchCoreMessage({
                message,
                source,
                accent,
                priority,
                duration
            });
        },
        MESSAGE_CHANGE_DELAY
    );

    if (duration > 0) {
        temporaryResetTimer =
            window.setTimeout(
                () => {
                    restoreCurrentSectionMessage();
                },
                duration
            );
    }
}

function restoreCurrentSectionMessage() {
    const config =
        SECTION_CONFIG[currentSectionId] ||
        SECTION_CONFIG.home;

    currentInterest = null;

    if (pageRoot) {
        delete pageRoot.dataset.currentInterest;
    }

    updateCoreMessage(
        config.message,
        {
            accent: config.accent,
            source: `section:${currentSectionId}`,
            duration: 0,
            announce: false
        }
    );
}

/* ==========================================================================
   SECTION DETECTION
============================================================================ */

function calculateSectionScore(entry) {
    const viewportHeight =
        window.innerHeight ||
        document.documentElement.clientHeight;

    const rect = entry.boundingClientRect;

    const viewportCenter =
        viewportHeight / 2;

    const sectionCenter =
        rect.top + rect.height / 2;

    const distanceFromCenter =
        Math.abs(
            viewportCenter -
            sectionCenter
        );

    const centerScore =
        Math.max(
            0,
            1 -
            distanceFromCenter /
            viewportHeight
        );

    return (
        entry.intersectionRatio * 0.72 +
        centerScore * 0.28
    );
}

function selectMostRelevantSection() {
    let selectedSection = null;
    let selectedScore = -1;

    observedSections.forEach(
        (entry, sectionElement) => {
            if (!entry.isIntersecting) {
                return;
            }

            const score =
                calculateSectionScore(entry);

            if (score > selectedScore) {
                selectedScore = score;
                selectedSection = sectionElement;
            }
        }
    );

    return selectedSection;
}

function setCurrentSection(sectionElement) {
    if (!sectionElement) {
        return;
    }

    const sectionId =
        sectionElement.id || "home";

    if (
        sectionId === currentSectionId &&
        currentInterest
    ) {
        return;
    }

    const previousSectionId =
        currentSectionId;

    currentSectionId = sectionId;

    const visitCount =
        incrementMapValue(
            sectionVisits,
            sectionId
        );

    document
        .querySelectorAll(
            ".section--awareness-active, .hero-scene--awareness-active"
        )
        .forEach((element) => {
            element.classList.remove(
                "section--awareness-active",
                "hero-scene--awareness-active"
            );
        });

    if (
        sectionElement.classList.contains(
            "hero-scene"
        )
    ) {
        sectionElement.classList.add(
            "hero-scene--awareness-active"
        );
    } else {
        sectionElement.classList.add(
            "section--awareness-active"
        );
    }

    if (pageRoot) {
        pageRoot.dataset.currentSection =
            sectionId;
    }

    if (coreStage) {
        coreStage.dataset.currentSection =
            sectionId;
    }

    const config =
        SECTION_CONFIG[sectionId] ||
        SECTION_CONFIG.home;

    if (!currentInterest) {
        updateCoreMessage(
            config.message,
            {
                accent: config.accent,
                source: `section:${sectionId}`,
                announce:
                    sectionId !== previousSectionId
            }
        );
    }

    dispatchOESCustomEvent(
        "oes:sectionchange",
        {
            sectionId,
            previousSectionId,
            sectionElement,
            message: config.message,
            accent: config.accent,
            visitCount
        }
    );
}

function handleSectionIntersections(entries) {
    entries.forEach((entry) => {
        observedSections.set(
            entry.target,
            entry
        );
    });

    const section =
        selectMostRelevantSection();

    if (section) {
        setCurrentSection(section);
    }
}

function selectSectionAtViewportFocus() {
    const sections =
        Array.from(
            document.querySelectorAll(
                ".hero-scene[id], .section[id]"
            )
        );

    const focusY =
        window.innerHeight * 0.42;

    let nearestSection = null;
    let nearestDistance = Infinity;

    sections.forEach((section) => {
        const rect =
            section.getBoundingClientRect();

        if (
            rect.top <= focusY &&
            rect.bottom >= focusY
        ) {
            nearestSection = section;
            nearestDistance = 0;
            return;
        }

        if (nearestDistance === 0) {
            return;
        }

        const distance =
            Math.min(
                Math.abs(rect.top - focusY),
                Math.abs(rect.bottom - focusY)
            );

        if (distance < nearestDistance) {
            nearestDistance = distance;
            nearestSection = section;
        }
    });

    return nearestSection;
}

function handleSectionScroll() {
    if (sectionScrollFrame) {
        return;
    }

    sectionScrollFrame =
        window.requestAnimationFrame(
            () => {
                sectionScrollFrame = null;

                setCurrentSection(
                    selectSectionAtViewportFocus()
                );
            }
        );
}

function initializeSectionObserver() {
    const sections =
        Array.from(
            document.querySelectorAll(
                ".hero-scene[id], .section[id]"
            )
        );

    if (sections.length === 0) {
        return;
    }

    if (
        !("IntersectionObserver" in window)
    ) {
        setCurrentSection(
            sections[0]
        );

        return;
    }

    const observer =
        new IntersectionObserver(
            handleSectionIntersections,
            {
                root: null,
                rootMargin:
                    "-20% 0px -44% 0px",
                threshold: [
                    0.05,
                    0.15,
                    0.25,
                    0.4,
                    0.55,
                    0.7
                ]
            }
        );

    sections.forEach((section) => {
        observer.observe(section);
    });
}

/* ==========================================================================
   INTEREST CLASSIFICATION
============================================================================ */

function detectInterestFromData(element) {
    const awarenessValue =
        element.closest(
            "[data-awareness]"
        )?.dataset.awareness;

    if (awarenessValue) {
        return awarenessValue;
    }

    const productElement =
        element.closest("[data-product]");

    if (productElement?.dataset.product) {
        return productElement.dataset.product;
    }

    return null;
}

function detectInterestFromClasses(element) {
    const closest = (selector) =>
        element.closest(selector);

    if (
        closest(
            ".product-card--chase, .chase-card"
        )
    ) {
        return "chaseingreen";
    }

    if (
        closest(
            ".product-card--lottovate, .lottovate-card"
        )
    ) {
        return "lottovate";
    }

    if (closest(".client-spotlight")) {
        return "client";
    }

    if (closest(".capability-card")) {
        return "government";
    }

    if (closest(".research-terminal, .research-line")) {
        return "research";
    }

    if (
        closest(
            ".contact-panel, .contact-email"
        )
    ) {
        return "contact";
    }

    return null;
}

function detectServiceInterest(element) {
    const serviceCard =
        element.closest(".service-card");

    if (!serviceCard) {
        return null;
    }

    const heading =
        normalizeText(
            serviceCard.querySelector("h3")
                ?.textContent
        );

    if (heading.includes("artificial intelligence")) {
        return "ai";
    }

    if (heading.includes("mobile")) {
        return "mobile";
    }

    if (heading.includes("web")) {
        return "web";
    }

    if (heading.includes("data")) {
        return "data";
    }

    if (heading.includes("saas")) {
        return "saas";
    }

    if (heading.includes("automation")) {
        return "automation";
    }

    if (heading.includes("consulting")) {
        return "consulting";
    }

    if (
        heading.includes("training") ||
        heading.includes("digital skills")
    ) {
        return "training";
    }

    return null;
}

function detectGovernmentInterest(element) {
    const capabilityCard =
        element.closest(".capability-card");

    if (!capabilityCard) {
        return null;
    }

    const heading =
        normalizeText(
            capabilityCard.querySelector("h3")
                ?.textContent
        );

    if (
        heading.includes("prototype") ||
        heading.includes("validation")
    ) {
        return "prototype";
    }

    if (
        heading.includes("training")
    ) {
        return "training";
    }

    if (
        heading.includes("ai") ||
        heading.includes("data")
    ) {
        return "data";
    }

    if (
        heading.includes("software") ||
        heading.includes("platform")
    ) {
        return "web";
    }

    return "government";
}

function detectCommunityInterest(element) {
    const communityCard =
        element.closest(".community-card");

    if (!communityCard) {
        return null;
    }

    const heading =
        normalizeText(
            communityCard.querySelector("h3")
                ?.textContent
        );

    if (heading.includes("apple developer")) {
        return "academy";
    }

    if (heading.includes("techtown")) {
        return "techtown";
    }

    if (heading.includes("black tech")) {
        return "black-tech";
    }

    if (heading.includes("crossroads")) {
        return "crossroads";
    }

    if (
        heading.includes("coaching") ||
        heading.includes("mentorship")
    ) {
        return "mentorship";
    }

    return "community";
}

function detectInterest(element) {
    if (!(element instanceof Element)) {
        return null;
    }

    return (
        detectInterestFromData(element) ||
        detectServiceInterest(element) ||
        detectGovernmentInterest(element) ||
        detectCommunityInterest(element) ||
        detectInterestFromClasses(element)
    );
}

/* ==========================================================================
   INTEREST REACTIONS
============================================================================ */

function getInterestConfig(interest) {
    return (
        INTEREST_CONFIG[interest] ||
        null
    );
}

function markInterestedElement(
    element,
    isActive
) {
    const awarenessElement =
        element.closest(
            [
                "[data-awareness]",
                "[data-product]",
                ".service-card",
                ".capability-card",
                ".community-card",
                ".client-spotlight",
                ".research-line",
                ".contact-panel"
            ].join(",")
        );

    if (!awarenessElement) {
        return;
    }

    awarenessElement.classList.toggle(
        "awareness-target--active",
        isActive
    );
}

function activateInterest(
    interest,
    element,
    {
        interactionType = "hover",
        temporary = true
    } = {}
) {
    const config =
        getInterestConfig(interest);

    if (!config) {
        return;
    }

    const interactionCount =
        incrementMapValue(
            interestInteractions,
            interest
        );

    currentInterest = interest;

    if (pageRoot) {
        pageRoot.dataset.currentInterest =
            interest;
    }

    if (coreStage) {
        coreStage.dataset.currentInterest =
            interest;

        coreStage.classList.add(
            "oes-core-stage--aware"
        );
    }

    markInterestedElement(
        element,
        true
    );

    const repeated =
        interactionCount >=
        REPEATED_INTEREST_THRESHOLD;

    const message =
        repeated
            ? config.repeatedMessage
            : config.message;

    updateCoreMessage(
        message,
        {
            accent: config.accent,
            source:
                `interest:${interest}:${interactionType}`,
            priority:
                repeated
                    ? "high"
                    : "normal",
            duration:
                temporary
                    ? DEFAULT_TEMPORARY_DURATION
                    : 0
        }
    );

    dispatchOESCustomEvent(
        "oes:interestchange",
        {
            interest,
            element,
            message,
            accent: config.accent,
            interactionType,
            interactionCount,
            repeated
        }
    );
}

function deactivateInterest(element) {
    markInterestedElement(
        element,
        false
    );

    if (coreStage) {
        coreStage.classList.remove(
            "oes-core-stage--aware"
        );
    }

    currentInterest = null;

    if (pageRoot) {
        delete pageRoot.dataset.currentInterest;
    }

    if (coreStage) {
        delete coreStage.dataset.currentInterest;
    }

    restoreCurrentSectionMessage();
}

/* ==========================================================================
   POINTER AND FOCUS HANDLERS
============================================================================ */

function isAwarenessTarget(element) {
    if (!(element instanceof Element)) {
        return false;
    }

    return Boolean(
        element.closest(
            [
                "[data-awareness]",
                "[data-product]",
                ".service-card",
                ".capability-card",
                ".community-card",
                ".client-spotlight",
                ".research-line",
                ".contact-panel"
            ].join(",")
        )
    );
}

function handlePointerOver(event) {
    const target = event.target;

    if (
        !isAwarenessTarget(target)
    ) {
        return;
    }

    const interest =
        detectInterest(target);

    if (!interest) {
        return;
    }

    clearTimer(hoverIntentTimer);

    hoverIntentTimer =
        window.setTimeout(
            () => {
                activateInterest(
                    interest,
                    target,
                    {
                        interactionType: "hover",
                        temporary: true
                    }
                );
            },
            HOVER_INTENT_DELAY
        );
}

function handlePointerOut(event) {
    const target = event.target;

    if (
        !isAwarenessTarget(target)
    ) {
        return;
    }

    const awarenessTarget =
        target.closest(
            [
                "[data-awareness]",
                "[data-product]",
                ".service-card",
                ".capability-card",
                ".community-card",
                ".client-spotlight",
                ".research-line",
                ".contact-panel"
            ].join(",")
        );

    if (!awarenessTarget) {
        return;
    }

    if (
        event.relatedTarget instanceof Node &&
        awarenessTarget.contains(
            event.relatedTarget
        )
    ) {
        return;
    }

    clearTimer(hoverIntentTimer);

    markInterestedElement(
        awarenessTarget,
        false
    );
}

function handleFocusIn(event) {
    const target = event.target;

    if (
        !isAwarenessTarget(target)
    ) {
        return;
    }

    const interest =
        detectInterest(target);

    if (!interest) {
        return;
    }

    activateInterest(
        interest,
        target,
        {
            interactionType: "focus",
            temporary: false
        }
    );
}

function handleFocusOut(event) {
    const target = event.target;

    if (
        !isAwarenessTarget(target)
    ) {
        return;
    }

    const awarenessTarget =
        target.closest(
            [
                "[data-awareness]",
                "[data-product]",
                ".service-card",
                ".capability-card",
                ".community-card",
                ".client-spotlight",
                ".research-line",
                ".contact-panel"
            ].join(",")
        );

    if (!awarenessTarget) {
        return;
    }

    if (
        event.relatedTarget instanceof Node &&
        awarenessTarget.contains(
            event.relatedTarget
        )
    ) {
        return;
    }

    deactivateInterest(
        awarenessTarget
    );
}

function handleClick(event) {
    const target = event.target;

    if (!(target instanceof Element)) {
        return;
    }

    const interest =
        detectInterest(target);

    if (!interest) {
        return;
    }

    activateInterest(
        interest,
        target,
        {
            interactionType: "click",
            temporary: true
        }
    );
}

/* ==========================================================================
   SECTION-LEVEL DATA ATTRIBUTES
============================================================================ */

function applySectionAwarenessMetadata() {
    const sectionMessages = {
        home: "OES systems online. Detroit is building.",
        products: "OES products combine intelligence with execution.",
        "client-work": "Client systems begin with real business needs.",
        services: "Choose the problem. OES helps define the system.",
        government: "Public-sector technology should produce measurable outcomes.",
        community: "Detroit grows when more people can participate.",
        research: "OES explores behavior, prediction and emerging interaction.",
        about: "Purpose, imagination and execution.",
        contact: "Bring OES the idea."
    };

    Object.entries(sectionMessages)
        .forEach(
            ([
                sectionId,
                message
            ]) => {
                const section =
                    getSectionById(sectionId);

                if (!section) {
                    return;
                }

                section.dataset.awarenessSection =
                    sectionId;

                section.dataset.awarenessMessage =
                    message;
            }
        );
}

function applyCardAwarenessMetadata() {
    const assignments = [
        {
            selector:
                ".product-card--chase",
            interest:
                "chaseingreen"
        },

        {
            selector:
                ".product-card--lottovate",
            interest:
                "lottovate"
        },

        {
            selector:
                ".client-spotlight",
            interest:
                "client"
        },

        {
            selector:
                ".research-terminal",
            interest:
                "research"
        },

        {
            selector:
                ".contact-panel",
            interest:
                "contact"
        }
    ];

    assignments.forEach(
        ({
            selector,
            interest
        }) => {
            document
                .querySelectorAll(selector)
                .forEach((element) => {
                    if (
                        !element.dataset.awareness
                    ) {
                        element.dataset.awareness =
                            interest;
                    }
                });
        }
    );
}

/* ==========================================================================
   PUBLIC MESSAGE API
============================================================================ */

export function showAwarenessMessage(
    message,
    options = {}
) {
    updateCoreMessage(
        message,
        {
            accent:
                options.accent ||
                "blue",

            source:
                options.source ||
                "manual",

            priority:
                options.priority ||
                "normal",

            duration:
                Number.isFinite(
                    options.duration
                )
                    ? options.duration
                    : DEFAULT_TEMPORARY_DURATION,

            announce:
                options.announce !== false
        }
    );
}

export function resetAwarenessMessage() {
    currentInterest = null;

    clearTimer(messageTimer);
    clearTimer(temporaryResetTimer);

    restoreCurrentSectionMessage();

    dispatchOESCustomEvent(
        "oes:awarenessreset",
        {
            sectionId:
                currentSectionId
        }
    );
}

export function getAwarenessState() {
    return {
        currentSectionId,
        currentInterest,

        sectionVisits:
            Object.fromEntries(
                sectionVisits
            ),

        interestInteractions:
            Object.fromEntries(
                interestInteractions
            )
    };
}

/* ==========================================================================
   INITIALIZATION
============================================================================ */

export function initializeSectionAwareness() {
    if (initialized) {
        return;
    }

    initialized = true;

    pageRoot =
        document.querySelector(
            "main"
        ) ||
        document.body;

    coreStage =
        document.querySelector(
            "[data-oes-core-stage]"
        );

    coreMessage =
        document.querySelector(
            "[data-core-message]"
        );

    applySectionAwarenessMetadata();
    applyCardAwarenessMetadata();

    initializeSectionObserver();

    window.addEventListener(
        "scroll",
        handleSectionScroll,
        {
            passive: true
        }
    );

    document.addEventListener(
        "pointerover",
        handlePointerOver,
        {
            passive: true
        }
    );

    document.addEventListener(
        "pointerout",
        handlePointerOut,
        {
            passive: true
        }
    );

    document.addEventListener(
        "focusin",
        handleFocusIn
    );

    document.addEventListener(
        "focusout",
        handleFocusOut
    );

    document.addEventListener(
        "click",
        handleClick
    );

    if (prefersReducedMotion()) {
        document.documentElement.classList.add(
            "awareness-reduced-motion"
        );
    }

    const initialSection =
        getSectionById("home") ||
        document.querySelector(
            ".hero-scene[id], .section[id]"
        );

    if (initialSection) {
        setCurrentSection(
            initialSection
        );
    } else {
        updateCoreMessage(
            DEFAULT_MESSAGE,
            {
                announce: false
            }
        );
    }

    document.documentElement.classList.add(
        "section-awareness-ready"
    );
}
