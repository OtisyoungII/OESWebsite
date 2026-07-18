/*
===============================================================================
FILE: static/js/oes-core-companion.js

PURPOSE:
    Allows the WebGL OES Core to leave the Detroit hero and become a movable,
    page-aware spatial companion throughout the OES website.

UPDATED:
    July 16, 2026

RESPONSIBILITIES:
    [x] Keep the OES Core visible after leaving the hero
    [x] Shrink the Core into a floating companion
    [x] Return the Core to its original hero position
    [x] Preserve the existing WebGL canvas and Core behavior
    [x] Reuse the original Core instead of creating a duplicate
    [x] React to the active homepage section
    [x] Travel between safe screen positions
    [x] Avoid important page content where possible
    [x] Support mouse dragging
    [x] Support touch dragging
    [x] Separate sphere spinning from companion movement
    [x] Provide a dedicated outer movement handle
    [x] Keep the companion inside the viewport
    [x] Dock to the nearest safe side after dragging
    [x] Support automatic left/right repositioning
    [x] Avoid the website navigation and footer
    [x] Respect reduced-motion preferences
    [x] Preserve keyboard accessibility
    [x] Restore the original DOM structure during cleanup
    [x] Require no local storage or personal tracking

ARCHITECTURE:
    static/js/oes-core.js
        Controls behavior, messages, awareness, activation, and intelligence.

    static/js/oes-core-3d.js
        Controls the three-dimensional sphere, iris, eyelids, lighting,
        particles, camera, and drag-to-spin behavior.

    static/js/oes-core-companion.js
        Controls where the complete Core exists on the page.

INTERACTION:
    Drag the center of the Core:
        Rotates the three-dimensional sphere.

    Drag the outer movement handle:
        Moves the complete Core around the viewport.

    Tap the Core:
        Preserves the existing activation behavior.

    Scroll away from the hero:
        The Core becomes a smaller floating companion.

    Return to the hero:
        The Core returns to its original stage.

EVENTS RECEIVED:
    oes:core3dready
    oes:core3dfallback
    oes:sectionchange
    oes:interestchange
    oes:coreactivated

EVENTS DISPATCHED:
    oes:companionready
    oes:companionenter
    oes:companionleave
    oes:companionmovestart
    oes:companionmove
    oes:companionmoveend
    oes:companiondock
    oes:companionsectionchange

IMPORTANT RULES:
    [x] Do not clone the WebGL canvas
    [x] Move the original Core element
    [x] Do not interfere with drag-to-spin
    [x] Do not activate companion mode before WebGL is ready
    [x] Do not trap keyboard focus
    [x] Do not save visitor position between browser sessions
    [x] Mobile users receive the same companion experience
    [x] Reduced-motion users receive immediate position changes
===============================================================================
*/

/* ==========================================================================
   CONFIGURATION
============================================================================ */

const COMPANION_CONFIG = {
    desktopSize: 330,
    tabletSize: 280,
    mobileSize: 230,
    landscapeMobileSize: 200,
    smallMobileSize: 200,

    viewportMarginDesktop: 28,
    viewportMarginMobile: 14,

    headerClearanceDesktop: 104,
    headerClearanceMobile: 82,

    footerClearance: 28,

    dockGap: 22,

    heroExitRatio: 0.28,
    heroReturnRatio: 0.58,

    dragThreshold: 5,
    longPressDuration: 460,

    automaticMoveDuration: 620,
    manualDockDuration: 440,
    heroReturnDuration: 520,

    obstaclePadding: 18,

    sectionVerticalPositions: {
        home: 0.48,
        products: 0.34,
        "client-work": 0.54,
        services: 0.4,
        government: 0.58,
        community: 0.42,
        research: 0.56,
        about: 0.38,
        contact: 0.48
    },

    sectionPreferredSides: {
        home: "right",
        products: "right",
        "client-work": "left",
        services: "right",
        government: "left",
        community: "right",
        research: "left",
        about: "right",
        contact: "left"
    },

    obstacleSelectors: [
        "[data-site-header]",
        ".site-header",
        ".primary-navigation",
        ".hero-copy-block",
        ".section-heading",
        ".product-card",
        ".client-spotlight",
        ".service-card",
        ".capability-card",
        ".community-card",
        ".research-terminal",
        ".contact-panel",
        ".site-footer",
        "footer"
    ]
};

/* ==========================================================================
   MODULE STATE
============================================================================ */

let initialized = false;
let destroyed = false;
let companionActive = false;
let webGLReady = false;
let reducedMotion = false;

let heroSection = null;
let originalStage = null;
let coreButton = null;

let originalParent = null;
let originalNextSibling = null;
let originalInlineStyle = null;

let placeholder = null;
let portal = null;
let visualHost = null;
let movementHandle = null;
let movementHandleIcon = null;

let heroObserver = null;
let resizeObserver = null;

let currentSectionId = "home";
let currentSide = "right";

let currentX = 0;
let currentY = 0;
let targetX = 0;
let targetY = 0;

let currentSize = 0;

let manualPosition = false;
let automaticMovementLocked = false;

let isDragging = false;
let dragPointerId = null;
let dragStarted = false;

let dragStartClientX = 0;
let dragStartClientY = 0;

let dragStartX = 0;
let dragStartY = 0;

let longPressTimer = null;
let movementAnimationFrame = null;

let latestHeroRatio = 1;

