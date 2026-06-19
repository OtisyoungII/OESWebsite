document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const chaseCard = document.querySelector(".chase-card");
    const lottovateCard = document.querySelector(".lottovate-card");

    createCursorGlow();
    createParticleField();
    setupCardTilt();
    setupChaseMoney(chaseCard);
    setupLottovateCoins(lottovateCard);
    setupScrollReveal();

    function createCursorGlow() {
        const glow = document.createElement("div");
        glow.className = "cursor-glow";
        body.appendChild(glow);

        window.addEventListener("mousemove", (event) => {
            glow.style.left = `${event.clientX}px`;
            glow.style.top = `${event.clientY}px`;
        });
    }

    function createParticleField() {
        const particleLayer = document.createElement("div");
        particleLayer.className = "particle-layer";
        body.appendChild(particleLayer);

        for (let i = 0; i < 70; i++) {
            const particle = document.createElement("span");
            particle.className = "particle";

            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            particle.style.animationDelay = `${Math.random() * 8}s`;
            particle.style.animationDuration = `${6 + Math.random() * 12}s`;

            particleLayer.appendChild(particle);
        }
    }

    function setupCardTilt() {
        const cards = document.querySelectorAll(".card");

        cards.forEach((card) => {
            card.addEventListener("mousemove", (event) => {
                const rect = card.getBoundingClientRect();

                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;

                const rotateY = ((x / rect.width) - 0.5) * 10;
                const rotateX = ((y / rect.height) - 0.5) * -10;

                card.style.transform = `translateY(-16px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
            });

            card.addEventListener("mouseleave", () => {
                card.style.transform = "";
            });
        });
    }

    function setupChaseMoney(card) {
        if (!card) return;

        let intervalId = null;

        card.addEventListener("mouseenter", () => {
            card.classList.add("money-active");

            burstMoney(card, 18);

            intervalId = setInterval(() => {
                rainMoney(card, 8);
            }, 260);
        });

        card.addEventListener("mouseleave", () => {
            card.classList.remove("money-active");

            if (intervalId) {
                clearInterval(intervalId);
                intervalId = null;
            }
        });
    }

    function rainMoney(container, amount) {
        for (let i = 0; i < amount; i++) {
            const bill = document.createElement("span");
            bill.className = "money-bill";
            bill.textContent = Math.random() > 0.5 ? "💵" : "💸";

            bill.style.left = `${Math.random() * 100}%`;
            bill.style.animationDuration = `${1.4 + Math.random() * 1.4}s`;
            bill.style.animationDelay = `${Math.random() * 0.25}s`;
            bill.style.fontSize = `${24 + Math.random() * 18}px`;

            container.appendChild(bill);

            setTimeout(() => {
                bill.remove();
            }, 3200);
        }
    }

    function burstMoney(container, amount) {
        for (let i = 0; i < amount; i++) {
            const bill = document.createElement("span");
            bill.className = "money-pop";
            bill.textContent = Math.random() > 0.5 ? "💵" : "💸";

            const angle = Math.random() * Math.PI * 2;
            const distance = 80 + Math.random() * 220;

            bill.style.setProperty("--x", `${Math.cos(angle) * distance}px`);
            bill.style.setProperty("--y", `${Math.sin(angle) * distance}px`);
            bill.style.left = "50%";
            bill.style.top = "50%";

            container.appendChild(bill);

            setTimeout(() => {
                bill.remove();
            }, 1000);
        }
    }

    function setupLottovateCoins(card) {
        if (!card) return;

        card.addEventListener("mouseenter", () => {
            explodeCoins(card, 44);
            bounceLotteryBalls(card);
        });

        card.addEventListener("click", () => {
            explodeCoins(card, 70);
        });
    }

    function explodeCoins(container, amount) {
        for (let i = 0; i < amount; i++) {
            const coin = document.createElement("span");
            coin.className = "coin";
            coin.textContent = Math.random() > 0.18 ? "🪙" : "✨";

            const angle = Math.random() * Math.PI * 2;
            const distance = 90 + Math.random() * 260;

            coin.style.setProperty("--x", `${Math.cos(angle) * distance}px`);
            coin.style.setProperty("--y", `${Math.sin(angle) * distance}px`);
            coin.style.left = `${35 + Math.random() * 30}%`;
            coin.style.top = `${35 + Math.random() * 30}%`;
            coin.style.fontSize = `${22 + Math.random() * 20}px`;

            container.appendChild(coin);

            setTimeout(() => {
                coin.remove();
            }, 1100);
        }
    }

    function bounceLotteryBalls(container) {
        const numbers = ["0", "3", "7", "9", "2", "8"];

        for (let i = 0; i < 10; i++) {
            const ball = document.createElement("span");
            ball.className = "lotto-ball-pop";
            ball.textContent = numbers[Math.floor(Math.random() * numbers.length)];

            ball.style.left = `${10 + Math.random() * 80}%`;
            ball.style.animationDelay = `${Math.random() * 0.25}s`;

            container.appendChild(ball);

            setTimeout(() => {
                ball.remove();
            }, 1400);
        }
    }

    function setupScrollReveal() {
        const revealItems = document.querySelectorAll(".hero-content, .section-heading, .product-card, .about, .contact");

        revealItems.forEach((item) => {
            item.classList.add("reveal");
        });

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("revealed");
                }
            });
        }, {
            threshold: 0.18
        });

        revealItems.forEach((item) => observer.observe(item));
    }
});