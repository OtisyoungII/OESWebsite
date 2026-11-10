(function (window, document) {
    if (window.__oesAdsPixelInstalled) return;
    window.__oesAdsPixelInstalled = true;

    const pixelId = document.querySelector('meta[name="openai-ads-pixel-id"]')?.content;
    if (!pixelId) return;
    const preferenceKey = 'oes-openai-ads-measurement-consent';
    const banner = document.querySelector('[data-ads-consent]');
    let preference;
    let initialized = false;
    let pageViewed = false;
    try { preference = window.localStorage.getItem(preferenceKey); } catch { preference = null; }

    function sdk() {
        if (window.oaiq) return;
        const queue = function () { queue.q.push(arguments); };
        queue.q = [];
        window.oaiq = queue;
        const script = document.createElement('script');
        script.async = true;
        script.src = 'https://bzrcdn.openai.com/sdk/oaiq.min.js';
        document.head.appendChild(script);
    }

    function activate() {
        if (initialized) {
            window.oaiq('consent', true);
            return;
        }
        sdk();
        window.oaiq('consent', true);
        window.oaiq('init', { pixelId });
        initialized = true;
        if (!pageViewed) {
            window.oaiq('measure', 'page_viewed', { type: 'contents' });
            pageViewed = true;
        }
    }

    function choose(value) {
        preference = value;
        try { window.localStorage.setItem(preferenceKey, value); } catch { /* Current-page choice still applies. */ }
        if (value === 'granted') activate();
        else if (initialized) window.oaiq('consent', false);
        if (banner) banner.hidden = true;
    }

    if (preference === 'granted') activate();
    else if (preference !== 'denied' && banner) banner.hidden = false;

    document.querySelector('[data-ads-consent-accept]')?.addEventListener('click', () => choose('granted'));
    document.querySelector('[data-ads-consent-decline]')?.addEventListener('click', () => choose('denied'));
    document.querySelectorAll('[data-ads-consent-settings]').forEach(button =>
        button.addEventListener('click', () => { if (banner) banner.hidden = false; }));

    document.addEventListener('click', event => {
        if (preference !== 'granted' || !initialized) return;
        const link = event.target.closest?.('a[href]');
        if (!link) return;
        let url;
        try { url = new URL(link.href, window.location.href); } catch { return; }
        let name;
        if (url.hostname === 'testflight.apple.com' && url.pathname.startsWith('/join/'))
            name = 'testflight_clicked';
        else if (url.hostname === 'apps.apple.com' && url.pathname === '/us/app/chaseingreen/id6770096789')
            name = 'app_store_clicked';
        if (name) window.oaiq('measure', 'custom', { type: 'custom' }, { custom_event_name: name });
    });
})(window, document);
