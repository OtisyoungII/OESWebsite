import * as THREE from "/static/js/three/three.module.js";
import { GLTFLoader } from "/static/js/three/addons/loaders/GLTFLoader.js";

const stage = document.querySelector("[data-eyeball-stage]");
const host = document.querySelector("[data-petal-stage]");
const canvas = document.querySelector("[data-petal-canvas]");
const loading = document.querySelector("[data-petal-loading]");
const fallback = document.querySelector("[data-petal-fallback]");
const status = document.querySelector("[data-petal-status]");
const controls = [...document.querySelectorAll("[data-expression]")];

const STATE_TIME = Object.freeze({
  neutral: 0,
  listening: 24 / 30,
  thinking: 44 / 30,
  blink: 66 / 30,
  responding: 94 / 30,
});
const PETAL_ACTIONS = Object.freeze([
  "gaze_listen_think",
  "petal_bottom_pivot_expression",
  "petal_left_pivot_expression",
  "petal_right_pivot_expression",
  "petal_top_pivot_expression",
]);

let renderer;
let scene;
let camera;
let mixer;
let model;
let presentation;
let idleAction;
let expressionActions = [];
let raf = 0;
let disposed = false;
let inView = false;
let pageVisible = !document.hidden;
let ready = false;
let currentState = "neutral";
let previousState = "neutral";
let currentTimeline = 0;
let targetTimeline = 0;
let blinkTimer = 0;
let lastFrame = performance.now();
let lastBlink = performance.now();
let dragging = false;
let pointerId = null;
let pointerX = 0;
let pointerY = 0;
let yaw = 0;
let pitch = 0;
let velocityX = 0;
let velocityY = 0;
let lastInteraction = 0;
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
let reducedMotion = reducedQuery.matches;

controls.forEach((button) => { button.disabled = true; });

function showFallback(message) {
  if (stage) stage.dataset.renderState = "fallback";
  loading.hidden = true;
  fallback.hidden = false;
  if (message) fallback.textContent = message;
  status.textContent = "Interactive preview unavailable · descriptive fallback active";
  controls.forEach((button) => { button.disabled = true; });
}

function webglAvailable() {
  try {
    const probe = document.createElement("canvas");
    return Boolean(probe.getContext("webgl2", { failIfMajorPerformanceCaveat: true }));
  } catch {
    return false;
  }
}

function resize() {
  if (!renderer || !camera || !host) return;
  const width = Math.max(1, host.clientWidth);
  const height = Math.max(1, host.clientHeight);
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75));
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderOnce();
}

function renderOnce() {
  if (renderer && scene && camera && !disposed) renderer.render(scene, camera);
}

function requestFrame() {
  if (disposed || !ready || !inView || !pageVisible || raf) return;
  raf = requestAnimationFrame(frame);
}

function setPressed(state) {
  controls.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.expression === state));
  });
}

function setExpression(state, automatic = false) {
  if (!Object.hasOwn(STATE_TIME, state) || !ready) return;
  if (state !== "blink") previousState = state;
  currentState = state;
  targetTimeline = STATE_TIME[state];
  setPressed(state);
  status.textContent = `${state[0].toUpperCase()}${state.slice(1)} expression · drag to rotate`;
  if (reducedMotion) currentTimeline = targetTimeline;
  if (state === "blink") {
    clearTimeout(blinkTimer);
    blinkTimer = window.setTimeout(() => setExpression(previousState, automatic),
      reducedMotion ? 180 : 650);
  }
  requestFrame();
}

function frame(now) {
  raf = 0;
  if (disposed || !ready || !inView || !pageVisible) return;
  const delta = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;

  if (reducedMotion) {
    expressionActions.forEach((action) => { action.time = currentTimeline; });
    mixer.update(0);
    renderOnce();
    return;
  }

  const blend = 1 - Math.exp(-delta * 8);
  currentTimeline += (targetTimeline - currentTimeline) * blend;
  expressionActions.forEach((action) => { action.time = currentTimeline; });
  mixer.update(delta);

  if (!dragging) {
    yaw = THREE.MathUtils.clamp(yaw + velocityX, -1.45, 1.45);
    pitch = THREE.MathUtils.clamp(pitch + velocityY, -0.58, 0.58);
    velocityX *= Math.pow(0.87, delta * 60);
    velocityY *= Math.pow(0.87, delta * 60);
    if (now - lastInteraction > 1100) {
      const settle = 1 - Math.exp(-delta * 2.4);
      yaw += (0 - yaw) * settle;
      pitch += (0 - pitch) * settle;
    }
  }
  presentation.rotation.y = yaw;
  presentation.rotation.x = pitch;
  stage.dataset.rotation = `${yaw.toFixed(3)},${pitch.toFixed(3)}`;

  if (currentState === "neutral" && now - lastBlink > 6200) {
    lastBlink = now;
    setExpression("blink", true);
  }
  renderOnce();
  requestFrame();
}

