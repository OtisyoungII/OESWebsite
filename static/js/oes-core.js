/*
===============================================================================
FILE: static/js/oes-core.js

PURPOSE:
    Controls the intelligent, spatial and human-like behavior of the OES Core.

UPDATED:
    July 16, 2026

RESPONSIBILITIES:
    [x] Smooth pointer awareness
    [x] Stronger visible 3D rotation
    [x] Controlled movement inside a defined spatial area
    [x] True top-and-bottom eyelid blinking
    [x] Idle curiosity and environmental observation
    [x] Breathing and heartbeat behavior
    [x] Section-aware color and energy changes
    [x] Interest-aware focus toward page content
    [x] Drag, keyboard and touch interaction
    [x] Core activation reactions
    [x] Orbit-speed control
    [x] Reduced-motion support
    [x] Safe initialization without duplicate listeners

EVENTS RECEIVED:
    oes:sectionchange
    oes:interestchange
    oes:coremessage
    oes:awarenessreset

EVENTS DISPATCHED:
    oes:coreactivated
    oes:corestatechange
    oes:coreattention
    oes:coreblink

CSS VARIABLES CONTROLLED:
    --core-rotate-x
    --core-rotate-y
    --core-translate-x
    --core-translate-y
    --core-spatial-x
    --core-spatial-y
    --core-spatial-z
    --core-glow-strength
    --core-activation-scale
    --core-breath-scale
    --core-orbit-speed
    --core-pulse-speed
    --core-focus-x
    --core-focus-y
    --core-depth-shadow-x
    --core-depth-shadow-y
    --core-eye-open
    --awareness-primary
    --awareness-secondary
    --awareness-glow

IMPORTANT RULES:
    [x] Movement must feel delayed and organic
    [x] The Core must never lock directly onto the pointer
    [x] The Core remains inside a controlled spatial area
    [x] Eyelids close from the top and bottom
    [x] Blinking must not simply fade the logo
    [x] The logo artwork remains unchanged
    [x] Reduced-motion preferences must be respected
===============================================================================
*/


/* ==========================================================================
   CONFIGURATION
============================================================================ */

const CORE_CONFIG = Object.freeze({
    pointerRotationX: 12,
    pointerRotationY: 16,

    attentionRotationX: 8,
    attentionRotationY: 11,

    maximumRotationX: 22,
    maximumRotationY: 28,

    pointerTranslationX: 16,
    pointerTranslationY: 12,

    spatialDriftX: 15,
    spatialDriftY: 12,
    spatialDriftZ: 26,

    springStrength: 0.062,
    springDamping: 0.84,

    translationSpringStrength: 0.048,
    translationSpringDamping: 0.83,

    breathingDuration: 8800,

    heartbeatMinimumDelay: 13000,
    heartbeatMaximumDelay: 26000,

    blinkMinimumDelay: 4200,
    blinkMaximumDelay: 9800,
    blinkClosedDuration: 105,
    doubleBlinkChance: 0.22,

    idleMinimumDelay: 7000,
    idleMaximumDelay: 15000,

    idleLookDurationMinimum: 1300,
    idleLookDurationMaximum: 2900,

    sectionEngagementDelay: 14000,
    deepSectionEngagementDelay: 27000,

    activationDuration: 1450,
    attentionReleaseDelay: 620,
    pointerIdleDelay: 3000,

    maximumDeltaTime: 50
});


const SECTION_BEHAVIORS = Object.freeze({
    home: {
        accent: "blue",
        glow: 0.62,
        orbitSpeed: 1,
        pulseSpeed: 1,
        message: "Move. Touch. Explore.",
        longMessage: "Detroit is still building.",
        deepMessage: "Every challenge is another place to build."
    },

    products: {
        accent: "green",
        glow: 0.72,
        orbitSpeed: 1.17,
        pulseSpeed: 1.12,
        message: "OES product systems active.",
        longMessage: "Two products. One execution system.",
        deepMessage: "Working systems reveal more than unfinished ideas."
    },

    "client-work": {
        accent: "pink",
        glow: 0.68,
        orbitSpeed: 0.98,
        pulseSpeed: 0.94,
        message: "Client development mode.",
        longMessage: "Client development starts with a real business need.",
        deepMessage: "Good software should strengthen the business behind it."
    },

    services: {
        accent: "blue",
        glow: 0.67,
        orbitSpeed: 1.06,
        pulseSpeed: 1,
        message: "Choose a capability.",
        longMessage: "Choose a capability. Start with the problem.",
        deepMessage: "Version 1 should prove what matters most."
    },

    government: {
        accent: "government",
        glow: 0.61,
        orbitSpeed: 0.82,
        pulseSpeed: 0.8,
        message: "Public-sector capabilities loaded.",
        longMessage: "Technology should solve measurable public problems.",
        deepMessage: "Clear outcomes. Responsible boundaries. Practical delivery."
    },

    community: {
        accent: "community",
        glow: 0.68,
        orbitSpeed: 0.92,
        pulseSpeed: 0.9,
        message: "Detroit ecosystem connected.",
        longMessage: "Detroit grows when more people can participate.",
        deepMessage: "Technology, education and mentorship belong together."
    },

    research: {
        accent: "purple",
        glow: 0.82,
        orbitSpeed: 1.35,
        pulseSpeed: 1.22,
        message: "Experimental systems active.",
        longMessage: "Still exploring?",
        deepMessage: "There is always another layer."
    },

    about: {
        accent: "blue",
        glow: 0.57,
        orbitSpeed: 0.86,
        pulseSpeed: 0.84,
        message: "Detroit built. Execution focused.",
        longMessage: "Purpose, imagination and execution.",
        deepMessage: "Imperfections are places where better systems can begin."
    },

    contact: {
        accent: "green",
        glow: 0.75,
        orbitSpeed: 1.08,
        pulseSpeed: 1.1,
        message: "Ready when you are.",
        longMessage: "Ready when you are.",
        deepMessage: "Bring OES the idea."
    }
});


