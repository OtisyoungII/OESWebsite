import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "static" / "design-exploration" / "motor-city"


class MotorCityDesignExplorationTests(unittest.TestCase):
    def test_three_distinct_concepts_exist(self):
        css = []
        for name in ("concept-a", "concept-b", "concept-c"):
            self.assertTrue((DESIGN / name / "index.html").is_file())
            content = (DESIGN / name / "concept.css").read_text(encoding="utf-8")
            self.assertGreater(len(content), 800)
            css.append(content)
        self.assertEqual(3, len(set(css)))

    def test_verified_product_names_statuses_and_links_are_preserved(self):
        content = (DESIGN / "shared" / "content.js").read_text(encoding="utf-8")
        for value in (
            "ChaseInGreen", "Lottovate", "Sportfolio", "Drinks With Friendz",
            "Active TestFlight Testing", "Active Field Testing", "TestFlight Beta",
            "https://testflight.apple.com/join/nPjjyDSf",
            "https://testflight.apple.com/join/CD35ByXj",
            "https://testflight.apple.com/join/mzknJ42e",
            "https://drinkswithfriendz.com/",
        ):
            self.assertIn(value, content)

    def test_all_existing_information_groups_are_represented(self):
        content = (DESIGN / "shared" / "content.js").read_text(encoding="utf-8")
        expected = ("services:", "government:", "community:", "research:", "about:", "contact:")
        for group in expected:
            self.assertIn(group, content)
        for service in (
            "Applied Artificial Intelligence", "Native Mobile Applications",
            "Web Platforms", "Data and Analytics", "SaaS Product Development",
            "Workflow Automation", "Product and Technology Consulting",
            "AI, Digital Skills and IT Training",
        ):
            self.assertIn(service, content)

    def test_interactions_are_keyboard_and_reduced_motion_aware(self):
        js = (DESIGN / "shared" / "prototype.js").read_text(encoding="utf-8")
        css = (DESIGN / "shared" / "common.css").read_text(encoding="utf-8")
        self.assertIn("<details", js)
        self.assertIn("<summary>", js)
        self.assertIn('event.key === "Escape"', js)
        self.assertIn("aria-expanded", js)
        self.assertIn("prefers-reduced-motion:reduce", css)
        self.assertIn(".skip-link:focus", css)

    def test_legal_links_and_contact_are_preserved(self):
        js = (DESIGN / "shared" / "prototype.js").read_text(encoding="utf-8")
        self.assertIn('href="/privacy"', js)
        self.assertIn('href="/drinks-with-friendz/privacy"', js)
        self.assertIn("mailto:${c.contact.email}", js)

    def test_prototype_does_not_call_production_chat_or_analytics(self):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in DESIGN.rglob("*") if path.is_file()
        )
        self.assertNotIn("/api/chat", source)
        self.assertNotIn("/api/product-intelligence", source)
        self.assertNotIn("fetch(", source)


if __name__ == "__main__":
    unittest.main()
