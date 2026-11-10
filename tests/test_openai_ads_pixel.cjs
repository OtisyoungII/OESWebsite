const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const source = fs.readFileSync(path.join(__dirname, '../static/js/openai-ads-pixel.js'), 'utf8');
const listeners = {};
const banner = { hidden: true };
const buttons = Object.fromEntries(['accept', 'decline', 'settings'].map(name => [name, {
    addEventListener(type, fn) { listeners[name + ':' + type] = fn; }
}]));
const scripts = [];
const calls = [];
const storage = new Map();
const document = {
    head: { appendChild(node) { scripts.push(node); } },
    querySelector(selector) {
        if (selector === 'meta[name="openai-ads-pixel-id"]') return { content: '3qM2gGrPhYMvgiPtiueQj5' };
        if (selector === '[data-ads-consent]') return banner;
        if (selector === '[data-ads-consent-accept]') return buttons.accept;
        if (selector === '[data-ads-consent-decline]') return buttons.decline;
    },
    querySelectorAll(selector) { return selector === '[data-ads-consent-settings]' ? [buttons.settings] : []; },
    createElement() { return {}; },
    addEventListener(type, fn) { listeners['document:' + type] = fn; }
};
const window = {
    location: { href: 'https://otisexecutionsystems.com/' },
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) }
};
const context = vm.createContext({ window, document, URL });
vm.runInContext(source, context);
assert.equal(banner.hidden, false);
assert.equal(scripts.length, 0);
assert.equal(window.oaiq, undefined);

listeners['accept:click']();
assert.equal(scripts.length, 1);
assert.equal(scripts[0].src, 'https://bzrcdn.openai.com/sdk/oaiq.min.js');
assert.deepEqual(Array.from(window.oaiq.q, args => args[0]), ['consent', 'init', 'measure']);
assert.equal(window.oaiq.q[0][1], true);
assert.equal(window.oaiq.q[1][1].pixelId, '3qM2gGrPhYMvgiPtiueQj5');
assert.equal(window.oaiq.q[2][1], 'page_viewed');

function click(href) {
    listeners['document:click']({ target: { closest: () => ({ href }) } });
}
click('https://testflight.apple.com/join/nPjjyDSf');
click('https://apps.apple.com/us/app/chaseingreen/id6770096789');
assert.deepEqual(Array.from(window.oaiq.q.slice(3), args => args[3].custom_event_name),
    ['testflight_clicked', 'app_store_clicked']);
vm.runInContext(source, context);
assert.equal(scripts.length, 1);
listeners['settings:click']();
listeners['decline:click']();
assert.equal(window.oaiq.q.at(-1)[0], 'consent');
assert.equal(window.oaiq.q.at(-1)[1], false);
click('https://apps.apple.com/us/app/chaseingreen/id6770096789');
assert.equal(window.oaiq.q.at(-1)[0], 'consent');
listeners['settings:click']();
listeners['accept:click']();
assert.equal(scripts.length, 1);
assert.equal(window.oaiq.q.filter(args => args[0] === 'init').length, 1);
assert.equal(window.oaiq.q.filter(args => args[1] === 'page_viewed').length, 1);
console.log('PASS OpenAI Ads Pixel consent, events, and duplicate guards');