const INTEREST_BEHAVIORS = Object.freeze({
    chaseingreen: {
        accent: "green",
        glow: 0.9,
        orbitSpeed: 1.5,
        pulseSpeed: 1.3,
        focusStrength: 1,
        message: "Analyzing trading systems."
    },

    lottovate: {
        accent: "yellow",
        glow: 0.86,
        orbitSpeed: 1.42,
        pulseSpeed: 1.22,
        focusStrength: 0.96,
        message: "Scanning prediction patterns."
    },

    client: {
        accent: "pink",
        glow: 0.78,
        orbitSpeed: 1.05,
        pulseSpeed: 1.02,
        focusStrength: 0.9,
        message: "Client development environment active."
    },

    ai: {
        accent: "purple",
        glow: 0.88,
        orbitSpeed: 1.55,
        pulseSpeed: 1.27,
        focusStrength: 1,
        message: "Applied intelligence loaded."
    },

    mobile: {
        accent: "blue",
        glow: 0.76,
        orbitSpeed: 1.16,
        pulseSpeed: 1.08,
        focusStrength: 0.9,
        message: "Native mobile systems ready."
    },

    web: {
        accent: "blue",
        glow: 0.7,
        orbitSpeed: 1.04,
        pulseSpeed: 1,
        focusStrength: 0.86,
        message: "Connected web systems ready."
    },

    data: {
        accent: "green",
        glow: 0.82,
        orbitSpeed: 1.24,
        pulseSpeed: 1.12,
        focusStrength: 0.94,
        message: "Organizing data into action."
    },

    saas: {
        accent: "purple",
        glow: 0.8,
        orbitSpeed: 1.26,
        pulseSpeed: 1.1,
        focusStrength: 0.92,
        message: "Platform architecture loaded."
    },

    automation: {
        accent: "green",
        glow: 0.78,
        orbitSpeed: 1.32,
        pulseSpeed: 1.18,
        focusStrength: 0.94,
        message: "Workflow automation active."
    },

    consulting: {
        accent: "blue",
        glow: 0.64,
        orbitSpeed: 0.9,
        pulseSpeed: 0.88,
        focusStrength: 0.84,
        message: "Defining scope and priorities."
    },

    training: {
        accent: "community",
        glow: 0.76,
        orbitSpeed: 0.96,
        pulseSpeed: 0.94,
        focusStrength: 0.88,
        message: "Learning systems connected."
    },

    government: {
        accent: "government",
        glow: 0.72,
        orbitSpeed: 0.82,
        pulseSpeed: 0.8,
        focusStrength: 0.86,
        message: "Public-sector capabilities loaded."
    },

    prototype: {
        accent: "government",
        glow: 0.8,
        orbitSpeed: 1.12,
        pulseSpeed: 1.04,
        focusStrength: 0.96,
        message: "Prototype validation mode."
    },

    academy: {
        accent: "community",
        glow: 0.76,
        orbitSpeed: 1,
        pulseSpeed: 0.94,
        focusStrength: 0.94,
        message: "Human-centered development connected."
    },

    techtown: {
        accent: "community",
        glow: 0.74,
        orbitSpeed: 0.98,
        pulseSpeed: 0.92,
        focusStrength: 0.92,
        message: "Detroit founder ecosystem connected."
    },

    "black-tech": {
        accent: "community",
        glow: 0.8,
        orbitSpeed: 1.06,
        pulseSpeed: 1,
        focusStrength: 0.96,
        message: "Black technology ecosystem connected."
    },

    crossroads: {
        accent: "community",
        glow: 0.72,
        orbitSpeed: 0.9,
        pulseSpeed: 0.86,
        focusStrength: 0.9,
        message: "Community technology support connected."
    },

    mentorship: {
        accent: "community",
        glow: 0.78,
        orbitSpeed: 0.96,
        pulseSpeed: 0.98,
        focusStrength: 0.94,
        message: "Technology, athletics and mentorship connected."
    },

    research: {
        accent: "purple",
        glow: 0.96,
        orbitSpeed: 1.68,
        pulseSpeed: 1.38,
        focusStrength: 1,
        message: "Experimental systems active."
    },

    contact: {
        accent: "green",
        glow: 0.88,
        orbitSpeed: 1.14,
        pulseSpeed: 1.18,
        focusStrength: 0.96,
        message: "Ready to begin."
    }
});


const ACCENT_VALUES = Object.freeze({
    blue: {
        primary: "#38bdf8",
        secondary: "#2563eb",
        glow: "rgba(56, 189, 248, 0.56)"
    },

    green: {
        primary: "#22c55e",
        secondary: "#38bdf8",
        glow: "rgba(34, 197, 94, 0.54)"
    },

    yellow: {
        primary: "#facc15",
        secondary: "#a855f7",
        glow: "rgba(250, 204, 21, 0.52)"
    },

    pink: {
        primary: "#ec4899",
        secondary: "#a855f7",
        glow: "rgba(236, 72, 153, 0.52)"
    },

    purple: {
        primary: "#a855f7",
        secondary: "#38bdf8",
        glow: "rgba(168, 85, 247, 0.55)"
    },

    government: {
        primary: "#60a5fa",
        secondary: "#2563eb",
        glow: "rgba(96, 165, 250, 0.52)"
    },

    community: {
        primary: "#34d399",
        secondary: "#f59e0b",
        glow: "rgba(52, 211, 153, 0.5)"
    }
});


/* ==========================================================================
   MODULE STATE
============================================================================ */

let initialized = false;
let animationFrameId = null;

let core = null;
let stage = null;
let heroScene = null;
let coreMessage = null;

let orbitOuter = null;
let orbitMiddle = null;
let orbitInner = null;
let pulseElement = null;

let eyelidTop = null;
let eyelidBottom = null;

let reducedMotion = false;
let isVisible = true;
let isPointerActive = false;
let isPointerInsideWindow = true;
let isDragging = false;
let isActivated = false;
let isBlinking = false;

let activeSection = "home";
let activeInterest = null;
let focusedElement = null;

let lastFrameTime = 0;
let lastPointerTime = 0;

let sectionEngagementTimer = null;
let deepSectionEngagementTimer = null;
let idleBehaviorTimer = null;
let heartbeatTimer = null;
let blinkTimer = null;
let attentionReleaseTimer = null;
let activationTimer = null;
let temporaryMessageTimer = null;

let pointerX = window.innerWidth / 2;
let pointerY = window.innerHeight / 2;

let targetRotationX = 0;
let targetRotationY = 0;
let currentRotationX = 0;
let currentRotationY = 0;
let rotationVelocityX = 0;
let rotationVelocityY = 0;

let targetTranslationX = 0;
let targetTranslationY = 0;
let currentTranslationX = 0;
let currentTranslationY = 0;
let translationVelocityX = 0;
let translationVelocityY = 0;

let targetSpatialX = 0;
let targetSpatialY = 0;
let targetSpatialZ = 0;
let currentSpatialX = 0;
let currentSpatialY = 0;
let currentSpatialZ = 0;

let targetGlow = 0.62;
let currentGlow = 0.62;

let targetActivationScale = 1;
let currentActivationScale = 1;

let targetBreathScale = 1;
let currentBreathScale = 1;

let targetOrbitSpeed = 1;
let currentOrbitSpeed = 1;

let targetPulseSpeed = 1;
let currentPulseSpeed = 1;

let idleTargetRotationX = 0;
let idleTargetRotationY = 0;

let attentionTargetRotationX = 0;
let attentionTargetRotationY = 0;

let dragStartX = 0;
let dragStartY = 0;
let dragStartRotationX = 0;
let dragStartRotationY = 0;


/* ==========================================================================
   UTILITIES
============================================================================ */

function prefersReducedMotion() {
    return window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;
}


