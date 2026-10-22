"""Privacy-bounded product events and an honest per-runtime public counter."""
from collections import OrderedDict
import secrets
import threading
import time

from flask import Blueprint, current_app, jsonify, request


bp = Blueprint('product_intelligence', __name__)
COOKIE = 'oes_product_session'
SESSION_SECONDS = 12 * 60 * 60
MAX_SESSIONS = 10000
MAX_EVENTS_PER_SESSION = 500
PRODUCTS = frozenset({'chaseingreen', 'lottovate', 'sportfolio', 'drinkswithfriendz'})
PLATFORMS = frozenset({'desktop', 'tablet', 'mobile', 'unknown'})
LANGUAGES = frozenset({'en', 'es', 'fr', 'ar', 'zh-CN'})
CLARIFICATION_REASONS = frozenset({
    'ambiguous_typo', 'high_impact_ambiguity', 'low_confidence'})

EVENT_RULES = {
    'website_session_started': frozenset({'platform', 'language'}),
    'product_card_activated': frozenset({'product_target'}),
    'eyeball_opened': frozenset({'platform', 'language'}),
    'eyeball_closed': frozenset(),
    'eyeball_message_submitted': frozenset({'language'}),
    'eyeball_language_changed': frozenset({'language'}),
    'external_product_link_activated': frozenset({'product_target'}),
    'testflight_link_activated': frozenset({'product_target'}),
    'web_app_link_activated': frozenset({'product_target'}),
    'contact_action_activated': frozenset(),
    'eyeball_clarification_rephrase': frozenset({'clarification_reason'}),
}


def same_origin():
    if request.headers.get('Sec-Fetch-Site') == 'cross-site':
        return False
    if not request.origin:
        return True
    expected = current_app.config.get('OES_PUBLIC_ORIGIN', '').strip()
    return request.origin == (expected or request.host_url.rstrip('/'))


class ProductIntelligence:
    """Keep bounded live tokens only; persisted telemetry receives no token."""
    def __init__(self, emit, clock=time.time):
        self.emit, self.clock = emit, clock
        self.started_at = int(clock())
        self.total_sessions = 0
        self.sessions = OrderedDict()
        self.lock = threading.RLock()

    def _expire(self, now):
        while self.sessions:
            token, state = next(iter(self.sessions.items()))
            if state['expires'] > now and len(self.sessions) <= MAX_SESSIONS:
                break
            self.sessions.pop(token, None)

    def open_session(self, token=None):
        now = self.clock()
        with self.lock:
            self._expire(now)
            if token in self.sessions:
                state = self.sessions.pop(token)
                state['expires'] = now + SESSION_SECONDS
                self.sessions[token] = state
                return token, False, self.total_sessions
            token = secrets.token_hex(16)
            self.sessions[token] = {'expires': now + SESSION_SECONDS,
                                    'events': 0, 'started': False, 'last': None}
            self.total_sessions += 1
            return token, True, self.total_sessions

    def record(self, token, payload):
        if not isinstance(payload, dict) or set(payload) != {'event', 'dimensions'}:
            raise ValueError('Invalid product event')
        event_type, supplied = payload['event'], payload['dimensions']
        expected = EVENT_RULES.get(event_type)
        if expected is None or not isinstance(supplied, dict) or set(supplied) != expected:
            raise ValueError('Invalid product event')
        if 'platform' in supplied and supplied['platform'] not in PLATFORMS:
            raise ValueError('Invalid product event')
        if 'language' in supplied and supplied['language'] not in LANGUAGES:
            raise ValueError('Invalid product event')
        if 'product_target' in supplied and supplied['product_target'] not in PRODUCTS:
            raise ValueError('Invalid product event')
        if ('clarification_reason' in supplied
                and supplied['clarification_reason'] not in CLARIFICATION_REASONS):
            raise ValueError('Invalid product event')
        now = self.clock()
        with self.lock:
            self._expire(now)
            state = self.sessions.get(token)
            if state is None or state['events'] >= MAX_EVENTS_PER_SESSION:
                raise PermissionError('Product session unavailable')
            if event_type == 'website_session_started' and state['started']:
                return False
            signature = (event_type, tuple(sorted(supplied.items())))
            if state['last'] and state['last'][0] == signature and now-state['last'][1] < .25:
                return False
            state['events'] += 1
            state['started'] |= event_type == 'website_session_started'
            state['last'] = (signature, now)
            state['expires'] = now + SESSION_SECONDS
            self.sessions.move_to_end(token)
        product = 'eyeball' if event_type.startswith('eyeball_') else 'oeswebsite'
        dimensions = {'product': product, 'surface': 'web', **supplied}
        if event_type == 'testflight_link_activated':
            dimensions['destination'] = 'testflight'
        elif event_type == 'web_app_link_activated':
            dimensions['destination'] = 'web_app'
        elif event_type == 'external_product_link_activated':
            dimensions['destination'] = 'external_site'
        elif event_type == 'contact_action_activated':
            dimensions['destination'] = 'contact'
        self.emit(event_type, outcome='accepted', dimensions=dimensions)
        return True


def init_product_intelligence(app):
    tracker = ProductIntelligence(app.extensions['worker_relay'].emit)
    app.extensions['product_intelligence'] = tracker
    app.register_blueprint(bp)


@bp.post('/api/product-intelligence/session')
def session():
    if not same_origin():
        return jsonify(error='same_origin_required'), 403
    tracker = current_app.extensions['product_intelligence']
    token, created, count = tracker.open_session(request.cookies.get(COOKIE))
    response = jsonify(sessions=count, scope='service_runtime',
                       started_at=tracker.started_at, created=created)
    response.headers['Cache-Control'] = 'no-store'
    host = request.host.split(':', 1)[0].strip('[]').lower()
    response.set_cookie(COOKIE, token, httponly=True, samesite='Lax',
                        secure=host not in {'localhost', '127.0.0.1', '::1'}, path='/')
    return response


@bp.post('/api/product-intelligence/event')
def event():
    if request.mimetype != 'application/json':
        return jsonify(error='application_json_required'), 415
    if not same_origin():
        return jsonify(error='same_origin_required'), 403
    request.max_content_length = 2048
    try:
        recorded = current_app.extensions['product_intelligence'].record(
            request.cookies.get(COOKIE), request.get_json())
    except PermissionError:
        return jsonify(error='product_session_unavailable'), 409
    except Exception:
        return jsonify(error='invalid_product_event'), 400
    return jsonify(recorded=recorded)
