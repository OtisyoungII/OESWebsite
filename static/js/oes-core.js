/*
===============================================================================
FILE: static/js/oes-core.js

PURPOSE:
    Controls the interactive OES Core shown inside the Detroit hero scene.

UPDATED:
    July 14, 2026

RESPONSIBILITIES:
    [x] Animate the OES Core with smooth floating motion
    [x] React to mouse, pointer and touch movement
    [x] Tilt the Core based on user position
    [x] Restore the Core smoothly when interaction ends
    [x] React to clicks and taps
    [x] Update the visible Core message
    [x] Illuminate destination holograms
    [x] Expose Core movement values to the Detroit scene
    [x] Respect reduced-motion preferences
    [x] Prevent duplicate initialization

IMPORTANT SELECTORS:
    [data-oes-core-stage]
    [data-oes-core]
    [data-core-message]
    [data-core-destination]

ARCHITECTURE:
    This file controls only the OES Core.

    Detroit environmental reactions belong in:
        static/js/detroit-scene.js

    Shared ambient particles belong in:
        static/js/ambient-effects.js

    Main startup belongs in:
        static/js/app.js

IMPORTANT RULES:
    [x] Do not query the old ".orb" selector
    [x] Do not overwrite transforms belonging to child elements
    [x] Do not initialize more than once
    [x] Do not require animation for core page usability
===============================================================================
*/

const CORE_MESSAGES = [
    "Ideas into execution.",
    "Detroit built.",
    "AI systems online.",
    "Build what comes next.",
    "Technology should feel alive.",
    "Explore the OES ecosystem."
];

const DESTINATION_MESSAGES = {
    products: "Explore OES products.",
    services: "Build your system with OES.",
    government: "Technology with public purpose.",
    research: "Explore what comes next."
};

const CORE_EVENT_NAME = "oes:core-movement";
const CORE_ACTIVATION_EVENT_NAME = "oes:core-activated";

/* ============================================================================
   Shared helpers
============================================================================ */

function prefersReducedMotion() {
    return window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;
}

function supportsFinePointer() {
    return window.matchMedia(
        "(pointer: fine)"
    ).matches;
}

function clamp(value, minimum, maximum) {
    return Math.min(
        Math.max(value, minimum),
        maximum
    );
}

function lerp(currentValue, targetValue, amount) {
    return currentValue + (
        targetValue - currentValue
    ) * amount;
}

function randomMessage() {
    const index = Math.floor(
        Math.random() * CORE_MESSAGES.length
    );

    return CORE_MESSAGES[index];
}

function dispatchCoreMovement(detail) {
    window.dispatchEvent(
        new CustomEvent(
            CORE_EVENT_NAME,
            {
                detail
            }
        )
    );
}

function dispatchCoreActivation(detail) {
    window.dispatchEvent(
        new CustomEvent(
            CORE_ACTIVATION_EVENT_NAME,
            {
                detail
            }
        )
    );
}

/* ============================================================================
   OES Core controller
============================================================================ */

class OESCoreController {
    constructor() {
        this.stage = document.querySelector(
            "[data-oes-core-stage]"
        );

        this.core = document.querySelector(
            "[data-oes-core]"
        );

        this.message = document.querySelector(
            "[data-core-message]"
        );

        this.destinations = Array.from(
            document.querySelectorAll(
                "[data-core-destination]"
            )
        );

        this.reducedMotion = prefersReducedMotion();
        this.finePointer = supportsFinePointer();

        this.isInitialized = false;
        this.isPointerInsideStage = false;
        this.isDragging = false;
        this.isActivated = false;

        this.pointerX = 0;
        this.pointerY = 0;

        this.targetRotateX = 0;
        this.targetRotateY = 0;

        this.currentRotateX = 0;
        this.currentRotateY = 0;

        this.targetTranslateX = 0;
        this.targetTranslateY = 0;

        this.currentTranslateX = 0;
        this.currentTranslateY = 0;

        this.targetGlow = 0.55;
        this.currentGlow = 0.55;

        this.floatOffset = 0;
        this.activationScale = 1;

        this.animationFrameId = null;
        this.messageTimerId = null;
        this.activationTimerId = null;

        this.boundHandlePointerMove =
            this.handlePointerMove.bind(this);

        this.boundHandlePointerEnter =
            this.handlePointerEnter.bind(this);

        this.boundHandlePointerLeave =
            this.handlePointerLeave.bind(this);

        this.boundHandlePointerDown =
            this.handlePointerDown.bind(this);

        this.boundHandlePointerUp =
            this.handlePointerUp.bind(this);

        this.boundHandleCoreClick =
            this.handleCoreClick.bind(this);

        this.boundHandleKeyDown =
            this.handleKeyDown.bind(this);

        this.boundAnimate =
            this.animate.bind(this);
    }

