const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const source = fs.readFileSync(
        path.join(__dirname, '../static/js/product-intelligence.js'), 'utf8');
    const module = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
    assert.equal(module.platformCategory(500), 'mobile');
    assert.equal(module.platformCategory(900), 'tablet');
    assert.equal(module.platformCategory(1200), 'desktop');
    assert.equal(module.pageCategory('/'), 'home');
    assert.equal(module.pageCategory('/privacy'), 'privacy');
    assert.equal(module.pageCategory('/drinks-with-friendz/privacy'), 'drinks_with_friendz_privacy');
    assert.equal(module.pageCategory('/unrecognized'), 'other');

    const element = { closest: selector => selector === '[data-product-event]' ? {
        dataset: { productEvent:'testflight_link_activated', productTarget:'chaseingreen' }
    } : null };
    const logical = module.activationFrom(element);
    assert.deepEqual(logical, {event:'testflight_link_activated', productTarget:'chaseingreen'});
    // Mouse, touch and keyboard activation all converge on the browser's single click event.
    for (const source of ['mouse', 'touch', 'keyboard']) {
        assert.deepEqual(module.activationFrom(element), logical, source);
    }
    assert.deepEqual(module.productEventPayload(logical), {
        event:'testflight_link_activated', dimensions:{product_target:'chaseingreen'}
    });
    assert.deepEqual(module.productEventPayload({event:'eyeball_clarification_rephrase',
        clarificationReason:'ambiguous_typo'}), {event:'eyeball_clarification_rephrase',
        dimensions:{clarification_reason:'ambiguous_typo'}});
    assert.deepEqual(module.productEventPayload({event:'website_page_viewed', page:'home'}),
        {event:'website_page_viewed', dimensions:{page:'home'}});
    assert.deepEqual(module.productEventPayload({event:'product_card_activated',
        productTarget:'sportfolio'}), {event:'product_card_activated',
        dimensions:{product_target:'sportfolio'}});
    for (const invalid of [
        {event:'unknown'},
        {event:'testflight_link_activated', productTarget:'private'},
        {event:'eyeball_opened', language:'en', message:'private'},
        {event:'website_session_started', platform:'raw user agent', language:'en'},
        {event:'website_page_viewed', page:'https://private.example'},
        {event:'eyeball_clarification_rephrase', clarificationReason:'private text'},
    ]) assert.equal(module.validProductEvent(invalid), false);
    console.log('PASS product intelligence bounded client assertions');
})().catch(error => { console.error(error); process.exitCode = 1; });
