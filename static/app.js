document.addEventListener("DOMContentLoaded", () => {
    const lottovateCard = document.querySelector(".lottovate-card");
    const chaseCard = document.querySelector(".chase-card");

    if (lottovateCard) {
        lottovateCard.addEventListener("mouseenter", () => {
            for (let i = 0; i < 24; i++) {
                const coin = document.createElement("span");
                coin.classList.add("coin");
                coin.textContent = "🪙";

                const angle = Math.random() * Math.PI * 2;
                const distance = 80 + Math.random() * 180;

                const x = Math.cos(angle) * distance;
                const y = Math.sin(angle) * distance;

                coin.style.setProperty("--x", `${x}px`);
                coin.style.setProperty("--y", `${y}px`);
                coin.style.left = "50%";
                coin.style.top = "45%";

                lottovateCard.appendChild(coin);

                setTimeout(() => {
                    coin.remove();
                }, 900);
            }
        });
    }

    if (chaseCard) {
        chaseCard.addEventListener("mouseenter", () => {
            chaseCard.classList.add("money-active");
        });

        chaseCard.addEventListener("mouseleave", () => {
            chaseCard.classList.remove("money-active");
        });
    }
});