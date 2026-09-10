// Local UI only. No transport, provider, storage, or HTML response rendering.
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
    let timer = null;

    function requestChat() {
        // Independent of oes:coreactivated, which also fires after dragging.
        core.dispatchEvent(new CustomEvent('oes:chatrequest', { bubbles: true }));
    }

    core.addEventListener('pointerdown', (event) => {
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
        status.textContent = busy ? 'Preparing local response…' : 'Ready · local preview';
    }
    function cancelResponse() {
        if (timer === null) return;
        window.clearTimeout(timer);
        timer = null;
        setBusy(false);
        status.textContent = 'Local response stopped.';
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
    }
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text || text.length > 2000 || timer !== null) return;
        appendMessage('YOU', text, true);
        input.value = '';
        setBusy(true);
        input.focus();
        timer = window.setTimeout(() => {
            timer = null;
            appendMessage('EYEBALL · LOCAL PREVIEW', 'Eyeball interface online. AI connection is not enabled in this build.');
            setBusy(false);
        }, 450);
    });
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            form.requestSubmit();
        }
    });
}
