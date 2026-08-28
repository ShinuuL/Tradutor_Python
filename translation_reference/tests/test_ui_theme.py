import sys
import os
import platform
import tkinter as tk
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from ui_theme import COLORS, RADII, SPACING, configure_fluent_night, contrast_ratio


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

    def test_panel_frame_has_no_inner_relief_or_border(self):
        if platform.system() != "Windows" and not os.environ.get("DISPLAY"):
            self.skipTest("Sem display disponivel")
        root = tk.Tk()
        self.addCleanup(root.destroy)
        style = configure_fluent_night(root)

        self.assertEqual(style.lookup("Panel.TFrame", "relief"), "flat")
        self.assertEqual(int(style.lookup("Panel.TFrame", "borderwidth")), 0)


if __name__ == "__main__":
    unittest.main()