/* ==========================================================================
   GENERAL UTILITIES
============================================================================ */

function clamp(
    value,
    minimum,
    maximum
) {
    return Math.min(
        Math.max(
            value,
            minimum
        ),
        maximum
    );
}

function lerp(
    start,
    end,
    amount
) {
    return (
        start +
        (
            end -
            start
        ) *
        amount
    );
}

function easeOutCubic(value) {
    return (
        1 -
        Math.pow(
            1 - value,
            3
        )
    );
}

function prefersReducedMotion() {
    return window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;
}

function isMobileViewport() {
    return window.innerWidth <= 760;
}

function isLandscapeMobileViewport() {
    return (
        window.innerHeight <= 560 &&
        window.innerWidth >
            window.innerHeight &&
        navigator.maxTouchPoints > 0
    );
}

function isSmallMobileViewport() {
    return window.innerWidth <= 480;
}

function isTabletViewport() {
    return (
        window.innerWidth > 760 &&
        window.innerWidth <= 1100
    );
}

function clearTimer(timerId) {
    if (timerId) {
        window.clearTimeout(timerId);
    }
}

function cancelMovementAnimation() {
    if (!movementAnimationFrame) {
        return;
    }

    window.cancelAnimationFrame(
        movementAnimationFrame
    );

    movementAnimationFrame = null;
}

function dispatchCompanionEvent(
    name,
    detail = {}
) {
    document.dispatchEvent(
        new CustomEvent(
            name,
            {
                detail: {
                    initialized,
                    active:
                        companionActive,
                    sectionId:
                        currentSectionId,
                    side:
                        currentSide,
                    position: {
                        x: currentX,
                        y: currentY
                    },
                    size:
                        currentSize,
                    manualPosition,
                    ...detail
                }
            }
        )
    );
}

/* ==========================================================================
   RESPONSIVE VALUES
============================================================================ */

function getCompanionSize() {
    if (isLandscapeMobileViewport()) {
        return COMPANION_CONFIG
            .landscapeMobileSize;
    }

    if (isSmallMobileViewport()) {
        return COMPANION_CONFIG
            .smallMobileSize;
    }

    if (isMobileViewport()) {
        return COMPANION_CONFIG
            .mobileSize;
    }

    if (isTabletViewport()) {
        return COMPANION_CONFIG
            .tabletSize;
    }

    return COMPANION_CONFIG
        .desktopSize;
}

function getViewportMargin() {
    return isMobileViewport()
        ? COMPANION_CONFIG
            .viewportMarginMobile
        : COMPANION_CONFIG
            .viewportMarginDesktop;
}

function getHeaderClearance() {
    const header =
        document.querySelector(
            "[data-site-header], .site-header"
        );

    const headerHeight =
        header?.getBoundingClientRect()
            .height || 0;

    const configuredClearance =
        isMobileViewport()
            ? COMPANION_CONFIG
                .headerClearanceMobile
            : COMPANION_CONFIG
                .headerClearanceDesktop;

    return Math.max(
        configuredClearance,
        headerHeight +
            getViewportMargin()
    );
}

/* ==========================================================================
   STYLE INSTALLATION
============================================================================ */

