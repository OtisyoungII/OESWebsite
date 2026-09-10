import { getAwarenessState } from './section-awareness.js';

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
    let pointer = null;
    let activeRequest = null;
    let history = [];
    let interactionMode = 'pointer';

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
        dialog.showModal();
        core.setAttribute('aria-expanded', 'true');
        input.focus();
    });

    function setBusy(busy) {
        send.disabled = busy;
        stop.disabled = !busy;
        status.textContent = busy ? 'Eyeball is responding…' : 'Ready';
    }
    function cancelResponse() {
        if (!activeRequest) return;
        activeRequest.abort();
        activeRequest = null;
        setBusy(false);
        status.textContent = 'Response stopped.';
    }
    dialog.querySelector('[data-chat-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('cancel', (event) => {
        event.preventDefault();
        dialog.close();
    });
    dialog.addEventListener('close', () => {
        cancelResponse();
        core.setAttribute('aria-expanded', 'false');
        core.focus({ preventScroll: true });
    });
    stop.addEventListener('click', () => {
        cancelResponse();
        input.focus();
    });
    function appendMessage(speaker, text, user = false) {
        const message = document.createElement('div');
        message.className = 'eyeball-chat__message' + (user ? ' eyeball-chat__message--user' : '');
        const label = document.createElement('p');
        label.className = 'eyeball-chat__speaker';
        label.textContent = speaker;
        const body = document.createElement('p');
        body.textContent = text;
        message.append(label, body);
        transcript.append(message);
        transcript.scrollTop = transcript.scrollHeight;
        return body;
    }
    function browserContext() {
        const section = getAwarenessState().currentSectionId;
        const allowed = ['home', 'products', 'client-work', 'services', 'government', 'community', 'research', 'about', 'contact'];
        return {
            ...(allowed.includes(section) ? { section } : {}),
            device: window.innerWidth <= 760 ? 'mobile' : window.innerWidth <= 1020 ? 'tablet' : 'desktop',
            interaction_mode: interactionMode
        };
    }
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text || text.length > 4000 || activeRequest) return;
        const controller = new AbortController();
        activeRequest = controller;
        appendMessage('YOU', text, true);
        input.value = '';
        setBusy(true);
        input.focus();
        let reader;
        let body;
        let answer = '';
        let complete = false;
        try {
            const response = await fetch(form.dataset.chatUrl, {
                method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
                credentials: 'same-origin', signal: controller.signal,
                body: JSON.stringify({ message: text, history, context: browserContext() })
            });
            if (!response.ok || !response.body || !response.headers.get('Content-Type')?.includes('text/event-stream')) {
                throw new Error('request failed');
            }
            reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (!complete) {
                const { value, done } = await reader.read();
                if (controller.signal.aborted) return;
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
                        body ||= appendMessage('EYEBALL', '');
                        answer += data.text;
                        body.textContent = answer;
                        transcript.scrollTop = transcript.scrollHeight;
                    } else if (kind === 'done') {
                        complete = true;
                        break;
                    } else if (kind !== 'start') throw new Error('invalid event');
                }
                if (done && !complete) throw new Error('interrupted stream');
            }
            if (!answer.trim()) throw new Error('empty response');
            history.push({ role: 'user', content: text }, { role: 'assistant', content: answer.slice(0, 4000) });
            while (history.length > 10 || history.reduce((sum, item) => sum + item.content.length, 0) > 12000) history.splice(0, 2);
        } catch (error) {
            if (!controller.signal.aborted) {
                appendMessage('EYEBALL', 'Eyeball is temporarily unavailable. Please try again shortly.');
            }
        } finally {
            try { await reader?.cancel(); } catch { /* Request may already be aborted. */ }
            if (activeRequest === controller) {
                activeRequest = null;
                setBusy(false);
                if (!complete) status.textContent = 'Response interrupted. You can try again.';
            }
        }
    });
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            form.requestSubmit();
        }
    });
}
