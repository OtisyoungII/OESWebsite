import io
import json
import queue
import ssl
import threading
import time
import unittest
from unittest.mock import patch

from flask import Flask
from chat import init_chat
from chat.providers import create_provider
from chat.service import ChatService
from chat.worker_protocol import canonical, decode, messages_valid, signed_headers
from chat.worker_relay import WorkerRelay, RelayError
from worker.client import OutboundWorker, WorkerFailure

# Deliberately public fixture material; never suitable for deployment.
CONFIG = {'OES_CHAT_PROVIDER': 'outbound_worker', 'OES_WORKER_ENABLED': 'true',
          'OES_WORKER_ID': 'test-worker', 'OES_WORKER_KEY_ID': 'test-key',
          'OES_WORKER_SHARED_KEY': 'ab' * 32, 'OES_AI_CHAT_ENABLED': 'true',
          'OES_EYEBALL_ENABLED': 'true', 'OES_PROACTIVE_ENABLED': 'false',
          'OES_AI_MAX_CONCURRENCY': '1'}
MESSAGES = [{'role': 'system', 'content': 'Bounded test policy'}, {'role': 'user', 'content': 'hello'}]


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(CONFIG)
        init_chat(self.app)
        self.relay = self.app.extensions['worker_relay']
        self.client = self.app.test_client()
        self.counter = 0
        self.streams = []

    def tearDown(self):
        for provider, thread in self.streams:
            provider.cancel()
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def post(self, action, body, raw=None, headers=None):
        path = '/api/worker/v1/' + action
        raw = canonical(body) if raw is None else raw
        self.counter += 1
        headers = headers or signed_headers(CONFIG, path, raw, 'nonce-' + str(self.counter))
        return self.client.post(path, data=raw, headers=headers)

    def connect(self, boot='boot-one'):
        response = self.post('connect', {'boot': boot, 'ollama': 'ready'})
        self.assertEqual(response.status_code, 200)
        return {**response.json, 'boot': boot}

    def start(self):
        provider = create_provider(self.app.config)
        output = queue.Queue()
        def consume():
            try:
                for event in provider.stream(MESSAGES):
                    output.put(event)
            except Exception as error:
                output.put(error)
        thread = threading.Thread(target=consume)
        thread.start()
        self.streams.append((provider, thread))
        for _ in range(100):
            if self.relay.job or not thread.is_alive():
                break
            time.sleep(.005)
        return provider, output, thread

    def claim(self, owner):
        response = self.post('poll', owner)
        self.assertEqual(response.status_code, 200)
        return response.json['job']

    def result(self, owner, job, **changes):
        return self.post('result', {**owner, 'job': job, 'seq': 0, 'text': 'Hello.',
                                    'done': True, 'error': False, **changes})

    def test_missing_and_invalid_authentication_allocates_nothing(self):
        r = self.client.post('/api/worker/v1/connect', json={'boot': 'x', 'ollama': 'ready'})
        self.assertEqual(r.status_code, 401)
        raw = canonical({'boot': 'x', 'ollama': 'ready'})
        for field in ('X-OES-Signature', 'X-OES-Key', 'X-OES-Worker'):
            headers = signed_headers(CONFIG, '/api/worker/v1/connect', raw, 'nonce')
            headers[field] = 'wrong'
            self.assertEqual(self.post('connect', {}, raw, headers).status_code, 401)
        self.assertIsNone(self.relay.session)
        self.assertFalse(self.relay.nonces)

    def test_replay_and_expired_timestamp(self):
        body = {'boot': 'b', 'ollama': 'ready'}
        raw = canonical(body)
        headers = signed_headers(CONFIG, '/api/worker/v1/connect', raw, 'same')
        self.assertEqual(self.post('connect', body, raw, headers).status_code, 200)
        self.assertEqual(self.post('connect', body, raw, headers).status_code, 401)
        for offset in (-31, 31):
            headers = signed_headers(CONFIG, '/api/worker/v1/connect', raw, 'expired', time.time()+offset)
            self.assertEqual(self.post('connect', body, raw, headers).status_code, 401)

    def test_wrong_path_and_tampering(self):
        raw = canonical({'boot': 'b', 'ollama': 'ready'})
        headers = signed_headers(CONFIG, '/api/worker/v1/connect', raw, 'one')
        self.assertEqual(self.post('poll', {}, raw, headers).status_code, 401)
        self.assertEqual(self.post('connect', {}, raw+b' ', headers).status_code, 401)

    def test_oversized_unknown_and_malformed(self):
        self.assertEqual(self.post('connect', {}, raw=b'x'*262145).status_code, 413)
        for raw in (b'no-json', b'{"boot":"a","boot":"b"}', b'[]', b'{"x":NaN}', b'{ "x":1}',
                    b'{"x":'+b'['*2000+b'0'+b']'*2000+b'}', b'\xff'):
            self.assertEqual(self.post('connect', {}, raw=raw).status_code, 409)
        self.assertEqual(self.post('connect', {'boot': 'b', 'ollama': 'ready', 'url': 'x'}).status_code, 409)
        self.assertEqual(self.post('shell', {}).status_code, 409)
        self.assertIsNone(self.relay.session)

    def test_signed_response(self):
        from chat.worker_protocol import settings, signature
        raw = canonical({'boot': 'b', 'ollama': 'ready'})
        path = '/api/worker/v1/connect'
        headers = signed_headers(CONFIG, path, raw, 'one')
        response = self.post('connect', {}, raw, headers)
        identity, key_id, key = settings(CONFIG)
        self.assertEqual(response.headers['X-OES-Signature'], signature(key, 'response', path,
                         identity, key_id, headers['X-OES-Time'], 'one', response.data))

    def test_stream_and_completed_job_cleanup(self):
        owner = self.connect()
        _, output, thread = self.start()
        job = self.claim(owner)
        self.assertEqual(self.result(owner, job).status_code, 200)
        thread.join(2)
        self.assertEqual(output.get().data, {'text': 'Hello.'})
        self.assertEqual(output.get().kind, 'done')
        self.assertIsNone(self.relay.job)

    def test_character_regeneration_reuses_completed_worker_lifecycle(self):
        owner = self.connect()
        provider = create_provider(self.app.config)
        output = queue.Queue()

        def converse():
            try:
                output.put(list(ChatService(provider).stream("you're back", [], {})))
            except Exception as error:
                output.put(error)

        thread = threading.Thread(target=converse)
        thread.start()
        self.streams.append((provider, thread))
        for _ in range(100):
            if self.relay.job:
                break
            time.sleep(.005)

        first = self.claim(owner)
        trace_id = self.relay.job['request_id']
        self.assertIsNotNone(trace_id)
        self.assertEqual(self.relay.job['attempt'], 1)
        self.assertEqual(self.result(owner, first, text="I'm OES Eyeball. How can I assist you today?").status_code, 200)
        self.assertIsNone(self.relay.session['job'])
        stale_heartbeat = self.post('heartbeat', {**owner, 'job': first, 'ollama': 'ready'})
        self.assertEqual(stale_heartbeat.status_code, 200)
        self.assertFalse(stale_heartbeat.json['active'])
        self.assertIsNone(self.relay.session['job'])

        # The terminal result cannot be replayed, including while regeneration starts.
        self.assertEqual(self.result(owner, first).status_code, 409)
        second = self.claim(owner)
        self.assertNotEqual(first, second)
        self.assertEqual(self.relay.job['request_id'], trace_id)
        self.assertEqual(self.relay.job['attempt'], 2)
        self.assertEqual(self.relay.session['job'], second)
        self.post('heartbeat', {**owner, 'job': first, 'ollama': 'ready'})
        self.assertEqual(self.relay.session['job'], second)
        self.assertEqual(self.result(owner, second,
                         text="Unfortunately for everyone involved, I'm back.").status_code, 200)

        thread.join(2)
        self.assertFalse(thread.is_alive())
        events = output.get()
        self.assertIsInstance(events, list)
        self.assertEqual([event.kind for event in events], ['start', 'delta', 'done'])
        self.assertIsNone(self.relay.job)

    def test_wrong_epoch_stale_lease_boot_and_sequence(self):
        owner = self.connect()
        self.start()
        job = self.claim(owner)
        for changes in ({'epoch':'wrong'}, {'lease':'wrong'}, {'boot':'wrong'}, {'seq':1}, {'seq':True}):
            self.assertEqual(self.result(owner, job, **changes).status_code, 409)
        self.assertEqual(self.relay.job['seq'], 0)

    def test_duplicate_result_fails_closed(self):
        owner = self.connect()
        self.start()
        job = self.claim(owner)
        self.assertEqual(self.result(owner, job, done=False).status_code, 200)
        self.assertEqual(self.result(owner, job, done=False).status_code, 409)

    def test_saturation_and_cancellation(self):
        owner = self.connect()
        provider, output, thread = self.start()
        job = self.claim(owner)
        second = create_provider(self.app.config)
        with self.assertRaises(RelayError):
            next(second.stream(MESSAGES))
        provider.cancel()
        thread.join(2)
        self.assertIsInstance(output.get(), RelayError)
        self.assertEqual(self.result(owner, job).status_code, 409)
        r = self.post('heartbeat', {**owner, 'job': job, 'ollama': 'ready'})
        self.assertFalse(r.json['active'])

    def test_disappearance_deadline_and_ollama_loss(self):
        for failure in ('lease', 'deadline', 'ollama'):
            with self.subTest(failure=failure):
                owner = self.connect()
                _, output, thread = self.start()
                job = self.claim(owner)
                with self.relay.cv:
                    if failure == 'lease': self.relay.session['expires'] = 0
                    if failure == 'deadline': self.relay.job['deadline'] = 0
                if failure == 'ollama':
                    self.post('heartbeat', {**owner, 'job': job, 'ollama': 'unavailable'})
                thread.join(2)
                self.assertIsInstance(output.get(), RelayError)
                self.relay.session = None

    def test_worker_and_ai_switches(self):
        for key in ('OES_WORKER_ENABLED', 'OES_AI_CHAT_ENABLED', 'OES_EYEBALL_ENABLED'):
            self.app.config[key] = 'false'
            with self.assertRaises(ValueError):
                list(create_provider(self.app.config).stream(MESSAGES))
            self.app.config[key] = 'true'
        self.app.config['OES_WORKER_ENABLED'] = 'false'
        self.assertEqual(self.post('connect', {'boot':'b', 'ollama':'ready'}).status_code, 401)

    def test_restart_and_overlapping_instances_have_distinct_ownership(self):
        owner = self.connect()
        other = WorkerRelay(dict(CONFIG))
        self.assertNotEqual(other.epoch, self.relay.epoch)
        other.dispatch('connect', {'boot':'boot-one', 'ollama':'ready'})
        with self.assertRaises(RelayError):
            other.dispatch('heartbeat', {**owner, 'job':None, 'ollama':'ready'})
        self.assertEqual(self.post('connect', {'boot':'other-process', 'ollama':'ready'}).status_code, 409)

    def test_bounded_nonce_cache(self):
        self.relay.nonces = {str(i): time.monotonic()+120 for i in range(2048)}
        self.assertEqual(self.post('connect', {'boot':'b', 'ollama':'ready'}).status_code, 401)

    def test_backpressure_does_not_accept_extra_batch(self):
        owner = self.connect()
        stream = self.relay.stream(MESSAGES)
        # Start and pause the consumer after one event to fill the bounded buffer.
        def deliver_first():
            while not self.relay.job: time.sleep(.005)
            job = self.relay.dispatch('poll', owner)['job']
            self.relay.dispatch('result', {**owner, 'job':job,'seq':0,'text':'a','done':False,'error':False})
        t = threading.Thread(target=deliver_first); t.start()
        next(stream); t.join()
        try:
            job = self.relay.job['id']
            for seq in range(1,9):
                self.assertTrue(self.relay.dispatch('result', {**owner,'job':job,'seq':seq,'text':'a','done':False,'error':False})['accepted'])
            self.assertFalse(self.relay.dispatch('result', {**owner,'job':job,'seq':9,'text':'a','done':False,'error':False})['accepted'])
            self.assertEqual(self.relay.job['seq'],9)
        finally:
            stream.close()

    def test_health_is_coarse_and_diagnostics_authenticated(self):
        self.assertEqual(self.client.get('/api/chat/health').status_code, 503)
        owner = self.connect()
        public = self.client.get('/api/chat/health')
        self.assertEqual(public.status_code, 200)
        self.assertNotIn('OLLAMA', public.get_data(as_text=True))
        private = self.post('heartbeat', {**owner, 'job':None, 'ollama':'ready'}).json['health']
        self.assertEqual(set(private), {'WEB_SERVICE_HEALTH','EYEBALL_CORE_HEALTH',
                         'AI_FEATURE_HEALTH','LOCAL_WORKER_HEALTH','OLLAMA_HEALTH'})

    def test_old_worker_must_acknowledge_idle_after_cancel(self):
        owner = self.connect()
        provider, _, thread = self.start()
        job = self.claim(owner)
        provider.cancel(); thread.join(2)
        self.assertEqual(self.relay.status()['LOCAL_WORKER_HEALTH'],'LOCAL_WORKER_DEGRADED')
        with self.assertRaises(RelayError):
            next(create_provider(self.app.config).stream(MESSAGES))
        self.post('heartbeat',{**owner,'job':None,'ollama':'ready'})
        self.assertEqual(self.relay.status()['LOCAL_WORKER_HEALTH'],'LOCAL_WORKER_HEALTHY')
        self.assertEqual(self.result(owner,job).status_code,409)

    def test_output_limit_and_malformed_result_fields(self):
        owner=self.connect(); self.start(); job=self.claim(owner)
        for change in ({'text':'x'*1025},{'text':42},{'done':1},{'error':'false'},
                       {'done':False,'error':True},{'text':'x','done':True,'error':True},
                       {'model':'other'}):
            self.assertEqual(self.result(owner,job,**change).status_code,409)
        self.relay.job['total']=16000
        self.assertEqual(self.result(owner,job).status_code,409)

    def test_switch_off_cancels_admitted_job(self):
        for key in ('OES_AI_CHAT_ENABLED','OES_WORKER_ENABLED'):
            owner=self.connect()
            _, output, thread=self.start(); self.claim(owner)
            self.app.config[key]='false'
            thread.join(2)
            self.assertIsInstance(output.get(),RelayError)
            self.app.config[key]='true'
            self.relay.session=None

    def test_only_one_long_poll_waiter(self):
        owner=self.connect()
        with patch('chat.worker_relay.POLL_SECONDS',.15):
            result=[]
            thread=threading.Thread(target=lambda:result.append(self.relay.dispatch('poll',owner)))
            thread.start()
            for _ in range(100):
                if self.relay.polling:break
                time.sleep(.001)
            with self.assertRaises(RelayError): self.relay.dispatch('poll',owner)
            thread.join(1)
            self.assertEqual(result,[{'job':None}])

    def test_disabled_ai_poll_does_not_spin(self):
        owner=self.connect()
        self.app.config['OES_AI_CHAT_ENABLED']='false'
        with patch('chat.worker_relay.POLL_SECONDS',.1):
            start=time.monotonic()
            self.assertEqual(self.relay.dispatch('poll',owner),{'job':None})
            self.assertGreaterEqual(time.monotonic()-start,.09)


