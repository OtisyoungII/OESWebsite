/*
===============================================================================
FILE: static/js/oes-core.js

PURPOSE:
    Controls the interactive OES Core shown in the hero section.

UPDATED:
    July 2026

FEATURE ROADMAP
-------------------------------------------------------------------------------
✓ Floating idle animation
✓ Mouse / touch interaction
✓ Tilt based on cursor position
✓ Spring return animation
✓ Dynamic glow intensity
✓ Responsive behavior
✓ Reduced motion support

FUTURE
-------------------------------------------------------------------------------
□ Detroit environment lighting
□ Data pulse effects
□ Holographic projections
□ Voice assistant visualization
□ 3D model support
□ Three.js integration
===============================================================================
*/

function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function initializeOESCore() {

    if (prefersReducedMotion()) {
        return;
    }

    const core = document.querySelector(".orb");

    if (!core) {
        return;
    }

    let targetX = 0;
    let targetY = 0;

    let currentX = 0;
    let currentY = 0;

    document.addEventListener("pointermove", (event) => {

        const rect = core.getBoundingClientRect();

        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        targetY = ((event.clientX - centerX) / rect.width) * 18;
        targetX = -((event.clientY - centerY) / rect.height) * 18;

    });

    function animate() {

        currentX += (targetX - currentX) * 0.08;
        currentY += (targetY - currentY) * 0.08;

        core.style.transform =
            `
            translateY(${Math.sin(Date.now() / 900) * -12}px)
            rotateX(${currentX}deg)
            rotateY(${currentY}deg)
            `;

        requestAnimationFrame(animate);
    }

    animate();
}