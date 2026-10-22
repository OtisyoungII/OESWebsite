const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; this.listeners = {}; }
    setAttribute(name, value) { this[name] = value; }
    append(...children) { this.children.push(...children); }
    addEventListener(kind, callback) { this.listeners[kind] = callback; }
    querySelectorAll(selector) {
        const found = [];
        const visit = item => { if (selector === 'button' && item.tag === 'button') found.push(item); item.children.forEach(visit); };
        this.children.forEach(visit); return found;
    }
    click() { this.listeners.click?.(); }
}

(async () => {
    const source = fs.readFileSync(path.join(__dirname, '../static/js/eyeball-clarification.js'), 'utf8');
    const module = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
    const token = 'a'.repeat(64);
    const value = {prompt:'Candidates', reason:'ambiguous_typo', choices:[{label:'isle', token}]};
    assert.equal(module.validClarification(value), true);
    for (const invalid of [
        {...value, capability:'deploy'}, {...value, choices:[...value.choices, ...value.choices, ...value.choices, ...value.choices]},
        {...value, choices:[{label:'x', token:'bad'}]}, {...value, reason:'private text'}
    ]) assert.equal(module.validClarification(invalid), false);

    const document = {createElement: tag => new Element(tag)};
    let selected = 0, rephrased = 0;
    const card = module.renderClarification(document, value, {
        clarificationLabel:'Clarification choices', clarificationSomethingElse:'Something else'
    }, {select: () => selected++, rephrase: () => rephrased++});
    const buttons = card.querySelectorAll('button');
    buttons[0].click(); // Native click is the common mouse/touch/keyboard activation path.
    buttons[0].click();
    buttons[1].click();
    assert.equal(selected, 1);
    assert.equal(rephrased, 0);
    assert.ok(buttons.every(button => button.disabled));
    assert.equal(card['aria-label'], 'Clarification choices');

    const second = module.renderClarification(document, value, {
        clarificationLabel:'Choices', clarificationSomethingElse:'Something else'
    }, {select: () => selected++, rephrase: () => rephrased++});
    second.querySelectorAll('button')[1].click();
    assert.equal(rephrased, 1);
    console.log('PASS bounded clarification client assertions');
})().catch(error => { console.error(error); process.exitCode = 1; });
