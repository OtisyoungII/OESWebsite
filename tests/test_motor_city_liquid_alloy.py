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
        ):
            self.assertIn(initializer, self.runtime)
        self.assertNotIn("initializeOESCoreCompanion", self.runtime)

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
        self.assertIn("not presented as an OES-owned product", self.concept)

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


if __name__ == "__main__":
    unittest.main()