function installCompanionStyles() {
    if (
        document.getElementById(
            "oes-core-companion-styles"
        )
    ) {
        return;
    }

    const style =
        document.createElement(
            "style"
        );

    style.id =
        "oes-core-companion-styles";

    style.textContent = `
        .oes-core-companion {
            --companion-size: 330px;
            --companion-x: 0px;
            --companion-y: 0px;

            position: fixed;
            top: 0;
            left: 0;
            z-index: 850;
            width: var(--companion-size);
            height: var(--companion-size);
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
            transform:
                translate3d(
                    var(--companion-x),
                    var(--companion-y),
                    0
                )
                scale(0.78);
            transform-origin: center;
            transition:
                opacity 240ms ease,
                visibility 240ms ease,
                filter 240ms ease;
        }

        .oes-core-companion::before {
            content: "";
            position: absolute;
            inset: 7%;
            border-radius: 50%;
            pointer-events: none;
            opacity: 0.62;
            background:
                radial-gradient(
                    circle,
                    var(
                        --awareness-glow,
                        rgba(56, 189, 248, 0.24)
                    ),
                    transparent 68%
                );
            filter: blur(24px);
            transform: scale(0.92);
            transition:
                opacity 320ms ease,
                transform 420ms ease;
        }

        .oes-core-companion--active {
            opacity: 1;
            visibility: visible;
            pointer-events: auto;
            transform:
                translate3d(
                    var(--companion-x),
                    var(--companion-y),
                    0
                )
                scale(1);
        }

        .oes-core-companion--active::before {
            opacity: 0.82;
            transform: scale(1);
        }

        .oes-core-companion--moving {
            filter:
                drop-shadow(
                    0 20px 38px
                    rgba(0, 0, 0, 0.42)
                );
        }

        .oes-core-companion--dragging {
            cursor: grabbing;
            filter:
                drop-shadow(
                    0 24px 46px
                    rgba(0, 0, 0, 0.52)
                )
                drop-shadow(
                    0 0 28px
                    var(
                        --awareness-glow,
                        rgba(56, 189, 248, 0.38)
                    )
                );
        }

        .oes-core-companion__visual-host {
            position: absolute;
            inset: 0;
            display: grid;
            place-items: center;
            overflow: visible;
            pointer-events: auto;
        }

        .oes-core-companion__visual-host > .oes-core {
            width: 78% !important;
            height: 78% !important;
            max-width: none !important;
            min-width: 0 !important;
            margin: 0 !important;
            position: relative !important;
            inset: auto !important;
            transform: none !important;
            transform-origin: center !important;
            overflow: visible !important;
        }

        .oes-core-companion__visual-host
        > .oes-core
        > .oes-core-3d-canvas {
            pointer-events: none !important;
        }

        .oes-core-companion__movement-handle {
            position: absolute;
            z-index: 90;
            right: 4%;
            bottom: 13%;
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            padding: 0;
            border:
                1px solid
                rgba(125, 211, 252, 0.46);
            border-radius: 50%;
            color: #e0f2fe;
            background:
                radial-gradient(
                    circle at 34% 28%,
                    rgba(255, 255, 255, 0.16),
                    transparent 34%
                ),
                rgba(2, 12, 28, 0.9);
            box-shadow:
                0 10px 24px
                rgba(0, 0, 0, 0.42),
                0 0 20px
                rgba(56, 189, 248, 0.2),
                inset 0 1px 0
                rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter:
                blur(12px);
            cursor: grab;
            touch-action: none;
            user-select: none;
            -webkit-user-select: none;
            transition:
                transform 180ms ease,
                border-color 180ms ease,
                box-shadow 180ms ease,
                background 180ms ease;
        }

        .oes-core-companion__movement-handle:hover,
        .oes-core-companion__movement-handle:focus-visible {
            border-color:
                var(
                    --awareness-primary,
                    #38bdf8
                );
            background:
                rgba(5, 24, 46, 0.96);
            box-shadow:
                0 12px 30px
                rgba(0, 0, 0, 0.48),
                0 0 26px
                var(
                    --awareness-glow,
                    rgba(56, 189, 248, 0.35)
                );
            transform: scale(1.08);
        }

        .oes-core-companion__movement-handle:active {
            cursor: grabbing;
            transform: scale(0.96);
        }

        .oes-core-companion__movement-handle:focus-visible {
            outline:
                2px solid
                var(
                    --awareness-primary,
                    #38bdf8
                );
            outline-offset: 4px;
        }

        .oes-core-companion__movement-icon {
            position: relative;
            width: 18px;
            height: 18px;
            pointer-events: none;
        }

        .oes-core-companion__movement-icon::before,
        .oes-core-companion__movement-icon::after {
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            background: currentColor;
            border-radius: 999px;
            box-shadow:
                0 0 8px
                rgba(125, 211, 252, 0.5);
            transform:
                translate(-50%, -50%);
        }

        .oes-core-companion__movement-icon::before {
            width: 18px;
            height: 2px;
        }

        .oes-core-companion__movement-icon::after {
            width: 2px;
            height: 18px;
        }

        .oes-core-companion-placeholder {
            width: 100%;
            aspect-ratio: 1;
            pointer-events: none;
            visibility: hidden;
        }

        .oes-core-stage--companion-away
        .core-message {
            opacity: 0.48;
        }

        @media (max-width: 760px) {
            .oes-core-companion__visual-host > .oes-core {
                width: 82% !important;
                height: 82% !important;
            }

            .oes-core-companion__movement-handle {
                right: 3%;
                bottom: 10%;
                width: 40px;
                height: 40px;
            }

        }

        @media (max-width: 480px) {
            .oes-core-companion__movement-handle {
                width: 38px;
                height: 38px;
            }

            .oes-core-companion__movement-icon {
                width: 16px;
                height: 16px;
            }

            .oes-core-companion__movement-icon::before {
                width: 16px;
            }

            .oes-core-companion__movement-icon::after {
                height: 16px;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .oes-core-companion,
            .oes-core-companion__movement-handle {
                transition: none !important;
            }
        }
    `;

    document.head.appendChild(
        style
    );
}

/* ==========================================================================
   PORTAL CREATION
============================================================================ */

function createPortal() {
    portal =
        document.createElement(
            "aside"
        );

    portal.className =
        "oes-core-companion";

    portal.dataset.oesCoreCompanion = "";

    portal.setAttribute(
        "aria-label",
        "Movable OES Core companion"
    );

    visualHost =
        document.createElement(
            "div"
        );

    visualHost.className =
        "oes-core-companion__visual-host";

    movementHandle =
        document.createElement(
            "button"
        );

    movementHandle.type =
        "button";

    movementHandle.className =
        "oes-core-companion__movement-handle";

    movementHandle.setAttribute(
        "aria-label",
        "Move the OES Core"
    );

    movementHandle.setAttribute(
        "title",
        "Drag to move the OES Core"
    );

    movementHandleIcon =
        document.createElement(
            "span"
        );

    movementHandleIcon.className =
        "oes-core-companion__movement-icon";

    movementHandleIcon.setAttribute(
        "aria-hidden",
        "true"
    );

    movementHandle.appendChild(
        movementHandleIcon
    );

    portal.append(
        visualHost,
        movementHandle
    );

    document.body.appendChild(
        portal
    );
}

/* ==========================================================================
   ORIGINAL CORE PRESERVATION
============================================================================ */

