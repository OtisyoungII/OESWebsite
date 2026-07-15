/*
===============================================================================
FILE: static/js/app.js

PURPOSE:
    Main JavaScript entry point for the Otis Execution Systems website.

UPDATED:
    July 14, 2026

RESPONSIBILITIES:
    [x] Start ambient effects
    [x] Start the interactive OES Core
    [x] Start Detroit scene reactions
    [x] Start product-card interactions
    [x] Start ChaseInGreen effects
    [x] Start Lottovate effects
    [x] Start scroll-reveal effects
    [x] Start mobile navigation behavior
    [x] Keep all major systems separated into modules

ARCHITECTURE:
    This file remains intentionally small.

    Global atmosphere:
        static/js/ambient-effects.js

    OES Core:
        static/js/oes-core.js

    Detroit hero environment:
        static/js/detroit-scene.js

    Shared card interactions:
        static/js/card-effects.js

    Product effects:
        static/js/product-effects.js

    Scroll reveal:
        static/js/reveal-effects.js

IMPORTANT RULES:
    [x] Initialize each system only once
    [x] Do not place major animation logic in this file
    [x] Missing optional elements must not break the page
    [x] Navigation must remain keyboard accessible
===============================================================================
*/

import {
    createCursorGlow,
    createParticleField
} from "./ambient-effects.js";

import {
    initializeOESCore
} from "./oes-core.js";

import {
    initializeDetroitScene
} from "./detroit-scene.js";

import {
    setupCardTilt
} from "./card-effects.js";

import {
    setupChaseMoney,
    setupLottovateCoins
} from "./product-effects.js";

import {
    setupScrollReveal
} from "./reveal-effects.js";

import {
    initializeSectionAwareness
} from "./section-awareness.js";

/* ============================================================================
   Mobile navigation
============================================================================ */

function setupMobileNavigation() {
    const menuToggle = document.querySelector(
        "[data-menu-toggle]"
    );

    const navigation = document.querySelector(
        "[data-navigation]"
    );

    const header = document.querySelector(
        "[data-site-header]"
    );

    if (
        !menuToggle ||
        !navigation ||
        !header
    ) {
        return;
    }

    const navigationLinks = Array.from(
        navigation.querySelectorAll("a")
    );

    function setMenuState(isOpen) {
        menuToggle.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

        menuToggle.setAttribute(
            "aria-label",
            isOpen
                ? "Close navigation"
                : "Open navigation"
        );

        header.classList.toggle(
            "site-header--menu-open",
            isOpen
        );

        navigation.classList.toggle(
            "primary-navigation--open",
            isOpen
        );

        document.body.classList.toggle(
            "navigation-open",
            isOpen
        );
    }

    menuToggle.addEventListener(
        "click",
        () => {
            const isOpen =
                menuToggle.getAttribute(
                    "aria-expanded"
                ) === "true";

            setMenuState(!isOpen);
        }
    );

    navigationLinks.forEach((link) => {
        link.addEventListener(
            "click",
            () => {
                setMenuState(false);
            }
        );
    });

    document.addEventListener(
        "keydown",
        (event) => {
            if (event.key !== "Escape") {
                return;
            }

            setMenuState(false);
            menuToggle.focus();
        }
    );

    window.addEventListener(
        "resize",
        () => {
            if (window.innerWidth > 900) {
                setMenuState(false);
            }
        }
    );
}

/* ============================================================================
   Header state
============================================================================ */

function setupHeaderScrollState() {
    const header = document.querySelector(
        "[data-site-header]"
    );

    if (!header) {
        return;
    }

    function updateHeader() {
        header.classList.toggle(
            "site-header--scrolled",
            window.scrollY > 24
        );
    }

    updateHeader();

    window.addEventListener(
        "scroll",
        updateHeader,
        {
            passive: true
        }
    );
}

/* ============================================================================
   Beta inquiry links
============================================================================ */

function setupBetaInquiryLinks() {
    const betaLinks = document.querySelectorAll(
        "[data-beta-product]"
    );

    betaLinks.forEach((link) => {
        link.addEventListener(
            "click",
            () => {
                const productName =
                    link.dataset.betaProduct;

                if (!productName) {
                    return;
                }

                const subject =
                    encodeURIComponent(
                        `${productName} Beta Testing`
                    );

                const body =
                    encodeURIComponent(
                        [
                            `Hello OES,`,
                            ``,
                            `I am interested in beta testing ${productName}.`,
                            ``,
                            `Name:`,
                            `Device:`,
                            `What interests me about the product:`,
                            ``,
                            `Thank you.`
                        ].join("\n")
                    );

                link.href =
                    `mailto:info@otisexecutionsystems.com?subject=${subject}&body=${body}`;
            }
        );
    });
}

/* ============================================================================
   Smooth same-page focus
============================================================================ */

function setupAccessibleAnchorNavigation() {
    const internalLinks = document.querySelectorAll(
        'a[href^="#"]'
    );

    internalLinks.forEach((link) => {
        link.addEventListener(
            "click",
            () => {
                const selector =
                    link.getAttribute("href");

                if (
                    !selector ||
                    selector === "#"
                ) {
                    return;
                }

                const destination =
                    document.querySelector(selector);

                if (!destination) {
                    return;
                }

                window.setTimeout(
                    () => {
                        destination.setAttribute(
                            "tabindex",
                            "-1"
                        );

                        destination.focus({
                            preventScroll: true
                        });
                    },
                    500
                );
            }
        );
    });
}

/* ============================================================================
   Application startup
============================================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {
        const chaseCard =
            document.querySelector(
                ".chase-card"
            );

        const lottovateCard =
            document.querySelector(
                ".lottovate-card"
            );

        createCursorGlow();
        createParticleField();

        initializeOESCore();
        initializeDetroitScene();
        initializeSectionAwareness();

        setupCardTilt();
        setupChaseMoney(chaseCard);
        setupLottovateCoins(lottovateCard);

        setupScrollReveal();
        setupMobileNavigation();
        setupHeaderScrollState();
        setupBetaInquiryLinks();
        setupAccessibleAnchorNavigation();

        document.documentElement.classList.add(
            "oes-ready"
        );
    }
);