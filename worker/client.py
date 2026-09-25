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
from urllib.error import URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPSHandler

from chat.providers import GenerationDeadline, NoRedirect, bounded_lines, open_response
from chat.worker_protocol import (CONTEXT_BUDGET, MAX_BODY, MAX_OUTPUT, canonical,
                                  context_cost, decode, fields, messages_valid, settings,
                                  signature, signed_headers, token)

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
    def __init__(self, config, tls_context=None):
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
        with open_response(self.remote, Request(self.origin + path, data=raw, headers=headers), 12) as response:
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
                response = self.rpc('heartbeat', {**owner, 'job': job, 'ollama': 'ready' if ready else 'unavailable'})
                fields(response, ('active', 'health'))
                if type(response['active']) is not bool:
                    raise ValueError('Invalid heartbeat')
                if job and not response['active']:
                    self.cancelled.set()
            except Exception:
                self.cancelled.set()
                with self.lock:
                    if self.owner is owner:
                        self.owner = None

    def infer(self, job, owner):
        try:
            fields(job, ('job', 'messages', 'seconds'))
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

    def run(self):
        heartbeat = threading.Thread(target=self.heartbeat, daemon=True, name='oes-worker-heartbeat')
        heartbeat.start()
        try:
            while not self.stop.is_set():
                try:
                    self.ready = self.model_ready()
                    with self.lock:
                        owner = self.owner
                    if owner is None:
                        response = self.rpc('connect', {'boot': self.boot, 'ollama': 'ready' if self.ready else 'unavailable'})
                        fields(response, ('epoch', 'lease'))
                        token(response['epoch']); token(response['lease'])
                        owner = {'epoch': response['epoch'], 'lease': response['lease'], 'boot': self.boot}
                        with self.lock:
                            self.owner = owner
                    response = self.rpc('poll', owner)
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
                            self.rpc('heartbeat', {**owner, 'job':self.job, 'ollama':'unavailable'})
                        except Exception:
                            pass
                        raise
                    finally:
                        with self.lock:
                            self.job = None
                except Exception as error:
                    self.cancelled.set()
                    with self.lock:
                        self.owner = None
                        self.ready = False
                    category = getattr(error, 'category', 'relay_ownership_lease')
                    LOG.warning('worker connection reset category=%s', category)
                    self.stop.wait(3)
        finally:
            self.cancelled.set()
            self.stop.set()
            heartbeat.join(timeout=13)
