/*
===============================================================================
FILE: static/js/oes-core.js

PURPOSE:
    Controls the intelligent, human-like behavior of the interactive OES Core.

UPDATED:
    July 15, 2026

RESPONSIBILITIES:
    [x] Smooth pointer tracking
    [x] Slow eye-like attention movement
    [x] Breathing and heartbeat behavior
    [x] Idle curiosity actions
    [x] Section-aware color and motion changes
    [x] Interest-aware focus toward hovered content
    [x] Core activation reactions
    [x] Orbit-speed control
    [x] Impatient and curious micro-behaviors
    [x] Long-section engagement messages
    [x] Keyboard and touch support
    [x] Reduced-motion support
    [x] Safe cleanup and reinitialization

EVENTS RECEIVED:
    oes:sectionchange
    oes:interestchange
    oes:coremessage
    oes:awarenessreset

EVENTS DISPATCHED:
    oes:coreactivated
    oes:corestatechange
    oes:coreattention

CSS VARIABLES CONTROLLED:
    --core-rotate-x
    --core-rotate-y
    --core-translate-x
    --core-translate-y
    --core-glow-strength
    --core-activation-scale
    --core-breath-scale
    --core-orbit-speed
    --core-pulse-speed
    --core-focus-x
    --core-focus-y
    --awareness-primary
    --awareness-secondary
    --awareness-glow

IMPORTANT RULES:
    [x] Movement must feel delayed and organic
    [x] The Core must never follow the pointer exactly
    [x] Behavior must remain subtle
    [x] The Core must not block navigation
    [x] Reduced-motion settings must be respected
    [x] Missing optional elements must not break the page
===============================================================================
*/

/* ==========================================================================
   CONFIGURATION
============================================================================ */

const CORE_CONFIG = {
    pointerRotationX: 7,
    pointerRotationY: 9,

    attentionRotationX: 5,
    attentionRotationY: 7,

    maximumRotationX: 13,
    maximumRotationY: 16,

    pointerTranslationX: 8,
    pointerTranslationY: 6,

    springStrength: 0.055,
    springDamping: 0.86,

    attentionSpringStrength: 0.075,

    breathingDuration: 9200,
    heartbeatMinimumDelay: 15000,
    heartbeatMaximumDelay: 30000,

    idleMinimumDelay: 9000,
    idleMaximumDelay: 19000,

    idleLookDurationMinimum: 1200,
    idleLookDurationMaximum: 2600,

    sectionEngagementDelay: 14000,
    deepSectionEngagementDelay: 26000,

    activationDuration: 1300,
    attentionReleaseDelay: 550,

    pointerIdleDelay: 3400,

    maximumDeltaTime: 50
};

const SECTION_BEHAVIORS = {
    home: {
        accent: "blue",
        glow: 0.58,
        orbitSpeed: 1,
        pulseSpeed: 1,
        idleEnergy: 0.42,
        longMessage: "Detroit is still building.",
        deepMessage: "Every challenge is another place to build."
    },

    products: {
        accent: "green",
        glow: 0.68,
        orbitSpeed: 1.15,
        pulseSpeed: 1.1,
        idleEnergy: 0.56,
        longMessage: "Two products. One execution system.",
        deepMessage: "Working systems reveal more than unfinished ideas."
    },

    "client-work": {
        accent: "pink",
        glow: 0.62,
        orbitSpeed: 0.95,
        pulseSpeed: 0.92,
        idleEnergy: 0.48,
        longMessage: "Client development starts with a real business need.",
        deepMessage: "Good software should strengthen the business behind it."
    },

    services: {
        accent: "blue",
        glow: 0.64,
        orbitSpeed: 1.05,
        pulseSpeed: 1,
        idleEnergy: 0.5,
        longMessage: "Choose a capability. Start with the problem.",
        deepMessage: "Version 1 should prove what matters most."
    },

    government: {
        accent: "government",
        glow: 0.57,
        orbitSpeed: 0.8,
        pulseSpeed: 0.78,
        idleEnergy: 0.4,
        longMessage: "Technology should solve measurable public problems.",
        deepMessage: "Clear outcomes. Responsible boundaries. Practical delivery."
    },

    community: {
        accent: "community",
        glow: 0.63,
        orbitSpeed: 0.9,
        pulseSpeed: 0.88,
        idleEnergy: 0.52,
        longMessage: "Detroit grows when more people can participate.",
        deepMessage: "Technology, education and mentorship belong together."
    },

    research: {
        accent: "purple",
        glow: 0.76,
        orbitSpeed: 1.32,
        pulseSpeed: 1.18,
        idleEnergy: 0.68,
        longMessage: "Still exploring?",
        deepMessage: "There is always another layer."
    },

    about: {
        accent: "blue",
        glow: 0.52,
        orbitSpeed: 0.84,
        pulseSpeed: 0.82,
        idleEnergy: 0.38,
        longMessage: "Purpose, imagination and execution.",
        deepMessage: "Imperfections are places where better systems can begin."
    },

    contact: {
        accent: "green",
        glow: 0.7,
        orbitSpeed: 1.05,
        pulseSpeed: 1.08,
        idleEnergy: 0.58,
        longMessage: "Ready when you are.",
        deepMessage: "Bring OES the idea."
    }
};

