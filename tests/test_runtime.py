import io
import json
import unittest
import time
from email.message import Message
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from flask import Flask
from chat import init_chat
from chat.providers import (ChatEvent, create_provider, OllamaProvider,
                            OpenAICompatibleProvider, NoRedirect, bounded_lines)
from chat.runtime import Admission
from chat.service import SAFE_ERROR


HOSTED = {'OES_CHAT_PROVIDER': 'openai_compatible', 'OES_AI_BASE_URL': 'https://inference.example/v1',
          'OES_AI_API_KEY': 'TEST-PRIVATE-KEY', 'OES_AI_MODEL': 'PRIVATE-MODEL'}


def frame(text='', finish=None):
    return ('data: ' + json.dumps({'choices': [{'index': 0, 'delta': {'content': text},
                                              'finish_reason': finish}]}) + '\n\n').encode()


class HTTPResponse(io.BytesIO):
    def __init__(self, data, content_type='text/event-stream'):
        super().__init__(data)
        self.headers = Message()
        self.headers['Content-Type'] = content_type


class FixtureProvider:
    def stream(self, messages):
        yield ChatEvent('delta', {'text': 'Hello there.'})
        yield ChatEvent('done', {})


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        init_chat(self.app)
        self.client = self.app.test_client()
        self.factory = Mock(return_value=FixtureProvider())
        self.app.extensions['chat_provider_factory'] = self.factory
        self.context = {'section': 'products', 'project': 'lottovate',
                        'time_on_section_seconds': 90, 'product_interaction_count': 1}

    def chat(self, **kwargs):
        return self.client.post('/api/chat', json={'message': 'hello'}, **kwargs)

    def hosted(self):
        self.app.config.update(HOSTED)
        self.app.extensions['chat_provider_factory'] = lambda: create_provider(self.app.config)

    def test_default_ollama_selection(self):
        self.assertIsInstance(create_provider(self.app.config), OllamaProvider)

    def test_hosted_selection(self):
        self.assertIsInstance(create_provider(HOSTED), OpenAICompatibleProvider)

    def test_unsupported_provider(self):
        with self.assertRaises(ValueError):
            create_provider({'OES_CHAT_PROVIDER': 'browser'})

    def test_missing_key_is_safe(self):
        self.hosted()
        self.app.config['OES_AI_API_KEY'] = ''
        r = self.chat()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json, {'message': SAFE_ERROR})
        self.assertEqual(self.app.extensions['chat_admission'].active, 0)

    def test_browser_overrides_rejected(self):
        for field in ['provider', 'model', 'base_url', 'system_prompt', 'api_key', 'tools', 'OES_AI_CHAT_ENABLED']:
            for payload in [{'message': 'hello', field: 'x'}, {'message': 'hello', 'context': {field: 'x'}}]:
                self.assertEqual(self.client.post('/api/chat', json=payload).status_code, 400)
        self.factory.assert_not_called()

    def test_switches_fail_closed(self):
        for key in ['OES_EYEBALL_ENABLED', 'OES_AI_CHAT_ENABLED']:
            for value in [False, 'false', 'invalid']:
                self.app.config[key] = value
                self.assertEqual(self.chat().status_code, 503)
                for endpoint in ['initiation', 'invitation']:
                    r = self.client.post('/api/chat/' + endpoint, json={'context': self.context})
                    self.assertEqual(r.json['action'], 'stay_silent')
            self.app.config[key] = True
        self.factory.assert_not_called()

    def test_proactive_switch_leaves_manual_chat(self):
        self.app.config['OES_PROACTIVE_ENABLED'] = 'false'
        for endpoint in ['initiation', 'invitation']:
            self.assertEqual(self.client.post('/api/chat/' + endpoint,
                                             json={'context': self.context}).json['action'], 'stay_silent')
        self.factory.assert_not_called()
        self.assertIn('event: done', self.chat().get_data(as_text=True))

    def test_reenable(self):
        self.app.config['OES_AI_CHAT_ENABLED'] = False
        self.assertEqual(self.chat().status_code, 503)
        self.app.config['OES_AI_CHAT_ENABLED'] = True
        self.assertIn('event: done', self.chat().get_data(as_text=True))

    def test_health_no_io_or_private_values(self):
        self.hosted()
        with patch('chat.providers.build_opener') as opener:
            r = self.client.get('/api/chat/health')
        opener.assert_not_called()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json['reachability'], 'unchecked')
        for secret in HOSTED.values():
            self.assertNotIn(secret, r.get_data(as_text=True))
        self.assertIn('no-store', r.headers['Cache-Control'])
        self.app.config['OES_AI_API_KEY'] = ''
        self.assertEqual(self.client.get('/api/chat/health').status_code, 503)

    def test_provider_failures_are_safe_and_release(self):
        self.hosted()
        for failure in [TimeoutError('PRIVATE'), HTTPError('https://PRIVATE', 429, 'PRIVATE', {}, io.BytesIO(b'PRIVATE')),
                        HTTPError('https://PRIVATE', 503, 'PRIVATE', {}, io.BytesIO(b'PRIVATE'))]:
            with self.subTest(failure=type(failure).__name__), patch('chat.providers.build_opener') as opener:
                opener.return_value.open.side_effect = failure
                body = self.chat().get_data(as_text=True)
                self.assertIn(SAFE_ERROR, body)
                self.assertNotIn('PRIVATE', body)
                self.assertNotIn('event: done', body)
                self.assertEqual(self.app.extensions['chat_admission'].active, 0)
                self.assertEqual(opener.return_value.open.call_count, 1)

    def test_malformed_stream_safe(self):
        self.hosted()
        for data in [b'data: not-json\n\n', b'data: [DONE]\n\n', frame('')]:
            with patch('chat.providers.build_opener') as opener:
                opener.return_value.open.return_value = HTTPResponse(data)
                body = self.chat().get_data(as_text=True)
                self.assertIn(SAFE_ERROR, body)
                self.assertNotIn('event: done', body)

    def test_hosted_sse_translation_and_request(self):
        self.hosted()
        response = HTTPResponse((b': heartbeat\r\n\r\n' + frame('Hello ') + frame('there.', 'stop') + b'data: [DONE]\n\n'))
        with patch('chat.providers.build_opener') as opener:
            opener.return_value.open.return_value = response
            body = self.chat().get_data(as_text=True)
            request = opener.return_value.open.call_args.args[0]
        self.assertIn('event: done', body)
        self.assertTrue(response.closed)
        self.assertEqual(request.full_url, HOSTED['OES_AI_BASE_URL'] + '/chat/completions')
        payload = json.loads(request.data)
        self.assertEqual(payload['model'], HOSTED['OES_AI_MODEL'])
        self.assertEqual(payload['max_tokens'], 600)
        self.assertNotIn('tools', payload)
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + HOSTED['OES_AI_API_KEY'])

    def test_serious_hosted_output_still_grounded(self):
        self.hosted()
        with patch('chat.providers.build_opener') as opener:
            opener.return_value.open.return_value = HTTPResponse(frame('We have SOC 2 certification.', 'stop') + b'data: [DONE]\n\n')
            body = self.client.post('/api/chat', json={'message': 'Prove your SOC 2 certification'}).get_data(as_text=True)
        self.assertNotIn('We have SOC 2', body)
        self.assertIn('confirmed', body)

    def test_unsafe_initiative_still_rejected_twice(self):
        self.hosted()
        with patch('chat.providers.build_opener') as opener:
            opener.return_value.open.side_effect = [HTTPResponse(frame('You clearly love Lottovate.', 'stop') + b'data: [DONE]\n\n') for _ in range(2)]
            r = self.client.post('/api/chat/invitation', json={'context': self.context})
        self.assertEqual(r.json['action'], 'stay_silent')
        self.assertEqual(opener.return_value.open.call_count, 2)
        self.assertEqual(self.app.extensions['chat_admission'].active, 0)

    def test_concurrency_until_close(self):
        self.app.extensions['chat_admission'] = Admission({'OES_AI_MAX_CONCURRENCY': 1})
        r = self.chat(buffered=False)
        self.assertEqual(self.chat().status_code, 503)
        self.assertEqual(self.factory.call_count, 1)
        r.close()
        self.assertEqual(self.app.extensions['chat_admission'].active, 0)
        self.assertIn('event: done', self.chat().get_data(as_text=True))

    def test_rate_and_forwarded_spoofing(self):
        self.app.extensions['chat_admission'] = Admission({'OES_CHAT_RATE_LIMIT': 1})
        self.chat().get_data()
        self.assertEqual(self.chat(headers={'X-Forwarded-For': '1.2.3.4'}).status_code, 429)
        self.assertEqual(self.factory.call_count, 1)

    def test_proactive_budget_is_not_browser_restraint(self):
        self.app.extensions['chat_admission'] = Admission({'OES_PROACTIVE_RATE_LIMIT': 1})
        self.client.post('/api/chat/invitation', json={'context': self.context}).get_data()
        r = self.client.post('/api/chat/invitation', json={'context': self.context, 'restraint': {}})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(self.factory.call_count, 1)

    def test_api_rate(self):
        self.app.extensions['chat_admission'] = Admission({'OES_API_RATE_LIMIT': 1})
        self.client.post('/api/chat/initiation', json={})
        self.assertEqual(self.client.post('/api/chat/initiation', json={}).status_code, 429)

    def test_limit_expiry_and_idempotent_release(self):
        now = [0]
        gate = Admission({'OES_CHAT_RATE_LIMIT': 1}, clock=lambda: now[0])
        release, _ = gate.acquire('a'); release(); release()
        self.assertEqual(gate.active, 0)
        self.assertEqual(gate.acquire('a')[1], 429)
        now[0] = 61
        release, status = gate.acquire('a')
        self.assertIsNone(status); release()

    def test_global_budget(self):
        gate = Admission({})
        for i in range(30):
            release, _ = gate.acquire(str(i)); release()
        self.assertEqual(gate.acquire('another')[1], 429)

    def test_hosted_url_validation(self):
        for url in ['http://inference.example/v1', 'https://localhost/v1', 'https://127.0.0.1/v1',
                    'https://10.0.0.1/v1', 'https://user:pass@inference.example/v1',
                    'https://inference.example/v1?key=x', 'https://inference.example/v1#x']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                create_provider({**HOSTED, 'OES_AI_BASE_URL': url})
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.example'))

    def test_bounded_transport_and_close(self):
        with self.assertRaises(ValueError):
            list(bounded_lines(HTTPResponse(b'x' * 65537), time.monotonic(), 120))
        with patch('chat.providers.time.monotonic', return_value=121), self.assertRaises(TimeoutError):
            list(bounded_lines(HTTPResponse(b'data'), 0, 120))

    def test_no_browser_config_in_html(self):
        from app import app
        with patch.dict(app.config, HOSTED):
            html = app.test_client().get('/').get_data(as_text=True)
        for secret in [HOSTED['OES_AI_API_KEY'], HOSTED['OES_AI_BASE_URL'], HOSTED['OES_AI_MODEL']]:
            self.assertNotIn(secret, html)