function clamp(value, minimum, maximum) {
    return Math.min(
        Math.max(value, minimum),
        maximum
    );
}


function randomBetween(minimum, maximum) {
    return (
        minimum +
        Math.random() *
        (maximum - minimum)
    );
}


function clearTimer(timerId) {
    if (timerId) {
        window.clearTimeout(timerId);
    }
}


function setRootVariable(name, value) {
    document.documentElement.style.setProperty(
        name,
        value
    );
}


function setStageVariable(name, value) {
    stage?.style.setProperty(
        name,
        value
    );
}


function dispatchCoreEvent(name, detail = {}) {
    document.dispatchEvent(
        new CustomEvent(name, {
            detail: {
                section: activeSection,
                interest: activeInterest,
                ...detail
            }
        })
    );
}


function getSectionBehavior(sectionId) {
    return (
        SECTION_BEHAVIORS[sectionId] ||
        SECTION_BEHAVIORS.home
    );
}


function getInterestBehavior(interest) {
    return (
        INTEREST_BEHAVIORS[interest] ||
        null
    );
}


/* ==========================================================================
   EYELID SYSTEM
============================================================================ */

function installEyelidStyles() {
    if (
        document.getElementById(
            "oes-core-eyelid-styles"
        )
    ) {
        return;
    }

    const style =
        document.createElement("style");

    style.id =
        "oes-core-eyelid-styles";

    style.textContent = `
        .oes-core {
            overflow: visible;
        }

        .oes-core__surface {
            isolation: isolate;
        }

        .oes-core__eyelid {
            position: absolute;
            z-index: 30;
            left: 8%;
            width: 84%;
            height: 47%;
            pointer-events: none;
            opacity: 1;
            background:
                radial-gradient(
                    ellipse at center,
                    rgba(2, 6, 23, 0.98) 0%,
                    rgba(3, 9, 21, 0.98) 58%,
                    rgba(7, 18, 36, 0.96) 100%
                );
            box-shadow:
                inset 0 0 30px rgba(56, 189, 248, 0.06),
                0 0 20px rgba(0, 0, 0, 0.48);
            transition:
                transform 105ms cubic-bezier(0.7, 0, 0.84, 0),
                border-color 160ms ease;
            will-change: transform;
        }

        .oes-core__eyelid::after {
            content: "";
            position: absolute;
            right: 4%;
            left: 4%;
            height: 2px;
            opacity: 0.52;
            background:
                linear-gradient(
                    90deg,
                    transparent,
                    var(--awareness-primary, #38bdf8),
                    transparent
                );
            filter:
                drop-shadow(
                    0 0 6px
                    var(--awareness-glow, rgba(56, 189, 248, 0.5))
                );
        }

        .oes-core__eyelid--top {
            top: 6%;
            border-radius:
                48% 48% 16% 16% /
                62% 62% 20% 20%;
            transform:
                translateY(
                    calc(
                        -101% +
                        (
                            101% *
                            (1 - var(--core-eye-open, 1))
                        )
                    )
                );
            transform-origin: top center;
        }

        .oes-core__eyelid--top::after {
            bottom: 0;
        }

        .oes-core__eyelid--bottom {
            bottom: 6%;
            border-radius:
                16% 16% 48% 48% /
                20% 20% 62% 62%;
            transform:
                translateY(
                    calc(
                        101% -
                        (
                            101% *
                            (1 - var(--core-eye-open, 1))
                        )
                    )
                );
            transform-origin: bottom center;
        }

        .oes-core__eyelid--bottom::after {
            top: 0;
        }

        .oes-core--blinking .oes-core__eyelid {
            transition-duration: 88ms;
        }

        .oes-core--watching .oes-core__surface {
            box-shadow:
                0 0 52px rgba(56, 189, 248, 0.36),
                0 0 110px rgba(37, 99, 235, 0.2),
                inset 0 0 76px rgba(56, 189, 248, 0.1),
                inset -28px -32px 58px rgba(0, 0, 0, 0.42);
        }

        @media (prefers-reduced-motion: reduce) {
            .oes-core__eyelid {
                display: none;
            }
        }
    `;

    document.head.appendChild(style);
}


function createEyelids() {
    if (!core) {
        return;
    }

    installEyelidStyles();

    eyelidTop =
        core.querySelector(
            ".oes-core__eyelid--top"
        );

    eyelidBottom =
        core.querySelector(
            ".oes-core__eyelid--bottom"
        );

    if (!eyelidTop) {
        eyelidTop =
            document.createElement("span");

        eyelidTop.className =
            "oes-core__eyelid oes-core__eyelid--top";

        eyelidTop.setAttribute(
            "aria-hidden",
            "true"
        );

        core.appendChild(eyelidTop);
    }

    if (!eyelidBottom) {
        eyelidBottom =
            document.createElement("span");

        eyelidBottom.className =
            "oes-core__eyelid oes-core__eyelid--bottom";

        eyelidBottom.setAttribute(
            "aria-hidden",
            "true"
        );

        core.appendChild(eyelidBottom);
    }

    setStageVariable(
        "--core-eye-open",
        "1"
    );
}


function setEyeOpenAmount(amount) {
    setStageVariable(
        "--core-eye-open",
        clamp(amount, 0, 1).toFixed(3)
    );
}


async function performSingleBlink() {
    if (
        reducedMotion ||
        isBlinking ||
        !core
    ) {
        return;
    }

    isBlinking = true;

    core.classList.add(
        "oes-core--blinking"
    );

    setEyeOpenAmount(0);

    dispatchCoreEvent(
        "oes:coreblink",
        {
            phase: "closed"
        }
    );

    await new Promise((resolve) => {
        window.setTimeout(
            resolve,
            CORE_CONFIG.blinkClosedDuration
        );
    });

    setEyeOpenAmount(1);

    await new Promise((resolve) => {
        window.setTimeout(
            resolve,
            150
        );
    });

    core.classList.remove(
        "oes-core--blinking"
    );

    isBlinking = false;

    dispatchCoreEvent(
        "oes:coreblink",
        {
            phase: "open"
        }
    );
}


async function triggerBlink() {
    if (
        reducedMotion ||
        isDragging ||
        isActivated
    ) {
        scheduleBlink();
        return;
    }

    await performSingleBlink();

    if (
        Math.random() <
        CORE_CONFIG.doubleBlinkChance
    ) {
        await new Promise((resolve) => {
            window.setTimeout(
                resolve,
                115
            );
        });

        await performSingleBlink();
    }

    scheduleBlink();
}


function scheduleBlink() {
    clearTimer(blinkTimer);

    if (reducedMotion) {
        return;
    }

    blinkTimer =
        window.setTimeout(
            triggerBlink,
            randomBetween(
                CORE_CONFIG.blinkMinimumDelay,
                CORE_CONFIG.blinkMaximumDelay
            )
        );
}


/* ==========================================================================
   ACCENT AND BEHAVIOR
============================================================================ */

