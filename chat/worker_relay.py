"""Single-process, single-job ephemeral relay. No provider policy lives here."""
from collections import deque
import hmac
import logging
import secrets
import threading
import time

from flask import Blueprint, Response, current_app, request
from .runtime import enabled
from .worker_protocol import (MAX_BODY, MAX_OUTPUT, JOB_SECONDS, LEASE_SECONDS,
                              POLL_SECONDS, canonical, decode, fields, messages_valid,
                              settings, signature, token)

bp = Blueprint('worker', __name__)
PREFIX = '/api/worker/v1/'
LOG = logging.getLogger('oes.relay')


class RelayError(ValueError):
    def __init__(self, message, category='relay_ownership_lease'):
        super().__init__(message)
        self.category = category


class WorkerRelay:
    def __init__(self, config, clock=time.monotonic, wall=time.time):
        self.config, self.clock, self.wall = config, clock, wall
        self.epoch = secrets.token_hex(16)
        self.cv = threading.Condition()
        self.nonces = {}
        self.session = None
        self.job = None
        self.polling = False

    def configured(self):
        settings(self.config)
        return enabled(self.config, 'OES_WORKER_ENABLED')

    def live(self):
        return (self.configured() and enabled(self.config, 'OES_EYEBALL_ENABLED')
                and enabled(self.config, 'OES_AI_CHAT_ENABLED')
                and self.config.get('OES_CHAT_PROVIDER') == 'outbound_worker')

    def authenticate(self, path, headers, raw):
        identity, key_id, key = settings(self.config)
        if not enabled(self.config, 'OES_WORKER_ENABLED'):
            raise RelayError('Disabled')
        stamp, nonce = headers.get('X-OES-Time', ''), headers.get('X-OES-Nonce', '')
        token(nonce)
        if (headers.get('X-OES-Worker') != identity or headers.get('X-OES-Key') != key_id
                or not stamp.isascii() or not stamp.isdigit() or len(stamp) > 12
                or abs(self.wall() - int(stamp)) > 30):
            raise RelayError('Authentication failed')
        expected = signature(key, 'request', path, identity, key_id, stamp, nonce, raw)
        if not hmac.compare_digest(expected, headers.get('X-OES-Signature', '')):
            raise RelayError('Authentication failed')
        with self.cv:
            now = self.clock()
            self.nonces = {n: expiry for n, expiry in self.nonces.items() if expiry > now}
            if nonce in self.nonces or len(self.nonces) >= 2048:
                raise RelayError('Replay rejected')
            self.nonces[nonce] = now + 120

    def _expire(self):
        now = self.clock()
        if self.session and now >= self.session['expires']:
            self.session = None
        if self.job and (not self.session or now >= self.job['deadline'] or not self.live()):
            self.job['error'] = True
            self.job['failure'] = ('job_deadline' if now >= self.job['deadline']
                                   else 'relay_ownership_lease')
            self.cv.notify_all()

    def status(self):
        with self.cv:
            self._expire()
            if not self.session:
                return {'LOCAL_WORKER_HEALTH': 'LOCAL_WORKER_OFFLINE', 'OLLAMA_HEALTH': 'unknown'}
            ready = self.session['ollama'] == 'ready' and not self.job and self.session['job'] is None
            return {'LOCAL_WORKER_HEALTH': 'LOCAL_WORKER_HEALTHY' if ready else 'LOCAL_WORKER_DEGRADED',
                    'OLLAMA_HEALTH': self.session['ollama']}

    def health_model(self):
        state = self.status()
        state.update(WEB_SERVICE_HEALTH='healthy', EYEBALL_CORE_HEALTH='client_observed_only',
                     AI_FEATURE_HEALTH=('disabled' if not self.live() else
                                        'ready' if state['LOCAL_WORKER_HEALTH'] == 'LOCAL_WORKER_HEALTHY'
                                        else 'unavailable'))
        return state

    def _owner(self, body):
        self._expire()
        if (body['epoch'] != self.epoch or not self.session
                or body['boot'] != self.session['boot'] or body['lease'] != self.session['lease']):
            raise RelayError('Obsolete owner')
        self.session['expires'] = self.clock() + LEASE_SECONDS

    def dispatch(self, action, body):
        common = {'epoch', 'boot', 'lease'}
        if action == 'connect':
            fields(body, ('boot', 'ollama'))
        elif action == 'poll':
            fields(body, common)
        elif action == 'heartbeat':
            fields(body, common | {'job', 'ollama'})
        elif action == 'result':
            fields(body, common | {'job', 'seq', 'text', 'done', 'error'})
        else:
            raise RelayError('Unknown operation')
        token(body['boot'])
        if action in ('connect', 'heartbeat') and body['ollama'] not in ('ready', 'unavailable'):
            raise RelayError('Invalid readiness')
        with self.cv:
            self._expire()
            if action == 'connect':
                if self.session and self.session['boot'] != body['boot']:
                    raise RelayError('Worker already leased')
                if not self.session:
                    self.session = {'boot': body['boot'], 'lease': secrets.token_hex(16),
                                    'expires': self.clock() + LEASE_SECONDS, 'ollama': body['ollama'], 'job':None}
                return {'epoch': self.epoch, 'lease': self.session['lease']}
            self._owner(body)
            if action == 'heartbeat':
                if body['job'] is not None:
                    token(body['job'])
                self.session['ollama'] = body['ollama']
                reported_active = bool(self.job and not self.job['error'] and not self.job['done']
                                       and self.job['claimed'] and self.job['id'] == body['job'])
                if reported_active:
                    self.session['job'] = body['job']
                elif (self.job and self.job['id'] == body['job']
                      and (self.job['done'] or self.job['error'])):
                    # A heartbeat captured before terminal acknowledgement cannot
                    # resurrect a completed marker. A heartbeat for some other job
                    # also cannot clear the current authoritative marker.
                    self.session['job'] = None
                elif body['job'] is None and not self.job:
                    self.session['job'] = None
                if body['ollama'] == 'unavailable' and self.job and body['job'] == self.job['id']:
                    self.job['error'] = True
                    self.job['failure'] = 'model_readiness_digest'
                    reported_active = False
                    self.cv.notify_all()
                active = reported_active
                return {'active': active, 'health': self.health_model()}
            if action == 'result':
                j = self.job
                if (not j or j['error'] or not j['claimed'] or body['job'] != j['id']
                        or type(body['seq']) is not int or body['seq'] != j['seq'] or j['done']):
                    raise RelayError('Obsolete or unordered result', 'result_rejection_obsolete')
                if (not isinstance(body['text'], str) or len(body['text']) > 1024
                        or type(body['done']) is not bool or type(body['error']) is not bool
                        or (body['error'] and (body['text'] or not body['done']))):
                    raise RelayError('Invalid result', 'result_rejection_obsolete')
                if j['total'] + len(body['text']) > MAX_OUTPUT:
                    j['error'] = True
                    self.cv.notify_all()
                    raise RelayError('Output exceeded', 'output_limit')
                if len(j['events']) >= 8:
                    return {'accepted': False, 'active': True}
                j['seq'] += 1
                j['total'] += len(body['text'])
                j['events'].append((body['text'], body['done'], body['error']))
                j['done'] = body['done']
                # A successfully acknowledged terminal result proves this worker has
                # finished the claimed job. Clear the session marker now so the
                # service's one bounded regeneration can allocate the next job.
                if body['done'] and not body['error']:
                    self.session['job'] = None
                self.cv.notify_all()
                return {'accepted': True, 'active': True}
            if self.polling:
                raise RelayError('Poll already active')
            # The separate worker polls only after its previous local stream closes.
            if not self.job:
                self.session['job'] = None
            self.polling = True
            try:
                end = self.clock() + POLL_SECONDS
                while True:
                    self._owner(body)
                    if self.live() and self.job and not self.job['error'] and not self.job['claimed']:
                        self.job['claimed'] = True
                        self.session['job'] = self.job['id']
                        return {'job': self.job['id'], 'messages': self.job['messages'],
                                'seconds': max(0, min(90, int(self.job['deadline'] - self.clock())))}
                    remaining = end - self.clock()
                    if remaining <= 0:
                        return {'job': None}
                    self.cv.wait(min(remaining, 1))
            finally:
                self.polling = False

    def stream(self, messages, cancelled=None, request_id=None, attempt=1):
        from .providers import ChatEvent
        try:
            messages_valid(messages)
        except (ValueError, TypeError, KeyError) as error:
            LOG.warning('relay job failed request_id=%s attempt=%s category=input_message_bounds',
                        request_id, attempt)
            raise RelayError('Invalid messages', 'input_message_bounds') from error
        with self.cv:
            self._expire()
            if (not self.live() or self.job or not self.session or self.session['ollama'] != 'ready'
                    or self.session['job'] is not None
                    or (cancelled is not None and cancelled.is_set())):
                LOG.warning('relay job failed request_id=%s attempt=%s category=worker_unavailable_busy',
                            request_id, attempt)
                raise RelayError('Worker unavailable', 'worker_unavailable_busy')
            j = {'id': secrets.token_hex(16), 'messages': messages,
                 'deadline': self.clock() + JOB_SECONDS, 'events': deque(),
                 'claimed': False, 'error': False, 'done': False, 'total': 0, 'seq': 0,
                 'failure': None, 'request_id': request_id, 'attempt': attempt}
            self.job = j
            self.cv.notify_all()
        try:
            while True:
                with self.cv:
                    self._expire()
                    if j['error'] or (cancelled is not None and cancelled.is_set()):
                        category = ('cancellation' if cancelled is not None and cancelled.is_set()
                                    else j.get('failure') or 'result_rejection_obsolete')
                        LOG.warning('relay job failed request_id=%s attempt=%s category=%s',
                                    j['request_id'], j['attempt'], category)
                        raise RelayError('Inference interrupted', category)
                    if not j['events']:
                        self.cv.wait(0.5)
                        continue
                    text, done, error = j['events'].popleft()
                if error:
                    LOG.warning('relay job failed request_id=%s attempt=%s category=ollama_protocol_malformed_event',
                                j['request_id'], j['attempt'])
                    raise RelayError('Inference failed', 'ollama_protocol_malformed_event')
                if text:
                    yield ChatEvent('delta', {'text': text})
                if done:
                    yield ChatEvent('done', {})
                    return
        finally:
            with self.cv:
                if self.job is j:
                    self.job = None
                self.cv.notify_all()


@bp.post(PREFIX + '<action>')
def worker_request(action):
    relay = current_app.extensions['worker_relay']
    request.max_content_length = MAX_BODY
    if request.mimetype != 'application/json' or request.headers.get('Content-Encoding'):
        return {'error': 'invalid_worker_request'}, 400
    try:
        raw = request.get_data()
        relay.authenticate(request.path, request.headers, raw)
    except (ValueError, TypeError):
        return {'error': 'worker_unauthorized'}, 401
    try:
        result = relay.dispatch(action, decode(raw))
    except (ValueError, TypeError, KeyError) as error:
        category = getattr(error, 'category', 'relay_ownership_lease')
        with relay.cv:
            job = relay.job
            request_id = job.get('request_id') if job else None
            attempt = job.get('attempt') if job else None
        LOG.warning('relay request rejected request_id=%s attempt=%s category=%s',
                    request_id, attempt, category)
        return {'error': 'worker_request_rejected'}, 409
    output = canonical(result)
    identity, key_id, key = settings(current_app.config)
    sig = signature(key, 'response', request.path, identity, key_id,
                    request.headers['X-OES-Time'], request.headers['X-OES-Nonce'], output)
    return Response(output, content_type='application/json', headers={
        'X-OES-Signature': sig, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
