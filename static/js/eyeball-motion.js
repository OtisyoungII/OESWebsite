// Local observations only. Scores express tentative geometry, never visitor intent.
const center = r => ({ x: r.left + r.width / 2, y: r.top + r.height / 2 });
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
export class MotionArbiter {
    constructor(now = () => performance.now()) {
        this.now = now;
        this.previous = null;
        this.sample = null;
        this.pointers = new Set();
        this.holdUntil = 0;
        this.cooldownUntil = 0;
    }
    observe(point, core, target = null, onCore = false) {
        const time = this.now(), c = center(core), d = distance(point, c);
        const previous = this.previous;
        const dt = previous ? time - previous.time : 0;
        const travel = previous ? distance(point, previous) : 0;
        const fresh = dt > 0 && dt <= 250 && travel >= 1;
        const toward = destination => fresh
            ? Math.max(0, Math.min(1, (distance(previous, destination) - distance(point, destination)) / travel)) : 0;
        const near = d <= Math.max(core.width, core.height) / 2 + 120;
        // Do not turn the Core's own travel under a pointer into visitor approach.
        const sweptUnderPointer = previous && distance(previous.core, c) > 2 && toward(c) < 0.65;
        const directedAtCore = onCore && !sweptUnderPointer;
        const approach = directedAtCore ? 1 : near ? toward(c) : 0;
        let obstruction = 0;
        if (target) {
            const overlap = Math.max(0, Math.min(core.right, target.right) - Math.max(core.left, target.left))
                * Math.max(0, Math.min(core.bottom, target.bottom) - Math.max(core.top, target.top));
            const fraction = overlap / Math.max(1, target.width * target.height);
            if (fraction >= 0.2 && distance(point, center(target)) <= 240) obstruction = toward(center(target));
        }
        if (approach >= 0.65) this.holdUntil = time + 900;
        this.sample = { time, distance: d, approach, obstruction, onCore: directedAtCore };
        this.previous = { ...point, time, core: c }; // One previous point, no trails or persistence.
    }
    down(id) { this.pointers.add(id); }
    up(id) { this.pointers.delete(id); this.holdUntil = this.now() + 900; }
    resetPointer() { this.pointers.clear(); this.previous = null; this.sample = null; }
    relocated() { this.cooldownUntil = this.now() + 3000; }
    decide({ reason = 'interest-change', chat = false, invitation = false, focused = false,
             suppressed = false, serious = false, continuing = false } = {}) {
        const now = this.now(), s = this.sample;
        const fresh = s && now - s.time <= 300;
        let state = 'observing', allowed = true, why = 'section-placement';
        // Explicit movement and viewport safety retain their existing owners.
        if (reason.startsWith('manual') || reason === 'drag' || reason === 'viewport-resize') {
            state = 'engaged'; why = 'explicit-or-viewport-movement';
        } else if (suppressed) { state = 'suppressed'; allowed = false; why = 'suppressed';
        } else if (chat || invitation || focused || this.pointers.size) {
            state = 'engaged'; allowed = false; why = 'interaction-lock';
        } else if (serious) { state = 'serious'; allowed = false; why = 'serious-context';
        } else if (now < this.holdUntil || (fresh && s.onCore)) {
            state = 'approached'; allowed = false; why = 'possible-approach';
        } else if (!continuing && now < this.cooldownUntil) {
            state = 'available'; allowed = false; why = 'relocation-cooldown';
        } else if (reason === 'interest-change') {
            allowed = continuing || Boolean(fresh && s.obstruction >= 0.8 && s.approach < 0.65);
            state = allowed ? 'avoiding' : 'available'; why = allowed ? 'observed-obstruction' : 'insufficient-obstruction';
        }
        return { state, pointer_distance: fresh ? Math.round(s.distance) : null,
            approach_score: fresh ? Number(s.approach.toFixed(2)) : 0,
            obstruction_score: fresh ? Number(s.obstruction.toFixed(2)) : 0,
            movement_allowed: allowed, movement_reason: why };
    }
}

export function createMotionController(core, portal, onObstruction) {
    const arbiter = new MotionArbiter();
    const listeners = new AbortController();
    const actionable = 'a[href],button,input,select,textarea,[role="button"]';
    let lastLog = '', lastLogAt = -Infinity;
    let observedTarget = null;
    function decision(reason, continuing = false) {
        const result = arbiter.decide({ reason, continuing,
            chat: Boolean(document.querySelector('#eyeball-chat')?.open),
            invitation: Boolean(document.querySelector('[data-eyeball-invitation]:not([hidden])')),
            focused: portal.contains(document.activeElement) || core.contains(document.activeElement),
            suppressed: document.hidden,
            serious: ['government', 'privacy'].includes(document.querySelector('main')?.dataset.currentSection)
        });
        const key = result.state + result.movement_reason;
        if (document.documentElement.dataset.motionDebug === 'true' && key !== lastLog && performance.now() - lastLogAt >= 500) {
            console.debug('Eyeball motion', result); lastLog = key; lastLogAt = performance.now();
        }
        return result;
    }
    document.addEventListener('pointermove', event => {
        if (!event.isPrimary || event.pointerType === 'touch') return;
        const rect = core.getBoundingClientRect();
        const onCore = portal.contains(event.target) || core.contains(event.target);
        // Read actual actionable geometry, including partially obscured targets.
        const target = document.elementsFromPoint(event.clientX, event.clientY)
            .map(e => e.closest(actionable)).find(e => e && !portal.contains(e) && !core.contains(e));
        observedTarget = target || null;
        arbiter.observe({ x: event.clientX, y: event.clientY }, rect, target?.getBoundingClientRect(), onCore);
        const policy = decision('interest-change');
        if (target && policy.movement_allowed) onObstruction(target);
    }, { capture: true, passive: true, signal: listeners.signal });
    document.addEventListener('pointerdown', event => {
        if (portal.contains(event.target) || core.contains(event.target)) arbiter.down(event.pointerId);
    }, { capture: true, passive: true, signal: listeners.signal });
    for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
        document.addEventListener(name, event => {
            if (arbiter.pointers.has(event.pointerId)) arbiter.up(event.pointerId);
        }, { capture: true, passive: true, signal: listeners.signal });
    }
    window.addEventListener('blur', () => arbiter.resetPointer(), { signal: listeners.signal });
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) arbiter.resetPointer();
    }, { signal: listeners.signal });
    return { allowed: (reason, continuing = false) => decision(reason, continuing).movement_allowed,
        obstructed: element => observedTarget && (element === observedTarget || observedTarget.contains(element)),
        relocated: () => arbiter.relocated(), destroy: () => listeners.abort() };
}