function applyAccent(accentName = "blue") {
    const accent =
        ACCENT_VALUES[accentName] ||
        ACCENT_VALUES.blue;

    setRootVariable(
        "--awareness-primary",
        accent.primary
    );

    setRootVariable(
        "--awareness-secondary",
        accent.secondary
    );

    setRootVariable(
        "--awareness-glow",
        accent.glow
    );

    if (stage) {
        stage.dataset.coreAccent =
            accentName;
    }

    if (core) {
        core.dataset.coreAccent =
            accentName;
    }
}


function applyBehavior(
    behavior,
    source = "unknown"
) {
    if (!behavior) {
        return;
    }

    applyAccent(
        behavior.accent ||
        "blue"
    );

    if (
        Number.isFinite(
            behavior.glow
        )
    ) {
        targetGlow =
            behavior.glow;
    }

    if (
        Number.isFinite(
            behavior.orbitSpeed
        )
    ) {
        targetOrbitSpeed =
            behavior.orbitSpeed;
    }

    if (
        Number.isFinite(
            behavior.pulseSpeed
        )
    ) {
        targetPulseSpeed =
            behavior.pulseSpeed;
    }

    if (stage) {
        stage.dataset.coreBehaviorSource =
            source;
    }

    dispatchCoreEvent(
        "oes:corestatechange",
        {
            source,
            behavior
        }
    );
}


function restoreSectionBehavior() {
    activeInterest = null;
    focusedElement = null;

    stage?.classList.remove(
        "oes-core-stage--focused",
        "oes-core-stage--curious"
    );

    if (stage) {
        delete stage.dataset.coreInterest;
    }

    attentionTargetRotationX = 0;
    attentionTargetRotationY = 0;

    applyBehavior(
        getSectionBehavior(activeSection),
        `section:${activeSection}`
    );
}


/* ==========================================================================
   MESSAGE CONTROL
============================================================================ */

function setCoreMessage(
    message,
    {
        temporary = false,
        duration = 4200
    } = {}
) {
    if (
        !message ||
        !coreMessage
    ) {
        return;
    }

    clearTimer(
        temporaryMessageTimer
    );

    coreMessage.classList.add(
        "core-message--changing"
    );

    window.setTimeout(() => {
        if (!coreMessage) {
            return;
        }

        coreMessage.textContent =
            message;

        coreMessage.classList.remove(
            "core-message--changing"
        );
    }, 90);

    if (temporary) {
        temporaryMessageTimer =
            window.setTimeout(
                restoreSectionMessage,
                duration
            );
    }
}


function restoreSectionMessage() {
    if (activeInterest) {
        const interestBehavior =
            getInterestBehavior(
                activeInterest
            );

        if (interestBehavior?.message) {
            setCoreMessage(
                interestBehavior.message
            );

            return;
        }
    }

    const behavior =
        getSectionBehavior(
            activeSection
        );

    setCoreMessage(
        behavior.message ||
        "OES systems online."
    );
}


/* ==========================================================================
   POINTER AND SPATIAL AWARENESS
============================================================================ */

function calculatePointerTargets() {
    if (
        !core ||
        reducedMotion ||
        isDragging
    ) {
        return;
    }

    const rect =
        core.getBoundingClientRect();

    const centerX =
        rect.left +
        rect.width / 2;

    const centerY =
        rect.top +
        rect.height / 2;

    const normalizedX =
        clamp(
            (
                pointerX -
                centerX
            ) /
            Math.max(
                rect.width,
                1
            ),
            -1.25,
            1.25
        );

    const normalizedY =
        clamp(
            (
                pointerY -
                centerY
            ) /
            Math.max(
                rect.height,
                1
            ),
            -1.25,
            1.25
        );

    const pointerInfluence =
        isPointerActive
            ? 1
            : 0.16;

    targetRotationY =
        (
            normalizedX *
            CORE_CONFIG.pointerRotationY *
            pointerInfluence
        ) +
        attentionTargetRotationY +
        idleTargetRotationY;

    targetRotationX =
        (
            -normalizedY *
            CORE_CONFIG.pointerRotationX *
            pointerInfluence
        ) +
        attentionTargetRotationX +
        idleTargetRotationX;

    targetTranslationX =
        normalizedX *
        CORE_CONFIG.pointerTranslationX *
        pointerInfluence;

    targetTranslationY =
        normalizedY *
        CORE_CONFIG.pointerTranslationY *
        pointerInfluence;

    targetRotationX =
        clamp(
            targetRotationX,
            -CORE_CONFIG.maximumRotationX,
            CORE_CONFIG.maximumRotationX
        );

    targetRotationY =
        clamp(
            targetRotationY,
            -CORE_CONFIG.maximumRotationY,
            CORE_CONFIG.maximumRotationY
        );
}


function updateSpatialDrift(time) {
    if (
        reducedMotion ||
        isDragging
    ) {
        targetSpatialX = 0;
        targetSpatialY = 0;
        targetSpatialZ = 0;
        return;
    }

    const slowPhase =
        time / 8200;

    const mediumPhase =
        time / 5600;

    targetSpatialX =
        Math.sin(slowPhase) *
        CORE_CONFIG.spatialDriftX;

    targetSpatialY =
        (
            Math.cos(mediumPhase) *
            CORE_CONFIG.spatialDriftY
        ) -
        4;

    targetSpatialZ =
        (
            Math.sin(
                time / 6900
            ) *
            CORE_CONFIG.spatialDriftZ
        );
}


function handlePointerMove(event) {
    pointerX = event.clientX;
    pointerY = event.clientY;

    lastPointerTime =
        performance.now();

    isPointerActive = true;
    isPointerInsideWindow = true;

    stage?.classList.add(
        "oes-core-stage--tracking"
    );

    core?.classList.add(
        "oes-core--watching"
    );
}


function handlePointerLeaveWindow() {
    isPointerInsideWindow = false;
    isPointerActive = false;

    targetTranslationX = 0;
    targetTranslationY = 0;

    stage?.classList.remove(
        "oes-core-stage--tracking"
    );

    core?.classList.remove(
        "oes-core--watching"
    );
}


/* ==========================================================================
   CONTENT ATTENTION
============================================================================ */

function findAttentionTarget(element) {
    if (!(element instanceof Element)) {
        return null;
    }

    return element.closest(
        [
            "[data-product]",
            "[data-awareness]",
            ".service-card",
            ".capability-card",
            ".community-card",
            ".client-spotlight",
            ".research-line",
            ".contact-panel",
            "h1",
            "h2",
            "h3",
            "p",
            "a",
            "button"
        ].join(",")
    );
}


