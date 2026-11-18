const DEFAULT_PALETTE = ["#f7c84b", "#27c5ff", "#ff3fa4", "#9b64ff", "#fff5d6"];
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const FLIGHT_PATHS = ["arc", "corkscrew", "zigzag", "loop"];

function between(minimum, maximum) {
    return minimum + Math.random() * (maximum - minimum);
}

function parseConfiguration(canvas) {
    const enabled = canvas.dataset.celebrationEnabled !== "false";
    const intensity = Math.min(Math.max(Number(canvas.dataset.celebrationIntensity) || 1, 0.4), 1.5);
    const finaleFrequency = Math.max(Number(canvas.dataset.celebrationFinaleFrequency) || 12, 6);
    const palette = (canvas.dataset.celebrationPalette || "").split(",")
        .map((color) => color.trim())
        .filter((color) => /^#[0-9a-f]{6}$/i.test(color));
    return {
        enabled,
        title: canvas.dataset.celebrationTitle || "Celebration",
        product: canvas.dataset.celebrationProduct || "product",
        intensity,
        finaleFrequency,
        palette: palette.length ? palette : DEFAULT_PALETTE,
    };
}

function createCelebrationController(canvas) {
    const context = canvas.getContext("2d", { alpha: true });
    const showcase = canvas.closest("[data-dwf-logo-showcase]");
    const config = parseConfiguration(canvas);
    if (!context || !showcase || !config.enabled) return null;

    const rockets = [];
    const sparks = [];
    let frame = null;
    let visible = false;
    let nextLaunch = 0;
    let nextFinale = 0;
    let finaleQueue = [];
    let lastTime = 0;
    let width = 0;
    let height = 0;
    let observer;
    let resizeObserver;

    const mobile = () => window.innerWidth <= 480;
    const particleLimit = () => Math.round((mobile() ? 150 : 250) * config.intensity);
    const rocketLimit = () => mobile() ? 5 : 8;
    const canAnimate = () => visible && !document.hidden && !window.matchMedia(REDUCED_MOTION).matches;
    const pickColor = () => config.palette[Math.floor(Math.random() * config.palette.length)];

    function resize() {
        const bounds = showcase.getBoundingClientRect();
        const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
        width = Math.max(1, Math.round(bounds.width));
        height = Math.max(1, Math.round(bounds.height));
        canvas.width = Math.round(width * ratio);
        canvas.height = Math.round(height * ratio);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
    }

    function addSpark(spark) {
        if (sparks.length < particleLimit()) sparks.push(spark);
    }

    function createBurst(x, y, options = {}) {
        const scale = (mobile() ? 0.82 : 1) * (options.scale || 1) * config.intensity;
        const patterns = ["ring", "asymmetric", "cascade"];
        const pattern = options.pattern || patterns[Math.floor(Math.random() * patterns.length)];
        const count = Math.round(between(34, 56) * scale);
        const color = options.color || pickColor();
        for (let index = 0; index < count; index += 1) {
            const baseAngle = (Math.PI * 2 * index) / count;
            const angle = pattern === "asymmetric" ? baseAngle + between(-0.22, 0.22) : baseAngle;
            let speed = between(72, 158) * scale;
            if (pattern === "cascade") speed *= 0.82 + Math.max(0, Math.sin(angle)) * 0.45;
            if (pattern === "asymmetric" && index % 3 === 0) speed *= 1.42;
            addSpark({
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: between(1.15, 2.05), age: 0,
                color: index % 7 === 0 ? "#fff5d6" : color,
                size: between(1.5, 3.2) * scale,
                gravity: pattern === "cascade" ? between(38, 58) : between(22, 42),
                drag: between(0.976, 0.989),
                secondary: options.multiStage && index % 11 === 0,
                split: false,
            });
        }
    }

    function launchRocket(now, options = {}) {
        if (rockets.length >= rocketLimit()) return;
        const fromLeft = Math.random() < 0.5;
        const startX = options.startX ?? width * (fromLeft ? between(0.04, 0.3) : between(0.7, 0.96));
        rockets.push({
            path: options.path || FLIGHT_PATHS[Math.floor(Math.random() * FLIGHT_PATHS.length)],
            startX,
            startY: height * between(0.9, 1.02),
            targetX: options.targetX ?? width * between(0.08, 0.92),
            targetY: options.targetY ?? height * between(0.07, 0.48),
            x: startX, y: height,
            controlX: width * between(0.12, 0.88),
            controlY: height * between(0.22, 0.68),
            amplitude: width * between(0.045, 0.13),
            turns: between(2, 4.5),
            duration: between(0.95, 1.65), age: 0,
            color: options.color || pickColor(),
            size: mobile() ? 2.6 : 3.2,
            scale: options.scale || between(0.85, 1.3),
            multiStage: options.multiStage ?? Math.random() < 0.3,
            trail: [], launchedAt: now,
        });
    }

    function rocketPosition(rocket, progress) {
        const inverse = 1 - progress;
        let x = inverse * inverse * rocket.startX + 2 * inverse * progress * rocket.controlX + progress * progress * rocket.targetX;
        const y = inverse * inverse * rocket.startY + 2 * inverse * progress * rocket.controlY + progress * progress * rocket.targetY;
        const fade = Math.sin(Math.PI * progress);
        if (rocket.path === "corkscrew") x += Math.sin(progress * Math.PI * rocket.turns * 2) * rocket.amplitude * fade;
        if (rocket.path === "zigzag") x += Math.sin(progress * Math.PI * 9) * rocket.amplitude * 0.72 * fade;
        if (rocket.path === "loop") x += Math.sin(progress * Math.PI * 4) * rocket.amplitude * fade;
        return { x, y };
    }

    function drawGlow(x, y, size, color, alpha = 1) {
        context.save();
        context.globalAlpha = Math.max(0, alpha);
        context.fillStyle = color;
        context.shadowColor = color;
        context.shadowBlur = size * 5;
        context.beginPath();
        context.arc(x, y, size, 0, Math.PI * 2);
        context.fill();
        context.restore();
    }

    function drawRocket(rocket) {
        context.save();
        context.lineCap = "round";
        for (let index = 1; index < rocket.trail.length; index += 1) {
            const alpha = index / rocket.trail.length;
            context.globalAlpha = alpha * 0.68;
            context.strokeStyle = rocket.color;
            context.shadowColor = rocket.color;
            context.shadowBlur = 8;
            context.lineWidth = 0.8 + alpha * 1.8;
            context.beginPath();
            context.moveTo(rocket.trail[index - 1].x, rocket.trail[index - 1].y);
            context.lineTo(rocket.trail[index].x, rocket.trail[index].y);
            context.stroke();
        }
        context.restore();
        drawGlow(rocket.x, rocket.y, rocket.size, rocket.color);
    }

    function updateRocket(rocket, elapsed) {
        rocket.age += elapsed;
        const progress = Math.min(rocket.age / rocket.duration, 1);
        const position = rocketPosition(rocket, progress);
        rocket.x = position.x;
        rocket.y = position.y;
        rocket.trail.push({ x: rocket.x, y: rocket.y });
        if (rocket.trail.length > 18) rocket.trail.shift();
        return progress >= 1;
    }

    function updateAndDrawSpark(spark, elapsed) {
        spark.age += elapsed;
        spark.x += spark.vx * elapsed;
        spark.y += spark.vy * elapsed;
        spark.vy += spark.gravity * elapsed;
        spark.vx *= Math.pow(spark.drag, elapsed * 60);
        spark.vy *= Math.pow(spark.drag, elapsed * 60);
        const alpha = Math.pow(Math.max(0, 1 - spark.age / spark.life), 0.65);
        drawGlow(spark.x, spark.y, spark.size, spark.color, alpha);
        if (spark.secondary && !spark.split && spark.age > spark.life * 0.48) {
            spark.split = true;
            for (let index = 0; index < 6; index += 1) {
                const angle = (Math.PI * 2 * index) / 6;
                addSpark({
                    x: spark.x, y: spark.y,
                    vx: Math.cos(angle) * between(28, 48),
                    vy: Math.sin(angle) * between(28, 48),
                    age: 0, life: 0.8, color: "#fff5d6", size: 1.2,
                    gravity: 26, drag: 0.98, secondary: false, split: true,
                });
            }
        }
        return spark.age >= spark.life;
    }

    function scheduleFinale(now) {
        const count = mobile() ? 3 : 5;
        finaleQueue = Array.from({ length: count }, (_, index) => ({
            at: now + index * 170,
            options: {
                startX: width * between(0.08, 0.92),
                targetX: width * ((index + 1) / (count + 1)),
                targetY: height * between(0.08, 0.38),
                path: FLIGHT_PATHS[index % FLIGHT_PATHS.length],
                color: config.palette[index % config.palette.length],
                scale: between(1.05, 1.35),
                multiStage: index % 2 === 0,
            },
        }));
        nextFinale = now + config.finaleFrequency * 1000;
    }

    function animate(time) {
        if (!canAnimate()) { frame = null; return; }
        const elapsed = Math.min((time - (lastTime || time)) / 1000, 0.04);
        lastTime = time;
        context.clearRect(0, 0, width, height);
        if (time >= nextFinale) scheduleFinale(time);
        while (finaleQueue.length && finaleQueue[0].at <= time) launchRocket(time, finaleQueue.shift().options);
        if (time >= nextLaunch && finaleQueue.length === 0) {
            launchRocket(time);
            nextLaunch = time + between(720, 1450) / config.intensity;
        }
        for (let index = rockets.length - 1; index >= 0; index -= 1) {
            const rocket = rockets[index];
            if (updateRocket(rocket, elapsed)) {
                createBurst(rocket.x, rocket.y, { color: rocket.color, scale: rocket.scale, multiStage: rocket.multiStage });
                rockets.splice(index, 1);
            } else drawRocket(rocket);
        }
        for (let index = sparks.length - 1; index >= 0; index -= 1) {
            if (updateAndDrawSpark(sparks[index], elapsed)) sparks.splice(index, 1);
        }
        frame = requestAnimationFrame(animate);
    }

    function syncAnimation() {
        if (canAnimate() && frame === null) {
            lastTime = 0;
            const now = performance.now();
            nextLaunch = now + 80;
            nextFinale = now + Math.min(config.finaleFrequency * 1000, 2600);
            frame = requestAnimationFrame(animate);
        } else if (!canAnimate() && frame !== null) {
            cancelAnimationFrame(frame);
            frame = null;
            rockets.length = 0;
            sparks.length = 0;
            finaleQueue = [];
            context.clearRect(0, 0, width, height);
        }
    }

    function start() {
        resize();
        showcase.dataset.celebrationTitle = config.title;
        showcase.dataset.celebrationProduct = config.product;
        observer = new IntersectionObserver(([entry]) => {
            visible = Boolean(entry?.isIntersecting);
            syncAnimation();
        }, { threshold: 0.08 });
        observer.observe(showcase);
        resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(showcase);
        document.addEventListener("visibilitychange", syncAnimation);
        return cleanup;
    }

    function cleanup() {
        observer?.disconnect();
        resizeObserver?.disconnect();
        document.removeEventListener("visibilitychange", syncAnimation);
        if (frame !== null) cancelAnimationFrame(frame);
        frame = null;
        rockets.length = 0;
        sparks.length = 0;
        finaleQueue = [];
        context.clearRect(0, 0, width, height);
    }

    return { start };
}

export function initializeDWFFireworks() {
    const cleanups = [];
    document.querySelectorAll("[data-dwf-fireworks]").forEach((canvas) => {
        const cleanup = createCelebrationController(canvas)?.start();
        if (cleanup) cleanups.push(cleanup);
    });
    if (cleanups.length) window.addEventListener("pagehide", () => cleanups.forEach((cleanup) => cleanup()), { once: true });
}
