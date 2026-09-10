import unittest
from flask import Flask
from chat import init_chat


class MotionBoundaryTests(unittest.TestCase):
    def test_motion_fields_cannot_enter_ai_context(self):
        app = Flask(__name__)
        app.testing = True
        init_chat(app)
        def forbidden_provider():
            self.fail('invalid motion context must not construct a provider')
        app.extensions['chat_provider_factory'] = forbidden_provider
        client = app.test_client()
        for field, value in [('movement_allowed', True), ('state', 'avoiding'), ('approach_score', 0)]:
            with self.subTest(field=field):
                self.assertEqual(client.post('/api/chat', json={
                    'message': 'hello', 'context': {field: value}}).status_code, 400)
                self.assertEqual(client.post('/api/chat/invitation', json={
                    'context': {field: value}}).status_code, 400)