const INTEREST_BEHAVIORS = {
    chaseingreen: {
        accent: "green",
        glow: 0.82,
        orbitSpeed: 1.45,
        pulseSpeed: 1.25,
        focusStrength: 1,
        message: "Analyzing trading systems."
    },

    lottovate: {
        accent: "yellow",
        glow: 0.8,
        orbitSpeed: 1.38,
        pulseSpeed: 1.18,
        focusStrength: 0.95,
        message: "Scanning prediction patterns."
    },

    client: {
        accent: "pink",
        glow: 0.72,
        orbitSpeed: 1.02,
        pulseSpeed: 1,
        focusStrength: 0.86,
        message: "Client development environment active."
    },

    ai: {
        accent: "purple",
        glow: 0.82,
        orbitSpeed: 1.5,
        pulseSpeed: 1.22,
        focusStrength: 1,
        message: "Applied intelligence loaded."
    },

    mobile: {
        accent: "blue",
        glow: 0.7,
        orbitSpeed: 1.12,
        pulseSpeed: 1.04,
        focusStrength: 0.86,
        message: "Native mobile systems ready."
    },

    web: {
        accent: "blue",
        glow: 0.65,
        orbitSpeed: 1,
        pulseSpeed: 0.96,
        focusStrength: 0.82,
        message: "Connected web systems ready."
    },

    data: {
        accent: "green",
        glow: 0.76,
        orbitSpeed: 1.2,
        pulseSpeed: 1.08,
        focusStrength: 0.9,
        message: "Organizing data into action."
    },

    saas: {
        accent: "purple",
        glow: 0.74,
        orbitSpeed: 1.22,
        pulseSpeed: 1.06,
        focusStrength: 0.88,
        message: "Platform architecture loaded."
    },

    automation: {
        accent: "green",
        glow: 0.72,
        orbitSpeed: 1.28,
        pulseSpeed: 1.14,
        focusStrength: 0.9,
        message: "Workflow automation active."
    },

    consulting: {
        accent: "blue",
        glow: 0.58,
        orbitSpeed: 0.86,
        pulseSpeed: 0.84,
        focusStrength: 0.78,
        message: "Defining scope and priorities."
    },

    training: {
        accent: "community",
        glow: 0.7,
        orbitSpeed: 0.92,
        pulseSpeed: 0.9,
        focusStrength: 0.84,
        message: "Learning systems connected."
    },

    government: {
        accent: "government",
        glow: 0.66,
        orbitSpeed: 0.78,
        pulseSpeed: 0.76,
        focusStrength: 0.82,
        message: "Public-sector capabilities loaded."
    },

    prototype: {
        accent: "government",
        glow: 0.74,
        orbitSpeed: 1.08,
        pulseSpeed: 1,
        focusStrength: 0.92,
        message: "Prototype validation mode."
    },

    academy: {
        accent: "community",
        glow: 0.7,
        orbitSpeed: 0.96,
        pulseSpeed: 0.9,
        focusStrength: 0.9,
        message: "Human-centered development connected."
    },

    techtown: {
        accent: "community",
        glow: 0.68,
        orbitSpeed: 0.94,
        pulseSpeed: 0.88,
        focusStrength: 0.88,
        message: "Detroit founder ecosystem connected."
    },

    "black-tech": {
        accent: "community",
        glow: 0.74,
        orbitSpeed: 1.02,
        pulseSpeed: 0.96,
        focusStrength: 0.92,
        message: "Black technology ecosystem connected."
    },

    crossroads: {
        accent: "community",
        glow: 0.66,
        orbitSpeed: 0.86,
        pulseSpeed: 0.82,
        focusStrength: 0.86,
        message: "Community technology support connected."
    },

    mentorship: {
        accent: "community",
        glow: 0.72,
        orbitSpeed: 0.92,
        pulseSpeed: 0.94,
        focusStrength: 0.9,
        message: "Technology, athletics and mentorship connected."
    },

    research: {
        accent: "purple",
        glow: 0.9,
        orbitSpeed: 1.6,
        pulseSpeed: 1.32,
        focusStrength: 1,
        message: "Experimental systems active."
    },

    contact: {
        accent: "green",
        glow: 0.82,
        orbitSpeed: 1.1,
        pulseSpeed: 1.14,
        focusStrength: 0.92,
        message: "Ready to begin."
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
        glow: "rgba(250, 204, 21, 0.48)"
    },

    pink: {
        primary: "#ec4899",
        secondary: "#a855f7",
        glow: "rgba(236, 72, 153, 0.48)"
    },

    purple: {
        primary: "#a855f7",
        secondary: "#38bdf8",
        glow: "rgba(168, 85, 247, 0.5)"
    },

    government: {
        primary: "#60a5fa",
        secondary: "#2563eb",
        glow: "rgba(96, 165, 250, 0.48)"
    },

    community: {
        primary: "#34d399",
        secondary: "#f59e0b",
        glow: "rgba(52, 211, 153, 0.46)"
    }
};

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