class WebsiteHealthTests(unittest.TestCase):
    def test_health_never_constructs_or_probes_provider(self):
        from app import app
        with patch.dict(app.config, {'OES_CHAT_PROVIDER':'outbound_worker','OES_WORKER_ENABLED':'false',
                                    'OES_WORKER_SHARED_KEY':'','OES_AI_CHAT_ENABLED':'true'}), \
             patch('chat.providers.create_provider', side_effect=AssertionError('provider probe')), \
             patch('chat.routes.create_provider', side_effect=AssertionError('provider probe')), \
             patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            response = app.test_client().get('/healthz')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {'status':'ok'})
            self.assertLess(len(response.data), 40)
            self.assertEqual(app.test_client().get('/').status_code, 200)

    def test_production_defaults_and_proxy_zero(self):
        import os, subprocess, sys
        env = {k:v for k,v in os.environ.items() if not k.startswith(('OES_','FLASK_'))}
        result = subprocess.run([sys.executable, '-B', '-c',
            "import wsgi; a=wsgi.app; assert not a.debug; assert not a.testing; "
            "assert a.config['OES_CHAT_PROVIDER']==''; assert a.config['OES_AI_CHAT_ENABLED']=='false'; "
            "assert a.config['OES_PROACTIVE_ENABLED']=='false'; "
            "assert a.test_client().get('/healthz').status_code==200"], env=env, capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())


