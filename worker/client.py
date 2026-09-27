"""HTTPS pull worker. The only local network target is fixed loopback Ollama."""
import hmac
import json
import logging
import re
import secrets
import ssl
import threading
import time
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPSHandler

from chat.providers import GenerationDeadline, NoRedirect, bounded_lines, open_response
from chat.worker_protocol import (CONTEXT_BUDGET, MAX_BODY, MAX_OUTPUT, canonical,
                                  context_cost, decode, fields, messages_valid, settings,
                                  signature, signed_headers, token)
from oes_telemetry import REASONS, validate_batch

LOG = logging.getLogger('oes.worker')
RPC_SECONDS = 27


class WorkerFailure(ValueError):
    """Content-free internal failure category safe for operational logs."""
    def __init__(self, category, message=None):
        super().__init__(message or category)
        self.category = category


class WorkerTimeout(WorkerFailure, TimeoutError):
    pass


class OutboundWorker:
    def __init__(self, config, tls_context=None, telemetry_store=None):
        self.config = config
        settings(config)
        origin = config.get('OES_WORKER_RELAY_URL', '')
        url = urlsplit(origin)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.path not in ('', '/')
                or any(c.isspace() for c in origin) or '\\' in origin):
            raise ValueError('Expected fixed HTTPS relay origin')
        if config.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434') != 'http://127.0.0.1:11434':
            raise ValueError('Ollama must stay on fixed loopback')
        if config.get('OLLAMA_MODEL', 'llama3.2') not in ('llama3.2', 'llama3.2:latest'):
            raise ValueError('Fixed model required')
        digest = config.get('OES_WORKER_MODEL_DIGEST', '')
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Expected model digest required')
        self.origin, self.digest = origin.rstrip('/'), digest
        context = tls_context or ssl.create_default_context()
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError('Verified TLS required')
        self.remote = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=context))
        self.local = self._new_local()
        self.boot = secrets.token_hex(16)
        self.owner = None
        self.job = None
        self.ready = False
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.cancelled = threading.Event()
        # DNS resolution can outlive socket timeouts on some operating systems.
        # Bound caller wait and outstanding transports, including that case.
        self.rpc_slots = threading.BoundedSemaphore(2)
        self.telemetry_ack = []
        self.telemetry_negotiated = False
        self.ownership_established = False
        if telemetry_store is None:
            try:
                from oes_core_launcher.telemetry import TelemetryStore
                telemetry_store = TelemetryStore()
            except Exception:
                telemetry_store = False
        self.telemetry_store = telemetry_store or None
        self._telemetry_runtime('worker_started_at', int(time.time()))
        self._telemetry_runtime('active_inference', 0)

    def _telemetry_runtime(self, key, value):
        try:
            if self.telemetry_store:
                self.telemetry_store.set_runtime(key, value)
        except Exception:
            pass

    def _telemetry_event(self, event_type, **fields):
        try:
            if self.telemetry_store:
                self.telemetry_store.record(event_type, **fields)
        except Exception:
            pass

    def _telemetry_response(self, response):
        """Persist before ack; failure leaves the batch pending without breaking work."""
        if not isinstance(response, dict):
            return response
        response = dict(response)
        events = response.pop('telemetry', None)
        if events is not None:
            try:
                events = validate_batch(events)
                if self.telemetry_store:
                    self.telemetry_ack = self.telemetry_store.insert_events(events)
            except Exception:
                self.telemetry_ack = []
        self._telemetry_runtime('last_relay_contact', int(time.time()))
        return response

    def _session_body(self, owner, **values):
        body = {**owner, **values}
        if self.telemetry_negotiated:
            body['telemetry_ack'] = self.telemetry_ack
        return body

    def _clear_session(self, expected=None):
        with self.lock:
            if expected is not None and self.owner is not expected:
                return False
            established = self.ownership_established
            self.owner = None
            self.telemetry_negotiated = False
            self.ownership_established = False
            return established

    @staticmethod
    def _connection_failure_reason(error):
        category = getattr(error, 'category', None)
        if category in ('protocol_rejection', 'authentication_rejection',
                        'transport_failure', 'timeout'):
            return category
        if isinstance(error, (WorkerTimeout, TimeoutError)):
            return 'timeout'
        return 'transport_failure'

    def _connect(self):
        state = 'ready' if self.ready else 'unavailable'
        try:
            response = self.rpc('connect', {'boot': self.boot, 'ollama': state,
                                             'telemetry_version': 1})
        except WorkerFailure as error:
            if error.category != 'protocol_rejection':
                raise
            self._telemetry_event('worker_connection_failed', outcome='failure',
                reason='protocol_rejection',
                dimensions={'component':'relay', 'state':'reconnecting'})
            # One authenticated compatibility retry, using the exact legacy body.
            response = self.rpc('connect', {'boot': self.boot, 'ollama': state})
            negotiated = False
        else:
            negotiated = isinstance(response, dict) and 'telemetry' in response
        response = self._telemetry_response(response)
        fields(response, ('epoch', 'lease'))
        token(response['epoch']); token(response['lease'])
        owner = {'epoch': response['epoch'], 'lease': response['lease'], 'boot': self.boot}
        with self.lock:
            self.telemetry_negotiated = negotiated
            self.owner = owner
            self.ownership_established = True
        return owner

    @staticmethod
    def _new_local():
        # A fresh opener contains no handler state from a failed Ollama request.
        return build_opener(ProxyHandler({}), NoRedirect())

    def _discard_local_transport(self):
        self.local = self._new_local()

    def rpc(self, action, body):
        if not self.rpc_slots.acquire(blocking=False):
            raise WorkerTimeout('transport_rpc_timeout')
        complete = threading.Event()
        outcome = []

        def perform():
            try:
                outcome.append((True, self._rpc(action, body)))
            except Exception as error:
                outcome.append((False, error))
            finally:
                self.rpc_slots.release()
                complete.set()

        threading.Thread(target=perform, daemon=True, name='oes-worker-https').start()
        if not complete.wait(RPC_SECONDS):
            # A late transport can close normally but its result cannot execute a job.
            raise WorkerTimeout('transport_rpc_timeout')
        success, value = outcome[0]
        if not success:
            if isinstance(value, WorkerFailure):
                raise value
            if isinstance(value, TimeoutError):
                raise WorkerTimeout('transport_rpc_timeout') from value
            category = ('result_rejection_obsolete' if action == 'result'
                        else 'relay_ownership_lease')
            raise WorkerFailure(category) from value
        return value

    def _rpc(self, action, body):
        path = '/api/worker/v1/' + action
        raw = canonical(body)
        if len(raw) > MAX_BODY:
            raise ValueError('Oversized worker request')
        headers = signed_headers(self.config, path, raw, secrets.token_hex(16))
        started = time.monotonic()
        request = Request(self.origin + path, data=raw, headers=headers)
        try:
            response = self.remote.open(request, timeout=12)
        except HTTPError as error:
            status = error.code
            error.close()
            if action == 'connect' and status == 409:
                raise WorkerFailure('protocol_rejection') from error
            if status in (401, 403):
                raise WorkerFailure('authentication_rejection') from error
            raise WorkerFailure('transport_failure') from error
        except TimeoutError as error:
            raise WorkerTimeout('timeout') from error
        except (URLError, OSError) as error:
            raise WorkerFailure('transport_failure') from error
        with response:
            chunks, size = [], 0
            while True:
                if time.monotonic() - started > 15:
                    raise WorkerTimeout('transport_rpc_timeout')
                chunk = response.read1(4096)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BODY:
                    raise ValueError('Oversized relay response')
                chunks.append(chunk)
            data = b''.join(chunks)
            identity, key_id, key = settings(self.config)
            expected = signature(key, 'response', path, identity, key_id,
                                 headers['X-OES-Time'], headers['X-OES-Nonce'], data)
            if not hmac.compare_digest(expected, response.headers.get('X-OES-Signature', '')):
                raise WorkerFailure('relay_ownership_lease')
            return decode(data)

    def model_ready(self):
        try:
            started = time.monotonic()
            with open_response(self.local, Request('http://127.0.0.1:11434/api/tags'), 3) as response:
                data = b''
                while True:
                    if time.monotonic() - started > 3:
                        return False
                    chunk = response.read1(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 65536:
                        return False
                models = json.loads(data)['models']
                return any(m.get('name') == 'llama3.2:latest' and m.get('digest') == self.digest for m in models)
        except Exception:
            return False

    def heartbeat(self):
        while not self.stop.wait(3):
            with self.lock:
                owner, job, ready = self.owner, self.job, self.ready
            if owner is None:
                continue
            try:
                response = self.rpc('heartbeat', self._session_body(owner, job=job,
                    ollama='ready' if ready else 'unavailable'))
                response = self._telemetry_response(response)
                fields(response, ('active', 'health'))
                if type(response['active']) is not bool:
                    raise ValueError('Invalid heartbeat')
                if job and not response['active']:
                    self.cancelled.set()
            except Exception as error:
                self.cancelled.set()
                if self._clear_session(owner):
                    category = getattr(error, 'category', 'relay_ownership_lease')
                    self._telemetry_event('worker_disconnected', outcome='failure',
                        reason=category if category in REASONS else 'relay_ownership_lease',
                        dimensions={'component':'relay', 'state':'disconnected'})

    def infer(self, job, owner):
        try:
            if set(job) == {'job', 'messages', 'seconds', 'request_id', 'attempt'}:
                request_id, attempt = job['request_id'], job['attempt']
                token(request_id)
                if type(attempt) is not int or attempt not in (1, 2):
                    raise ValueError('Invalid attempt')
            else:
                fields(job, ('job', 'messages', 'seconds'))
                request_id, attempt = None, 1
            token(job['job'])
            messages_valid(job['messages'])
        except (ValueError, TypeError, KeyError) as error:
            raise WorkerFailure('input_message_bounds') from error
        if type(job['seconds']) is not int or not 1 <= job['seconds'] <= 90:
            raise WorkerFailure('job_deadline')
        # Conservative byte-based upper bound, including chat-template allowance.
        # Refuse oversized prompts; never silently trim authoritative instructions.
        if context_cost(job['messages']) > CONTEXT_BUDGET:
            raise WorkerFailure('context_budget', 'Context budget exceeded')
        if not self.model_ready():
            raise WorkerFailure('model_readiness_digest')
        deadline = time.monotonic() + job['seconds']
        sequence = 0

        def send(text, done=False, error=False, failure=None):
            nonlocal sequence
            while True:
                if self.cancelled.is_set() or self.stop.is_set() or time.monotonic() >= deadline:
                    category = ('cancellation' if self.cancelled.is_set() or self.stop.is_set()
                                else 'job_deadline')
                    raise WorkerFailure(category)
                try:
                    body = {**owner, 'job': job['job'], 'seq': sequence,
                            'text': text, 'done': done, 'error': error}
                    if error:
                        body['failure'] = failure
                    result = self.rpc('result', body)
                except WorkerFailure as result_failure:
                    if result_failure.category == 'transport_rpc_timeout':
                        raise
                    raise WorkerFailure('result_rejection_obsolete') from result_failure
                except TimeoutError as result_failure:
                    raise WorkerTimeout('transport_rpc_timeout') from result_failure
                fields(result, ('accepted', 'active'))
                if type(result['accepted']) is not bool or result['active'] is not True:
                    raise WorkerFailure('result_rejection_obsolete')
                if result['accepted']:
                    sequence += 1
                    return
                # Retry only a specifically unaccepted batch, never an ambiguous HTTP result.
                self.cancelled.wait(0.1)

        payload = canonical({'model': 'llama3.2', 'messages': job['messages'], 'stream': True,
                             'options': {'num_predict': 600, 'num_ctx': CONTEXT_BUDGET}})
        request = Request('http://127.0.0.1:11434/api/chat', data=payload,
                          headers={'Content-Type': 'application/json'})
        started = time.monotonic()
        self._telemetry_runtime('active_inference', 1)
        self._telemetry_event('inference_attempted', request_id=request_id,
                              attempt=attempt, outcome='accepted')
        opened = False
        response = None
        completed = False
        received_event = False
        try:
            # A stalled read fails within ten seconds, including during cancellation.
            response = open_response(self.local, request, 10)
            opened = True
            total, pending, last_send = 0, '', time.monotonic()
            for line in bounded_lines(response, started, job['seconds']):
                received_event = True
                if self.cancelled.is_set() or self.stop.is_set() or time.monotonic() >= deadline:
                    category = ('cancellation' if self.cancelled.is_set() or self.stop.is_set()
                                else 'job_deadline')
                    raise WorkerFailure(category)
                try:
                    value = json.loads(line)
                except (ValueError, TypeError) as error:
                    raise WorkerFailure('ollama_protocol_malformed_event') from error
                if (not isinstance(value, dict) or value.get('error')
                        or value.get('model') not in ('llama3.2', 'llama3.2:latest')):
                    raise WorkerFailure('ollama_protocol_malformed_event')
                message = value.get('message')
                if (not isinstance(message, dict) or message.get('role') != 'assistant'
                        or message.get('tool_calls') or not isinstance(message.get('content'), str)
                        or type(value.get('done')) is not bool):
                    raise WorkerFailure('ollama_protocol_malformed_event')
                text = message['content']
                total += len(text)
                if total > MAX_OUTPUT:
                    raise WorkerFailure('output_limit')
                pending += text
                while len(pending) >= 1024:
                    send(pending[:1024])
                    pending = pending[1024:]
                if value['done']:
                    if value.get('done_reason') not in (None, 'stop'):
                        raise WorkerFailure('ollama_protocol_malformed_event')
                    send(pending, done=True)
                    completed = True
                    duration = min(600000, int((time.monotonic() - started) * 1000))
                    self._telemetry_event('inference_completed', request_id=request_id,
                                          attempt=attempt, duration_ms=duration,
                                          outcome='success')
                    self._telemetry_runtime('last_inference_success', int(time.time()))
                    return
                if pending and time.monotonic() - last_send >= 0.1:
                    send(pending)
                    pending, last_send = '', time.monotonic()
            raise WorkerFailure('incomplete_ollama_stream')
        except Exception as error:
            if isinstance(error, WorkerFailure):
                failure = error
            elif isinstance(error, GenerationDeadline):
                failure = WorkerFailure('job_deadline')
            elif isinstance(error, TimeoutError):
                failure = WorkerTimeout('ollama_read_timeout' if received_event
                                        else 'ollama_cold_start_timeout')
            elif isinstance(error, (URLError, OSError)):
                failure = WorkerFailure('ollama_connect_failure')
            else:
                failure = WorkerFailure('ollama_protocol_malformed_event')
            LOG.warning('worker job failed category=%s', failure.category)
            duration = min(600000, int((time.monotonic() - started) * 1000))
            self._telemetry_event('inference_failed', request_id=request_id, attempt=attempt,
                                  duration_ms=duration, outcome='failure',
                                  reason=failure.category)
            self._telemetry_runtime('last_failure_at', int(time.time()))
            try:
                send('', done=True, error=True, failure=failure.category)
            except Exception:
                pass
            if failure is error:
                raise
            raise failure from error
        finally:
            cleanup_failed = False
            if response is not None:
                try:
                    response.close()
                except Exception:
                    cleanup_failed = True
            if opened:
                LOG.warning('worker upstream stream closed')
            if not completed:
                self._discard_local_transport()
            if cleanup_failed:
                LOG.warning('worker recovery category=ollama_cleanup_recovery_failure')
                self._telemetry_event('worker_recovered', outcome='failure',
                    reason='ollama_cleanup_recovery_failure',
                    dimensions={'component':'ollama', 'state':'unavailable'})
            self._telemetry_runtime('active_inference', 0)

    def run(self):
        heartbeat = threading.Thread(target=self.heartbeat, daemon=True, name='oes-worker-heartbeat')
        heartbeat.start()
        try:
            while not self.stop.is_set():
                owner = None
                try:
                    self.ready = self.model_ready()
                    with self.lock:
                        owner = self.owner
                    if owner is None:
                        owner = self._connect()
                        LOG.warning('worker relay connected')
                        self._telemetry_event('worker_connected', outcome='success',
                            dimensions={'component':'relay', 'state':'connected'})
                    response = self.rpc('poll', self._session_body(owner))
                    response = self._telemetry_response(response)
                    if response == {'job': None}:
                        self.stop.wait(0.25)
                        continue
                    with self.lock:
                        if self.owner is not owner:
                            raise ValueError('Obsolete connection')
                        self.job = response.get('job')
                        self.cancelled.clear()
                    try:
                        self.infer(response, owner)
                        LOG.warning('worker inference completed')
                    except Exception:
                        # Also terminate a claimed job rejected before opening Ollama
                        # (for example its context budget or expected digest failed).
                        try:
                            response = self.rpc('heartbeat', self._session_body(
                                owner, job=self.job, ollama='unavailable'))
                            self._telemetry_response(response)
                        except Exception:
                            pass
                        raise
                    finally:
                        with self.lock:
                            self.job = None
                except Exception as error:
                    self.cancelled.set()
                    with self.lock:
                        self.ready = False
                    established = self._clear_session()
                    category = getattr(error, 'category', 'relay_ownership_lease')
                    LOG.warning('worker connection reset category=%s', category)
                    if established:
                        self._telemetry_event('worker_disconnected', outcome='failure',
                            reason=category if category in REASONS
                            else 'relay_ownership_lease',
                            dimensions={'component':'relay', 'state':'disconnected'})
                    elif owner is None:
                        self._telemetry_event('worker_connection_failed', outcome='failure',
                            reason=self._connection_failure_reason(error),
                            dimensions={'component':'relay', 'state':'reconnecting'})
                    self.stop.wait(3)
        finally:
            self.cancelled.set()
            self.stop.set()
            heartbeat.join(timeout=13)
