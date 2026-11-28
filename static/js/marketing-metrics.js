const page = document.querySelector('[data-marketing-page]')?.dataset.marketingPage;
if (page) {
    // The target is a fixed same-origin route. No URLs or visitor details are sent.
    const send = action => fetch('/api/marketing-metric', {
        method: 'POST', credentials: 'same-origin', keepalive: true,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page, action })
    }).catch(() => {});
    send('view');
    document.addEventListener('click', event => {
        const action = event.target.closest?.('[data-marketing-click]')?.dataset.marketingClick;
        if (action) send(action);
    });
}