function calculateAttentionRotation(
    element
) {
    if (
        !element ||
        !core ||
        reducedMotion
    ) {
        return {
            x: 0,
            y: 0
        };
    }

    const targetRect =
        element.getBoundingClientRect();

    const coreRect =
        core.getBoundingClientRect();

    const horizontalDistance =
        (
            targetRect.left +
            targetRect.width / 2
        ) -
        (
            coreRect.left +
            coreRect.width / 2
        );

    const verticalDistance =
        (
            targetRect.top +
            targetRect.height / 2
        ) -
        (
            coreRect.top +
            coreRect.height / 2
        );

    return {
        x:
            -clamp(
                verticalDistance /
                Math.max(
                    window.innerHeight,
                    1
                ),
                -1,
                1
            ) *
            CORE_CONFIG.attentionRotationX,

        y:
            clamp(
                horizontalDistance /
                Math.max(
                    window.innerWidth,
                    1
                ),
                -1,
                1
            ) *
            CORE_CONFIG.attentionRotationY
    };
}


function focusOnElement(
    element,
    interest = null
) {
    const target =
        findAttentionTarget(
            element
        );

    if (!target) {
        return;
    }

    focusedElement =
        target;

    const rotation =
        calculateAttentionRotation(
            target
        );

    const behavior =
        getInterestBehavior(
            interest
        );

    const focusStrength =
        behavior?.focusStrength ||
        0.82;

    attentionTargetRotationX =
        rotation.x *
        focusStrength;

    attentionTargetRotationY =
        rotation.y *
        focusStrength;

    activeInterest =
        interest;

    stage?.classList.add(
        "oes-core-stage--focused"
    );

    core?.classList.add(
        "oes-core--watching"
    );

    if (
        stage &&
        interest
    ) {
        stage.dataset.coreInterest =
            interest;
    }

    if (behavior) {
        applyBehavior(
            behavior,
            `interest:${interest}`
        );

        if (behavior.message) {
            setCoreMessage(
                behavior.message,
                {
                    temporary: true,
                    duration: 4800
                }
            );
        }
    }

    dispatchCoreEvent(
        "oes:coreattention",
        {
            element: target,
            interest,
            rotation
        }
    );
}


function releaseAttention() {
    clearTimer(
        attentionReleaseTimer
    );

    attentionReleaseTimer =
        window.setTimeout(
            () => {
                attentionTargetRotationX = 0;
                attentionTargetRotationY = 0;

                core?.classList.remove(
                    "oes-core--watching"
                );

                restoreSectionBehavior();
                restoreSectionMessage();
            },
            CORE_CONFIG.attentionReleaseDelay
        );
}


/* ==========================================================================
   BREATHING AND HEARTBEAT
============================================================================ */

function updateBreathing(time) {
    if (reducedMotion) {
        targetBreathScale = 1;
        return;
    }

    const phase =
        (
            time %
            CORE_CONFIG.breathingDuration
        ) /
        CORE_CONFIG.breathingDuration;

    targetBreathScale =
        1 +
        (
            Math.sin(
                phase *
                Math.PI *
                2
            ) *
            0.012
        ) +
        (
            Math.sin(
                phase *
                Math.PI *
                4 +
                0.8
            ) *
            0.003
        );
}


function triggerHeartbeat() {
    if (
        reducedMotion ||
        !core ||
        isActivated
    ) {
        scheduleHeartbeat();
        return;
    }

    core.classList.remove(
        "oes-core--heartbeat"
    );

    void core.offsetWidth;

    core.classList.add(
        "oes-core--heartbeat"
    );

    window.setTimeout(() => {
        core?.classList.remove(
            "oes-core--heartbeat"
        );
    }, 1300);

    scheduleHeartbeat();
}


function scheduleHeartbeat() {
    clearTimer(
        heartbeatTimer
    );

    heartbeatTimer =
        window.setTimeout(
            triggerHeartbeat,
            randomBetween(
                CORE_CONFIG.heartbeatMinimumDelay,
                CORE_CONFIG.heartbeatMaximumDelay
            )
        );
}


/* ==========================================================================
   IDLE BEHAVIOR
============================================================================ */

function performIdleLook() {
    if (
        reducedMotion ||
        isDragging ||
        isActivated ||
        activeInterest ||
        isPointerActive
    ) {
        scheduleIdleBehavior();
        return;
    }

    const direction =
        Math.random() >
        0.5
            ? 1
            : -1;

    idleTargetRotationY =
        randomBetween(
            4,
            9
        ) *
        direction;

    idleTargetRotationX =
        randomBetween(
            -4,
            4
        );

    stage?.classList.add(
        "oes-core-stage--curious"
    );

    core?.classList.add(
        "oes-core--watching"
    );

    window.setTimeout(() => {
        idleTargetRotationX = 0;
        idleTargetRotationY = 0;

        stage?.classList.remove(
            "oes-core-stage--curious"
        );

        core?.classList.remove(
            "oes-core--watching"
        );
    }, randomBetween(
        CORE_CONFIG.idleLookDurationMinimum,
        CORE_CONFIG.idleLookDurationMaximum
    ));

    scheduleIdleBehavior();
}


function performIdlePulse() {
    if (
        reducedMotion ||
        isActivated
    ) {
        scheduleIdleBehavior();
        return;
    }

    stage?.classList.remove(
        "oes-core-stage--idle-pulse"
    );

    void stage?.offsetWidth;

    stage?.classList.add(
        "oes-core-stage--idle-pulse"
    );

    window.setTimeout(() => {
        stage?.classList.remove(
            "oes-core-stage--idle-pulse"
        );
    }, 1500);

    scheduleIdleBehavior();
}


function performImpatientBehavior() {
    if (
        reducedMotion ||
        isActivated ||
        isDragging
    ) {
        scheduleIdleBehavior();
        return;
    }

    stage?.classList.add(
        "oes-core-stage--impatient"
    );

    idleTargetRotationY =
        randomBetween(
            -6,
            6
        );

    idleTargetRotationX =
        randomBetween(
            -3,
            3
        );

    window.setTimeout(() => {
        stage?.classList.remove(
            "oes-core-stage--impatient"
        );

        idleTargetRotationX = 0;
        idleTargetRotationY = 0;
    }, 1800);

    scheduleIdleBehavior();
}


function chooseIdleBehavior() {
    const randomValue =
        Math.random();

    if (randomValue < 0.5) {
        performIdleLook();
        return;
    }

    if (randomValue < 0.78) {
        performIdlePulse();
        return;
    }

    if (randomValue < 0.9) {
        triggerBlink();
        return;
    }

    performImpatientBehavior();
}


function scheduleIdleBehavior() {
    clearTimer(
        idleBehaviorTimer
    );

    idleBehaviorTimer =
        window.setTimeout(
            chooseIdleBehavior,
            randomBetween(
                CORE_CONFIG.idleMinimumDelay,
                CORE_CONFIG.idleMaximumDelay
            )
        );
}


/* ==========================================================================
   SECTION ENGAGEMENT
============================================================================ */

function clearSectionEngagementTimers() {
    clearTimer(
        sectionEngagementTimer
    );

    clearTimer(
        deepSectionEngagementTimer
    );
}


