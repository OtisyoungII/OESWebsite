/*
===============================================================================
FILE: static/js/app.js
PURPOSE:
    Main JavaScript entry point for the Otis Execution Systems website.

UPDATED:
    July 14, 2026

RESPONSIBILITIES:
    [x] Start ambient background effects
    [x] Start interactive product-card effects
    [x] Start ChaseInGreen and Lottovate effects
    [x] Start scroll reveal animations
    [x] Keep feature logic separated into focused modules

ARCHITECTURE:
    This file should remain small.
    Individual visual systems belong in their own module files.
===============================================================================
*/

import {
    createCursorGlow,
    createParticleField
} from "./ambient-effects.js";

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

    createCursorGlow();
    createParticleField();

    setupCardTilt();
    setupChaseMoney(chaseCard);
    setupLottovateCoins(lottovateCard);
    setupScrollReveal();
});