import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from ui_theme import COLORS, RADII, SPACING, contrast_ratio


class ThemeTokenTests(unittest.TestCase):
    def test_design_tokens_match_approved_spec(self):
        self.assertEqual(COLORS["window"], "#0B111B")
        self.assertEqual(COLORS["accent"], "#66D4FF")
        self.assertEqual(COLORS["text"], "#EAF4FC")
        self.assertEqual(SPACING["panel"] % 4, 0)
        self.assertIn(RADII["panel"], range(12, 17))

    def test_primary_text_contrast_is_wcag_aa(self):
        self.assertGreaterEqual(contrast_ratio(COLORS["text"], COLORS["window"]), 4.5)
        self.assertGreaterEqual(contrast_ratio(COLORS["text"], COLORS["panel"]), 4.5)


if __name__ == "__main__":
    unittest.main()
