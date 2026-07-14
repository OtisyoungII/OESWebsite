/*
===============================================================================
FILE: static/js/product-effects.js
PURPOSE:
    Controls product-specific interactions for ChaseInGreen and Lottovate.

UPDATED:
    July 14, 2026

CHASEINGREEN:
    [x] Money burst on hover
    [x] Controlled money rain
    [x] Cleanup when interaction ends

LOTTOVATE:
    [x] Coin explosion
    [x] Lottery-ball bounce
    [x] Click reaction
    [x] Cleanup after animations

PERFORMANCE RULES:
    [x] Temporary elements are removed automatically
    [x] Repeating effects stop when the pointer leaves
    [x] Reduced-motion preference is respected
===============================================================================
*/

function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/* ============================================================================
   ChaseInGreen
============================================================================ */

export function setupChaseMoney(card) {
    if (!card || prefersReducedMotion()) {
        return;
    }

    let intervalId = null;

    card.addEventListener("pointerenter", () => {
        card.classList.add("money-active");

        burstMoney(card, 18);

        if (intervalId !== null) {
            clearInterval(intervalId);
        }

        intervalId = window.setInterval(() => {
            rainMoney(card, 8);
        }, 260);
    });

    card.addEventListener("pointerleave", () => {
        card.classList.remove("money-active");

        if (intervalId !== null) {
            clearInterval(intervalId);
            intervalId = null;
        }
    });
}

function rainMoney(container, amount) {
    for (let index = 0; index < amount; index += 1) {
        const bill = document.createElement("span");

        bill.className = "money-bill";
        bill.textContent = Math.random() > 0.5 ? "💵" : "💸";

        bill.style.left = `${Math.random() * 100}%`;
        bill.style.animationDuration = `${1.4 + Math.random() * 1.4}s`;
        bill.style.animationDelay = `${Math.random() * 0.25}s`;
        bill.style.fontSize = `${24 + Math.random() * 18}px`;

        container.appendChild(bill);

        window.setTimeout(() => {
            bill.remove();
        }, 3200);
    }
}

function burstMoney(container, amount) {
    for (let index = 0; index < amount; index += 1) {
        const bill = document.createElement("span");

        bill.className = "money-pop";
        bill.textContent = Math.random() > 0.5 ? "💵" : "💸";

        const angle = Math.random() * Math.PI * 2;
        const distance = 80 + Math.random() * 220;

        bill.style.setProperty(
            "--x",
            `${Math.cos(angle) * distance}px`
        );

        bill.style.setProperty(
            "--y",
            `${Math.sin(angle) * distance}px`
        );

        bill.style.left = "50%";
        bill.style.top = "50%";

        container.appendChild(bill);

        window.setTimeout(() => {
            bill.remove();
        }, 1100);
    }
}

/* ============================================================================
   Lottovate
============================================================================ */

export function setupLottovateCoins(card) {
    if (!card || prefersReducedMotion()) {
        return;
    }

    card.addEventListener("pointerenter", () => {
        explodeCoins(card, 44);
        bounceLotteryBalls(card);
    });

    card.addEventListener("click", () => {
        explodeCoins(card, 70);
        bounceLotteryBalls(card);
    });
}

function explodeCoins(container, amount) {
    for (let index = 0; index < amount; index += 1) {
        const coin = document.createElement("span");

        coin.className = "coin";
        coin.textContent = Math.random() > 0.18 ? "🪙" : "✨";

        const angle = Math.random() * Math.PI * 2;
        const distance = 90 + Math.random() * 260;

        coin.style.setProperty(
            "--x",
            `${Math.cos(angle) * distance}px`
        );

        coin.style.setProperty(
            "--y",
            `${Math.sin(angle) * distance}px`
        );

        coin.style.left = `${35 + Math.random() * 30}%`;
        coin.style.top = `${35 + Math.random() * 30}%`;
        coin.style.fontSize = `${22 + Math.random() * 20}px`;

        container.appendChild(coin);

        window.setTimeout(() => {
            coin.remove();
        }, 1100);
    }
}

function bounceLotteryBalls(container) {
    const numbers = ["0", "2", "3", "7", "8", "9"];

    for (let index = 0; index < 10; index += 1) {
        const ball = document.createElement("span");

        ball.className = "lotto-ball-pop";
        ball.textContent = numbers[
            Math.floor(Math.random() * numbers.length)
        ];

        ball.style.left = `${10 + Math.random() * 80}%`;
        ball.style.animationDelay = `${Math.random() * 0.25}s`;

        container.appendChild(ball);

        window.setTimeout(() => {
            ball.remove();
        }, 1500);
    }
}