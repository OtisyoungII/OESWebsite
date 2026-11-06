import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const url = process.argv[2] || "http://127.0.0.1:5058/static/design-exploration/motor-city/concept-d/index.html";
const output = resolve(process.argv[3] || "docs/design-previews/liquid-alloy/stage-e");
const chrome = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const profile = mkdtempSync(join(tmpdir(), "oes-petal-chrome-"));
const port = 9338;
mkdirSync(output, { recursive: true });

const browser = spawn(chrome, [
  "--headless=new", "--no-first-run", "--disable-default-apps",
  "--remote-allow-origins=*", `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, "--window-size=1440,1000", url,
], { windowsHide: true, stdio: "ignore" });

const delay = (ms) => new Promise((resolveDelay) => setTimeout(resolveDelay, ms));
let socket;
let nextId = 1;
const pending = new Map();
const browserErrors = [];

function command(method, params = {}) {
  const id = nextId++;
  return new Promise((resolveCommand, rejectCommand) => {
    pending.set(id, { resolve: resolveCommand, reject: rejectCommand });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await command("Runtime.evaluate", {
    expression, returnByValue: true, awaitPromise: true,
  });
  if (response.result.exceptionDetails) throw new Error(response.result.exceptionDetails.text);
  return response.result.result.value;
}

async function capture(name) {
  const response = await command("Page.captureScreenshot", {
    format: "png", captureBeyondViewport: false,
  });
  const path = join(output, name);
  writeFileSync(path, Buffer.from(response.result.data, "base64"));
  return path;
}

try {
  let target;
  for (let attempt = 0; attempt < 60 && !target; attempt += 1) {
    await delay(150);
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      target = pages.find((page) => page.type === "page");
    } catch { /* Chrome is still starting. */ }
  }
  if (!target) throw new Error("Chrome DevTools target did not become ready");
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolveOpen, rejectOpen) => {
    socket.addEventListener("open", resolveOpen, { once: true });
    socket.addEventListener("error", rejectOpen, { once: true });
  });
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.method === "Runtime.exceptionThrown") {
      browserErrors.push(message.params?.exceptionDetails?.text || "runtime exception");
    }
    if (message.method === "Log.entryAdded" && message.params?.entry?.level === "error") {
      browserErrors.push({ text: message.params.entry.text || "browser log error",
        url: message.params.entry.url || "" });
    }
    if (!message.id || !pending.has(message.id)) return;
    const waiter = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) waiter.reject(new Error(message.error.message));
    else waiter.resolve(message);
  });
  await command("Runtime.enable");
  await command("Page.enable");
  await command("Log.enable");
  await command("Page.reload", { ignoreCache: true });
  await delay(400);

  let ready = false;
  for (let attempt = 0; attempt < 80 && !ready; attempt += 1) {
    await delay(150);
    ready = await evaluate("document.querySelector('[data-eyeball-stage]')?.dataset.renderState === 'ready'");
  }
  if (!ready) throw new Error("Petal Core did not reach the ready state");
  const initial = await evaluate(`(() => {
    const stage = document.querySelector('[data-eyeball-stage]');
    return { state: stage.dataset.renderState, meshes: Number(stage.dataset.meshCount),
      materials: Number(stage.dataset.materialCount), animations: Number(stage.dataset.animationCount),
      status: document.querySelector('[data-petal-status]').textContent,
      fallback: !document.querySelector('[data-petal-fallback]').hidden };
  })()`);
  await evaluate("(() => { document.documentElement.style.scrollBehavior='auto'; const e=document.querySelector('#eyeball'); window.scrollTo(0, e.getBoundingClientRect().top + scrollY - 78); return true; })()");
  await delay(500);
  const desktopScreenshot = await capture("petal-core-stage-e-desktop.png");

  const expressions = {};
  for (const name of ["listening", "thinking", "responding", "blink", "neutral"]) {
    expressions[name] = await evaluate(`(() => {
      const button = document.querySelector('[data-expression="${name}"]'); button.click();
      return { pressed: button.getAttribute('aria-pressed'),
        status: document.querySelector('[data-petal-status]').textContent };
    })()`);
    await delay(750);
  }

  const rect = await evaluate(`(() => { const r=document.querySelector('[data-petal-canvas]').getBoundingClientRect();
    return {x:r.x,y:r.y,w:r.width,h:r.height}; })()`);
  const startX = rect.x + rect.w * 0.45;
  const startY = rect.y + rect.h * 0.5;
  await command("Input.dispatchMouseEvent", { type: "mousePressed", x: startX, y: startY,
    button: "left", clickCount: 1 });
  await command("Input.dispatchMouseEvent", { type: "mouseMoved", x: startX + 110, y: startY - 35,
    button: "left", buttons: 1 });
  await command("Input.dispatchMouseEvent", { type: "mouseReleased", x: startX + 110, y: startY - 35,
    button: "left", clickCount: 1 });
  await delay(250);
  const dragRotation = await evaluate("document.querySelector('[data-eyeball-stage]').dataset.rotation");

  await command("Emulation.setDeviceMetricsOverride", {
    width: 390, height: 844, deviceScaleFactor: 1, mobile: true,
  });
  await evaluate("(() => { document.documentElement.style.scrollBehavior='auto'; const e=document.querySelector('#eyeball'); window.scrollTo(0, e.getBoundingClientRect().top + scrollY - 68); return true; })()");
  await delay(400);
  const mobileRect = await evaluate(`(() => { const r=document.querySelector('[data-petal-canvas]').getBoundingClientRect();
    return {x:r.x,y:r.y,w:r.width,h:r.height}; })()`);
  const touchX = mobileRect.x + mobileRect.w * 0.5;
  const touchY = mobileRect.y + mobileRect.h * 0.45;
  await command("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: touchX, y: touchY }] });
  await command("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: touchX - 70, y: touchY + 20 }] });
  await command("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await delay(250);
  const touchRotation = await evaluate("document.querySelector('[data-eyeball-stage]').dataset.rotation");
  const mobileScreenshot = await capture("petal-core-stage-e-mobile.png");

  await command("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-reduced-motion", value: "reduce" }],
  });
  const reducedMotion = await evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches");
  const emptyLinks = await evaluate("[...document.querySelectorAll('a[href]')].filter(a => !a.href).length");
  console.log(JSON.stringify({ initial, expressions, dragRotation, touchRotation,
    reducedMotion, emptyLinks, browserErrors, desktopScreenshot, mobileScreenshot }, null, 2));
  await command("Browser.close");
} finally {
  try { socket?.close(); } catch { /* already closed */ }
  await delay(350);
  if (!browser.killed) browser.kill();
  await delay(350);
  rmSync(profile, { recursive: true, force: true, maxRetries: 4, retryDelay: 150 });
}