function bindInteraction() {
  canvas.addEventListener("pointerdown", (event) => {
    if (!ready) return;
    dragging = true;
    pointerId = event.pointerId;
    pointerX = event.clientX;
    pointerY = event.clientY;
    velocityX = 0;
    velocityY = 0;
    lastInteraction = performance.now();
    canvas.setPointerCapture(pointerId);
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!dragging || event.pointerId !== pointerId || reducedMotion) return;
    const dx = event.clientX - pointerX;
    const dy = event.clientY - pointerY;
    pointerX = event.clientX;
    pointerY = event.clientY;
    const scale = 0.008;
    velocityX = THREE.MathUtils.clamp(dx * scale, -0.11, 0.11);
    velocityY = THREE.MathUtils.clamp(dy * scale, -0.09, 0.09);
    yaw = THREE.MathUtils.clamp(yaw + velocityX, -1.45, 1.45);
    pitch = THREE.MathUtils.clamp(pitch + velocityY, -0.58, 0.58);
    lastInteraction = performance.now();
    requestFrame();
  });
  const release = (event) => {
    if (!dragging || event.pointerId !== pointerId) return;
    dragging = false;
    if (canvas.hasPointerCapture(pointerId)) canvas.releasePointerCapture(pointerId);
    pointerId = null;
    lastInteraction = performance.now();
    requestFrame();
  };
  canvas.addEventListener("pointerup", release);
  canvas.addEventListener("pointercancel", release);
  canvas.addEventListener("keydown", (event) => {
    const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home"];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Home") { yaw = 0; pitch = 0; }
    if (event.key === "ArrowLeft") yaw = Math.max(-1.45, yaw - 0.12);
    if (event.key === "ArrowRight") yaw = Math.min(1.45, yaw + 0.12);
    if (event.key === "ArrowUp") pitch = Math.max(-0.58, pitch - 0.10);
    if (event.key === "ArrowDown") pitch = Math.min(0.58, pitch + 0.10);
    lastInteraction = performance.now();
    requestFrame();
  });
  controls.forEach((button) => {
    button.addEventListener("click", () => setExpression(button.dataset.expression));
  });
}

function dispose() {
  if (disposed) return;
  disposed = true;
  cancelAnimationFrame(raf);
  clearTimeout(blinkTimer);
  if (model) {
    model.traverse((object) => {
      object.geometry?.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.filter(Boolean).forEach((material) => {
        Object.values(material).forEach((value) => value?.isTexture && value.dispose());
        material.dispose();
      });
    });
  }
  renderer?.dispose();
  renderer?.forceContextLoss();
}

async function initialize() {
  if (!stage || !host || !canvas || !webglAvailable()) {
    showFallback();
    return;
  }
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true,
      powerPreference: "high-performance" });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.AgXToneMapping;
    renderer.toneMappingExposure = 1.05;
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    camera.position.set(0, 0.15, 6.2);
    presentation = new THREE.Group();
    scene.add(presentation);
    scene.add(new THREE.HemisphereLight(0xd9f3ff, 0x061018, 1.8));
    const key = new THREE.DirectionalLight(0xffead4, 3.2);
    key.position.set(-4, 5, 6);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x38a9d1, 2.2);
    rim.position.set(5, 1, -4);
    scene.add(rim);

    const asset = stage.dataset.approvedGlb;
    if (!asset) throw new Error("missing development asset");
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(asset, (event) => {
      if (event.total > 0) {
        const percent = Math.min(99, Math.round(event.loaded / event.total * 100));
        loading.querySelector("strong").textContent = `Loading Petal Core… ${percent}%`;
      }
    });
    model = gltf.scene;
    let meshCount = 0;
    const materials = new Set();
    model.traverse((object) => {
      if (object.isMesh) meshCount += 1;
      const objectMaterials = Array.isArray(object.material) ? object.material : [object.material];
      objectMaterials.filter(Boolean).forEach((material) => materials.add(material.uuid));
    });
    stage.dataset.meshCount = String(meshCount);
    stage.dataset.materialCount = String(materials.size);
    stage.dataset.animationCount = String(gltf.animations.length);
    const bounds = new THREE.Box3().setFromObject(model);
    const size = bounds.getSize(new THREE.Vector3());
    const center = bounds.getCenter(new THREE.Vector3());
    model.position.sub(center);
    const scale = 3.7 / Math.max(size.x, size.y, size.z);
    model.scale.setScalar(scale);
    presentation.add(model);

    mixer = new THREE.AnimationMixer(model);
    const clips = new Map(gltf.animations.map((clip) => [clip.name, clip]));
    const idleClip = clips.get("idle_float");
    if (!idleClip || PETAL_ACTIONS.some((name) => !clips.has(name))) {
      throw new Error("Stage D animation contract incomplete");
    }
    idleAction = mixer.clipAction(idleClip);
    idleAction.setLoop(THREE.LoopRepeat, Infinity).play();
    idleAction.paused = reducedMotion;
    expressionActions = PETAL_ACTIONS.map((name) => {
      const action = mixer.clipAction(clips.get(name));
      action.play();
      action.setEffectiveTimeScale(0);
      action.time = 0;
      return action;
    });

    ready = true;
    stage.dataset.renderState = "ready";
    loading.hidden = true;
    status.textContent = "Neutral expression · drag to rotate";
    controls.forEach((button) => { button.disabled = false; });
    resize();
    requestFrame();
  } catch (error) {
    showFallback("The interactive Petal Core development asset could not be loaded. The rest of the OES website remains available.");
  }
}

const observer = new IntersectionObserver(([entry]) => {
  inView = entry.isIntersecting;
  if (inView) { lastFrame = performance.now(); requestFrame(); }
  else { cancelAnimationFrame(raf); raf = 0; }
}, { rootMargin: "120px" });
if (stage) observer.observe(stage);
document.addEventListener("visibilitychange", () => {
  pageVisible = !document.hidden;
  if (pageVisible) { lastFrame = performance.now(); requestFrame(); }
  else { cancelAnimationFrame(raf); raf = 0; }
});
reducedQuery.addEventListener("change", (event) => {
  reducedMotion = event.matches;
  if (idleAction) idleAction.paused = reducedMotion;
  velocityX = 0;
  velocityY = 0;
  requestFrame();
});
new ResizeObserver(resize).observe(host);
window.addEventListener("pagehide", dispose, { once: true });
bindInteraction();
initialize();