    initialize() {
        if (
            this.isInitialized ||
            !this.stage ||
            !this.core
        ) {
            return;
        }

        this.isInitialized = true;

        this.core.dataset.coreInitialized = "true";

        this.setupCoreState();
        this.setupPointerInteractions();
        this.setupKeyboardInteractions();
        this.setupDestinationInteractions();
        this.setupMessageRotation();

        if (this.reducedMotion) {
            this.applyReducedMotionState();
            return;
        }

        this.animationFrameId = window.requestAnimationFrame(
            this.boundAnimate
        );
    }

    setupCoreState() {
        this.stage.style.setProperty(
            "--core-rotate-x",
            "0deg"
        );

        this.stage.style.setProperty(
            "--core-rotate-y",
            "0deg"
        );

        this.stage.style.setProperty(
            "--core-translate-x",
            "0px"
        );

        this.stage.style.setProperty(
            "--core-translate-y",
            "0px"
        );

        this.stage.style.setProperty(
            "--core-glow-strength",
            "0.55"
        );

        this.stage.style.setProperty(
            "--core-activation-scale",
            "1"
        );

        if (this.message) {
            this.message.textContent =
                "Move. Touch. Explore.";
        }
    }

    setupPointerInteractions() {
        this.stage.addEventListener(
            "pointerenter",
            this.boundHandlePointerEnter
        );

        this.stage.addEventListener(
            "pointermove",
            this.boundHandlePointerMove
        );

        this.stage.addEventListener(
            "pointerleave",
            this.boundHandlePointerLeave
        );

        this.core.addEventListener(
            "pointerdown",
            this.boundHandlePointerDown
        );

        window.addEventListener(
            "pointerup",
            this.boundHandlePointerUp
        );

        this.core.addEventListener(
            "click",
            this.boundHandleCoreClick
        );
    }

    setupKeyboardInteractions() {
        this.core.addEventListener(
            "keydown",
            this.boundHandleKeyDown
        );
    }

    setupDestinationInteractions() {
        this.destinations.forEach((destination) => {
            const destinationName =
                destination.dataset.coreDestination;

            destination.addEventListener(
                "pointerenter",
                () => {
                    this.activateDestination(
                        destinationName
                    );
                }
            );

            destination.addEventListener(
                "focus",
                () => {
                    this.activateDestination(
                        destinationName
                    );
                }
            );

            destination.addEventListener(
                "pointerleave",
                () => {
                    this.deactivateDestinations();
                }
            );

            destination.addEventListener(
                "blur",
                () => {
                    this.deactivateDestinations();
                }
            );
        });
    }

    setupMessageRotation() {
        if (
            !this.message ||
            this.reducedMotion
        ) {
            return;
        }

        this.messageTimerId = window.setInterval(
            () => {
                if (
                    this.isPointerInsideStage ||
                    this.isActivated
                ) {
                    return;
                }

                this.setMessage(
                    randomMessage()
                );
            },
            5200
        );
    }

    handlePointerEnter() {
        this.isPointerInsideStage = true;
        this.targetGlow = 0.92;

        this.stage.classList.add(
            "oes-core-stage--engaged"
        );

        this.setMessage(
            "The OES Core is listening."
        );
    }

    handlePointerMove(event) {
        if (this.reducedMotion) {
            return;
        }

        const stageRect =
            this.stage.getBoundingClientRect();

        const normalizedX = clamp(
            (
                event.clientX -
                stageRect.left
            ) / stageRect.width,
            0,
            1
        );

        const normalizedY = clamp(
            (
                event.clientY -
                stageRect.top
            ) / stageRect.height,
            0,
            1
        );

        const centeredX =
            normalizedX - 0.5;

        const centeredY =
            normalizedY - 0.5;

        this.pointerX = centeredX;
        this.pointerY = centeredY;

        const tiltStrength =
            this.isDragging ? 30 : 18;

        const translationStrength =
            this.isDragging ? 30 : 12;

        this.targetRotateY =
            centeredX * tiltStrength;

        this.targetRotateX =
            centeredY * tiltStrength * -1;

        this.targetTranslateX =
            centeredX * translationStrength;

        this.targetTranslateY =
            centeredY * translationStrength;

        this.targetGlow = clamp(
            0.7 +
            Math.abs(centeredX) * 0.45 +
            Math.abs(centeredY) * 0.3,
            0.7,
            1.25
        );
    }

