/*
===============================================================================
FILE: static/js/ambient-effects.js
PURPOSE:
    Controls global atmosphere effects across the OES website.

UPDATED:
    July 14, 2026

FEATURES:
    [x] Cursor-following blue glow
    [x] Animated particle field
    [x] Prevents duplicate effect layers
    [x] Respects reduced-motion preferences
===============================================================================
*/

function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function createCursorGlow() {
    if (prefersReducedMotion()) {
        return;
    }

    if (document.querySelector(".cursor-glow")) {
        return;
    }

    const glow = document.createElement("div");
    glow.className = "cursor-glow";
    document.body.appendChild(glow);

    window.addEventListener("pointermove", (event) => {
        glow.style.left = `${event.clientX}px`;
        glow.style.top = `${event.clientY}px`;
    });
}

export function createParticleField() {
    if (prefersReducedMotion()) {
        return;
    }

    let particleLayer = document.querySelector(".particle-layer");

    if (!particleLayer) {
        particleLayer = document.createElement("div");
        particleLayer.className = "particle-layer";
        document.body.appendChild(particleLayer);
    }

    if (particleLayer.children.length > 0) {
        return;
    }

    const particleCount = window.innerWidth < 700 ? 30 : 70;

    for (let index = 0; index < particleCount; index += 1) {
        const particle = document.createElement("span");

        particle.className = "particle";
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.top = `${Math.random() * 100}%`;
        particle.style.animationDelay = `${Math.random() * 8}s`;
        particle.style.animationDuration = `${6 + Math.random() * 12}s`;

        particleLayer.appendChild(particle);
    }
}