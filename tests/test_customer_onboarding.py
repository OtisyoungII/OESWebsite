import re
import unittest
from unittest.mock import patch

from app import app


class CustomerOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

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
        self.assertEqual(response.status_code, 503)
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
