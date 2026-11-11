import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "static" / "design-exploration" / "motor-city" / "concept-d"


class MotorCityLiquidAlloyReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        cls.css = (CONCEPT / "concept.css").read_text(encoding="utf-8")
        cls.refinement = (CONCEPT / "refinement.css").read_text(encoding="utf-8")
        cls.concept = (CONCEPT / "concept.js").read_text(encoding="utf-8")
        cls.content = (CONCEPT.parent / "shared" / "content.js").read_text(encoding="utf-8")
        cls.runtime = (ROOT / "static" / "js" / "liquid-alloy-app.js").read_text(
            encoding="utf-8")

    def test_homepage_uses_liquid_alloy_with_original_eyeball(self):
        for required in (
            "product-system", 'id="client-work"', "public-sector",
            'include "partials/eyeball_chat.html"', "data-product-counter",
            "liquid-alloy-app.js", "data-oes-core", "data-oes-core-stage",
            "oes-core__surface", "Open OES Eyeball Chat", "hero-scene.css",
        ):
            self.assertIn(required, self.template)
        for initializer in (
            "initializeEyeballChat", "initializeProductIntelligence",
            "initializeSectionAwareness", "initializeOESCore", "initializeOESCore3D",
            "initializeOESCoreCompanion", "initializeProductExperiences",
        ):
            self.assertIn(initializer, self.runtime)

    def test_interactive_product_stories_are_local_and_truthful(self):
        experience = (ROOT / "static" / "js" / "product-experiences.js").read_text(encoding="utf-8")
        source = self.template + self.concept + experience
        for required in (
            'data-product-demo="chaseingreen"', 'data-product-demo="lottovate"',
            'data-product-demo="sportfolio"', 'data-product-demo="drinkswithfriendz"',
            "Illustrative data", "not financial advice", "do not guarantee",
            "source attached", "authorized location",
        ):
            self.assertIn(required, source)
        for forbidden in ("fetch(", "WebSocket", "EventSource", "Scout", "broker order"):
            self.assertNotIn(forbidden, experience)

    def test_lottovate_membership_demo_matches_product_contract(self):
        experience = (ROOT / "static" / "js" / "product-experiences.js").read_text(
            encoding="utf-8")
        source = self.concept + experience
        for required in (
            "Freemium", "Premium", "Six daily prediction lanes",
            "Midday and evening · 3D, 4D and 5D", "Regular daily predictions",
            "Favorites, with sign-in for syncing", "Platform Picks", "Easy Picks",
            "Additional analytics and performance cards", "XP, tokens",
            "Community activity and leaderboards", "do not guarantee future results",
        ):
            self.assertIn(required, source)
        for unsupported in ("unlimited predictions", "$9.99", "guaranteed accuracy"):
            self.assertNotIn(unsupported, source.lower())

    def test_chaseingreen_uses_approved_sculpted_brand_artwork(self):
        source_asset = ROOT / "static" / "images" / "chaseingreen" / "02-sculpted.png"
        web_asset = (
            ROOT / "static" / "images" / "chaseingreen"
            / "chaseingreen-bull-bear-sculpted.webp"
        )
        self.assertTrue(source_asset.is_file())
        self.assertTrue(web_asset.is_file())
        self.assertIn(
            "/static/images/chaseingreen/chaseingreen-bull-bear-sculpted.webp",
            self.concept,
        )
        self.assertIn("Sculpted gold bull and bear emblem for ChaseInGreen", self.concept)
        self.assertNotIn("chaseingreen-bull-bear-sculpted", self.template.lower())

    def test_additive_product_branding_assets_and_visuals_are_present(self):
        restoration = (
            ROOT / "static" / "css" / "product-restoration.css"
        ).read_text(encoding="utf-8")
        for asset in (
            ROOT / "static" / "images" / "lottovate" / "lottovate-icon.png",
            ROOT / "static" / "images" / "sportfolio"
            / "sportfolio-approved-master.webp",
        ):
            self.assertTrue(asset.is_file())
            self.assertGreater(asset.stat().st_size, 0)
        for required in (
            "market-display__metrics", "lottery-display__scan",
            "sportfolio-display__diamond", "sportfolio-display__metrics",
            "sportfolio-approved-master.webp", "lottovate-icon.png",
        ):
            self.assertIn(required, self.concept + restoration)
        self.assertIn("partials/dwf_logo_showcase.html", self.template)
        self.assertIn("css/dwf-logo.css", self.template)

    def test_original_eyeball_opens_in_hero_and_companion_is_not_encounter_gated(self):
        companion = (ROOT / "static" / "js" / "oes-core-companion.js").read_text(
            encoding="utf-8")
        self.assertEqual(self.template.count("data-oes-core-stage"), 1)
        self.assertIn('id="eyeball"', self.template)
        self.assertIn("Meet Eyeball — your guide to OES.", self.template)
        self.assertLess(
            self.template.index("data-oes-core-stage"),
            self.template.index('id="products"'),
        )
        self.assertNotIn("eyeball-dock", self.template)
        self.assertNotIn("homeEncountered", companion)
        self.assertIn('"[data-eyeball-hero]"', companion)

    def test_rejected_petal_core_is_not_in_release_surface(self):
        release = self.template + self.runtime + self.concept + self.refinement
        for rejected in (
            "oes-petal-core-stage-d.glb", "petal-core-stage.js", "GLTFLoader",
            "data-approved-glb", "data-petal-stage", "data-petal-move",
            "Stage D development preview", "visual approval pending",
            ".petal-stage", ".petal-controls", "@keyframes petal-load",
        ):
            self.assertNotIn(rejected, release)

    def test_products_client_work_and_destinations_are_preserved(self):
        source = self.template + self.concept + self.content
        for product in ("chaseingreen", "lottovate", "sportfolio", "drinkswithfriendz"):
            self.assertIn(product, source.lower())
        for destination in (
            "https://apps.apple.com/us/app/chaseingreen/id6770096789",
            "https://testflight.apple.com/join/CD35ByXj",
            "https://sportfolio-api-ktd5.onrender.com/",
            "https://drinkswithfriendz.com/",
            "https://testflight.apple.com/join/mzknJ42e",
            "/privacy", "/drinks-with-friendz/privacy",
        ):
            self.assertIn(destination, source)
        self.assertIn("const products = baseProducts.filter", self.concept)
        self.assertIn("const clientProjects = [drinks]", self.concept)
        self.assertIn("client-owned brand", self.concept)

    def test_product_and_eyeball_analytics_are_preserved(self):
        source = self.template + self.concept + self.runtime
        for event in (
            "product_card_activated", "external_product_link_activated",
            "testflight_link_activated", "web_app_link_activated",
            "contact_action_activated",
        ):
            self.assertIn(event, source)
        self.assertIn("initializeProductIntelligence", self.runtime)
        self.assertIn("data-sportfolio-url", self.template)

    def test_keyboard_mobile_and_reduced_motion_contracts(self):
        source = self.template + self.css + self.refinement + self.concept
        for required in (
            "skip-link", "aria-expanded", 'role="tablist"', 'role="tab"',
            'role="tabpanel"', "ArrowRight", "ArrowLeft", "<details",
            ":focus-visible", "prefers-reduced-motion:reduce", "@media(max-width:760px)",
        ):
            self.assertIn(required, source)

    def test_release_has_no_preview_or_native_runtime_controls(self):
        source = self.template + self.concept + self.runtime
        for forbidden in (
            "prototype-switcher", "renderer.exe", "subprocess", "desktop companion",
            "development-preview", "data-eyeball-preview",
        ):
            self.assertNotIn(forbidden, source)

    def test_homepage_copy_is_written_for_visitors(self):
        source = self.template + self.concept + self.content
        for removed in (
            "precision navigation spine", "verified state", "public destinations",
            "development and technical dossier", "current verified state",
            "public intelligence interface", "technical architecture",
            "implementation terminology", "client delivery",
        ):
            self.assertNotIn(removed, source.lower())
        for visitor_copy in (
            "Explore what", "See how it works", "What can we", "Ready to",
            "Tell us what you want to build", "Ask about our technology",
        ):
            self.assertIn(visitor_copy, source)


if __name__ == "__main__":
    unittest.main()
