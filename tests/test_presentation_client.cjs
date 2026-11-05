const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const presentationPath = path.join(__dirname, '../static/js/eyeball-presentation.js');
    const presentationSource = fs.readFileSync(presentationPath, 'utf8');
    const chatSource = fs.readFileSync(path.join(__dirname, '../static/js/eyeball-chat.js'), 'utf8');
    const cssSource = fs.readFileSync(path.join(__dirname, '../static/css/eyeball-chat.css'), 'utf8');
    const module = await import('data:text/javascript;base64,' + Buffer.from(presentationSource).toString('base64'));

    const target = { dataset: {} };
    let nextTimer = 1;
    const timers = new Map();
    const presentation = module.createEyeballPresentation({
        targets: [target], reducedMotion: false,
        setTimer: (callback, delay) => { const id = nextTimer++; timers.set(id, {callback, delay}); return id; },
        clearTimer: id => timers.delete(id)
    });
    const lifecycle = module.createEyeballPresentationLifecycle(presentation);
    const runDelay = delay => {
        const match = [...timers.entries()].find(([, timer]) => timer.delay === delay);
        assert.ok(match, `expected ${delay}ms timer`);
        timers.delete(match[0]);
        match[1].callback();
    };

    assert.equal(target.dataset.eyeballState, 'idle');
    lifecycle.aware(); assert.equal(target.dataset.eyeballState, 'aware');
    lifecycle.open(false); assert.equal(target.dataset.eyeballState, 'open');
    assert.equal(target.dataset.eyeballMoment, 'activation');
    runDelay(280); assert.equal(target.dataset.eyeballState, 'attentive');

    lifecycle.submitted(); assert.equal(target.dataset.eyeballState, 'thinking');
    lifecycle.responseStarted(); assert.equal(target.dataset.eyeballState, 'speaking');
    lifecycle.completed(); assert.equal(target.dataset.eyeballState, 'success');
    runDelay(360); assert.equal(target.dataset.eyeballState, 'attentive');

    lifecycle.submitted();
    lifecycle.failed(); assert.equal(target.dataset.eyeballState, 'error');
    runDelay(520); assert.equal(target.dataset.eyeballState, 'attentive');
    lifecycle.submitted();
    lifecycle.cancelled(true); assert.equal(target.dataset.eyeballState, 'attentive');
    lifecycle.submitted();
    lifecycle.cancelled(false); assert.equal(target.dataset.eyeballState, 'idle');
    lifecycle.responseStarted();
    lifecycle.closed(); assert.equal(target.dataset.eyeballState, 'idle');

    lifecycle.clarifying(); assert.equal(target.dataset.eyeballState, 'clarifying');
    lifecycle.clarified(); assert.equal(target.dataset.eyeballState, 'attentive');

    // Reopening replaces bounded state/moment timers instead of accumulating them.
    lifecycle.open(false);
    lifecycle.open(true);
    assert.ok(timers.size <= 2);
    assert.equal(target.dataset.eyeballMoment, 'curious');

    presentation.setReducedMotion(true);
    assert.equal(target.dataset.eyeballMotion, 'reduced');
    presentation.showMoment('completion');
    runDelay(0);
    assert.equal(target.dataset.eyeballMoment, undefined);
    assert.match(cssSource, /prefers-reduced-motion:\s*reduce/);
    assert.match(cssSource, /animation:\s*none\s*!important/);

    // Presentation remains local and content-blind; request/capability data stay untouched.
    assert.doesNotMatch(presentationSource, /fetch\s*\(|XMLHttpRequest|sendBeacon|localStorage/);
    assert.match(chatSource, /body:\s*JSON\.stringify\(\{ message: text, history, context: browserContext\(\), locale,/);
    assert.doesNotMatch(presentationSource, /capabilit|authority|telemetry|analytics/i);
    assert.match(chatSource, /event\.pointerType !== 'touch'/);
    assert.match(chatSource, /if \(shouldRefocusComposer\(\)\) input\.focus\(\)/);
    assert.match(chatSource, /dialog\.dataset\.initialized/);

    presentation.destroy();
    assert.deepEqual(target.dataset, {});
    assert.equal(timers.size, 0);
    console.log('PASS Eyeball presentation state, lifecycle, privacy, and reduced-motion assertions');
})().catch(error => { console.error(error); process.exitCode = 1; });
