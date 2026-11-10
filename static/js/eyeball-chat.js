import { getAwarenessState } from './section-awareness.js';
import { createObservationController } from './eyeball-observations.js';
import { EYEBALL_LOCALES, initialEyeballLocale, localeDefinition,
    persistEyeballLocale, shouldRefocusEyeballComposer } from './eyeball-localization.js';
import { completionDirective } from './eyeball-continuity.js';
import { renderClarification } from './eyeball-clarification.js';

// Same-origin transport only; provider selection and policy stay on the server.
export function initializeEyeballChat() {
    const core = document.querySelector('[data-oes-core]');
    const dialog = document.querySelector('#eyeball-chat');
    if (!core || !dialog || dialog.dataset.initialized) return;
    dialog.dataset.initialized = 'true';

    const input = dialog.querySelector('textarea');
    const form = dialog.querySelector('[data-chat-form]');
    const transcript = dialog.querySelector('[data-chat-transcript]');
    const status = dialog.querySelector('[data-chat-status]');
    const send = dialog.querySelector('[data-chat-send]');
    const stop = dialog.querySelector('[data-chat-stop]');
    const localeControl = dialog.querySelector('[data-chat-locale]');
    const invitation = document.querySelector('[data-eyeball-invitation]');
    let pointer = null;
    let activeRequest = null;
    let history = [];
    let lookupContinuation = null;
    let pendingClarification = null;
    let interactionMode = 'pointer';
    let activityMessage = null;
    let activityTimer = null;
    let retryWithoutEcho = false;
    let preferenceStorage;
    try { preferenceStorage = window.localStorage; } catch { preferenceStorage = null; }
    let locale = initialEyeballLocale(preferenceStorage, navigator.languages || [navigator.language]);

    function applyLocale(selected) {
        const definition = localeDefinition(selected);
        locale = Object.hasOwn(EYEBALL_LOCALES, selected) ? selected : 'en';
        for (const root of [dialog, invitation].filter(Boolean)) {
            root.lang = definition.tag;
            root.dir = definition.dir;
            root.querySelectorAll('[data-i18n]').forEach(element => {
                const value = definition.strings[element.dataset.i18n];
                if (value) element.textContent = value;
            });
            root.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
                const value = definition.strings[element.dataset.i18nAriaLabel];
                if (value) element.setAttribute('aria-label', value);
            });
            root.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
                const value = definition.strings[element.dataset.i18nPlaceholder];
                if (value) element.setAttribute('placeholder', value);
            });
        }
        localeControl.value = locale;
        if (activityMessage?.dataset.state) showActivity(activityMessage.dataset.state);
    }

    function translated(key) { return localeDefinition(locale).strings[key]; }
    function setStatus(key) {
        status.dataset.i18n = key;
        status.textContent = translated(key);
    }
    function shouldRefocusComposer() {
        return shouldRefocusEyeballComposer(
            interactionMode, Boolean(window.matchMedia?.('(pointer: coarse)').matches));
    }

    applyLocale(locale);
    localeControl.addEventListener('change', () => {
        if (!Object.hasOwn(EYEBALL_LOCALES, localeControl.value)) return;
        applyLocale(localeControl.value);
        persistEyeballLocale(preferenceStorage, locale);
        document.dispatchEvent(new CustomEvent('oes:product-event', {
            detail: { event: 'eyeball_language_changed', language: locale }
        }));
    });

    const observations = createObservationController({
        invitation,
        endpoint: form.dataset.initiationUrl,
        generationEndpoint: form.dataset.invitationUrl,
        getHistory: () => history,
        getSection: () => getAwarenessState().currentSectionId,
        getContext: () => [window.innerWidth <= 760 ? 'mobile' : window.innerWidth <= 1020 ? 'tablet' : 'desktop', interactionMode],
        openChat: requestChat,
        onInteraction: mode => { interactionMode = mode; }
    });

    function requestChat() {
        // Independent of oes:coreactivated, which also fires after dragging.
        core.dispatchEvent(new CustomEvent('oes:chatrequest', { bubbles: true }));
    }

    core.addEventListener('pointerdown', (event) => {
        interactionMode = event.pointerType === 'touch' ? 'touch' : 'pointer';
        pointer = event.isPrimary && event.button === 0
            ? { id: event.pointerId, x: event.clientX, y: event.clientY, moved: false }
            : null;
    });
    function trackPointer(event) {
        if (!pointer || pointer.id !== event.pointerId) return;
        // Remember the maximum excursion, even if the pointer returns home.
        pointer.moved ||= Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) >= 5;
    }
    core.addEventListener('pointermove', trackPointer);
    core.addEventListener('pointerup', (event) => {
        trackPointer(event);
        const intentional = pointer && pointer.id === event.pointerId && !pointer.moved;
        pointer = null;
        // Let both existing Core release handlers finish before moving focus.
        if (intentional) queueMicrotask(requestChat);
    });
    core.addEventListener('pointercancel', () => { pointer = null; });
    core.addEventListener('lostpointercapture', () => { pointer = null; });
    window.addEventListener('blur', () => { pointer = null; });
    core.addEventListener('keydown', (event) => {
        if ((event.key === 'Enter' || event.key === ' ') && !event.repeat) {
            interactionMode = 'keyboard';
            event.preventDefault();
            requestChat();
        }
    });
    // Assistive-technology activation may produce click without pointer events.
    core.addEventListener('click', (event) => {
        if (event.detail === 0) requestChat();
    });
    core.addEventListener('oes:chatrequest', () => {
        if (dialog.open) return;
        observations.opened();
        document.dispatchEvent(new CustomEvent('oes:product-event', {
            detail: { event: 'eyeball_opened', language: locale,
                platform: window.innerWidth <= 760 ? 'mobile' : window.innerWidth <= 1020 ? 'tablet' : 'desktop' }
        }));
        dialog.showModal();
        core.setAttribute('aria-expanded', 'true');
        input.focus();
    });

    function setBusy(busy) {
        send.disabled = busy;
        stop.disabled = !busy;
        input.setAttribute('aria-busy', String(busy));
    }
    function removeActivity() {
        clearTimeout(activityTimer);
        activityTimer = null;
        activityMessage?.remove();
        activityMessage = null;
    }
    function showActivity(key) {
        if (!activityMessage) {
            const message = document.createElement('div');
            message.className = 'eyeball-chat__message eyeball-chat__message--activity';
            message.setAttribute('role', 'status');
            message.setAttribute('aria-live', 'polite');
            message.setAttribute('aria-atomic', 'true');
            const label = document.createElement('p');
            label.className = 'eyeball-chat__speaker';
            label.textContent = localeDefinition(locale).strings.eyeball;
            const body = document.createElement('p');
            body.className = 'eyeball-chat__activity';
            message.append(label, body);
            transcript.append(message);
            activityMessage = message;
        }
        const body = activityMessage.querySelector('.eyeball-chat__activity');
        body.dataset.i18n = key;
        body.textContent = translated(key);
        const dots = document.createElement('span');
        dots.className = 'eyeball-chat__activity-dots';
        dots.setAttribute('aria-hidden', 'true');
        dots.textContent = '…';
        body.append(' ', dots);
        activityMessage.dataset.state = key;
        setStatus(key);
        transcript.scrollTop = transcript.scrollHeight;
    }
    function appendFailure(key, text) {
        const message = document.createElement('div');
        message.className = 'eyeball-chat__message eyeball-chat__message--error';
        const label = document.createElement('p');
        label.className = 'eyeball-chat__speaker';
        label.textContent = localeDefinition(locale).strings.eyeball;
        const body = document.createElement('p');
        body.dir = 'auto';
        body.textContent = translated(key);
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'eyeball-chat__retry';
        retry.dataset.i18n = 'retry';
        retry.textContent = translated('retry');
        retry.addEventListener('click', () => {
            if (activeRequest) return;
            retry.disabled = true;
            retryWithoutEcho = true;
            input.value = text;
            message.remove();
            form.requestSubmit();
        }, { once: true });
        message.append(label, body, retry);
        transcript.append(message);
        transcript.scrollTop = transcript.scrollHeight;
    }
    function failureKey(error, timedOut) {
        if (timedOut) return 'timeoutError';
        const responseFailures = new Set([
            'request failed', 'generation failed', 'invalid response',
            'oversized event', 'invalid event', 'interrupted stream', 'empty response'
        ]);
        return responseFailures.has(error?.message) ? 'responseError' : 'connectionError';
    }
    function cancelResponse() {
        if (!activeRequest) return;
        activeRequest.abort();
        activeRequest = null;
        removeActivity();
        setBusy(false);
        setStatus('stopped');
    }
    dialog.querySelector('[data-chat-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', (event) => {
        event.preventDefault();
        dialog.close();
    });
    dialog.addEventListener('close', () => {
        observations.closed();
        document.dispatchEvent(new CustomEvent('oes:product-event', {
            detail: { event: 'eyeball_closed' }
        }));
        cancelResponse();
        core.setAttribute('aria-expanded', 'false');
        core.focus({ preventScroll: true });
    });
    stop.addEventListener('click', () => {
        cancelResponse();
        if (shouldRefocusComposer()) input.focus();
    });
    function appendMessage(speaker, text, user = false) {
        const message = document.createElement('div');
        message.className = 'eyeball-chat__message' + (user ? ' eyeball-chat__message--user' : '');
        const label = document.createElement('p');
        label.className = 'eyeball-chat__speaker';
        label.textContent = speaker;
        const body = document.createElement('p');
        body.dir = 'auto';
        body.textContent = text;
        message.append(label, body);
        transcript.append(message);
        transcript.scrollTop = transcript.scrollHeight;
        return body;
    }
    function browserContext() {
        return observations.snapshot();
    }
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text || text.length > 4000 || activeRequest) return;
        const appendUserMessage = !retryWithoutEcho;
        retryWithoutEcho = false;
        observations.sent();
        document.dispatchEvent(new CustomEvent('oes:product-event', {
            detail: { event: 'eyeball_message_submitted', language: locale }
        }));
        const controller = new AbortController();
        activeRequest = controller;
        if (appendUserMessage) appendMessage(localeDefinition(locale).strings.you, text, true);
        input.value = '';
        setBusy(true);
        showActivity('thinking');
        activityTimer = setTimeout(() => {
            if (activeRequest === controller && !answer) showActivity('stillWorking');
        }, 12000);
        if (shouldRefocusComposer()) input.focus();
        let reader;
        let body;
        let answer = '';
        let complete = false;
        let clarificationShown = false;
        let historyDisposition = 'include';
        let timedOut = false;
        // Two bounded provider/validation attempts plus transport allowance.
        const requestTimer = setTimeout(() => { timedOut = true; controller.abort(); }, 330000);
        try {
            const continuation = lookupContinuation;
            lookupContinuation = null;
            const response = await fetch(form.dataset.chatUrl, {
                method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
                credentials: 'same-origin', signal: controller.signal,
                body: JSON.stringify({ message: text, history, context: browserContext(), locale,
                    ...(continuation ? { continuation } : {}),
                    ...(pendingClarification ? { clarification: pendingClarification } : {}) })
            });
            pendingClarification = null;
            if (controller.signal.aborted || activeRequest !== controller) return;
            if (!response.ok || !response.body || !response.headers.get('Content-Type')?.includes('text/event-stream')) {
                throw new Error('request failed');
            }
            reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (!complete) {
                const { value, done } = await reader.read();
                if (controller.signal.aborted || activeRequest !== controller) return;
                buffer += decoder.decode(value, { stream: !done });
                if (buffer.length > 65536) throw new Error('oversized event');
                let boundary;
                while ((boundary = buffer.indexOf('\n\n')) !== -1) {
                    const frame = buffer.slice(0, boundary);
                    buffer = buffer.slice(boundary + 2);
                    const lines = frame.split('\n');
                    const kind = lines.find(line => line.startsWith('event: '))?.slice(7);
                    const data = JSON.parse(lines.filter(line => line.startsWith('data: ')).map(line => line.slice(6)).join('\n'));
                    if (kind === 'error') throw new Error('generation failed');
                    if (kind === 'delta') {
                        if (typeof data.text !== 'string' || answer.length + data.text.length > 16000) throw new Error('invalid response');
                        if (!answer && data.text) showActivity('answering');
                        body ||= appendMessage(localeDefinition(locale).strings.eyeball, '');
                        answer += data.text;
                        body.textContent = answer;
                        transcript.scrollTop = transcript.scrollHeight;
                    } else if (kind === 'clarification') {
                        showActivity('answering');
                        const card = renderClarification(document, data, localeDefinition(locale).strings, {
                            select(choice) {
                                pendingClarification = choice.token;
                                input.value = choice.label;
                                setTimeout(() => form.requestSubmit(), 0);
                            },
                            rephrase() {
                                document.dispatchEvent(new CustomEvent('oes:product-event', { detail: {
                                    event: 'eyeball_clarification_rephrase', clarificationReason: data.reason
                                }}));
                                if (shouldRefocusComposer()) input.focus();
                            }
                        });
                        transcript.append(card);
                        transcript.scrollTop = transcript.scrollHeight;
                        clarificationShown = true;
                    } else if (kind === 'done') {
                        const directive = completionDirective(data);
                        lookupContinuation = directive.continuation;
                        historyDisposition = directive.retainExchange ? 'include' : 'exclude_exchange';
                        complete = true;
                        break;
                    } else if (kind !== 'start') throw new Error('invalid event');
                }
                if (done && !complete) throw new Error('interrupted stream');
            }
            if (!answer.trim() && !clarificationShown) throw new Error('empty response');
            if (historyDisposition === 'include') {
                history.push({ role: 'user', content: text }, { role: 'assistant', content: answer.slice(0, 4000) });
                while (history.length > 10 || history.reduce((sum, item) => sum + item.content.length, 0) > 12000) history.splice(0, 2);
            }
        } catch (error) {
            if (activeRequest === controller && (!controller.signal.aborted || timedOut)) {
                removeActivity();
                appendFailure(failureKey(error, timedOut), text);
            }
        } finally {
            clearTimeout(requestTimer);
            if (activeRequest === controller) {
                activeRequest = null;
                removeActivity();
                setBusy(false);
                setStatus(complete ? 'ready' : 'interrupted');
            }
            try { await reader?.cancel(); } catch { /* Request may already be aborted. */ }
        }
    });
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            form.requestSubmit();
        }
    });
}