function scheduleSectionEngagementMessages() {
    clearSectionEngagementTimers();

    const behavior =
        getSectionBehavior(
            activeSection
        );

    sectionEngagementTimer =
        window.setTimeout(
            () => {
                if (
                    activeInterest ||
                    isActivated
                ) {
                    return;
                }

                if (behavior.longMessage) {
                    setCoreMessage(
                        behavior.longMessage,
                        {
                            temporary: true,
                            duration: 6500
                        }
                    );
                }

                stage?.classList.add(
                    "oes-core-stage--observing"
                );

                window.setTimeout(() => {
                    stage?.classList.remove(
                        "oes-core-stage--observing"
                    );
                }, 2200);
            },
            CORE_CONFIG.sectionEngagementDelay
        );

    deepSectionEngagementTimer =
        window.setTimeout(
            () => {
                if (
                    activeInterest ||
                    isActivated
                ) {
                    return;
                }

                if (behavior.deepMessage) {
                    setCoreMessage(
                        behavior.deepMessage,
                        {
                            temporary: true,
                            duration: 7800
                        }
                    );
                }

                performIdlePulse();
            },
            CORE_CONFIG.deepSectionEngagementDelay
        );
}


/* ==========================================================================
   ACTIVATION
============================================================================ */

function activateCore() {
    if (
        !core ||
        !stage ||
        isActivated
    ) {
        return;
    }

    isActivated = true;

    clearTimer(
        activationTimer
    );

    core.classList.add(
        "oes-core--activated"
    );

    stage.classList.add(
        "oes-core-stage--activated"
    );

    heroScene?.classList.add(
        "hero-scene--core-activated"
    );

    targetActivationScale = 1.065;
    targetGlow = 1;
    targetOrbitSpeed = 1.72;
    targetPulseSpeed = 1.48;
    targetSpatialZ = 34;

    setCoreMessage(
        "OES Core activated.",
        {
            temporary: true,
            duration: 3900
        }
    );

    performSingleBlink();

    dispatchCoreEvent(
        "oes:coreactivated",
        {
            activated: true
        }
    );

    activationTimer =
        window.setTimeout(
            () => {
                isActivated = false;

                targetActivationScale = 1;

                core?.classList.remove(
                    "oes-core--activated"
                );

                stage?.classList.remove(
                    "oes-core-stage--activated"
                );

                heroScene?.classList.remove(
                    "hero-scene--core-activated"
                );

                if (activeInterest) {
                    applyBehavior(
                        getInterestBehavior(
                            activeInterest
                        ),
                        `interest:${activeInterest}`
                    );
                } else {
                    restoreSectionBehavior();
                }
            },
            CORE_CONFIG.activationDuration
        );
}


/* ==========================================================================
   DRAG INTERACTION
============================================================================ */

function handleCorePointerDown(event) {
    if (
        reducedMotion ||
        !core
    ) {
        activateCore();
        return;
    }

    isDragging = true;

    dragStartX =
        event.clientX;

    dragStartY =
        event.clientY;

    dragStartRotationX =
        currentRotationX;

    dragStartRotationY =
        currentRotationY;

    core.setPointerCapture?.(
        event.pointerId
    );

    core.classList.add(
        "oes-core--dragging",
        "oes-core--watching"
    );

    stage?.classList.add(
        "oes-core-stage--dragging"
    );
}


function handleCorePointerMove(event) {
    if (!isDragging) {
        return;
    }

    const deltaX =
        event.clientX -
        dragStartX;

    const deltaY =
        event.clientY -
        dragStartY;

    targetRotationY =
        clamp(
            dragStartRotationY +
            deltaX * 0.16,
            -CORE_CONFIG.maximumRotationY,
            CORE_CONFIG.maximumRotationY
        );

    targetRotationX =
        clamp(
            dragStartRotationX -
            deltaY * 0.16,
            -CORE_CONFIG.maximumRotationX,
            CORE_CONFIG.maximumRotationX
        );

    targetSpatialZ =
        clamp(
            Math.abs(deltaX) * 0.08 +
            Math.abs(deltaY) * 0.05,
            0,
            34
        );

    targetGlow = 0.94;
    targetOrbitSpeed = 1.52;
}


function handleCorePointerUp(event) {
    if (!isDragging) {
        return;
    }

    isDragging = false;

    core?.releasePointerCapture?.(
        event.pointerId
    );

    core?.classList.remove(
        "oes-core--dragging"
    );

    stage?.classList.remove(
        "oes-core-stage--dragging"
    );

    restoreSectionBehavior();
    activateCore();
}


/* ==========================================================================
   EVENT RESPONSES
============================================================================ */

function handleSectionChange(event) {
    const sectionId =
        event.detail?.sectionId;

    if (!sectionId) {
        return;
    }

    activeSection =
        sectionId;

    activeInterest = null;
    focusedElement = null;

    attentionTargetRotationX = 0;
    attentionTargetRotationY = 0;

    if (stage) {
        stage.dataset.coreSection =
            sectionId;

        delete stage.dataset.coreInterest;
    }

    applyBehavior(
        getSectionBehavior(sectionId),
        `section:${sectionId}`
    );

    restoreSectionMessage();
    scheduleSectionEngagementMessages();

    stage?.classList.remove(
        "oes-core-stage--section-change"
    );

    void stage?.offsetWidth;

    stage?.classList.add(
        "oes-core-stage--section-change"
    );

    performSingleBlink();

    window.setTimeout(() => {
        stage?.classList.remove(
            "oes-core-stage--section-change"
        );
    }, 1150);
}


function handleInterestChange(event) {
    const interest =
        event.detail?.interest;

    const element =
        event.detail?.element;

    if (!interest) {
        return;
    }

    clearTimer(
        attentionReleaseTimer
    );

    focusOnElement(
        element,
        interest
    );
}


function handleCoreMessageEvent(event) {
    const message =
        event.detail?.message;

    if (!message) {
        return;
    }

    const accent =
        event.detail?.accent;

    if (accent) {
        applyAccent(
            accent
        );
    }

    setCoreMessage(
        message,
        {
            temporary:
                Number(
                    event.detail?.duration
                ) > 0,

            duration:
                Number(
                    event.detail?.duration
                ) ||
                4200
        }
    );
}


function handleAwarenessReset() {
    restoreSectionBehavior();
    restoreSectionMessage();
}


function handleVisibilityChange() {
    isVisible =
        document.visibilityState ===
        "visible";

    if (isVisible) {
        lastFrameTime =
            performance.now();

        scheduleIdleBehavior();
        scheduleHeartbeat();
        scheduleBlink();
    }
}


/* ==========================================================================
   PHYSICS
============================================================================ */

function applySpring(
    current,
    target,
    velocity,
    strength,
    damping,
    deltaMultiplier
) {
    const force =
        (
            target -
            current
        ) *
        strength *
        deltaMultiplier;

    const nextVelocity =
        (
            velocity +
            force
        ) *
        damping;

    return {
        current:
            current +
            nextVelocity *
            deltaMultiplier,

        velocity:
            nextVelocity
    };
}