    handlePointerLeave() {
        this.isPointerInsideStage = false;
        this.isDragging = false;

        this.targetRotateX = 0;
        this.targetRotateY = 0;

        this.targetTranslateX = 0;
        this.targetTranslateY = 0;

        this.targetGlow = 0.55;

        this.stage.classList.remove(
            "oes-core-stage--engaged"
        );

        this.stage.classList.remove(
            "oes-core-stage--dragging"
        );

        this.setMessage(
            "Explore the OES ecosystem."
        );
    }

    handlePointerDown(event) {
        if (this.reducedMotion) {
            return;
        }

        this.isDragging = true;

        this.stage.classList.add(
            "oes-core-stage--dragging"
        );

        if (
            typeof this.core.setPointerCapture ===
            "function"
        ) {
            try {
                this.core.setPointerCapture(
                    event.pointerId
                );
            } catch {
                // Pointer capture is optional.
            }
        }

        this.setMessage(
            "Move the Core."
        );
    }

    handlePointerUp() {
        this.isDragging = false;

        this.stage.classList.remove(
            "oes-core-stage--dragging"
        );
    }

    handleCoreClick() {
        this.activateCore();
    }

    handleKeyDown(event) {
        const activationKeys = [
            "Enter",
            " "
        ];

        if (
            !activationKeys.includes(
                event.key
            )
        ) {
            return;
        }

        event.preventDefault();
        this.activateCore();
    }

    activateCore() {
        if (this.activationTimerId) {
            window.clearTimeout(
                this.activationTimerId
            );
        }

        this.isActivated = true;
        this.activationScale = 1.08;
        this.targetGlow = 1.4;

        this.stage.classList.add(
            "oes-core-stage--activated"
        );

        this.core.classList.add(
            "oes-core--activated"
        );

        this.setMessage(
            randomMessage()
        );

        dispatchCoreActivation({
            activated: true,
            message:
                this.message?.textContent ?? ""
        });

        this.activationTimerId =
            window.setTimeout(
                () => {
                    this.isActivated = false;
                    this.activationScale = 1;
                    this.targetGlow =
                        this.isPointerInsideStage
                            ? 0.92
                            : 0.55;

                    this.stage.classList.remove(
                        "oes-core-stage--activated"
                    );

                    this.core.classList.remove(
                        "oes-core--activated"
                    );

                    dispatchCoreActivation({
                        activated: false
                    });
                },
                1400
            );
    }

    activateDestination(destinationName) {
        this.destinations.forEach(
            (destination) => {
                const isActive =
                    destination.dataset
                        .coreDestination ===
                    destinationName;

                destination.classList.toggle(
                    "hologram-link--active",
                    isActive
                );
            }
        );

        this.stage.dataset.activeDestination =
            destinationName;

        this.targetGlow = 1.15;

        const destinationMessage =
            DESTINATION_MESSAGES[
                destinationName
            ];

        if (destinationMessage) {
            this.setMessage(
                destinationMessage
            );
        }
    }

    deactivateDestinations() {
        this.destinations.forEach(
            (destination) => {
                destination.classList.remove(
                    "hologram-link--active"
                );
            }
        );

        delete this.stage.dataset.activeDestination;

        this.targetGlow =
            this.isPointerInsideStage
                ? 0.92
                : 0.55;

        this.setMessage(
            this.isPointerInsideStage
                ? "Choose a destination."
                : "Explore the OES ecosystem."
        );
    }

    setMessage(text) {
        if (
            !this.message ||
            !text
        ) {
            return;
        }

        this.message.classList.remove(
            "core-message--changing"
        );

        window.requestAnimationFrame(
            () => {
                this.message.classList.add(
                    "core-message--changing"
                );

                this.message.textContent = text;

                window.setTimeout(
                    () => {
                        this.message?.classList.remove(
                            "core-message--changing"
                        );
                    },
                    320
                );
            }
        );
    }