class WorkerTests(unittest.TestCase):
    def config(self):
        return {**CONFIG, 'OES_WORKER_RELAY_URL':'https://relay.example', 'OES_WORKER_MODEL_DIGEST':'cd'*32}

    def test_fixed_destinations_and_tls(self):
        for field, value in [('OES_WORKER_RELAY_URL','http://relay.example'),
                             ('OES_WORKER_RELAY_URL','https://user:pass@relay.example'),
                             ('OES_WORKER_RELAY_URL','https://relay.example/path'),
                             ('OLLAMA_BASE_URL','http://192.168.1.2:11434'),
                             ('OLLAMA_MODEL','arbitrary'), ('OES_WORKER_MODEL_DIGEST','')]:
            with self.assertRaises(ValueError): OutboundWorker({**self.config(),field:value})
        with self.assertRaises(ValueError): OutboundWorker(self.config(),ssl._create_unverified_context())

    def test_invalid_message_and_context_budget(self):
        worker = OutboundWorker(self.config())
        for messages in ([{'role':'tool','content':'x'},MESSAGES[-1]],
                         [MESSAGES[0],{'role':'user','content':'x','model':'x'}]):
            with self.assertRaises(ValueError): messages_valid(messages)
        huge = [{'role':'system','content':'x'*8000},MESSAGES[-1]]
        with self.assertRaisesRegex(ValueError,'Context budget') as raised:
            worker.infer({'job':'j','messages':huge,'seconds':90},{})
        self.assertEqual(raised.exception.category, 'context_budget')

    def test_model_unavailable_and_digest_mismatch(self):
        worker = OutboundWorker(self.config())
        with patch.object(worker.local,'open',side_effect=TimeoutError()):
            self.assertFalse(worker.model_ready())
        with patch.object(worker.local,'open',return_value=io.BytesIO(b'{"models":[]}')):
            self.assertFalse(worker.model_ready())
        with patch.object(worker, 'model_ready', return_value=False):
            with self.assertRaises(WorkerFailure) as raised:
                worker.infer({'job':'j','messages':MESSAGES,'seconds':90},{})
        self.assertEqual(raised.exception.category, 'model_readiness_digest')

    def test_normal_upstream_close_is_not_failure_category(self):
        worker = OutboundWorker(self.config())
        data = canonical({'model':'llama3.2','message':{'role':'assistant','content':'Hello'},
                          'done':True}) + b'\n'
        with patch.object(worker, 'model_ready', return_value=True), \
             patch.object(worker.local, 'open', return_value=io.BytesIO(data)), \
             patch.object(worker, 'rpc', return_value={'accepted':True,'active':True}), \
             self.assertLogs('oes.worker', level='WARNING') as logs:
            worker.infer({'job':'j','messages':MESSAGES,'seconds':90},{})
        self.assertTrue(any('upstream stream closed' in line for line in logs.output))
        self.assertFalse(any('category=' in line for line in logs.output))

    def test_malformed_timeout_and_cancelled_ollama(self):
        for data in (b'bad\n', b'{"model":"other"}\n', b'{"model":"llama3.2","message":{"role":"assistant","content":"x","tool_calls":[{}]},"done":true}\n'):
            worker = OutboundWorker(self.config())
            with patch.object(worker,'model_ready',return_value=True), \
                 patch.object(worker.local,'open',return_value=io.BytesIO(data)), \
                 patch.object(worker,'rpc',return_value={'accepted':True,'active':True}) as rpc:
                with self.assertRaises(ValueError): worker.infer({'job':'j','messages':MESSAGES,'seconds':90},{})
                self.assertTrue(rpc.call_args.args[1]['error'])
        worker = OutboundWorker(self.config())
        with patch.object(worker,'model_ready',return_value=True), \
             patch.object(worker.local,'open',side_effect=TimeoutError()), \
             patch.object(worker,'rpc',return_value={'accepted':True,'active':True}):
            with self.assertRaises(TimeoutError): worker.infer({'job':'j','messages':MESSAGES,'seconds':90},{})

    def test_no_retry_after_ambiguous_result(self):
        worker = OutboundWorker(self.config())
        data = canonical({'model':'llama3.2','message':{'role':'assistant','content':'Hello'},'done':True})+b'\n'
        with patch.object(worker,'model_ready',return_value=True), \
             patch.object(worker.local,'open',return_value=io.BytesIO(data)), \
             patch.object(worker,'rpc',side_effect=TimeoutError()) as rpc:
            with self.assertRaises(TimeoutError): worker.infer({'job':'j','messages':MESSAGES,'seconds':90},{})
            self.assertEqual(sum(not c.args[1]['error'] for c in rpc.call_args_list),1)

    def test_unauthenticated_and_oversized_relay_response(self):
        class RemoteResponse(io.BytesIO):
            headers={}
        worker=OutboundWorker(self.config())
        for data in (b'{"job":null}',b'x'*262145):
            with patch.object(worker.remote,'open',return_value=RemoteResponse(data)):
                with self.assertRaises(ValueError): worker.rpc('poll',{})

    def test_cancel_closes_ollama_response(self):
        worker=OutboundWorker(self.config())
        data=canonical({'model':'llama3.2','message':{'role':'assistant','content':'Hello'},'done':True})+b'\n'
        response=io.BytesIO(data)
        worker.cancelled.set()
        with patch.object(worker,'model_ready',return_value=True), \
             patch.object(worker.local,'open',return_value=response), patch.object(worker,'rpc') as rpc:
            with self.assertRaises(ValueError): worker.infer({'job':'j','messages':MESSAGES,'seconds':90},{})
            self.assertTrue(response.closed)
            rpc.assert_not_called()

    def test_input_bounds(self):
        for messages in ([MESSAGES[0],*([MESSAGES[1]]*12)],
                         [MESSAGES[0],{'role':'user','content':'x'*4001}],
                         [MESSAGES[0],*([{'role':'assistant','content':'x'*4000}]*4),MESSAGES[1]]):
            with self.assertRaises(ValueError):messages_valid(messages)

    def test_default_worker_disabled(self):
        app=Flask(__name__); init_chat(app)
        self.assertEqual(app.config['OES_WORKER_ENABLED'],'false')

    def test_stalled_transport_wait_and_thread_count_are_bounded(self):
        worker=OutboundWorker(self.config())
        release=threading.Event()
        def stalled(*args):
            release.wait(2)
            return {'job':None}
        try:
            with patch.object(worker,'_rpc',side_effect=stalled) as rpc, \
                 patch('worker.client.RPC_SECONDS',.01):
                for _ in range(3):
                    with self.assertRaises(TimeoutError):worker.rpc('poll',{})
                self.assertEqual(rpc.call_count,2)
        finally:
            release.set()