function updatePhysics(deltaTime) {
    const deltaMultiplier =
        clamp(
            deltaTime / 16.67,
            0.2,
            3
        );

    const rotationXSpring =
        applySpring(
            currentRotationX,
            targetRotationX,
            rotationVelocityX,
            isDragging
                ? 0.12
                : CORE_CONFIG.springStrength,
            CORE_CONFIG.springDamping,
            deltaMultiplier
        );

    currentRotationX =
        rotationXSpring.current;

    rotationVelocityX =
        rotationXSpring.velocity;

    const rotationYSpring =
        applySpring(
            currentRotationY,
            targetRotationY,
            rotationVelocityY,
            isDragging
                ? 0.12
                : CORE_CONFIG.springStrength,
            CORE_CONFIG.springDamping,
            deltaMultiplier
        );

    currentRotationY =
        rotationYSpring.current;

    rotationVelocityY =
        rotationYSpring.velocity;

    const translationXSpring =
        applySpring(
            currentTranslationX,
            targetTranslationX,
            translationVelocityX,
            CORE_CONFIG.translationSpringStrength,
            CORE_CONFIG.translationSpringDamping,
            deltaMultiplier
        );

    currentTranslationX =
        translationXSpring.current;

    translationVelocityX =
        translationXSpring.velocity;

    const translationYSpring =
        applySpring(
            currentTranslationY,
            targetTranslationY,
            translationVelocityY,
            CORE_CONFIG.translationSpringStrength,
            CORE_CONFIG.translationSpringDamping,
            deltaMultiplier
        );

    currentTranslationY =
        translationYSpring.current;

    translationVelocityY =
        translationYSpring.velocity;

    currentSpatialX +=
        (
            targetSpatialX -
            currentSpatialX
        ) *
        0.025 *
        deltaMultiplier;

    currentSpatialY +=
        (
            targetSpatialY -
            currentSpatialY
        ) *
        0.025 *
        deltaMultiplier;

    currentSpatialZ +=
        (
            targetSpatialZ -
            currentSpatialZ
        ) *
        0.03 *
        deltaMultiplier;

    currentGlow +=
        (
            targetGlow -
            currentGlow
        ) *
        0.065 *
        deltaMultiplier;

    currentActivationScale +=
        (
            targetActivationScale -
            currentActivationScale
        ) *
        0.09 *
        deltaMultiplier;

    currentBreathScale +=
        (
            targetBreathScale -
            currentBreathScale
        ) *
        0.04 *
        deltaMultiplier;

    currentOrbitSpeed +=
        (
            targetOrbitSpeed -
            currentOrbitSpeed
        ) *
        0.045 *
        deltaMultiplier;

    currentPulseSpeed +=
        (
            targetPulseSpeed -
            currentPulseSpeed
        ) *
        0.045 *
        deltaMultiplier;
}


/* ==========================================================================
   CSS OUTPUT
============================================================================ */

function renderCoreState() {
    if (!stage) {
        return;
    }

    setStageVariable(
        "--core-rotate-x",
        `${currentRotationX.toFixed(3)}deg`
    );

    setStageVariable(
        "--core-rotate-y",
        `${currentRotationY.toFixed(3)}deg`
    );

    setStageVariable(
        "--core-translate-x",
        `${currentTranslationX.toFixed(3)}px`
    );

    setStageVariable(
        "--core-translate-y",
        `${currentTranslationY.toFixed(3)}px`
    );

    setStageVariable(
        "--core-spatial-x",
        `${currentSpatialX.toFixed(3)}px`
    );

    setStageVariable(
        "--core-spatial-y",
        `${currentSpatialY.toFixed(3)}px`
    );

    setStageVariable(
        "--core-spatial-z",
        `${currentSpatialZ.toFixed(3)}px`
    );

    setStageVariable(
        "--core-depth-shadow-x",
        `${(
            currentRotationY *
            -0.65
        ).toFixed(3)}px`
    );

    setStageVariable(
        "--core-depth-shadow-y",
        `${(
            currentRotationX *
            0.65
        ).toFixed(3)}px`
    );

    setStageVariable(
        "--core-glow-strength",
        currentGlow.toFixed(3)
    );

    setStageVariable(
        "--core-activation-scale",
        (
            currentActivationScale *
            currentBreathScale
        ).toFixed(4)
    );

    setStageVariable(
        "--core-breath-scale",
        currentBreathScale.toFixed(4)
    );

    setStageVariable(
        "--core-orbit-speed",
        currentOrbitSpeed.toFixed(3)
    );

    setStageVariable(
        "--core-pulse-speed",
        currentPulseSpeed.toFixed(3)
    );

    setStageVariable(
        "--core-focus-x",
        attentionTargetRotationY.toFixed(3)
    );

    setStageVariable(
        "--core-focus-y",
        attentionTargetRotationX.toFixed(3)
    );

    if (orbitOuter) {
        orbitOuter.style.animationDuration =
            `${(
                22 /
                Math.max(
                    currentOrbitSpeed,
                    0.2
                )
            ).toFixed(2)}s`;
    }

    if (orbitMiddle) {
        orbitMiddle.style.animationDuration =
            `${(
                16 /
                Math.max(
                    currentOrbitSpeed,
                    0.2
                )
            ).toFixed(2)}s`;
    }

    if (orbitInner) {
        orbitInner.style.animationDuration =
            `${(
                12 /
                Math.max(
                    currentOrbitSpeed,
                    0.2
                )
            ).toFixed(2)}s`;
    }

    if (pulseElement) {
        pulseElement.style.animationDuration =
            `${(
                3 /
                Math.max(
                    currentPulseSpeed,
                    0.2
                )
            ).toFixed(2)}s`;
    }
}


/* ==========================================================================
   ANIMATION LOOP
============================================================================ */

function animate(time) {
    animationFrameId =
        window.requestAnimationFrame(
            animate
        );

    if (
        !isVisible ||
        reducedMotion
    ) {
        return;
    }

    const deltaTime =
        lastFrameTime === 0
            ? 16.67
            : clamp(
                time -
                lastFrameTime,
                0,
                CORE_CONFIG.maximumDeltaTime
            );

    lastFrameTime =
        time;

    if (
        time -
        lastPointerTime >
        CORE_CONFIG.pointerIdleDelay
    ) {
        isPointerActive = false;

        stage?.classList.remove(
            "oes-core-stage--tracking"
        );

        if (
            !focusedElement &&
            !isDragging
        ) {
            core?.classList.remove(
                "oes-core--watching"
            );
        }
    }

    updateBreathing(time);
    updateSpatialDrift(time);
    calculatePointerTargets();
    updatePhysics(deltaTime);
    renderCoreState();
}