function preserveOriginalCorePosition() {
    originalParent =
        coreButton.parentNode;

    originalNextSibling =
        coreButton.nextSibling;

    originalInlineStyle =
        coreButton.getAttribute(
            "style"
        );

    placeholder =
        document.createElement(
            "div"
        );

    placeholder.className =
        "oes-core-companion-placeholder";

    placeholder.setAttribute(
        "aria-hidden",
        "true"
    );
}

function insertPlaceholder() {
    if (
        !originalParent ||
        placeholder?.isConnected
    ) {
        return;
    }

    originalParent.insertBefore(
        placeholder,
        coreButton
    );
}

function removePlaceholder() {
    placeholder?.remove();
}

/* ==========================================================================
   VIEWPORT BOUNDS
============================================================================ */

function getMovementBounds() {
    const margin =
        getViewportMargin();

    const headerClearance =
        getHeaderClearance();

    const maximumX =
        Math.max(
            margin,
            window.innerWidth -
                currentSize -
                margin
        );

    const maximumY =
        Math.max(
            headerClearance,
            window.innerHeight -
                currentSize -
                COMPANION_CONFIG
                    .footerClearance
        );

    return {
        minimumX: margin,
        maximumX,
        minimumY: headerClearance,
        maximumY
    };
}

function clampPosition(
    x,
    y
) {
    const bounds =
        getMovementBounds();

    return {
        x: clamp(
            x,
            bounds.minimumX,
            bounds.maximumX
        ),

        y: clamp(
            y,
            bounds.minimumY,
            bounds.maximumY
        )
    };
}

/* ==========================================================================
   OBSTACLE DETECTION
============================================================================ */

function getVisibleObstacles() {
    return Array.from(
        document.querySelectorAll(
            COMPANION_CONFIG
                .obstacleSelectors
                .join(",")
        )
    ).filter(
        (element) => {
            if (
                !element ||
                element === portal ||
                portal?.contains(element)
            ) {
                return false;
            }

            const style =
                window.getComputedStyle(
                    element
                );

            if (
                style.display === "none" ||
                style.visibility === "hidden" ||
                Number(style.opacity) === 0
            ) {
                return false;
            }

            const rect =
                element.getBoundingClientRect();

            return (
                rect.width > 0 &&
                rect.height > 0 &&
                rect.bottom > 0 &&
                rect.top <
                    window.innerHeight
            );
        }
    );
}

function calculateOverlapArea(
    first,
    second
) {
    const overlapWidth =
        Math.max(
            0,
            Math.min(
                first.right,
                second.right
            ) -
            Math.max(
                first.left,
                second.left
            )
        );

    const overlapHeight =
        Math.max(
            0,
            Math.min(
                first.bottom,
                second.bottom
            ) -
            Math.max(
                first.top,
                second.top
            )
        );

    return (
        overlapWidth *
        overlapHeight
    );
}

function scoreCandidatePosition(
    x,
    y
) {
    const padding =
        COMPANION_CONFIG
            .obstaclePadding;

    const candidateRect = {
        left: x - padding,
        top: y - padding,
        right:
            x +
            currentSize +
            padding,
        bottom:
            y +
            currentSize +
            padding
    };

    return getVisibleObstacles()
        .reduce(
            (
                total,
                obstacle
            ) => {
                const rect =
                    obstacle
                        .getBoundingClientRect();

                return (
                    total +
                    calculateOverlapArea(
                        candidateRect,
                        rect
                    )
                );
            },
            0
        );
}

/* ==========================================================================
   AUTOMATIC POSITIONING
============================================================================ */

function getSectionVerticalFraction(
    sectionId
) {
    return (
        COMPANION_CONFIG
            .sectionVerticalPositions[
                sectionId
            ] ??
        0.48
    );
}

function getPreferredSide(
    sectionId
) {
    return (
        COMPANION_CONFIG
            .sectionPreferredSides[
                sectionId
            ] ||
        "right"
    );
}

function createSideCandidate(
    side,
    verticalFraction
) {
    const bounds =
        getMovementBounds();

    const x =
        side === "left"
            ? bounds.minimumX
            : bounds.maximumX;

    const availableHeight =
        Math.max(
            bounds.maximumY -
                bounds.minimumY,
            0
        );

    const y =
        bounds.minimumY +
        availableHeight *
            verticalFraction;

    return clampPosition(
        x,
        y
    );
}

function findBestAutomaticPosition(
    sectionId
) {
    const verticalFraction =
        getSectionVerticalFraction(
            sectionId
        );

    const preferredSide =
        getPreferredSide(
            sectionId
        );

    const alternateSide =
        preferredSide === "left"
            ? "right"
            : "left";

    const verticalOffsets = [
        0,
        -0.18,
        0.18,
        -0.32,
        0.32
    ];

    const candidates = [];

    [
        preferredSide,
        alternateSide
    ].forEach(
        (side) => {
            verticalOffsets.forEach(
                (offset) => {
                    const adjusted =
                        clamp(
                            verticalFraction +
                                offset,
                            0,
                            1
                        );

                    const position =
                        createSideCandidate(
                            side,
                            adjusted
                        );

                    candidates.push({
                        ...position,
                        side,
                        score:
                            scoreCandidatePosition(
                                position.x,
                                position.y
                            )
                    });
                }
            );
        }
    );

    candidates.sort(
        (first, second) => {
            if (
                first.score ===
                second.score
            ) {
                return (
                    first.side ===
                    preferredSide
                        ? -1
                        : 1
                );
            }

            return (
                first.score -
                second.score
            );
        }
    );

    return (
        candidates[0] || {
            ...createSideCandidate(
                preferredSide,
                verticalFraction
            ),
            side:
                preferredSide
        }
    );
}