    applyReducedMotionState() {
        this.stage.classList.add(
            "oes-core-stage--reduced-motion"
        );

        this.stage.style.setProperty(
            "--core-rotate-x",
            "0deg"
        );

        this.stage.style.setProperty(
            "--core-rotate-y",
            "0deg"
        );

        this.stage.style.setProperty(
            "--core-translate-x",
            "0px"
        );

        this.stage.style.setProperty(
            "--core-translate-y",
            "0px"
        );

        this.stage.style.setProperty(
            "--core-glow-strength",
            "0.7"
        );

        this.stage.style.setProperty(
            "--core-activation-scale",
            "1"
        );
    }

    animate(timestamp) {
        const smoothing =
            this.isDragging
                ? 0.16
                : 0.085;

        this.currentRotateX = lerp(
            this.currentRotateX,
            this.targetRotateX,
            smoothing
        );

        this.currentRotateY = lerp(
            this.currentRotateY,
            this.targetRotateY,
            smoothing
        );

        this.currentTranslateX = lerp(
            this.currentTranslateX,
            this.targetTranslateX,
            smoothing
        );

        this.currentTranslateY = lerp(
            this.currentTranslateY,
            this.targetTranslateY,
            smoothing
        );

        this.currentGlow = lerp(
            this.currentGlow,
            this.targetGlow,
            0.08
        );

        this.floatOffset =
            Math.sin(
                timestamp / 1050
            ) * -11;

        const secondaryFloat =
            Math.cos(
                timestamp / 1600
            ) * 3;

        const finalTranslateY =
            this.currentTranslateY +
            this.floatOffset +
            secondaryFloat;

        this.stage.style.setProperty(
            "--core-rotate-x",
            `${this.currentRotateX.toFixed(3)}deg`
        );

        this.stage.style.setProperty(
            "--core-rotate-y",
            `${this.currentRotateY.toFixed(3)}deg`
        );

        this.stage.style.setProperty(
            "--core-translate-x",
            `${this.currentTranslateX.toFixed(3)}px`
        );

        this.stage.style.setProperty(
            "--core-translate-y",
            `${finalTranslateY.toFixed(3)}px`
        );

        this.stage.style.setProperty(
            "--core-glow-strength",
            this.currentGlow.toFixed(3)
        );

        this.stage.style.setProperty(
            "--core-activation-scale",
            this.activationScale.toFixed(3)
        );

        dispatchCoreMovement({
            rotateX: this.currentRotateX,
            rotateY: this.currentRotateY,
            translateX:
                this.currentTranslateX,
            translateY:
                finalTranslateY,
            pointerX: this.pointerX,
            pointerY: this.pointerY,
            glow: this.currentGlow,
            engaged:
                this.isPointerInsideStage,
            dragging:
                this.isDragging,
            activated:
                this.isActivated
        });

        this.animationFrameId =
            window.requestAnimationFrame(
                this.boundAnimate
            );
    }

    destroy() {
        if (!this.isInitialized) {
            return;
        }

        this.stage.removeEventListener(
            "pointerenter",
            this.boundHandlePointerEnter
        );

        this.stage.removeEventListener(
            "pointermove",
            this.boundHandlePointerMove
        );

        this.stage.removeEventListener(
            "pointerleave",
            this.boundHandlePointerLeave
        );

        this.core.removeEventListener(
            "pointerdown",
            this.boundHandlePointerDown
        );

        window.removeEventListener(
            "pointerup",
            this.boundHandlePointerUp
        );

        this.core.removeEventListener(
            "click",
            this.boundHandleCoreClick
        );

        this.core.removeEventListener(
            "keydown",
            this.boundHandleKeyDown
        );

        if (this.animationFrameId) {
            window.cancelAnimationFrame(
                this.animationFrameId
            );
        }

        if (this.messageTimerId) {
            window.clearInterval(
                this.messageTimerId
            );
        }

        if (this.activationTimerId) {
            window.clearTimeout(
                this.activationTimerId
            );
        }

        this.isInitialized = false;
    }
}

/* ============================================================================
   Public initializer
============================================================================ */

let controllerInstance = null;

export function initializeOESCore() {
    if (controllerInstance) {
        return controllerInstance;
    }

    controllerInstance =
        new OESCoreController();

    controllerInstance.initialize();

    return controllerInstance;
}