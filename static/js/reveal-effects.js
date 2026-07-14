/*
===============================================================================
FILE: static/js/reveal-effects.js
PURPOSE:
    Controls scroll-based entrance animations across the OES website.

UPDATED:
    July 14, 2026

FEATURES:
    [x] Reveals major page sections
    [x] Stops observing elements after they appear
    [x] Supports additional future sections
    [x] Respects reduced-motion preferences
===============================================================================
*/

export function setupScrollReveal() {
    const revealItems = document.querySelectorAll([
        ".hero-content",
        ".hero-visual",
        ".section-heading",
        ".product-card",
        ".glass-panel",
        ".services",
        ".government",
        ".client-work",
        ".research",
        ".community"
    ].join(", "));

    const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    if (reducedMotion) {
        revealItems.forEach((item) => {
            item.classList.add("revealed");
        });

        return;
    }

    revealItems.forEach((item) => {
        item.classList.add("reveal");
    });

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) {
                    return;
                }

                entry.target.classList.add("revealed");
                observer.unobserve(entry.target);
            });
        },
        {
            threshold: 0.14,
            rootMargin: "0px 0px -40px 0px"
        }
    );

    revealItems.forEach((item) => {
        observer.observe(item);
    });
}