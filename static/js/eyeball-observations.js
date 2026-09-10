// Page-memory only. Software permission precedes server-generated wording.
const sections = new Set(['home', 'products', 'client-work', 'services', 'government', 'community', 'research', 'about', 'contact']);
const projects = new Set(['chaseingreen', 'lottovate', 'drinkswithfriendz']);
const testflightPaths = new Set(['/join/nPjjyDSf', '/join/CD35ByXj', '/join/mzknJ42e']);

export function repeatedInvitation(text, recent) {
    const words = value => value.toLowerCase().match(/[a-z0-9]+(?:['’][a-z]+)?/g) || [];
    const current = words(text);
    const grams = list => new Set(list.slice(0, -3).map((_, i) => list.slice(i, i + 4).join(' ')));
    const currentGrams = grams(current);
    return recent.some(previous => {
        const prior = words(previous), priorGrams = grams(prior);
        const a = new Set(current), b = new Set(prior);
        const overlap = [...a].filter(word => b.has(word)).length / Math.max(1, new Set([...a, ...b]).size);
        return current.join(' ') === prior.join(' ') || [...currentGrams].some(gram => priorGrams.has(gram)) || overlap >= 0.7;
    });
}

export class ObservationSession {
    constructor(now = () => performance.now()) {
        this.now = now;
        this.section = 'home';
        this.project = null;
        this.elapsed = 0;
        this.since = now();
        this.visible = true;
        this.details = 0;
        this.interactions = 0;
        this.lastInteraction = -Infinity;
        this.invitationTexts = [];
        this.testflight = false;
        this.opens = 0;
        this.messages = 0;
        this.dismissed = false;
        this.active = false;
        this.visits = new Map();
        this.seen = new Set();
        this.lastOffer = -Infinity;
        this.revision = 0;
        this.visitSerial = 0;
        this.visits.set('home', { offered: false, leftAt: null, id: this.visitSerial });
    }
    setVisible(visible) {
        if (this.visible) this.elapsed += this.now() - this.since;
        this.visible = visible;
        this.since = this.now();
        this.revision++;
    }
    enter(section) {
        if (!sections.has(section) || section === this.section) return;
        const now = this.now();
        this.visits.get(this.section).leftAt = now;
        const previous = this.visits.get(section);
        // Brief observer oscillation does not create a fresh invitation allowance.
        if (!previous || (previous.leftAt !== null && now - previous.leftAt >= 15000)) {
            this.visits.set(section, { offered: false, leftAt: null, id: ++this.visitSerial });
        }
        this.section = section;
        this.project = null;
        this.details = 0;
        this.interactions = 0;
        this.lastInteraction = -Infinity;
        this.elapsed = 0;
        this.since = now;
        this.revision++;
    }
    selectProject(project) {
        if (!projects.has(project) || !['products', 'client-work'].includes(this.section)) return;
        if (this.project !== project) {
            this.project = project;
            this.details = 0;
            this.interactions = 0;
            this.lastInteraction = -Infinity;
            this.revision++;
        }
    }
    interacted(project) {
        this.selectProject(project);
        if (this.project === project && this.now() - this.lastInteraction >= 3000) {
            this.interactions = Math.min(20, this.interactions + 1);
            this.lastInteraction = this.now();
            this.revision++;
        }
    }
    openedDetails(project) {
        this.selectProject(project);
        if (this.project === project) this.details = Math.min(20, this.details + 1);
        this.revision++;
    }
    clickedTestflight() { this.testflight = true; this.revision++; }
    openedChat() { this.opens = Math.min(20, this.opens + 1); this.active = true; this.revision++; }
    sentMessage() { this.messages = Math.min(100, this.messages + 1); this.revision++; }
    dismissedChat() { this.dismissed = true; this.active = false; this.revision++; }
    snapshot(device = 'desktop', interactionMode = 'pointer') {
        return {
            section: this.section, ...(this.project ? { project: this.project } : {}),
            device, interaction_mode: interactionMode,
            time_on_section_seconds: Math.min(3600, Math.floor((this.elapsed + (this.visible ? this.now() - this.since : 0)) / 1000)),
            details_opened_count: this.details, product_interaction_count: this.interactions, testflight_clicked: this.testflight,
            chat_open_count: this.opens, chat_message_count: this.messages
        };
    }
    restraint() {
        return {
            dismissed: this.dismissed, user_active: this.active,
            visit_offered: this.visits.get(this.section).offered,
            suggestion_seen: this.seen.has('offer_help:' + this.project),
            seconds_since_last: Math.min(3600, Math.floor((this.now() - this.lastOffer) / 1000))
        };
    }
    eligible() {
        const observation = this.snapshot(), restraint = this.restraint();
        return this.visible && ['products', 'client-work'].includes(this.section) && this.project
            && !this.testflight && !this.opens && !this.messages && !restraint.dismissed
            && !restraint.user_active && !restraint.visit_offered && !restraint.suggestion_seen
            && restraint.seconds_since_last >= 180 && observation.time_on_section_seconds >= 45
            && (this.interactions >= 2 || this.details >= 2 || observation.time_on_section_seconds >= 90);
    }
    markOffered(text) {
        if (typeof text === 'string') this.invitationTexts = [...this.invitationTexts, text].slice(-3);
        this.visits.get(this.section).offered = true;
        this.seen.add('offer_help:' + this.project);
        this.lastOffer = this.now();
        this.revision++;
    }
}

export function createObservationController({ invitation, endpoint, generationEndpoint, getSection, getContext, getHistory, openChat, onInteraction }) {
    const session = new ObservationSession();
    session.enter(getSection());
    session.setVisible(!document.hidden);
    let timer = null;
    let pending = null;
    const attempted = new Set();
    function cancel() {
        clearTimeout(timer);
        pending?.abort();
        pending = null;
        invitation.hidden = true;
    }
    function syncSection() { session.enter(getSection()); }
    async function evaluate() {
        syncSection();
        if (!session.eligible()) return;
        const key = session.section + ':' + session.project + ':' + session.visits.get(session.section).id;
        if (attempted.has(key)) return;
        attempted.add(key); // No polling/retry after a failed or declined decision.
        const revision = session.revision;
        const controller = new AbortController();
        pending = controller;
        try {
            const response = await fetch(endpoint, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin', signal: controller.signal,
                body: JSON.stringify({ context: session.snapshot(...getContext()), restraint: session.restraint() })
            });
            if (!response.ok) return;
            const decision = await response.json();
            if (decision.action === 'offer_help' && !controller.signal.aborted
                    && session.revision === revision && session.eligible()) {
                const generated = await fetch(generationEndpoint, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin', signal: controller.signal,
                    body: JSON.stringify({ context: session.snapshot(...getContext()), restraint: session.restraint(),
                        history: getHistory(), recent_invitations: session.invitationTexts })
                });
                if (!generated.ok) return;
                const wording = await generated.json();
                if (wording.action !== 'offer_help' || typeof wording.text !== 'string' || !wording.text.trim()
                        || wording.text.length > 240 || repeatedInvitation(wording.text, session.invitationTexts)
                        || controller.signal.aborted || session.revision !== revision || !session.eligible()) return;
                invitation.querySelector('[data-invitation-open]').textContent = wording.text;
                session.markOffered(wording.text);
                invitation.hidden = false; // Never opens the drawer, sends chat, or moves focus.
            }
        } catch { /* Silence is the safe fallback, including offline operation. */ }
        finally { if (pending === controller) pending = null; }
    }
    function schedule() {
        cancel();
        syncSection();
        if (session.dismissed || session.opens || session.testflight || !session.visible || !session.project) return;
        const threshold = session.interactions >= 2 || session.details >= 2 ? 45 : 90;
        const wait = Math.max(0, threshold - session.snapshot().time_on_section_seconds);
        timer = setTimeout(evaluate, wait * 1000); // One eligibility check, no interval.
    }
    document.addEventListener('oes:sectionchange', schedule);
    document.addEventListener('pointerdown', event => onInteraction(event.pointerType === 'touch' ? 'touch' : 'pointer'), { passive: true });
    document.addEventListener('keydown', () => onInteraction('keyboard'));
    document.addEventListener('visibilitychange', () => { session.setVisible(!document.hidden); schedule(); });
    function observeProduct(event) {
        if (!(event.target instanceof Element) || invitation.contains(event.target)) return;
        syncSection();
        const product = event.target.closest('[data-product]');
        // Current client-work card lacks data-product; use its existing container.
        const project = product?.dataset.product || (event.target.closest('#client-work .client-spotlight') ? 'drinkswithfriendz' : null);
        const before = session.revision;
        if (project) session.interacted(project);
        const link = event.target.closest('a[href]');
        if (event.type === 'click' && link) {
            const url = new URL(link.href, location.href);
            if (url.hostname === 'testflight.apple.com' && testflightPaths.has(url.pathname)) session.clickedTestflight();
        }
        if (before !== session.revision || session.testflight) schedule();
    }
    document.addEventListener('click', observeProduct);
    document.addEventListener('focusin', observeProduct);
    // No current product-details expanders exist; only real native opening events count.
    document.addEventListener('toggle', event => {
        const details = event.target;
        if (!(details instanceof HTMLDetailsElement) || !details.open) return;
        const product = details.closest('[data-product]');
        if (!product) return;
        syncSection();
        session.openedDetails(product.dataset.product);
        schedule();
    }, true);
    invitation.querySelector('[data-invitation-open]').addEventListener('click', () => {
        cancel();
        openChat();
    });
    invitation.querySelector('[data-invitation-dismiss]').addEventListener('click', () => {
        session.dismissedChat();
        cancel();
    });
    return {
        snapshot: () => { syncSection(); return session.snapshot(...getContext()); },
        opened: () => { session.openedChat(); cancel(); },
        sent: () => { session.sentMessage(); cancel(); },
        closed: () => { session.dismissedChat(); cancel(); }
    };
}