let reducedMotion = false;
let isVisible = true;
let isPointerInsideWindow = true;
let isPointerActive = false;
let isDragging = false;
let isActivated = false;

let activeSection = "home";
let activeInterest = null;
let focusedElement = null;

let lastFrameTime = 0;
let lastPointerTime = 0;

let sectionEngagementTimer = null;
let deepSectionEngagementTimer = null;
let idleBehaviorTimer = null;
let heartbeatTimer = null;
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

let targetGlow = 0.58;
let currentGlow = 0.58;

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
   GENERAL UTILITIES
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
    if (!stage) {
        return;
    }

    stage.style.setProperty(
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
   ACCENT AND VISUAL STATE
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

function applyBehavior(behavior, source = "unknown") {
    if (!behavior) {
        return;
    }

    applyAccent(
        behavior.accent ||
        "blue"
    );

    targetGlow =
        Number.isFinite(behavior.glow)
            ? behavior.glow
            : targetGlow;

    targetOrbitSpeed =
        Number.isFinite(
            behavior.orbitSpeed
        )
            ? behavior.orbitSpeed
            : targetOrbitSpeed;

    targetPulseSpeed =
        Number.isFinite(
            behavior.pulseSpeed
        )
            ? behavior.pulseSpeed
            : targetPulseSpeed;

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

    if (stage) {
        delete stage.dataset.coreInterest;

        stage.classList.remove(
            "oes-core-stage--focused",
            "oes-core-stage--curious"
        );
    }

    applyBehavior(
        getSectionBehavior(activeSection),
        `section:${activeSection}`
    );

    attentionTargetRotationX = 0;
    attentionTargetRotationY = 0;
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
    if (!message || !coreMessage) {
        return;
    }

    clearTimer(temporaryMessageTimer);

    coreMessage.classList.add(
        "core-message--changing"
    );

    window.setTimeout(() => {
        if (!coreMessage) {
            return;
        }

        coreMessage.textContent = message;

        coreMessage.classList.remove(
            "core-message--changing"
        );
    }, 90);

    if (temporary) {
        temporaryMessageTimer =
            window.setTimeout(
                () => {
                    restoreSectionMessage();
                },
                duration
            );
    }
}

function restoreSectionMessage() {
    const behavior =
        getSectionBehavior(activeSection);

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

    const sectionMessages = {
        home: "Move. Touch. Explore.",
        products: "OES product systems active.",
        "client-work": "Client development mode.",
        services: "Choose a capability.",
        government: "Public-sector capabilities loaded.",
        community: "Detroit ecosystem connected.",
        research: "Experimental systems active.",
        about: "Detroit built. Execution focused.",
        contact: "Ready when you are."
    };

    setCoreMessage(
        sectionMessages[activeSection] ||
        behavior.longMessage ||
        "OES systems online."
    );
}

/* ==========================================================================
   POINTER AWARENESS
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
            (pointerX - centerX) /
            Math.max(rect.width, 1),
            -1.3,
            1.3
        );

    const normalizedY =
        clamp(
            (pointerY - centerY) /
            Math.max(rect.height, 1),
            -1.3,
            1.3
        );

    const pointerInfluence =
        isPointerActive
            ? 1
            : 0.25;

    targetRotationY =
        normalizedX *
        CORE_CONFIG.pointerRotationY *
        pointerInfluence +
        attentionTargetRotationY +
        idleTargetRotationY;

    targetRotationX =
        -normalizedY *
        CORE_CONFIG.pointerRotationX *
        pointerInfluence +
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

function handlePointerMove(event) {
    pointerX = event.clientX;
    pointerY = event.clientY;

    lastPointerTime =
        performance.now();

    isPointerActive = true;
    isPointerInsideWindow = true;

    if (
        !isDragging &&
        stage
    ) {
        stage.classList.add(
            "oes-core-stage--tracking"
        );
    }
}

function handlePointerLeaveWindow() {
    isPointerInsideWindow = false;
    isPointerActive = false;

    targetTranslationX = 0;
    targetTranslationY = 0;

    if (stage) {
        stage.classList.remove(
            "oes-core-stage--tracking"
        );
    }
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

function calculateAttentionRotation(element) {
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

    const targetCenterX =
        targetRect.left +
        targetRect.width / 2;

    const targetCenterY =
        targetRect.top +
        targetRect.height / 2;

    const coreCenterX =
        coreRect.left +
        coreRect.width / 2;

    const coreCenterY =
        coreRect.top +
        coreRect.height / 2;

    const horizontalDistance =
        targetCenterX -
        coreCenterX;

    const verticalDistance =
        targetCenterY -
        coreCenterY;

    const normalizedX =
        clamp(
            horizontalDistance /
            Math.max(window.innerWidth, 1),
            -1,
            1
        );

    const normalizedY =
        clamp(
            verticalDistance /
            Math.max(window.innerHeight, 1),
            -1,
            1
        );

    return {
        x:
            -normalizedY *
            CORE_CONFIG.attentionRotationX,

        y:
            normalizedX *
            CORE_CONFIG.attentionRotationY
    };
}

function focusOnElement(
    element,
    interest = null
) {
    const target =
        findAttentionTarget(element);

    if (!target) {
        return;
    }

    focusedElement = target;

    const rotation =
        calculateAttentionRotation(target);

    const behavior =
        getInterestBehavior(interest);

    const focusStrength =
        behavior?.focusStrength || 0.8;

    attentionTargetRotationX =
        rotation.x *
        focusStrength;

    attentionTargetRotationY =
        rotation.y *
        focusStrength;

    activeInterest = interest;

    if (stage) {
        stage.classList.add(
            "oes-core-stage--focused"
        );

        if (interest) {
            stage.dataset.coreInterest =
                interest;
        }
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
    clearTimer(attentionReleaseTimer);

    attentionReleaseTimer =
        window.setTimeout(
            () => {
                attentionTargetRotationX = 0;
                attentionTargetRotationY = 0;

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

    const breathPhase =
        (
            time %
            CORE_CONFIG.breathingDuration
        ) /
        CORE_CONFIG.breathingDuration;

    const primaryBreath =
        Math.sin(
            breathPhase *
            Math.PI *
            2
        );

    const secondaryBreath =
        Math.sin(
            breathPhase *
            Math.PI *
            4 +
            0.8
        );

    targetBreathScale =
        1 +
        primaryBreath * 0.009 +
        secondaryBreath * 0.0025;
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
    clearTimer(heartbeatTimer);

    const delay =
        randomBetween(
            CORE_CONFIG.heartbeatMinimumDelay,
            CORE_CONFIG.heartbeatMaximumDelay
        );

    heartbeatTimer =
        window.setTimeout(
            triggerHeartbeat,
            delay
        );
}

/* ==========================================================================
   IDLE CURIOSITY
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
        Math.random() > 0.5
            ? 1
            : -1;

    idleTargetRotationY =
        randomBetween(2.5, 6) *
        direction;

    idleTargetRotationX =
        randomBetween(-2.5, 2.5);

    if (stage) {
        stage.classList.add(
            "oes-core-stage--curious"
        );
    }

    const duration =
        randomBetween(
            CORE_CONFIG.idleLookDurationMinimum,
            CORE_CONFIG.idleLookDurationMaximum
        );

    window.setTimeout(() => {
        idleTargetRotationX = 0;
        idleTargetRotationY = 0;

        stage?.classList.remove(
            "oes-core-stage--curious"
        );
    }, duration);

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
        randomBetween(-3.5, 3.5);

    idleTargetRotationX =
        randomBetween(-1.8, 1.8);

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

    if (randomValue < 0.52) {
        performIdleLook();
        return;
    }

    if (randomValue < 0.82) {
        performIdlePulse();
        return;
    }

    performImpatientBehavior();
}

function scheduleIdleBehavior() {
    clearTimer(idleBehaviorTimer);

    const delay =
        randomBetween(
            CORE_CONFIG.idleMinimumDelay,
            CORE_CONFIG.idleMaximumDelay
        );

    idleBehaviorTimer =
        window.setTimeout(
            chooseIdleBehavior,
            delay
        );
}

/* ==========================================================================
   SECTION ENGAGEMENT
============================================================================ */

function clearSectionEngagementTimers() {
    clearTimer(sectionEngagementTimer);
    clearTimer(deepSectionEngagementTimer);
}

function scheduleSectionEngagementMessages() {
    clearSectionEngagementTimers();

    const behavior =
        getSectionBehavior(activeSection);

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
   CORE ACTIVATION
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

    clearTimer(activationTimer);

    core.classList.add(
        "oes-core--activated"
    );

    stage.classList.add(
        "oes-core-stage--activated"
    );

    heroScene?.classList.add(
        "hero-scene--core-activated"
    );

    targetActivationScale = 1.045;
    targetGlow = 1;
    targetOrbitSpeed = 1.65;
    targetPulseSpeed = 1.4;

    setCoreMessage(
        "OES Core activated.",
        {
            temporary: true,
            duration: 3800
        }
    );

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

    dragStartX = event.clientX;
    dragStartY = event.clientY;

    dragStartRotationX =
        currentRotationX;

    dragStartRotationY =
        currentRotationY;

    core.setPointerCapture?.(
        event.pointerId
    );

    core.classList.add(
        "oes-core--dragging"
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
            deltaX * 0.1,
            -CORE_CONFIG.maximumRotationY,
            CORE_CONFIG.maximumRotationY
        );

    targetRotationX =
        clamp(
            dragStartRotationX -
            deltaY * 0.1,
            -CORE_CONFIG.maximumRotationX,
            CORE_CONFIG.maximumRotationX
        );

    targetGlow = 0.88;
    targetOrbitSpeed = 1.45;
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

    activeSection = sectionId;

    activeInterest = null;
    focusedElement = null;

    if (stage) {
        stage.dataset.coreSection =
            sectionId;

        delete stage.dataset.coreInterest;
    }

    attentionTargetRotationX = 0;
    attentionTargetRotationY = 0;

    applyBehavior(
        getSectionBehavior(sectionId),
        `section:${sectionId}`
    );

    scheduleSectionEngagementMessages();

    stage?.classList.remove(
        "oes-core-stage--section-change"
    );

    void stage?.offsetWidth;

    stage?.classList.add(
        "oes-core-stage--section-change"
    );

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

    clearTimer(attentionReleaseTimer);

    activeInterest = interest;

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
        applyAccent(accent);
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
    }
}

