import { initializeEyeballChat } from "./eyeball-chat.js";
import { initializeProductIntelligence } from "./product-intelligence.js";
import { initializeSectionAwareness } from "./section-awareness.js";
import { initializeOESCore } from "./oes-core.js";
import { initializeOESCore3D } from "./oes-core-3d.js";
import { initializeOESCoreCompanion } from "./oes-core-companion.js";
import { initializeProductExperiences } from "./product-experiences.js";

function initializeLiquidAlloyHomepage() {
    const sectionMap = {
        top: "home",
        products: "products",
        "client-work": "client-work",
        capabilities: "services",
        "public-sector": "government",
        detroit: "community",
        research: "research",
        about: "about",
        contact: "contact",
    };
    Object.entries(sectionMap).forEach(([id, logicalSection]) => {
        const section = document.getElementById(id);
        if (!section) return;
        section.classList.add("section");
        section.dataset.awarenessSection = logicalSection;
    });
    initializeSectionAwareness();
    initializeOESCore();
    initializeOESCore3D();
    initializeOESCoreCompanion();
    initializeEyeballChat();
    initializeProductIntelligence();
    initializeProductExperiences();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeLiquidAlloyHomepage, { once: true });
} else {
    initializeLiquidAlloyHomepage();
}
