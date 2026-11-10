import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EyeballFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chat = (ROOT / "static/js/eyeball-chat.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "static/css/eyeball-chat.css").read_text(encoding="utf-8")
        cls.locales = (ROOT / "static/js/eyeball-localization.js").read_text(encoding="utf-8")

    def test_status_lifecycle_uses_real_stream_boundaries(self):
        self.assertIn("showActivity('thinking')", self.chat)
        self.assertIn("if (!answer && data.text) showActivity('answering')", self.chat)
        self.assertIn("showActivity('stillWorking')", self.chat)
        self.assertIn("kind === 'delta'", self.chat)
        self.assertNotIn("setInterval(", self.chat)

    def test_every_terminal_path_removes_activity(self):
        self.assertGreaterEqual(self.chat.count("removeActivity();"), 3)
        self.assertIn("controller.abort()", self.chat)
        self.assertIn("dialog.addEventListener('close'", self.chat)

    def test_retry_is_explicit_and_preserves_single_request_guard(self):
        self.assertIn("if (activeRequest) return", self.chat)
        self.assertIn("retryWithoutEcho = true", self.chat)
        self.assertIn("form.requestSubmit()", self.chat)
        self.assertIn("send.disabled = busy", self.chat)

    def test_accessibility_and_reduced_motion_contract(self):
        for required in ("role', 'status", "aria-live', 'polite", "aria-atomic', 'true"):
            self.assertIn(required, self.chat)
        self.assertIn("prefers-reduced-motion: reduce", self.css)
        self.assertIn("animation: none", self.css)

    def test_feedback_and_failure_copy_is_localized(self):
        for key in ("thinking:", "answering:", "stillWorking:", "connectionError:", "responseError:",
                    "timeoutError:", "retry:"):
            self.assertEqual(self.locales.count(key), 5)


if __name__ == "__main__":
    unittest.main()