/* ==========================================================================
   POSITION APPLICATION
============================================================================ */

function applyPosition(
    x,
    y
) {
    currentX = x;
    currentY = y;

    portal?.style.setProperty(
        "--companion-x",
        `${currentX}px`
    );

    portal?.style.setProperty(
        "--companion-y",
        `${currentY}px`
    );
}

function applySize(size) {
    currentSize = size;

    portal?.style.setProperty(
        "--companion-size",
        `${currentSize}px`
    );
}

function animateToPosition(
    x,
    y,
    {
        duration =
            COMPANION_CONFIG
                .automaticMoveDuration,

        reason = "automatic",

        side = currentSide
    } = {}
) {
    const clamped =
        clampPosition(
            x,
            y
        );

    targetX =
        clamped.x;

    targetY =
        clamped.y;

    currentSide = side;

    cancelMovementAnimation();

    if (
        reducedMotion ||
        duration <= 0
    ) {
        applyPosition(
            targetX,
            targetY
        );

        portal?.classList.remove(
            "oes-core-companion--moving"
        );

        dispatchCompanionEvent(
            "oes:companionmove",
            {
                reason,
                completed: true
            }
        );

        return;
    }

    const startX =
        currentX;

    const startY =
        currentY;

    const startedAt =
        performance.now();

    portal?.classList.add(
        "oes-core-companion--moving"
    );

    function update(time) {
        if (
            destroyed ||
            !companionActive
        ) {
            portal?.classList.remove(
                "oes-core-companion--moving"
            );

            movementAnimationFrame =
                null;

            return;
        }

        const progress =
            clamp(
                (
                    time -
                    startedAt
                ) /
                Math.max(
                    duration,
                    1
                ),
                0,
                1
            );

        const eased =
            easeOutCubic(
                progress
            );

        applyPosition(
            lerp(
                startX,
                targetX,
                eased
            ),
            lerp(
                startY,
                targetY,
                eased
            )
        );

        if (progress >= 1) {
            portal?.classList.remove(
                "oes-core-companion--moving"
            );

            movementAnimationFrame =
                null;

            dispatchCompanionEvent(
                "oes:companionmove",
                {
                    reason,
                    completed: true
                }
            );

            return;
        }

        movementAnimationFrame =
            window.requestAnimationFrame(
                update
            );
    }

    movementAnimationFrame =
        window.requestAnimationFrame(
            update
        );
}

/* ==========================================================================
   ENTER AND LEAVE COMPANION MODE
============================================================================ */

function enterCompanionMode({
    reason = "hero-exit"
} = {}) {
    if (
        companionActive ||
        !webGLReady ||
        !coreButton ||
        !visualHost
    ) {
        return;
    }

    companionActive = true;

    applySize(
        getCompanionSize()
    );

    insertPlaceholder();

    visualHost.appendChild(
        coreButton
    );

    originalStage?.classList.add(
        "oes-core-stage--companion-away"
    );

    coreButton.classList.add(
        "oes-core--companion"
    );

    portal.classList.add(
        "oes-core-companion--active"
    );

    portal.setAttribute(
        "aria-hidden",
        "false"
    );

    const position =
        findBestAutomaticPosition(
            currentSectionId
        );

    currentSide =
        position.side;

    applyPosition(
        position.x,
        position.y
    );

    dispatchCompanionEvent(
        "oes:companionenter",
        {
            reason
        }
    );
}

function restoreCoreToOriginalStage({
    reason = "hero-return"
} = {}) {
    if (
        !companionActive ||
        !coreButton ||
        !originalParent
    ) {
        return;
    }

    companionActive = false;

    cancelMovementAnimation();

    portal?.classList.remove(
        "oes-core-companion--active",
        "oes-core-companion--moving",
        "oes-core-companion--dragging"
    );

    portal?.setAttribute(
        "aria-hidden",
        "true"
    );

    originalStage?.classList.remove(
        "oes-core-stage--companion-away"
    );

    coreButton.classList.remove(
        "oes-core--companion"
    );

    if (
        originalNextSibling &&
        originalNextSibling.parentNode ===
            originalParent
    ) {
        originalParent.insertBefore(
            coreButton,
            originalNextSibling
        );
    } else {
        originalParent.appendChild(
            coreButton
        );
    }

    if (originalInlineStyle === null) {
        coreButton.removeAttribute(
            "style"
        );
    } else {
        coreButton.setAttribute(
            "style",
            originalInlineStyle
        );
    }

    removePlaceholder();

    manualPosition = false;
    automaticMovementLocked = false;
    isDragging = false;
    dragStarted = false;

    dispatchCompanionEvent(
        "oes:companionleave",
        {
            reason
        }
    );
}

/* ==========================================================================
   SECTION TRAVEL
============================================================================ */

function moveToCurrentSection({
    reason = "section-change",
    force = false
} = {}) {
    if (
        !companionActive ||
        (
            manualPosition &&
            !force
        ) ||
        automaticMovementLocked
    ) {
        return;
    }

    const position =
        findBestAutomaticPosition(
            currentSectionId
        );

    animateToPosition(
        position.x,
        position.y,
        {
            reason,
            side:
                position.side
        }
    );

    dispatchCompanionEvent(
        "oes:companionsectionchange",
        {
            reason,
            destination: {
                x: position.x,
                y: position.y,
                side:
                    position.side
            }
        }
    );
}

