import re
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app import app
from public_destinations import AQUAFUNDED_CHANNELS, active_community_invites


class CustomerOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_aquafunded_guide_navigation_and_single_public_channel(self):
        path = '/chaseingreen/onboarding/aquafunded'
        for parent in ('/', '/chaseingreen', '/chaseingreen/onboarding'):
            self.assertIn(f'href="{path}"', self.client.get(parent).get_data(as_text=True))
        guide = self.client.get(path)
        self.assertEqual(guide.status_code, 200)
        body = guide.get_data(as_text=True)
        self.assertEqual(len(AQUAFUNDED_CHANNELS), 8)
        for channel, url in AQUAFUNDED_CHANNELS.items():
            self.assertEqual(url in body, channel == 'OES-ChaseInGreen-Website')
        self.assertIn('OES may earn a commission from qualifying purchases made through affiliate links.', body)
        self.assertNotIn('BLACKFRIDAY', body)
        for step in range(1, 9):
            self.assertIn(f'data-marketing-click="step_{step}"', body)

    def test_expiring_communities_are_omitted_after_provider_expiration(self):
        pre = datetime(2026, 12, 25, 21, 2, 49, tzinfo=timezone.utc)
        post = datetime(2026, 12, 25, 21, 2, 58, tzinfo=timezone.utc)
        self.assertEqual(set(active_community_invites(pre)), {'chaseingreen', 'lottovate'})
        self.assertEqual(active_community_invites(post), {})
        with patch('app.active_community_invites', return_value={}):
            self.assertNotIn('discord.gg', self.client.get('/lottovate').get_data(as_text=True))

    def test_private_marketing_counts_are_opt_in_and_allowlisted(self):
        url = '/api/marketing-metric'
        with patch.dict(app.config, {'OES_MARKETING_METRICS_DSN': ''}):
            self.assertEqual(self.client.post(url, json={'page': 'aquafunded', 'action': 'view'}).status_code, 404)
            self.assertNotIn('marketing-metrics.js',
                             self.client.get('/chaseingreen/onboarding').get_data(as_text=True))
        with patch.dict(app.config, {'OES_MARKETING_METRICS_DSN': 'test'}), \
                patch('marketing_metrics.increment') as increment:
            self.assertEqual(self.client.get(url).status_code, 405)
            for data in ({'page': 'aquafunded', 'action': 'step_12'},
                         {'page': 'chaseingreen', 'action': 'affiliate'},
                         {'page': 'onboarding', 'action': 'view', 'email': 'private@example.test'}):
                self.assertEqual(self.client.post(url, json=data).status_code, 400)
            self.assertEqual(self.client.post(url, json={'page': 'aquafunded', 'action': 'view'},
                                              headers={'Origin': 'https://unrelated.test'}).status_code, 403)
            increment.assert_not_called()
            for action in ('view', 'step_3', 'affiliate', 'app_store', 'discord', 'linkedin'):
                self.assertEqual(self.client.post(url, json={'page': 'aquafunded', 'action': action}).status_code, 204)
            self.assertEqual(increment.call_count, 6)

    def test_chaseingreen_public_and_invited_paths_are_separate(self):
        landing = self.client.get('/chaseingreen')
        setup = self.client.get('/chaseingreen/getting-started')
        for response in (landing, setup):
            self.assertEqual(response.status_code, 200)
            body = response.get_data(as_text=True)
            self.assertIn('https://apps.apple.com/us/app/chaseingreen/id6770096789', body)
            self.assertIn('$29.99 monthly', body)
            self.assertIn('$299.99 annually', body)
            self.assertNotIn('https://testflight.apple.com/', body)
            self.assertNotIn('type="password"', body)
        self.assertIn('authorized you to participate', setup.get_data(as_text=True))
        for index in (1, 2, 3):
            image = self.client.get(f'/static/images/chaseingreen/app-store-0{index}.jpg')
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image.mimetype, 'image/jpeg')
            image.close()

    def test_portfolio_status_and_legal_routes(self):
        for path, expected in (
            ('/products', 'Client work'),
            ('/lottovate', 'Not accepting new testers'),
            ('/products/sportfolio', 'Baseball field testing'),
            ('/products/drinks-with-friendz', 'Drinks With Friendz Privacy Policy'),
            ('/products/scout', 'In development'),
            ('/products/rush-and-risk', 'Public availability unconfirmed'),
            ('/products/eyeball', 'Available on the OES website'),
            ('/privacy', 'Privacy'),
            ('/drinks-with-friendz/privacy', 'Privacy'),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, response.get_data(as_text=True))
        self.assertEqual(self.client.get('/products/not-approved').status_code, 404)

    def test_home_links_and_existing_click_telemetry(self):
        body = self.client.get('/').get_data(as_text=True)
        self.assertIn('href="/chaseingreen/getting-started"', body)
        self.assertIn('href="/products"', body)
        setup = self.client.get('/chaseingreen/getting-started').get_data(as_text=True)
        self.assertIn('data-product-event="external_product_link_activated"', setup)
        self.assertIn('data-product-event="contact_action_activated"', setup)

    def test_android_registration_disabled_without_private_storage(self):
        with patch.dict(app.config, {'OES_ANDROID_INTEREST_DSN': ''}):
            response = self.client.get('/chaseingreen/android')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<form', response.get_data(as_text=True))

    def test_android_registration_requires_consent_and_csrf(self):
        url = '/chaseingreen/android'
        origin = 'https://localhost'
        with patch.dict(app.config, {'OES_ANDROID_INTEREST_DSN': 'test-placeholder',
                                     'OPENAI_ADS_PIXEL_ID': 'test-pixel'}):
            with patch('android_interest.save_interest') as save:
                form = self.client.get(url, base_url=origin)
                self.assertNotIn('test-pixel', form.get_data(as_text=True))
                self.assertIn('HttpOnly', form.headers['Set-Cookie'])
                self.assertEqual(self.client.post(url, base_url=origin,
                                                  data={'email': 'test@example.com'}).status_code, 403)
                form = self.client.get(url, base_url=origin)
                csrf = re.search(r'name="csrf" type="hidden" value="([^"]+)"',
                                 form.get_data(as_text=True))[1]
                blocked = self.client.post(url, base_url=origin, data={
                    'csrf': csrf, 'email': 'test@example.com'})
                self.assertEqual(blocked.status_code, 400)
                save.assert_not_called()
                csrf = re.search(r'name="csrf" type="hidden" value="([^"]+)"',
                                 blocked.get_data(as_text=True))[1]
                response = self.client.post(url, base_url=origin, data={
                    'csrf': csrf, 'email': ' TEST@example.com ', 'consent': 'yes'})
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('test@example.com', response.get_data(as_text=True))
                save.assert_called_once_with('test-placeholder', 'test@example.com')
