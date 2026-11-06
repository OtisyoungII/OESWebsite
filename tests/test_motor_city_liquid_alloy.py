import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOTOR_CITY = ROOT / "static" / "design-exploration" / "motor-city"
CONCEPT = MOTOR_CITY / "concept-d"


class MotorCityLiquidAlloyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (CONCEPT / "index.html").read_text(encoding="utf-8")
        cls.css = (CONCEPT / "concept.css").read_text(encoding="utf-8")
        cls.js = (CONCEPT / "concept.js").read_text(encoding="utf-8")
        cls.shared = (MOTOR_CITY / "shared" / "content.js").read_text(encoding="utf-8")

    def test_concept_d_is_navigable_from_showroom(self):
        showroom = (MOTOR_CITY / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="concept-d/index.html"', showroom)
        self.assertIn("Motor City Liquid Alloy", showroom)

    def test_chaseingreen_uses_verified_app_store_release(self):
        self.assertIn("Live on the App Store", self.js)
        self.assertIn("https://apps.apple.com/us/app/chaseingreen/id6770096789", self.js)
        self.assertIn("does not claim download counts, ratings, rankings", self.js.lower())
        self.assertNotIn("5-star", self.js.lower())

    def test_all_products_and_existing_destinations_are_present(self):
        for product in ("chaseingreen", "lottovate", "sportfolio", "drinkswithfriendz", "eyeball"):
            self.assertIn(product, self.js.lower())
        for destination in (
            "https://testflight.apple.com/join/CD35ByXj",
            "https://sportfolio-api-ktd5.onrender.com/",
            "https://drinkswithfriendz.com/",
            "https://testflight.apple.com/join/mzknJ42e",
            "/privacy",
            "/drinks-with-friendz/privacy",
        ):
            self.assertIn(destination, self.js + self.html + self.shared)

    def test_client_work_is_separate_from_oes_owned_products(self):
        self.assertIn('id="client-work"', self.html)
        self.assertIn('data-client-work', self.html)
        self.assertIn('const products = baseProducts.filter', self.js)
        self.assertIn('const clientProjects = [drinks]', self.js)
        self.assertIn('Client application', self.js)
        self.assertIn('not presented as an OES-owned product', self.js)

    def test_premium_eyeball_stage_does_not_fake_completed_art(self):
        self.assertIn('Blender review candidate · visual approval pending', self.html)
        self.assertIn('actual Blender-authored review candidate', self.html)
        self.assertIn('not declared final', self.html)
        self.assertIn('assets/oes-eyeball-candidate-front.png', self.html)
        self.assertNotIn('eyeball-dock__visual" aria-hidden="true"><span class="eyeball-orbit"', self.html)

    def test_product_spine_is_accessible_without_hover(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('role="tab"', self.js)
        self.assertIn('role="tabpanel"', self.js)
        self.assertIn("ArrowRight", self.js)
        self.assertIn("ArrowLeft", self.js)
        self.assertIn("<details", self.js)
        self.assertIn("<summary>", self.js)

    def test_accessibility_and_reduced_motion_contract(self):
        self.assertIn("skip-link", self.html)
        self.assertIn("aria-expanded", self.html)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("prefers-reduced-motion:reduce", self.css)
        self.assertIn("@media(max-width:760px)", self.css)

    def test_prototype_performs_no_chat_analytics_or_native_calls(self):
        source = self.html + self.js
        for forbidden in ("/api/chat", "/api/product", "fetch(", "subprocess", "renderer.exe"):
            self.assertNotIn(forbidden, source)

    def test_concepts_a_b_c_files_are_not_part_of_this_change(self):
        # Git-level verification additionally confirms these paths are unchanged.
        for name in ("concept-a", "concept-b", "concept-c"):
            self.assertTrue((MOTOR_CITY / name / "index.html").is_file())
            self.assertTrue((MOTOR_CITY / name / "concept.css").is_file())


if __name__ == "__main__":
    unittest.main()