/* ==========================================================================
   MOVEMENT DRAGGING
============================================================================ */

function beginMovementDrag(event) {
    if (
        !companionActive ||
        event.button > 0
    ) {
        return;
    }

    event.preventDefault();
    event.stopPropagation();

    cancelMovementAnimation();
    clearTimer(longPressTimer);

    isDragging = true;
    dragStarted = false;

    dragPointerId =
        event.pointerId;

    dragStartClientX =
        event.clientX;

    dragStartClientY =
        event.clientY;

    dragStartX =
        currentX;

    dragStartY =
        currentY;

    movementHandle
        ?.setPointerCapture?.(
            event.pointerId
        );

    longPressTimer =
        window.setTimeout(
            () => {
                if (!isDragging) {
                    return;
                }

                dragStarted = true;

                portal?.classList.add(
                    "oes-core-companion--dragging"
                );
            },
            COMPANION_CONFIG
                .longPressDuration
        );
}

function continueMovementDrag(event) {
    if (
        !isDragging ||
        event.pointerId !==
            dragPointerId
    ) {
        return;
    }

    event.preventDefault();
    event.stopPropagation();

    const deltaX =
        event.clientX -
        dragStartClientX;

    const deltaY =
        event.clientY -
        dragStartClientY;

    const distance =
        Math.sqrt(
            deltaX * deltaX +
            deltaY * deltaY
        );

    if (
        !dragStarted &&
        distance >=
            COMPANION_CONFIG
                .dragThreshold
    ) {
        dragStarted = true;

        clearTimer(longPressTimer);

        portal?.classList.add(
            "oes-core-companion--dragging"
        );

        dispatchCompanionEvent(
            "oes:companionmovestart",
            {
                pointerType:
                    event.pointerType
            }
        );
    }

    if (!dragStarted) {
        return;
    }

    const position =
        clampPosition(
            dragStartX +
                deltaX,
            dragStartY +
                deltaY
        );

    applyPosition(
        position.x,
        position.y
    );

    manualPosition = true;
    automaticMovementLocked = true;

    dispatchCompanionEvent(
        "oes:companionmove",
        {
            reason: "drag",
            completed: false
        }
    );
}

function dockAfterMovement() {
    const bounds =
        getMovementBounds();

    const centerX =
        currentX +
        currentSize / 2;

    const viewportCenterX =
        window.innerWidth / 2;

    currentSide =
        centerX <
        viewportCenterX
            ? "left"
            : "right";

    const targetDockX =
        currentSide === "left"
            ? bounds.minimumX
            : bounds.maximumX;

    const clampedY =
        clamp(
            currentY,
            bounds.minimumY,
            bounds.maximumY
        );

    animateToPosition(
        targetDockX,
        clampedY,
        {
            duration:
                COMPANION_CONFIG
                    .manualDockDuration,

            reason:
                "manual-dock",

            side:
                currentSide
        }
    );

    dispatchCompanionEvent(
        "oes:companiondock",
        {
            side:
                currentSide
        }
    );
}

function endMovementDrag(event) {
    if (
        !isDragging ||
        event.pointerId !==
            dragPointerId
    ) {
        return;
    }

    event.preventDefault();
    event.stopPropagation();

    clearTimer(longPressTimer);

    movementHandle
        ?.releasePointerCapture?.(
            event.pointerId
        );

    const completedDrag =
        dragStarted;

    isDragging = false;
    dragStarted = false;
    dragPointerId = null;

    portal?.classList.remove(
        "oes-core-companion--dragging"
    );

    if (completedDrag) {
        dockAfterMovement();

        dispatchCompanionEvent(
            "oes:companionmoveend",
            {
                pointerType:
                    event.pointerType
            }
        );
    }
}

/* ==========================================================================
   AUTOMATIC POSITION RESET
============================================================================ */

function resetAutomaticPosition() {
    manualPosition = false;
    automaticMovementLocked = false;

    moveToCurrentSection({
        reason:
            "manual-reset",

        force: true
    });
}

/* ==========================================================================
   HERO VISIBILITY
============================================================================ */

function handleHeroVisibility(entries) {
    const entry =
        entries[0];

    if (!entry) {
        return;
    }

    latestHeroRatio =
        entry.intersectionRatio;

    const stageRect =
        originalStage
            ?.getBoundingClientRect();

    const stageInHomeZone =
        Boolean(
            stageRect &&
            stageRect.top <
                window.innerHeight * 0.78 &&
            stageRect.bottom >
                getHeaderClearance()
        );

    if (
        window.scrollY <= 120 ||
        stageInHomeZone
    ) {
        restoreCoreToOriginalStage({
            reason:
                "hero-home-zone"
        });

        return;
    }

    if (
        latestHeroRatio <=
            COMPANION_CONFIG
                .heroExitRatio &&
        window.scrollY > 120
    ) {
        enterCompanionMode({
            reason:
                "hero-exit"
        });

        return;
    }

}

/* ==========================================================================
   OES EVENT HANDLERS
============================================================================ */

