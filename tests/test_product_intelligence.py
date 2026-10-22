import unittest
from unittest.mock import Mock

from app import app
from product_intelligence import ProductIntelligence
from oes_telemetry import make_event


class ProductIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.emit = Mock()
        app.config.update(TESTING=True, OES_PUBLIC_ORIGIN='http://localhost')
        app.extensions['product_intelligence'] = ProductIntelligence(self.emit)
        self.client = app.test_client()

    def open_session(self):
        response = self.client.post('/api/product-intelligence/session',
                                    headers={'Origin': 'http://localhost'})
        self.assertEqual(response.status_code, 200)
        return response

    def post(self, event, dimensions):
        return self.client.post('/api/product-intelligence/event',
                                json={'event': event, 'dimensions': dimensions},
                                headers={'Origin': 'http://localhost'})

    def test_server_issues_and_counts_one_browser_session(self):
        first = self.open_session()
        second = self.open_session()
        self.assertEqual(first.json['sessions'], 1)
        self.assertTrue(first.json['created'])
        self.assertEqual(second.json['sessions'], 1)
        self.assertFalse(second.json['created'])
        self.assertEqual(first.json['scope'], 'service_runtime')
        self.assertIn('HttpOnly', first.headers['Set-Cookie'])

    def test_browser_cannot_submit_counts_or_unknown_content(self):
        self.open_session()
        bad = [
            {'event':'website_session_started', 'dimensions':{'platform':'desktop',
                                                              'language':'en'}, 'count':999},
            {'event':'arbitrary_name', 'dimensions':{}},
            {'event':'website_session_started', 'dimensions':{'platform':'desktop',
                                                              'language':'en', 'message':'private'}},
            {'event':'website_session_started', 'dimensions':{'platform':'desktop',
                                                              'language':'en', 'latitude':'42.3'}},
            {'event':'website_session_started', 'dimensions':{'platform':'raw user agent',
                                                              'language':'en'}},
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                response = self.client.post('/api/product-intelligence/event', json=payload,
                                            headers={'Origin':'http://localhost'})
                self.assertEqual(response.status_code, 400)
        self.emit.assert_not_called()

    def test_session_and_meaningful_activation_emit_fixed_events(self):
        self.open_session()
        self.assertEqual(self.post('website_session_started',
                                   {'platform':'desktop', 'language':'en'}).status_code, 200)
        self.assertEqual(self.post('testflight_link_activated',
                                   {'product_target':'chaseingreen'}).status_code, 200)
        calls = self.emit.call_args_list
        self.assertEqual([call.args[0] for call in calls],
                         ['website_session_started', 'testflight_link_activated'])
        self.assertEqual(calls[1].kwargs['dimensions'], {
            'product':'oeswebsite', 'surface':'web', 'product_target':'chaseingreen',
            'destination':'testflight'})

    def test_duplicate_session_event_and_immediate_duplicate_activation_are_deduped(self):
        self.open_session()
        dimensions = {'platform':'mobile', 'language':'fr'}
        self.assertTrue(self.post('website_session_started', dimensions).json['recorded'])
        self.assertFalse(self.post('website_session_started', dimensions).json['recorded'])
        action = {'product_target':'sportfolio'}
        self.assertTrue(self.post('web_app_link_activated', action).json['recorded'])
        self.assertFalse(self.post('web_app_link_activated', action).json['recorded'])
        self.assertEqual(self.emit.call_count, 2)

    def test_event_requires_server_issued_session_and_same_origin(self):
        response = self.post('eyeball_closed', {})
        self.assertEqual(response.status_code, 409)
        rejected = self.client.post('/api/product-intelligence/session',
                                    headers={'Origin':'https://attacker.example'})
        self.assertEqual(rejected.status_code, 403)

    def test_clarification_rephrase_is_fixed_and_content_free(self):
        self.open_session()
        response = self.post('eyeball_clarification_rephrase',
                             {'clarification_reason': 'low_confidence'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.emit.call_args.args[0], 'eyeball_clarification_rephrase')
        self.assertEqual(self.emit.call_args.kwargs['dimensions'], {
            'product': 'eyeball', 'surface': 'web',
            'clarification_reason': 'low_confidence'})
        for reason in ('the original message', 'deploy', '', None):
            with self.subTest(reason=reason):
                rejected = self.post('eyeball_clarification_rephrase',
                                     {'clarification_reason': reason})
                self.assertEqual(rejected.status_code, 400)

    def test_common_schema_rejects_identifiers_and_free_text(self):
        valid = make_event('eyeball_opened', outcome='accepted', dimensions={
            'product':'eyeball', 'surface':'web', 'platform':'desktop', 'language':'en'})
        self.assertEqual(valid['event_type'], 'eyeball_opened')
        for field in ('session_id', 'ip_address', 'url', 'message', 'user_agent',
                      'latitude', 'longitude', 'prompt', 'response'):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    make_event('eyeball_opened', dimensions={
                        'product':'eyeball', 'surface':'web', 'platform':'desktop',
                        'language':'en', field:'private'})

    def test_home_contains_honest_counter_and_fixed_activation_metadata(self):
        body = self.client.get('/').get_data(as_text=True)
        self.assertIn('SESSIONS THIS SERVICE RUN', body)
        self.assertIn('data-product-counter', body)
        self.assertIn('data-product-event="testflight_link_activated"', body)
        self.assertIn('data-product-target="chaseingreen"', body)
        self.assertNotIn('VISITORS', body)


if __name__ == '__main__':
    unittest.main()
