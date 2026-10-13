// Run with node tests/test_localization_client.cjs; no packages or browser required.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
    const source = fs.readFileSync(path.join(__dirname, '../static/js/eyeball-localization.js'), 'utf8');
    const module = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
    const { EYEBALL_LOCALES, EYEBALL_LOCALE_STORAGE_KEY, initialEyeballLocale,
        localeDefinition, mapBrowserLocale, persistEyeballLocale,
        shouldRefocusEyeballComposer } = module;

    assert.equal(mapBrowserLocale(['es-MX']), 'es');
    assert.equal(mapBrowserLocale(['fr-CA']), 'fr');
    assert.equal(mapBrowserLocale(['ar-EG']), 'ar');
    assert.equal(mapBrowserLocale(['zh-Hans-SG']), 'zh-CN');
    assert.equal(mapBrowserLocale(['zh-TW']), 'en');
    assert.equal(mapBrowserLocale(['de-DE']), 'en');

    const values = new Map([[EYEBALL_LOCALE_STORAGE_KEY, 'fr']]);
    const storage = { getItem: key => values.get(key) ?? null,
        setItem: (key, value) => values.set(key, value) };
    assert.equal(initialEyeballLocale(storage, ['es-MX']), 'fr',
        'explicit preference overrides browser locale');
    assert.equal(persistEyeballLocale(storage, 'ar'), true);
    assert.equal(values.get(EYEBALL_LOCALE_STORAGE_KEY), 'ar');
    assert.equal(persistEyeballLocale(storage, 'de'), false);
    assert.equal(values.get(EYEBALL_LOCALE_STORAGE_KEY), 'ar');

    assert.equal(localeDefinition('ar').dir, 'rtl');
    for (const locale of ['en', 'es', 'fr', 'zh-CN']) assert.equal(localeDefinition(locale).dir, 'ltr');

    const required = Object.keys(EYEBALL_LOCALES.en.strings).sort();
    assert.deepEqual(Object.keys(EYEBALL_LOCALES).sort(), ['ar', 'en', 'es', 'fr', 'zh-CN']);
    for (const [locale, definition] of Object.entries(EYEBALL_LOCALES)) {
        assert.equal(definition.tag, locale);
        assert.deepEqual(Object.keys(definition.strings).sort(), required,
            `${locale} must contain every required translation key`);
        for (const key of required) assert.ok(definition.strings[key].trim(), `${locale}.${key}`);
    }

    assert.equal(shouldRefocusEyeballComposer('touch', false), false);
    assert.equal(shouldRefocusEyeballComposer('pointer', true), false);
    assert.equal(shouldRefocusEyeballComposer('keyboard', false), true);
    assert.equal(shouldRefocusEyeballComposer('pointer', false), true);

    console.log('PASS Eyeball localization catalog assertions');
})().catch(error => { console.error(error); process.exitCode = 1; });