function handleCore3DReady(event) {
    if (
        event.detail?.renderer !==
        "webgl"
    ) {
        return;
    }

    webGLReady = true;

    portal?.classList.add(
        "oes-core-companion--webgl-ready"
    );

    if (
        latestHeroRatio <=
            COMPANION_CONFIG
                .heroExitRatio &&
        window.scrollY > 120
    ) {
        enterCompanionMode({
            reason:
                "webgl-ready-offscreen"
        });
    }
}

function handleCore3DFallback() {
    webGLReady = false;

    restoreCoreToOriginalStage({
        reason:
            "webgl-fallback"
    });
}

function handleSectionChange(event) {
    const sectionId =
        event.detail?.sectionId;

    if (!sectionId) {
        return;
    }

    currentSectionId =
        sectionId;

    moveToCurrentSection({
        reason:
            "section-change"
    });
}

function handleInterestChange(event) {
    if (
        !companionActive ||
        manualPosition
    ) {
        return;
    }

    const element =
        event.detail?.element;

    if (!(element instanceof Element)) {
        return;
    }

    const rect =
        element.getBoundingClientRect();

    const elementCenterX =
        rect.left +
        rect.width / 2;

    const preferredSide =
        elementCenterX <
        window.innerWidth / 2
            ? "right"
            : "left";

    const position =
        createSideCandidate(
            preferredSide,
            clamp(
                (
                    rect.top +
                    rect.height / 2
                ) /
                Math.max(
                    window.innerHeight,
                    1
                ),
                0.18,
                0.78
            )
        );

    animateToPosition(
        position.x,
        position.y,
        {
            duration: 420,
            reason:
                "interest-change",
            side:
                preferredSide
        }
    );
}

function handleCoreActivated() {
    if (!companionActive) {
        return;
    }

    portal?.classList.add(
        "oes-core-companion--moving"
    );

    window.setTimeout(
        () => {
            portal?.classList.remove(
                "oes-core-companion--moving"
            );
        },
        520
    );
}

/* ==========================================================================
   RESIZE HANDLING
============================================================================ */

function handleResize() {
    if (!portal) {
        return;
    }

    applySize(
        getCompanionSize()
    );

    if (!companionActive) {
        return;
    }

    if (manualPosition) {
        const position =
            clampPosition(
                currentX,
                currentY
            );

        applyPosition(
            position.x,
            position.y
        );

        dockAfterMovement();

        return;
    }

    moveToCurrentSection({
        reason:
            "viewport-resize",

        force: true
    });
}

/* ==========================================================================
   OBSERVERS
============================================================================ */

function createObservers() {
    if (
        "IntersectionObserver" in window
    ) {
        heroObserver =
            new IntersectionObserver(
                handleHeroVisibility,
                {
                    root: null,
                    threshold: [
                        0,
                        0.1,
                        COMPANION_CONFIG
                            .heroExitRatio,
                        0.4,
                        COMPANION_CONFIG
                            .heroReturnRatio,
                        0.75,
                        1
                    ]
                }
            );

        heroObserver.observe(
            heroSection
        );
    }

    /*
    Intersection ratios alone cannot return the Core on a portrait phone when
    the hero is taller than the viewport. Layout sampling keeps the stage's
    actual home zone authoritative during touch and inertial scrolling.
    */

    window.addEventListener(
        "scroll",
        handleLegacyScroll,
        {
            passive: true
        }
    );

    if (
        "ResizeObserver" in window &&
        portal
    ) {
        resizeObserver =
            new ResizeObserver(
                () => {
                    if (
                        companionActive &&
                        !isDragging
                    ) {
                        handleResize();
                    }
                }
            );

        resizeObserver.observe(
            portal
        );
    }
}

function handleLegacyScroll() {
    const rect =
        heroSection
            .getBoundingClientRect();

    const visibleHeight =
        Math.max(
            0,
            Math.min(
                rect.bottom,
                window.innerHeight
            ) -
            Math.max(
                rect.top,
                0
            )
        );

    latestHeroRatio =
        visibleHeight /
        Math.max(
            rect.height,
            1
        );

    handleHeroVisibility([
        {
            intersectionRatio:
                latestHeroRatio
        }
    ]);
}

/* ==========================================================================
   EVENT LISTENERS
============================================================================ */

function attachListeners() {
    movementHandle.addEventListener(
        "pointerdown",
        beginMovementDrag
    );

    movementHandle.addEventListener(
        "pointermove",
        continueMovementDrag
    );

    movementHandle.addEventListener(
        "pointerup",
        endMovementDrag
    );

    movementHandle.addEventListener(
        "pointercancel",
        endMovementDrag
    );

    movementHandle.addEventListener(
        "lostpointercapture",
        (event) => {
            if (isDragging) {
                endMovementDrag(
                    event
                );
            }
        }
    );

    window.addEventListener(
        "resize",
        handleResize,
        {
            passive: true
        }
    );

    window.addEventListener(
        "orientationchange",
        handleResize,
        {
            passive: true
        }
    );

    window.visualViewport
        ?.addEventListener(
            "resize",
            handleResize,
            {
                passive: true
            }
        );

    document.addEventListener(
        "oes:core3dready",
        handleCore3DReady
    );

    document.addEventListener(
        "oes:core3dfallback",
        handleCore3DFallback
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
        "oes:coreactivated",
        handleCoreActivated
    );
}

