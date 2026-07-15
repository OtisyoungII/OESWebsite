/*
===============================================================================
FILE: static/js/detroit-scene.js

PURPOSE:
    Controls environmental reactions inside the Detroit hero scene.

UPDATED:
    July 14, 2026

RESPONSIBILITIES:
    [x] React to OES Core movement
    [x] Shift scene lighting based on pointer position
    [x] Animate Detroit reflections and atmosphere
    [x] React when the OES Core is activated
    [x] Illuminate environmental signs and holograms
    [x] Respect reduced-motion preferences
    [x] Prevent duplicate initialization

EVENTS CONSUMED:
    oes:core-movement
    oes:core-activated

IMPORTANT SELECTORS:
    [data-detroit-scene]
    .scene-light--left
    .scene-light--right
    .scene-light--center
    .street-reflection
    .city-sign
    .club-sign
    .steam

ARCHITECTURE:
    OES Core behavior belongs in:
        static/js/oes-core.js

    Shared particles belong in:
        static/js/ambient-effects.js

    This file owns only Detroit scene reactions.
===============================================================================
*/

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

function lerp(currentValue, targetValue, amount) {
    return currentValue + (
        targetValue - currentValue
    ) * amount;
}

class DetroitSceneController {
    constructor() {
        this.scene = document.querySelector(
            "[data-detroit-scene]"
        );

        this.leftLight = document.querySelector(
            ".scene-light--left"
        );

        this.rightLight = document.querySelector(
            ".scene-light--right"
        );

        this.centerLight = document.querySelector(
            ".scene-light--center"
        );

        this.reflections = Array.from(
            document.querySelectorAll(
                ".street-reflection"
            )
        );

        this.signs = Array.from(
            document.querySelectorAll(
                ".city-sign, .club-sign"
            )
        );

        this.steamElements = Array.from(
            document.querySelectorAll(
                ".steam"
            )
        );

        this.reducedMotion = prefersReducedMotion();
        this.isInitialized = false;
        this.isActivated = false;

        this.targetSceneX = 0;
        this.targetSceneY = 0;
        this.currentSceneX = 0;
        this.currentSceneY = 0;

        this.targetBrightness = 1;
        this.currentBrightness = 1;

        this.animationFrameId = null;
        this.activationTimerId = null;

        this.boundHandleCoreMovement =
            this.handleCoreMovement.bind(this);

        this.boundHandleCoreActivation =
            this.handleCoreActivation.bind(this);

        this.boundAnimate =
            this.animate.bind(this);
    }

    initialize() {
        if (
            this.isInitialized ||
            !this.scene
        ) {
            return;
        }

        this.isInitialized = true;
        this.scene.dataset.detroitInitialized = "true";

        this.setupInitialState();

        window.addEventListener(
            "oes:core-movement",
            this.boundHandleCoreMovement
        );

        window.addEventListener(
            "oes:core-activated",
            this.boundHandleCoreActivation
        );

        if (this.reducedMotion) {
            this.applyReducedMotionState();
            return;
        }

        this.animationFrameId =
            window.requestAnimationFrame(
                this.boundAnimate
            );
    }

    setupInitialState() {
        this.scene.style.setProperty(
            "--scene-shift-x",
            "0px"
        );

        this.scene.style.setProperty(
            "--scene-shift-y",
            "0px"
        );

        this.scene.style.setProperty(
            "--scene-brightness",
            "1"
        );

        this.scene.style.setProperty(
            "--scene-core-glow",
            "0.55"
        );
    }

    handleCoreMovement(event) {
        const detail = event.detail ?? {};

        const pointerX = clamp(
            Number(detail.pointerX) || 0,
            -0.5,
            0.5
        );

        const pointerY = clamp(
            Number(detail.pointerY) || 0,
            -0.5,
            0.5
        );

        const glow = clamp(
            Number(detail.glow) || 0.55,
            0.4,
            1.6
        );

        this.targetSceneX =
            pointerX * -18;

        this.targetSceneY =
            pointerY * -10;

        this.targetBrightness =
            detail.engaged
                ? 1.08
                : 1;

        this.scene.style.setProperty(
            "--scene-core-glow",
            glow.toFixed(3)
        );

        this.updateDirectionalLights(
            pointerX,
            pointerY,
            glow
        );

        this.updateSigns(
            detail.engaged,
            detail.dragging
        );
    }

    handleCoreActivation(event) {
        const activated =
            Boolean(
                event.detail?.activated
            );

        if (!activated) {
            this.isActivated = false;

            this.scene.classList.remove(
                "hero-scene--core-activated"
            );

            return;
        }

        this.isActivated = true;

        this.scene.classList.add(
            "hero-scene--core-activated"
        );

        this.pulseReflections();
        this.pulseSigns();

        if (this.activationTimerId) {
            window.clearTimeout(
                this.activationTimerId
            );
        }

        this.activationTimerId =
            window.setTimeout(
                () => {
                    this.isActivated = false;

                    this.scene.classList.remove(
                        "hero-scene--core-activated"
                    );
                },
                1500
            );
    }

