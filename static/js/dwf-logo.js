/*
===============================================================================
FILE: static/js/dwf-logo.js

PURPOSE:
    Adds restrained spatial interaction to the Drinks With Friendz client-logo
    showcase without changing the original client artwork.

UPDATED:
    July 16, 2026

RESPONSIBILITIES:
    [x] Track pointer movement inside the logo showcase
    [x] Apply smooth 3D stage rotation
    [x] Apply small spatial translation
    [x] Return the logo gently to center
    [x] Support touch interaction
    [x] Respect reduced-motion preferences
    [x] Avoid interfering with links or page scrolling
    [x] Keep client branding unchanged

CSS VARIABLES:
    --dwf-stage-rotate-x
    --dwf-stage-rotate-y
    --dwf-stage-shift-x
    --dwf-stage-shift-y
    --dwf-stage-scale

IMPORTANT SELECTORS:
    [data-dwf-logo-showcase]
    [data-dwf-logo-stage]

IMPORTANT RULES:
    [x] Movement remains subtle and professional
    [x] The logo never follows the pointer across the page
    [x] Effects only run while the showcase is visible
    [x] Touch scrolling must remain usable
===============================================================================
*/

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

const CONFIG = Object.freeze({
    maxRotateX: 7,
    maxRotateY: 10,
    maxShiftX: 12,
    maxShiftY: 9,
    smoothing: 0.085,
    idleSmoothing: 0.055,
    visibilityThreshold: 0.08
});


function prefersReducedMotion() {
    return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}


function clamp(value, minimum, maximum) {
    return Math.min(Math.max(value, minimum), maximum);
}


function normalizePointerPosition(event, element) {
    const bounds = element.getBoundingClientRect();

    const normalizedX = clamp(
        ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
        -1,
        1
    );

    const normalizedY = clamp(
        ((event.clientY - bounds.top) / bounds.height) * 2 - 1,
        -1,
        1
    );

    return {
        x: normalizedX,
        y: normalizedY
    };
}


function createLogoController(showcase) {
    const stage = showcase.querySelector("[data-dwf-logo-stage]");

    if (!stage) {
        return null;
    }

    let isVisible = true;
    let isInteracting = false;
    let animationFrameId = null;

    const current = {
        rotateX: 0,
        rotateY: 0,
        shiftX: 0,
        shiftY: 0
    };

    const target = {
        rotateX: 0,
        rotateY: 0,
        shiftX: 0,
        shiftY: 0
    };


    function applyStageVariables() {
        stage.style.setProperty(
            "--dwf-stage-rotate-x",
            `${current.rotateX.toFixed(3)}deg`
        );

        stage.style.setProperty(
            "--dwf-stage-rotate-y",
            `${current.rotateY.toFixed(3)}deg`
        );

        stage.style.setProperty(
            "--dwf-stage-shift-x",
            `${current.shiftX.toFixed(3)}px`
        );

        stage.style.setProperty(
            "--dwf-stage-shift-y",
            `${current.shiftY.toFixed(3)}px`
        );
    }


    function updateTargetsFromPointer(event) {
        const pointer = normalizePointerPosition(event, showcase);

        target.rotateX = pointer.y * -CONFIG.maxRotateX;
        target.rotateY = pointer.x * CONFIG.maxRotateY;

        target.shiftX = pointer.x * CONFIG.maxShiftX;
        target.shiftY = pointer.y * CONFIG.maxShiftY;
    }


    function returnToCenter() {
        isInteracting = false;

        target.rotateX = 0;
        target.rotateY = 0;
        target.shiftX = 0;
        target.shiftY = 0;

        showcase.classList.remove(
            "dwf-logo-showcase--tracking"
        );
    }


    function animate() {
        if (!isVisible) {
            animationFrameId = requestAnimationFrame(animate);
            return;
        }

        const smoothing = isInteracting
            ? CONFIG.smoothing
            : CONFIG.idleSmoothing;

        current.rotateX +=
            (target.rotateX - current.rotateX) * smoothing;

        current.rotateY +=
            (target.rotateY - current.rotateY) * smoothing;

        current.shiftX +=
            (target.shiftX - current.shiftX) * smoothing;

        current.shiftY +=
            (target.shiftY - current.shiftY) * smoothing;

        applyStageVariables();

        animationFrameId = requestAnimationFrame(animate);
    }


    function handlePointerEnter(event) {
        if (event.pointerType === "touch") {
            return;
        }

        isInteracting = true;

        showcase.classList.add(
            "dwf-logo-showcase--tracking"
        );

        updateTargetsFromPointer(event);
    }


    function handlePointerMove(event) {
        if (event.pointerType === "touch") {
            return;
        }

        isInteracting = true;
        updateTargetsFromPointer(event);
    }


    function handlePointerLeave() {
        returnToCenter();
    }


    function handlePointerDown(event) {
        if (event.pointerType !== "touch") {
            return;
        }

        isInteracting = true;

        showcase.classList.add(
            "dwf-logo-showcase--tracking"
        );

        updateTargetsFromPointer(event);
    }


    function handlePointerUp() {
        returnToCenter();
    }


    function handleVisibility(entries) {
        const entry = entries[0];

        if (!entry) {
            return;
        }

        isVisible = entry.isIntersecting;

        if (!isVisible) {
            returnToCenter();
        }
    }


    function start() {
        showcase.addEventListener(
            "pointerenter",
            handlePointerEnter
        );

        showcase.addEventListener(
            "pointermove",
            handlePointerMove
        );

        showcase.addEventListener(
            "pointerleave",
            handlePointerLeave
        );

        showcase.addEventListener(
            "pointerdown",
            handlePointerDown,
            {
                passive: true
            }
        );

        showcase.addEventListener(
            "pointerup",
            handlePointerUp,
            {
                passive: true
            }
        );

        showcase.addEventListener(
            "pointercancel",
            handlePointerUp,
            {
                passive: true
            }
        );

        const observer = new IntersectionObserver(
            handleVisibility,
            {
                threshold: CONFIG.visibilityThreshold
            }
        );

        observer.observe(showcase);

        animate();

        return function cleanup() {
            observer.disconnect();

            showcase.removeEventListener(
                "pointerenter",
                handlePointerEnter
            );

            showcase.removeEventListener(
                "pointermove",
                handlePointerMove
            );

            showcase.removeEventListener(
                "pointerleave",
                handlePointerLeave
            );

            showcase.removeEventListener(
                "pointerdown",
                handlePointerDown
            );

            showcase.removeEventListener(
                "pointerup",
                handlePointerUp
            );

            showcase.removeEventListener(
                "pointercancel",
                handlePointerUp
            );

            if (animationFrameId !== null) {
                cancelAnimationFrame(animationFrameId);
            }
        };
    }


    return {
        start
    };
}


export function initializeDWFLogoShowcase() {
    if (prefersReducedMotion()) {
        return;
    }

    const showcases = document.querySelectorAll(
        "[data-dwf-logo-showcase]"
    );

    if (!showcases.length) {
        return;
    }

    showcases.forEach((showcase) => {
        const controller = createLogoController(showcase);

        controller?.start();
    });
}