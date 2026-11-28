const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const origin = process.env.OES_LOCAL_PREVIEW || 'http://127.0.0.1:5095';
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) throw new Error('Use a local loopback preview.');

async function main() {
    const browser = await chromium.launch({ channel: 'msedge', headless: true });
    try {
        const guide = '/chaseingreen/onboarding/aquafunded';
        for (const width of [390, 768, 1440]) {
            const page = await browser.newPage({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
            const errors = [];
            page.on('pageerror', error => errors.push(error.name));
            await page.route('**/*', route => route.request().url().startsWith(origin + '/') ?
                route.continue() : route.abort());
            for (const path of ['/', '/products', '/chaseingreen', '/chaseingreen/getting-started',
                '/chaseingreen/onboarding', guide, '/chaseingreen/android', '/privacy',
                '/drinks-with-friendz/privacy']) {
                assert.equal((await page.goto(origin + path)).status(), 200, path);
                assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2),
                    width + 'px overflow: ' + path);
            }
            for (const path of ['/', '/chaseingreen']) {
                await page.goto(origin + path);
                await page.getByRole('link', { name: 'AquaFunded guide', exact: true }).click();
                await page.waitForURL('**' + guide);
            }
            assert.equal(await page.locator('[data-marketing-click="affiliate"]').getAttribute('href'),
                'https://www.aquafunded.com/?afmc=121w');
            const steps = page.getByRole('navigation', { name: 'Guide steps' }).getByRole('link');
            assert.equal(await steps.count(), 8);
            for (const link of await steps.all()) {
                assert.equal(await page.locator(await link.getAttribute('href')).count(), 1);
            }
            await steps.nth(5).focus();
            await page.keyboard.press('Enter');
            await page.waitForURL('**#platform');
            const image = page.locator('.guide-app-reference img');
            await image.scrollIntoViewIfNeeded();
            await image.evaluate(element => element.decode());
            assert.ok(await image.evaluate(element => element.naturalWidth > 0));
            const summary = page.locator('#troubleshoot summary').first();
            await summary.focus();
            await page.keyboard.press('Enter');
            assert.equal(await page.locator('#troubleshoot details[open]').count(), 1);
            assert.deepEqual(errors, []);
            console.log(width + 'px: nine routes, guide links, images and keyboard checks passed');
            await page.close();
        }
    } finally {
        await browser.close();
    }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