/* ==========================================================================
   ANIMATION PHYSICS
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
        (target - current) *
        strength *
        deltaMultiplier;

    const nextVelocity =
        (
            velocity +
            force
        ) *
        damping;

    const nextCurrent =
        current +
        nextVelocity *
        deltaMultiplier;

    return {
        current: nextCurrent,
        velocity: nextVelocity
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
                ? 0.11
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
                ? 0.11
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
            0.045,
            0.84,
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
            0.045,
            0.84,
            deltaMultiplier
        );

    currentTranslationY =
        translationYSpring.current;

    translationVelocityY =
        translationYSpring.velocity;

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

    const pulse =
        core.querySelector(
            ".oes-core__pulse"
        );

    if (pulse) {
        pulse.style.animationDuration =
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
   MAIN ANIMATION LOOP
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

    lastFrameTime = time;

    if (
        time -
        lastPointerTime >
        CORE_CONFIG.pointerIdleDelay
    ) {
        isPointerActive = false;

        stage?.classList.remove(
            "oes-core-stage--tracking"
        );
    }

    updateBreathing(time);

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

    const keyboardStep = 2.4;

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
            break;
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
   DOM LISTENERS
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
        () => {
            releaseAttention();
        }
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

    currentBreathScale = 1;
    targetBreathScale = 1;

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
        ) ||
        document.querySelector(
            ".orb"
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

    initialized = true;

    initializeReducedMotionState();

    applyBehavior(
        getSectionBehavior(activeSection),
        "initialization"
    );

    attachListeners();

    scheduleIdleBehavior();
    scheduleHeartbeat();
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