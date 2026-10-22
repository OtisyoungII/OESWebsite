const events = new Set([
    'website_session_started', 'product_card_activated', 'eyeball_opened',
    'eyeball_closed', 'eyeball_message_submitted', 'eyeball_language_changed',
    'external_product_link_activated', 'testflight_link_activated',
    'web_app_link_activated', 'contact_action_activated',
    'eyeball_clarification_rephrase'
]);
const products = new Set(['chaseingreen', 'lottovate', 'sportfolio', 'drinkswithfriendz']);
const languages = new Set(['en', 'es', 'fr', 'ar', 'zh-CN']);
const clarificationReasons = new Set(['ambiguous_typo', 'high_impact_ambiguity', 'low_confidence']);

export function platformCategory(width) {
    return width <= 760 ? 'mobile' : width <= 1020 ? 'tablet' : 'desktop';
}

export function validProductEvent(detail) {
    if (!detail || typeof detail !== 'object' || !events.has(detail.event)) return false;
    if (detail.productTarget !== undefined && !products.has(detail.productTarget)) return false;
    if (detail.language !== undefined && !languages.has(detail.language)) return false;
    if (detail.platform !== undefined
            && !['desktop', 'tablet', 'mobile', 'unknown'].includes(detail.platform)) return false;
    if (detail.clarificationReason !== undefined
            && !clarificationReasons.has(detail.clarificationReason)) return false;
    return Object.keys(detail).every(key =>
        ['event', 'productTarget', 'language', 'platform', 'clarificationReason'].includes(key));
}

export function activationFrom(element) {
    const activation = element?.closest?.('[data-product-event]');
    if (!activation) return null;
    const detail = { event: activation.dataset.productEvent };
    if (activation.dataset.productTarget) detail.productTarget = activation.dataset.productTarget;
    return validProductEvent(detail) ? detail : null;
}

export function productEventPayload(detail) {
    if (!validProductEvent(detail)) throw new Error('invalid product event');
    const dimensions = {};
    if (detail.productTarget) dimensions.product_target = detail.productTarget;
    if (detail.language) dimensions.language = detail.language;
    if (detail.platform) dimensions.platform = detail.platform;
    if (detail.clarificationReason) dimensions.clarification_reason = detail.clarificationReason;
    return { event: detail.event, dimensions };
}

export async function initializeProductIntelligence() {
    const counter = document.querySelector('[data-product-counter]');
    if (!counter) return;
    const queue = [];
    let ready = false;
    const send = detail => {
        if (!validProductEvent(detail)) return;
        if (!ready) { queue.push(detail); return; }
        fetch(counter.dataset.eventUrl, {
            method: 'POST', credentials: 'same-origin', keepalive: true,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(productEventPayload(detail))
        }).catch(() => {});
    };
    document.addEventListener('oes:product-event', event => send(event.detail));
    document.addEventListener('click', event => {
        const detail = activationFrom(event.target);
        if (detail) send(detail);
    });
    try {
        const response = await fetch(counter.dataset.sessionUrl, {
            method: 'POST', credentials: 'same-origin', headers: { Accept: 'application/json' }
        });
        if (!response.ok) return;
        const result = await response.json();
        if (!Number.isSafeInteger(result.sessions) || result.sessions < 1
                || result.scope !== 'service_runtime') return;
        counter.querySelector('[data-product-counter-value]').textContent =
            result.sessions.toLocaleString();
        counter.hidden = false;
        ready = true;
        send({ event: 'website_session_started', platform: platformCategory(window.innerWidth),
            language: languages.has(document.documentElement.lang) ? document.documentElement.lang : 'en' });
        queue.splice(0).forEach(send);
    } catch { /* Product intelligence never blocks the website. */ }
}
