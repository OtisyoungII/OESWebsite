/*
===============================================================================
FILE: static/js/card-effects.js
PURPOSE:
    Provides shared interaction behavior for OES cards and panels.

UPDATED:
    July 14, 2026

FEATURES:
    [x] Product-card pointer tilt
    [x] Smooth reset when pointer leaves
    [x] Touch-safe behavior
    [x] Reduced-motion support

IMPORTANT FIX:
    The previous file searched for ".card", but the website uses
    ".product-card". This file uses the correct selector.
===============================================================================
*/

function supportsInteractiveTilt() {
    const hasFinePointer = window.matchMedia("(pointer: fine)").matches;
    const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    return hasFinePointer && !reducedMotion;
}

export function setupCardTilt() {
    if (!supportsInteractiveTilt()) {
        return;
    }

    const cards = document.querySelectorAll(".product-card");

    cards.forEach((card) => {
        card.addEventListener("pointermove", (event) => {
            const rect = card.getBoundingClientRect();

            const pointerX = event.clientX - rect.left;
            const pointerY = event.clientY - rect.top;

            const rotateY = ((pointerX / rect.width) - 0.5) * 10;
            const rotateX = ((pointerY / rect.height) - 0.5) * -10;

            card.style.transform = [
                "translateY(-16px)",
                `rotateX(${rotateX}deg)`,
                `rotateY(${rotateY}deg)`,
                "scale(1.02)"
            ].join(" ");
        });

        card.addEventListener("pointerleave", () => {
            card.style.transform = "";
        });
    });
}