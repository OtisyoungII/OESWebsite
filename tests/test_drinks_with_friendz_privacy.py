import unittest

from app import app


class DrinksWithFriendzPrivacyTests(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_privacy_policy_route_is_public(self):
        response = self.client.get('/drinks-with-friendz/privacy')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.content_type)

    def test_privacy_policy_contains_required_product_disclosures(self):
        html = self.client.get('/drinks-with-friendz/privacy').get_data(as_text=True)

        for expected in (
            'September 30, 2026',
            'Location Information',
            'Google Maps and Google Places',
            'does not request or use\n                            background location access',
            'does not have user accounts',
            'does not currently use OES-owned\n                            analytics or advertising tracking',
            'Google reviews are not displayed',
            'info@otisexecutionsystems.com',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, html)

    def test_privacy_policy_internal_navigation_targets_exist(self):
        html = self.client.get('/drinks-with-friendz/privacy').get_data(as_text=True)
        targets = (
            'information-we-access',
            'how-information-is-used',
            'location-information',
            'google-maps-and-places',
            'third-party-services',
            'data-storage',
            'analytics-and-tracking',
            'childrens-privacy',
            'changes',
            'contact',
        )

        for target in targets:
            with self.subTest(target=target):
                self.assertIn(f'href="#{target}"', html)
                self.assertIn(f'id="{target}"', html)


if __name__ == '__main__':
    unittest.main()
