/*
===============================================================================
FILE: static/js/app.js

PURPOSE:
    Main JavaScript entry point for the Otis Execution Systems website.

UPDATED:
    July 16, 2026

RESPONSIBILITIES:
    [x] Start ambient effects
    [x] Start the intelligent OES Core behavior system
    [x] Start the true WebGL OES Core renderer
    [x] Start the movable OES Core companion
    [x] Start Detroit scene reactions
    [x] Start section-awareness behavior
    [x] Start the Drinks With Friendz spatial logo
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

    OES Core behavior:
        static/js/oes-core.js

    OES Core WebGL renderer:
        static/js/oes-core-3d.js

    OES Core page companion:
        static/js/oes-core-companion.js

    Detroit hero environment:
        static/js/detroit-scene.js

    Section awareness:
        static/js/section-awareness.js

    Drinks With Friendz showcase:
        static/js/dwf-logo.js

    Shared card interactions:
        static/js/card-effects.js

    Product effects:
        static/js/product-effects.js

    Scroll reveal:
        static/js/reveal-effects.js

STARTUP ORDER:
    1. Global atmosphere
    2. OES Core behavior
    3. OES Core WebGL renderer
    4. OES Core companion
    5. Detroit scene
    6. Section awareness
    7. Remaining page systems

IMPORTANT RULES:
    [x] Initialize each system only once
    [x] Initialize OES Core behavior before the WebGL renderer
    [x] Initialize the WebGL renderer before the Core companion
    [x] Preserve the CSS Core as the WebGL fallback
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
    initializeOESCore3D
} from "./oes-core-3d.js";

import {
    initializeOESCoreCompanion
} from "./oes-core-companion.js";

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

import {
    initializeDWFLogoShowcase
} from "./dwf-logo.js";

/* ==========================================================================
   MOBILE NAVIGATION
========================================================================== */

function setupMobileNavigation() {
    const menuToggle =
        document.querySelector(
            "[data-menu-toggle]"
        );

    const navigation =
        document.querySelector(
            "[data-navigation]"
        );

    const header =
        document.querySelector(
            "[data-site-header]"
        );

    if (
        !menuToggle ||
        !navigation ||
        !header
    ) {
        return;
    }

    const navigationLinks =
        Array.from(
            navigation.querySelectorAll(
                "a"
            )
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

            setMenuState(
                !isOpen
            );
        }
    );

    navigationLinks.forEach(
        (link) => {
            link.addEventListener(
                "click",
                () => {
                    setMenuState(
                        false
                    );
                }
            );
        }
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key !==
                "Escape"
            ) {
                return;
            }

            setMenuState(
                false
            );

            menuToggle.focus();
        }
    );

    window.addEventListener(
        "resize",
        () => {
            if (
                window.innerWidth >
                900
            ) {
                setMenuState(
                    false
                );
            }
        }
    );
}

/* ==========================================================================
   HEADER STATE
========================================================================== */

function setupHeaderScrollState() {
    const header =
        document.querySelector(
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

/* ==========================================================================
   BETA INQUIRY LINKS
========================================================================== */

function setupBetaInquiryLinks() {
    const betaLinks =
        document.querySelectorAll(
            "[data-beta-product]"
        );

    betaLinks.forEach(
        (link) => {
            link.addEventListener(
                "click",
                () => {
                    const productName =
                        link.dataset
                            .betaProduct;

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
                                "Hello OES,",
                                "",
                                `I am interested in beta testing ${productName}.`,
                                "",
                                "Name:",
                                "Device:",
                                "What interests me about the product:",
                                "",
                                "Thank you."
                            ].join("\n")
                        );

                    link.href =
                        `mailto:info@otisexecutionsystems.com?subject=${subject}&body=${body}`;
                }
            );
        }
    );
}

/* ==========================================================================
   ACCESSIBLE SAME-PAGE NAVIGATION
========================================================================== */

function setupAccessibleAnchorNavigation() {
    const internalLinks =
        document.querySelectorAll(
            'a[href^="#"]'
        );

    internalLinks.forEach(
        (link) => {
            link.addEventListener(
                "click",
                () => {
                    const selector =
                        link.getAttribute(
                            "href"
                        );

                    if (
                        !selector ||
                        selector === "#"
                    ) {
                        return;
                    }

                    let destination = null;

                    try {
                        destination =
                            document.querySelector(
                                selector
                            );
                    } catch {
                        return;
                    }

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
        }
    );
}

/* ==========================================================================
   OPTIONAL SYSTEM INITIALIZATION
========================================================================== */

function safelyInitialize(
    systemName,
    initializer
) {
    if (
        typeof initializer !==
        "function"
    ) {
        console.warn(
            `${systemName} initializer is unavailable.`
        );

        return false;
    }

    try {
        initializer();

        return true;
    } catch (error) {
        console.error(
            `${systemName} failed to initialize:`,
            error
        );

        return false;
    }
}

/* ==========================================================================
   APPLICATION STARTUP
========================================================================== */

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

        safelyInitialize(
            "OES cursor glow",
            createCursorGlow
        );

        safelyInitialize(
            "OES particle field",
            createParticleField
        );

        /*
        The Core behavior system starts first.

        The WebGL renderer starts second and reads the behavior system's CSS
        variables, classes, colors, movement, activation, and awareness.

        The companion starts third because it moves the completed Core around
        the page without creating a second canvas or second Core instance.
        */

        safelyInitialize(
            "OES Core behavior",
            initializeOESCore
        );

        safelyInitialize(
            "OES Core WebGL",
            initializeOESCore3D
        );

        safelyInitialize(
            "OES Core companion",
            initializeOESCoreCompanion
        );

        safelyInitialize(
            "Detroit scene",
            initializeDetroitScene
        );

        safelyInitialize(
            "Section awareness",
            initializeSectionAwareness
        );

        safelyInitialize(
            "Drinks With Friendz showcase",
            initializeDWFLogoShowcase
        );

        safelyInitialize(
            "Card tilt",
            setupCardTilt
        );

        safelyInitialize(
            "ChaseInGreen effects",
            () => {
                setupChaseMoney(
                    chaseCard
                );
            }
        );

        safelyInitialize(
            "Lottovate effects",
            () => {
                setupLottovateCoins(
                    lottovateCard
                );
            }
        );

        safelyInitialize(
            "Scroll reveal",
            setupScrollReveal
        );

        safelyInitialize(
            "Mobile navigation",
            setupMobileNavigation
        );

        safelyInitialize(
            "Header scroll state",
            setupHeaderScrollState
        );

        safelyInitialize(
            "Beta inquiry links",
            setupBetaInquiryLinks
        );

        safelyInitialize(
            "Accessible anchor navigation",
            setupAccessibleAnchorNavigation
        );

        document.documentElement
            .classList.add(
                "oes-ready"
            );
    }
);