const STATES = new Set([
    'idle', 'aware', 'open', 'attentive', 'thinking', 'speaking',
    'success', 'clarifying', 'error'
]);

const MOMENTS = new Set(['activation', 'completion', 'curious', 'error']);

function defaultReducedMotion() {
    return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

// Presentation only: no request data, chat facts, reporting, or network access.
export function createEyeballPresentation({
    targets = [],
    reducedMotion = defaultReducedMotion(),
    setTimer = (callback, delay) => window.setTimeout(callback, delay),
    clearTimer = timer => window.clearTimeout(timer)
} = {}) {
    const roots = targets.filter(Boolean);
    let state = 'idle';
    let moment = null;
    let motionReduced = Boolean(reducedMotion);
    let stateTimer = null;
    let momentTimer = null;
    let revision = 0;

    function apply() {
        for (const root of roots) {
            root.dataset.eyeballState = state;
            root.dataset.eyeballMotion = motionReduced ? 'reduced' : 'full';
            if (moment) root.dataset.eyeballMoment = moment;
            else delete root.dataset.eyeballMoment;
        }
    }

    function transition(next) {
        if (!STATES.has(next)) throw new TypeError(`Unknown Eyeball presentation state: ${next}`);
        revision += 1;
        if (stateTimer !== null) clearTimer(stateTimer);
        stateTimer = null;
        state = next;
        apply();
        return state;
    }

    function transitionFor(next, duration, fallback) {
        transition(next);
        const expectedRevision = revision;
        stateTimer = setTimer(() => {
            stateTimer = null;
            if (revision === expectedRevision) transition(fallback);
        }, duration);
    }

    function showMoment(next, duration = 420) {
        if (!MOMENTS.has(next)) throw new TypeError(`Unknown Eyeball presentation moment: ${next}`);
        if (momentTimer !== null) clearTimer(momentTimer);
        moment = next;
        apply();
        momentTimer = setTimer(() => {
            momentTimer = null;
            if (moment === next) {
                moment = null;
                apply();
            }
        }, motionReduced ? 0 : duration);
    }

    function setReducedMotion(value) {
        motionReduced = Boolean(value);
        apply();
    }

    function destroy() {
        revision += 1;
        if (stateTimer !== null) clearTimer(stateTimer);
        if (momentTimer !== null) clearTimer(momentTimer);
        stateTimer = null;
        momentTimer = null;
        for (const root of roots) {
            delete root.dataset.eyeballState;
            delete root.dataset.eyeballMotion;
            delete root.dataset.eyeballMoment;
        }
    }

    apply();
    return {
        transition,
        transitionFor,
        showMoment,
        setReducedMotion,
        snapshot: () => ({ state, moment, reducedMotion: motionReduced }),
        destroy
    };
}

export const EYEBALL_PRESENTATION_STATES = Object.freeze([...STATES]);

export function createEyeballPresentationLifecycle(presentation) {
    return Object.freeze({
        aware: () => presentation.transition('aware'),
        idle: () => presentation.transition('idle'),
        open: rare => {
            presentation.transitionFor('open', 280, 'attentive');
            presentation.showMoment(rare ? 'curious' : 'activation');
        },
        attentive: () => presentation.transition('attentive'),
        submitted: () => presentation.transition('thinking'),
        responseStarted: () => presentation.transition('speaking'),
        completed: () => {
            presentation.transitionFor('success', 360, 'attentive');
            presentation.showMoment('completion', 320);
        },
        failed: () => {
            presentation.transitionFor('error', 520, 'attentive');
            presentation.showMoment('error', 360);
        },
        cancelled: dialogOpen => presentation.transition(dialogOpen ? 'attentive' : 'idle'),
        closed: () => presentation.transition('idle'),
        clarifying: () => presentation.transitionFor('clarifying', 900, 'attentive')
    });
}
