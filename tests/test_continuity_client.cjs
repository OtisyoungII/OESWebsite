const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const source = fs.readFileSync(
        path.join(__dirname, '../static/js/eyeball-continuity.js'), 'utf8');
    const module = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
    const token = 'a'.repeat(64);
    assert.deepEqual(module.completionDirective({continuation: token}),
        {continuation: token, retainExchange: true});
    assert.deepEqual(module.completionDirective({history: 'exclude_exchange'}),
        {continuation: null, retainExchange: false});
    assert.deepEqual(module.completionDirective({}),
        {continuation: null, retainExchange: true});
    for (const invalid of [null, [], {continuation: 'public_world_lookup'},
            {history: 'include'}, {capability: 'public_world_lookup'}]) {
        assert.throws(() => module.completionDirective(invalid));
    }
    console.log('PASS Eyeball bounded continuity metadata assertions');
})().catch(error => { console.error(error); process.exitCode = 1; });
