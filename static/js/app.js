/*
===============================================================================
FILE: static/js/app.js

PURPOSE:
    Main JavaScript entry point for the Otis Execution Systems website.

UPDATED:
    July 14, 2026

RESPONSIBILITIES
-------------------------------------------------------------------------------
[x] Start ambient effects
[x] Start OES Core interactions
[x] Start product card effects
[x] Start ChaseInGreen animations
[x] Start Lottovate animations
[x] Start scroll reveal system

IMPORTANT
-------------------------------------------------------------------------------
This file should stay very small.

Every major visual system belongs in its own JavaScript module.

Do NOT place large animation systems in this file.
===============================================================================
*/

import {
    createCursorGlow,
    createParticleField
} from "./ambient-effects.js";

import {
    initializeOESCore
} from "./oes-core.js";

import {
    setupCardTilt
} from "./card-effects.js";

import {
    setupChaseMoney,
    setupLottovateCoins
} from "./product-effects.js";

import {
    setupScrollReveal
} from "./reveal-effects.js";

document.addEventListener("DOMContentLoaded", () => {

    const chaseCard = document.querySelector(".chase-card");
    const lottovateCard = document.querySelector(".lottovate-card");

    /*
    ===============================================================
    Global Ambient Systems
    ===============================================================
    */

    createCursorGlow();
    createParticleField();

    /*
    ===============================================================
    OES Core
    ===============================================================
    */

    initializeOESCore();

    /*
    ===============================================================
    Product Interactions
    ===============================================================
    */

    setupCardTilt();
    setupChaseMoney(chaseCard);
    setupLottovateCoins(lottovateCard);

    /*
    ===============================================================
    Page Effects
    ===============================================================
    */

    setupScrollReveal();

});