    updateDirectionalLights(
        pointerX,
        pointerY,
        glow
    ) {
        if (
            !this.leftLight ||
            !this.rightLight ||
            !this.centerLight
        ) {
            return;
        }

        const leftOpacity = clamp(
            0.28 +
            (-pointerX * 0.7) +
            (glow * 0.18),
            0.18,
            0.95
        );

        const rightOpacity = clamp(
            0.28 +
            (pointerX * 0.7) +
            (glow * 0.18),
            0.18,
            0.95
        );

        const centerOpacity = clamp(
            0.35 +
            (-Math.abs(pointerY) * 0.2) +
            (glow * 0.24),
            0.3,
            1
        );

        this.leftLight.style.opacity =
            leftOpacity.toFixed(3);

        this.rightLight.style.opacity =
            rightOpacity.toFixed(3);

        this.centerLight.style.opacity =
            centerOpacity.toFixed(3);
    }

    updateSigns(
        engaged,
        dragging
    ) {
        this.signs.forEach(
            (sign, index) => {
                const delay =
                    index * 35;

                window.setTimeout(
                    () => {
                        sign.classList.toggle(
                            "city-sign--engaged",
                            Boolean(engaged)
                        );

                        sign.classList.toggle(
                            "city-sign--dragging",
                            Boolean(dragging)
                        );
                    },
                    delay
                );
            }
        );
    }

    pulseReflections() {
        this.reflections.forEach(
            (reflection, index) => {
                reflection.classList.remove(
                    "street-reflection--pulse"
                );

                window.setTimeout(
                    () => {
                        reflection.classList.add(
                            "street-reflection--pulse"
                        );
                    },
                    index * 80
                );

                window.setTimeout(
                    () => {
                        reflection.classList.remove(
                            "street-reflection--pulse"
                        );
                    },
                    1200 + index * 80
                );
            }
        );
    }

    pulseSigns() {
        this.signs.forEach(
            (sign, index) => {
                sign.classList.remove(
                    "city-sign--pulse"
                );

                window.setTimeout(
                    () => {
                        sign.classList.add(
                            "city-sign--pulse"
                        );
                    },
                    index * 70
                );

                window.setTimeout(
                    () => {
                        sign.classList.remove(
                            "city-sign--pulse"
                        );
                    },
                    1150 + index * 70
                );
            }
        );
    }

    applyReducedMotionState() {
        this.scene.classList.add(
            "hero-scene--reduced-motion"
        );

        this.scene.style.setProperty(
            "--scene-shift-x",
            "0px"
        );

        this.scene.style.setProperty(
            "--scene-shift-y",
            "0px"
        );

        this.scene.style.setProperty(
            "--scene-brightness",
            "1"
        );

        this.steamElements.forEach(
            (steam) => {
                steam.style.animation = "none";
            }
        );
    }

    animate(timestamp) {
        this.currentSceneX = lerp(
            this.currentSceneX,
            this.targetSceneX,
            0.045
        );

        this.currentSceneY = lerp(
            this.currentSceneY,
            this.targetSceneY,
            0.045
        );

        this.currentBrightness = lerp(
            this.currentBrightness,
            this.targetBrightness,
            0.05
        );

        const idleX =
            Math.sin(
                timestamp / 4800
            ) * 2.4;

        const idleY =
            Math.cos(
                timestamp / 5600
            ) * 1.8;

        this.scene.style.setProperty(
            "--scene-shift-x",
            `${(
                this.currentSceneX +
                idleX
            ).toFixed(3)}px`
        );

        this.scene.style.setProperty(
            "--scene-shift-y",
            `${(
                this.currentSceneY +
                idleY
            ).toFixed(3)}px`
        );

        this.scene.style.setProperty(
            "--scene-brightness",
            this.currentBrightness.toFixed(3)
        );

        this.updateAmbientSteam(
            timestamp
        );

        this.animationFrameId =
            window.requestAnimationFrame(
                this.boundAnimate
            );
    }

    updateAmbientSteam(timestamp) {
        this.steamElements.forEach(
            (steam, index) => {
                const offset =
                    Math.sin(
                        timestamp /
                        (
                            1300 +
                            index * 350
                        )
                    ) *
                    (
                        5 +
                        index * 2
                    );

                steam.style.setProperty(
                    "--steam-drift",
                    `${offset.toFixed(2)}px`
                );
            }
        );
    }

    destroy() {
        if (!this.isInitialized) {
            return;
        }

        window.removeEventListener(
            "oes:core-movement",
            this.boundHandleCoreMovement
        );

        window.removeEventListener(
            "oes:core-activated",
            this.boundHandleCoreActivation
        );

        if (this.animationFrameId) {
            window.cancelAnimationFrame(
                this.animationFrameId
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

let controllerInstance = null;

export function initializeDetroitScene() {
    if (controllerInstance) {
        return controllerInstance;
    }

    controllerInstance =
        new DetroitSceneController();

    controllerInstance.initialize();

    return controllerInstance;
}