function detachListeners() {
    movementHandle?.removeEventListener(
        "pointerdown",
        beginMovementDrag
    );

    movementHandle?.removeEventListener(
        "pointermove",
        continueMovementDrag
    );

    movementHandle?.removeEventListener(
        "pointerup",
        endMovementDrag
    );

    movementHandle?.removeEventListener(
        "pointercancel",
        endMovementDrag
    );

    window.removeEventListener(
        "resize",
        handleResize
    );

    window.removeEventListener(
        "orientationchange",
        handleResize
    );

    window.visualViewport
        ?.removeEventListener(
            "resize",
            handleResize
        );

    window.removeEventListener(
        "scroll",
        handleLegacyScroll
    );

    document.removeEventListener(
        "oes:core3dready",
        handleCore3DReady
    );

    document.removeEventListener(
        "oes:core3dfallback",
        handleCore3DFallback
    );

    document.removeEventListener(
        "oes:sectionchange",
        handleSectionChange
    );

    document.removeEventListener(
        "oes:interestchange",
        handleInterestChange
    );

    document.removeEventListener(
        "oes:coreactivated",
        handleCoreActivated
    );
}

/* ==========================================================================
   PUBLIC CONTROLS
============================================================================ */

export function moveOESCoreCompanion(
    x,
    y,
    options = {}
) {
    if (!companionActive) {
        return false;
    }

    manualPosition =
        options.manual !== false;

    automaticMovementLocked =
        manualPosition;

    animateToPosition(
        x,
        y,
        {
            duration:
                Number.isFinite(
                    options.duration
                )
                    ? options.duration
                    : COMPANION_CONFIG
                        .automaticMoveDuration,

            reason:
                options.reason ||
                "manual-api",

            side:
                options.side ||
                currentSide
        }
    );

    return true;
}

export function dockOESCoreCompanion(
    side = "right",
    verticalFraction = 0.48
) {
    if (!companionActive) {
        return false;
    }

    const safeSide =
        side === "left"
            ? "left"
            : "right";

    const position =
        createSideCandidate(
            safeSide,
            clamp(
                verticalFraction,
                0,
                1
            )
        );

    manualPosition = true;
    automaticMovementLocked = true;

    animateToPosition(
        position.x,
        position.y,
        {
            reason:
                "manual-api-dock",

            side:
                safeSide
        }
    );

    return true;
}

export function resetOESCoreCompanion() {
    resetAutomaticPosition();
}

export function returnOESCoreToHero() {
    restoreCoreToOriginalStage({
        reason:
            "manual-api-return"
    });
}

export function getOESCoreCompanionState() {
    return {
        initialized,
        destroyed,
        webGLReady,
        active:
            companionActive,
        reducedMotion,

        sectionId:
            currentSectionId,

        side:
            currentSide,

        position: {
            x: currentX,
            y: currentY
        },

        target: {
            x: targetX,
            y: targetY
        },

        size:
            currentSize,

        interaction: {
            isDragging,
            manualPosition,
            automaticMovementLocked
        },

        hero: {
            visibilityRatio:
                latestHeroRatio
        }
    };
}

/* ==========================================================================
   CLEANUP
============================================================================ */

export function destroyOESCoreCompanion() {
    if (!initialized) {
        return;
    }

    destroyed = true;

    clearTimer(longPressTimer);
    cancelMovementAnimation();

    heroObserver?.disconnect();
    resizeObserver?.disconnect();

    detachListeners();

    restoreCoreToOriginalStage({
        reason:
            "companion-destroyed"
    });

    portal?.remove();
    placeholder?.remove();

    document
        .getElementById(
            "oes-core-companion-styles"
        )
        ?.remove();

    initialized = false;
}

/* ==========================================================================
   INITIALIZATION
============================================================================ */

export function initializeOESCoreCompanion() {
    if (
        initialized ||
        destroyed
    ) {
        return;
    }

    heroSection =
        document.querySelector(
            ".hero-scene"
        );

    originalStage =
        document.querySelector(
            "[data-oes-core-stage]"
        );

    coreButton =
        document.querySelector(
            "[data-oes-core]"
        );

    if (
        !heroSection ||
        !originalStage ||
        !coreButton
    ) {
        return;
    }

    initialized = true;

    reducedMotion =
        prefersReducedMotion();

    currentSectionId =
        document.querySelector(
            "main"
        )?.dataset.currentSection ||
        "home";

    installCompanionStyles();
    createPortal();
    preserveOriginalCorePosition();

    applySize(
        getCompanionSize()
    );

    window.requestAnimationFrame(
        handleResize
    );

    attachListeners();
    createObservers();

    webGLReady =
        originalStage.dataset
            .oesCoreRenderer ===
        "webgl";

    if (
        webGLReady &&
        window.scrollY > 120
    ) {
        const heroRect =
            heroSection
                .getBoundingClientRect();

        if (
            heroRect.bottom <
            window.innerHeight *
                0.72
        ) {
            latestHeroRatio = 0;

            enterCompanionMode({
                reason:
                    "initialized-below-hero"
            });
        }
    }

    document.documentElement
        .classList.add(
            "oes-core-companion-ready"
        );

    dispatchCompanionEvent(
        "oes:companionready",
        {
            webGLReady,
            reducedMotion,
            controls: {
                spin:
                    "drag-core",
                move:
                    "drag-outer-handle",
                reset:
                    "public-api"
            }
        }
    );
}
