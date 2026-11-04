import base64
from datetime import date, datetime, timezone
import hashlib
import hmac
import re
import struct
import unittest
from unittest.mock import MagicMock, Mock

from flask import Flask

from owner_analytics.auth import (LoginLimiter, OwnerAuthStore, OwnerSession, password_hash,
                                  totp_counter, verify_password)
from owner_analytics.query import AnalyticsQuery
from owner_analytics.routes import init_owner_analytics


TOTP_BYTES = b'owner-analytics-key!'
TOTP_SECRET = base64.b32encode(TOTP_BYTES).decode('ascii')
NOW = 1800000000


def code(counter=NOW // 30):
    digest = hmac.new(TOTP_BYTES, struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 15
    value = (struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1_000_000
    return f'{value:06d}'


class FakeAuth:
    def __init__(self):
        self.counter = None
        self.deleted = []

    def consume_totp(self, counter):
        if self.counter is not None and counter <= self.counter:
            return False
        self.counter = counter
        return True

    def create(self): return OwnerSession('owner-token', 'owner-csrf')

    def validate(self, token, csrf=None, touch=True):
        return token == 'owner-token' and (csrf is None or csrf == 'owner-csrf')

    def delete(self, token): self.deleted.append(token)


class FakeQuery:
    def __init__(self, fail=False): self.fail = fail
    def snapshot(self, selected):
        if self.fail: raise RuntimeError('private database failure')
        return {
            'range':selected, 'start':date(2026,10,6), 'end':date(2026,11,4),
            'timezone':'UTC', 'earliest_available':'2026-10-01',
            'latest_event':None, 'latest_aggregate':None,
            'totals':{'sessions':2,'visits':3,'page_views':4,'product_activations':1,
                      'eyeball_interactions':5,'response_successes':4,'safe_errors':1,
                      'cancelled_requests':0,'analytics_drops':2,'telemetry_gaps':3},
            'latency':{'samples':4,'average_ms':250},
            'known_gap_count':3, 'drop_count':2, 'provisional_days':1,
            'finalized_days':2,
            'trend':{'2026-11-03':{'sessions':2,'visits':3,'page_views':4,
                                    'product_activations':1,'eyeball_interactions':5}},
            'status':{'2026-11-03':{'finalized':False}},
        }


def configured_app(*, secure=False):
    app = Flask(__name__)
    app.config.update(
        TESTING=True, OES_OWNER_ANALYTICS_ENABLED='true',
        OES_ANALYTICS_DATABASE_URL='postgresql://private',
        OES_OWNER_USERNAME='owner',
        OES_OWNER_PASSWORD_HASH=password_hash('correct horse battery staple', salt=b'fixed-owner-salt!'),
        OES_OWNER_TOTP_SECRET=TOTP_SECRET,
        OES_OWNER_SESSION_SECRET='s' * 48,
        OES_OWNER_COOKIE_SECURE='true' if secure else 'false',
    )
    assert init_owner_analytics(app)
    app.extensions['owner_analytics_auth'] = FakeAuth()
    app.extensions['owner_analytics_query'] = FakeQuery()
    return app


class OwnerAnalyticsTests(unittest.TestCase):
    def csrf(self, client):
        body = client.get('/owner/analytics/login').get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', body).group(1)

    def login(self, client):
        token = self.csrf(client)
        with unittest.mock.patch('owner_analytics.routes.totp_counter', return_value=60000000):
            return client.post('/owner/analytics/login', data={
                'csrf_token':token, 'username':'owner',
                'password':'correct horse battery staple', 'totp':'123456'})

    def test_disabled_by_default_registers_no_private_routes(self):
        app = Flask(__name__)
        self.assertFalse(init_owner_analytics(app))
        self.assertEqual(app.test_client().get('/owner/analytics/').status_code, 404)
        self.assertFalse(any(rule.rule.startswith('/owner/analytics') for rule in app.url_map.iter_rules()))

    def test_invalid_or_incomplete_configuration_fails_closed(self):
        app = Flask(__name__)
        app.config.update(OES_OWNER_ANALYTICS_ENABLED='true',
                          OES_ANALYTICS_DATABASE_URL='postgresql://private')
        self.assertFalse(init_owner_analytics(app))
        self.assertEqual(app.test_client().get('/owner/analytics/login').status_code, 404)

    def test_password_hash_and_totp_are_strict(self):
        encoded = password_hash('correct horse battery staple', salt=b'fixed-owner-salt!')
        self.assertTrue(verify_password('correct horse battery staple', encoded))
        self.assertFalse(verify_password('wrong password value', encoded))
        self.assertEqual(totp_counter(TOTP_SECRET, code(), NOW), NOW // 30)
        self.assertIsNone(totp_counter(TOTP_SECRET, '12345', NOW))

    def test_anonymous_dashboard_redirects_and_never_queries(self):
        app = configured_app()
        query = Mock()
        app.extensions['owner_analytics_query'] = query
        response = app.test_client().get('/owner/analytics/')
        self.assertEqual(response.status_code, 302)
        query.snapshot.assert_not_called()

    def test_every_owner_route_fails_closed_for_anonymous_and_allows_authenticated_flow(self):
        app = configured_app(); client = app.test_client()
        self.assertEqual(client.get('/owner/analytics/login').status_code, 200)
        self.assertEqual(client.get('/owner/analytics/').status_code, 302)
        self.assertEqual(client.post('/owner/analytics/logout').status_code, 400)
        self.assertEqual(client.post('/owner/analytics/login', data={}).status_code, 400)
        self.assertEqual(self.login(client).status_code, 302)
        self.assertEqual(client.get('/owner/analytics/login').status_code, 302)
        self.assertEqual(client.get('/owner/analytics/').status_code, 200)
        self.assertEqual(client.post('/owner/analytics/logout',
                                    data={'csrf_token':'owner-csrf'}).status_code, 302)

    def test_login_requires_signed_csrf_password_totp_and_consumes_replay(self):
        app = configured_app()
        client = app.test_client()
        self.assertEqual(client.post('/owner/analytics/login', data={}).status_code, 400)
        token = self.csrf(client)
        bad = client.post('/owner/analytics/login', data={
            'csrf_token':token,'username':'owner','password':'wrong password value','totp':'000000'})
        self.assertEqual(bad.status_code, 401)
        response = self.login(client)
        self.assertEqual(response.status_code, 302)
        cookies = '\n'.join(response.headers.getlist('Set-Cookie'))
        self.assertIn('HttpOnly', cookies)
        self.assertIn('SameSite=Strict', cookies)
        self.assertIn('Path=/owner/analytics', cookies)
        second = app.test_client()
        token = self.csrf(second)
        with unittest.mock.patch('owner_analytics.routes.totp_counter', return_value=60000000):
            replay = second.post('/owner/analytics/login', data={
                'csrf_token':token,'username':'owner',
                'password':'correct horse battery staple','totp':'123456'})
        self.assertEqual(replay.status_code, 401)

    def test_authenticated_dashboard_is_aggregate_only_and_security_hardened(self):
        app = configured_app()
        client = app.test_client()
        self.login(client)
        response = client.get('/owner/analytics/?range=7d')
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        for expected in ('Sessions', 'Visits', 'Page views', 'Product activations',
                         'Successful responses', '250 ms', 'Provisional', 'UTC'):
            self.assertIn(expected, body)
        for forbidden in ('raw conversation', 'owner-token', 'postgresql://private'):
            self.assertNotIn(forbidden, body)
        self.assertEqual(response.headers['Cache-Control'], 'no-store, private')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertIn("default-src 'none'", response.headers['Content-Security-Policy'])

    def test_database_outage_is_accurate_and_public_routes_are_independent(self):
        app = configured_app()
        app.extensions['owner_analytics_query'] = FakeQuery(fail=True)
        app.add_url_rule('/healthz', 'healthz', lambda: {'status':'ok'})
        client = app.test_client(); self.login(client)
        body = client.get('/owner/analytics/').get_data(as_text=True)
        self.assertIn('Analytics unavailable', body)
        self.assertIn('No totals are inferred', body)
        self.assertEqual(client.get('/healthz').status_code, 200)

    def test_logout_requires_csrf_and_revokes_server_session(self):
        app = configured_app(); client = app.test_client(); self.login(client)
        self.assertEqual(client.post('/owner/analytics/logout', data={'csrf_token':'wrong'}).status_code, 400)
        response = client.post('/owner/analytics/logout', data={'csrf_token':'owner-csrf'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(app.extensions['owner_analytics_auth'].deleted, ['owner-token'])

    def test_rate_limiter_is_bounded(self):
        limiter = LoginLimiter(maximum=2, window=60, clock=lambda: 10)
        self.assertTrue(limiter.allow(b'fixed'))
        self.assertTrue(limiter.allow(b'fixed'))
        self.assertFalse(limiter.allow(b'fixed'))

    def test_rate_limit_is_process_local_and_requires_edge_enforcement(self):
        workers = [LoginLimiter(maximum=2, window=60, clock=lambda: 10) for _ in range(2)]
        accepted = sum(worker.allow(b'same-client') for worker in workers for _ in range(2))
        self.assertEqual(accepted, 4)
        self.assertFalse(workers[0].allow(b'same-client'))
        self.assertFalse(workers[1].allow(b'same-client'))

    def test_secure_cookie_policy_is_server_authoritative_behind_proxy(self):
        app = configured_app(secure=True); client = app.test_client()
        response = client.get('/owner/analytics/login', base_url='https://oes.example',
                              headers={'X-Forwarded-Proto':'http'})
        token = re.search(r'name="csrf_token" value="([^"]+)"',
                          response.get_data(as_text=True)).group(1)
        self.assertIn('Secure', '\n'.join(response.headers.getlist('Set-Cookie')))
        with unittest.mock.patch('owner_analytics.routes.totp_counter', return_value=60000000):
            response = client.post('/owner/analytics/login', base_url='https://oes.example',
                                   headers={'X-Forwarded-Proto':'http'}, data={
                                       'csrf_token':token,'username':'owner',
                                       'password':'correct horse battery staple','totp':'123456'})
        cookies = '\n'.join(response.headers.getlist('Set-Cookie'))
        self.assertIn('Secure', cookies)
        self.assertIn('HttpOnly', cookies)
        self.assertIn('SameSite=Strict', cookies)

    def test_owner_session_storage_receives_only_keyed_digests(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        store = OwnerAuthStore('postgresql://private', 's' * 48,
                               connect=Mock(return_value=connection),
                               now=lambda: datetime(2026,11,4,tzinfo=timezone.utc))
        with unittest.mock.patch('owner_analytics.auth.secrets.token_urlsafe',
                                 side_effect=['raw-owner-token','raw-csrf-token']):
            result = store.create()
        self.assertEqual(result, OwnerSession('raw-owner-token','raw-csrf-token'))
        rendered = repr(connection.execute.call_args_list)
        self.assertNotIn('raw-owner-token', rendered)
        self.assertNotIn('raw-csrf-token', rendered)
        self.assertNotIn('ssssssss', rendered)
        insert = connection.execute.call_args_list[1].args[1]
        self.assertEqual(int((insert[4] - insert[3]).total_seconds()), 30 * 60)
        self.assertEqual(int((insert[5] - insert[2]).total_seconds()), 8 * 60 * 60)


class QueryTests(unittest.TestCase):
    def test_query_returns_empty_and_provisional_states_without_inference(self):
        cursor = Mock()
        cursor.fetchall.side_effect = [[], []]
        cursor.fetchone.side_effect = [None, (None,), (None,)]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        query = AnalyticsQuery('postgresql://private', connect=Mock(return_value=connection),
                               now=lambda: datetime(2026,11,4,tzinfo=timezone.utc))
        result = query.snapshot('7d')
        self.assertEqual(result['totals']['sessions'], 0)
        self.assertIsNone(result['latency']['average_ms'])
        self.assertIsNone(result['earliest_available'])
        self.assertEqual(result['provisional_days'], 0)
        with self.assertRaises(ValueError): query.snapshot('arbitrary')


if __name__ == '__main__':
    unittest.main()