/* ==========================================================================
   KEYBOARD SUPPORT
============================================================================ */

function handleCoreKeyDown(event) {
    if (
        event.key === "Enter" ||
        event.key === " "
    ) {
        event.preventDefault();
        activateCore();
        return;
    }

    const keyboardStep =
        3.4;

    switch (event.key) {
        case "ArrowLeft":
            event.preventDefault();
            idleTargetRotationY -=
                keyboardStep;
            break;

        case "ArrowRight":
            event.preventDefault();
            idleTargetRotationY +=
                keyboardStep;
            break;

        case "ArrowUp":
            event.preventDefault();
            idleTargetRotationX -=
                keyboardStep;
            break;

        case "ArrowDown":
            event.preventDefault();
            idleTargetRotationX +=
                keyboardStep;
            break;

        case "Escape":
            idleTargetRotationX = 0;
            idleTargetRotationY = 0;
            restoreSectionBehavior();
            restoreSectionMessage();
            break;

        default:
            return;
    }

    idleTargetRotationX =
        clamp(
            idleTargetRotationX,
            -CORE_CONFIG.maximumRotationX,
            CORE_CONFIG.maximumRotationX
        );

    idleTargetRotationY =
        clamp(
            idleTargetRotationY,
            -CORE_CONFIG.maximumRotationY,
            CORE_CONFIG.maximumRotationY
        );
}


/* ==========================================================================
   LISTENERS
============================================================================ */

function attachListeners() {
    window.addEventListener(
        "pointermove",
        handlePointerMove,
        {
            passive: true
        }
    );

    document.documentElement.addEventListener(
        "mouseleave",
        handlePointerLeaveWindow
    );

    window.addEventListener(
        "blur",
        handlePointerLeaveWindow
    );

    document.addEventListener(
        "visibilitychange",
        handleVisibilityChange
    );

    document.addEventListener(
        "oes:sectionchange",
        handleSectionChange
    );

    document.addEventListener(
        "oes:interestchange",
        handleInterestChange
    );

    document.addEventListener(
        "oes:coremessage",
        handleCoreMessageEvent
    );

    document.addEventListener(
        "oes:awarenessreset",
        handleAwarenessReset
    );

    document.addEventListener(
        "pointerout",
        (event) => {
            if (
                !focusedElement ||
                !(event.target instanceof Node)
            ) {
                return;
            }

            if (
                event.relatedTarget instanceof Node &&
                focusedElement.contains(
                    event.relatedTarget
                )
            ) {
                return;
            }

            releaseAttention();
        },
        {
            passive: true
        }
    );

    document.addEventListener(
        "focusout",
        releaseAttention
    );

    core.addEventListener(
        "pointerdown",
        handleCorePointerDown
    );

    core.addEventListener(
        "pointermove",
        handleCorePointerMove
    );

    core.addEventListener(
        "pointerup",
        handleCorePointerUp
    );

    core.addEventListener(
        "pointercancel",
        handleCorePointerUp
    );

    core.addEventListener(
        "dblclick",
        activateCore
    );

    core.addEventListener(
        "keydown",
        handleCoreKeyDown
    );
}


/* ==========================================================================
   REDUCED MOTION
============================================================================ */

function initializeReducedMotionState() {
    reducedMotion =
        prefersReducedMotion();

    if (!reducedMotion) {
        return;
    }

    currentRotationX = 0;
    currentRotationY = 0;
    targetRotationX = 0;
    targetRotationY = 0;

    currentTranslationX = 0;
    currentTranslationY = 0;
    targetTranslationX = 0;
    targetTranslationY = 0;

    currentSpatialX = 0;
    currentSpatialY = 0;
    currentSpatialZ = 0;

    targetSpatialX = 0;
    targetSpatialY = 0;
    targetSpatialZ = 0;

    currentBreathScale = 1;
    targetBreathScale = 1;

    setEyeOpenAmount(1);
    renderCoreState();

    stage?.classList.add(
        "oes-core-stage--reduced-motion"
    );
}


/* ==========================================================================
   PUBLIC API
============================================================================ */

export function focusOESCoreOnElement(
    element,
    interest = null
) {
    focusOnElement(
        element,
        interest
    );
}


export function releaseOESCoreFocus() {
    releaseAttention();
}


export function activateOESCore() {
    activateCore();
}


export function blinkOESCore() {
    return triggerBlink();
}


export function setOESCoreSection(
    sectionId
) {
    if (!sectionId) {
        return;
    }

    handleSectionChange({
        detail: {
            sectionId
        }
    });
}


export function getOESCoreState() {
    return {
        initialized,
        activeSection,
        activeInterest,
        isActivated,
        isDragging,
        isBlinking,
        isPointerActive,
        isPointerInsideWindow,
        reducedMotion,

        rotation: {
            x: currentRotationX,
            y: currentRotationY
        },

        translation: {
            x: currentTranslationX,
            y: currentTranslationY
        },

        spatial: {
            x: currentSpatialX,
            y: currentSpatialY,
            z: currentSpatialZ
        },

        glow: currentGlow,
        orbitSpeed: currentOrbitSpeed,
        pulseSpeed: currentPulseSpeed
    };
}


/* ==========================================================================
   INITIALIZATION
============================================================================ */

export function initializeOESCore() {
    if (initialized) {
        return;
    }

    core =
        document.querySelector(
            "[data-oes-core]"
        ) ||
        document.querySelector(
            ".oes-core"
        );

    if (!core) {
        return;
    }

    stage =
        document.querySelector(
            "[data-oes-core-stage]"
        ) ||
        core.closest(
            ".oes-core-stage"
        ) ||
        core.parentElement;

    heroScene =
        document.querySelector(
            "[data-detroit-scene]"
        ) ||
        document.querySelector(
            ".hero-scene"
        );

    coreMessage =
        document.querySelector(
            "[data-core-message]"
        );

    orbitOuter =
        document.querySelector(
            ".core-orbit--outer"
        );

    orbitMiddle =
        document.querySelector(
            ".core-orbit--middle"
        );

    orbitInner =
        document.querySelector(
            ".core-orbit--inner"
        );

    pulseElement =
        core.querySelector(
            ".oes-core__pulse"
        );

    initialized = true;

    createEyelids();
    initializeReducedMotionState();

    applyBehavior(
        getSectionBehavior(
            activeSection
        ),
        "initialization"
    );

    restoreSectionMessage();
    attachListeners();

    scheduleIdleBehavior();
    scheduleHeartbeat();
    scheduleBlink();
    scheduleSectionEngagementMessages();

    if (!reducedMotion) {
        animationFrameId =
            window.requestAnimationFrame(
                animate
            );
    }

    stage?.classList.add(
        "oes-core-stage--ready"
    );

    core.classList.add(
        "oes-core--ready"
    );

    dispatchCoreEvent(
        "oes:corestatechange",
        {
            source: "initialization",
            initialized: true
        }
    );
}