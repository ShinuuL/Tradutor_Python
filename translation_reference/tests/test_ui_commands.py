# -*- coding: utf-8 -*-
"""Caracterização dos comandos preservados pela migração da interface."""

import os
import platform
import sys
import tkinter as tk
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from text_scanner_app import (  # noqa: E402
    DEFAULT_ENGINE_MODEL,
    DEFAULT_ENGINE_URL,
    SCRIPT_PATH,
    TM_DIR,
    TRANSLATE_SCRIPT_PATH,
    TextScannerApp,
)


class UiCommandCharacterizationTests(unittest.TestCase):
    """The widget layout may move, but its CLI contract must not."""

    @classmethod
    def _has_display(cls):
        if platform.system() == "Windows":
            return True
        return os.environ.get("DISPLAY") is not None

    def setUp(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        try:
            self.app = TextScannerApp()
        except tk.TclError:
            self.skipTest("Probe Tcl/Tk indisponivel")

        self.game_dir = HERE / "fixtures" / "game"
        self.scan_jsonl = SCRIPT_PATH
        self.addCleanup(self.app.destroy)

    def test_scan_command_preserves_executable_paths_and_enabled_flags(self):
        self.app.game_path.set(str(self.game_dir))
        self.app.output_path.set(str(HERE / "fixtures" / "scan_report"))
        self.app.extra_ext.set(".rpy, txt")
        self.app.max_file_mb.set(40)
        self.app.context_chars.set(240)
        self.app.batch_size.set(750)
        self.app.dedupe.set(True)
        self.app.skip_plugin_js.set(True)

        command = self.app.build_command()

        self.assertEqual(command[:2], [sys.executable, str(SCRIPT_PATH)])
        self.assertEqual(command[2], str(self.game_dir))
        self.assertEqual(command[command.index("--out") + 1], str(HERE / "fixtures" / "scan_report"))
        self.assertEqual(command[command.index("--max-file-mb") + 1], "40")
        self.assertEqual(command[command.index("--context") + 1], "240")
        self.assertEqual(command[command.index("--batch-size") + 1], "750")
        self.assertEqual(command.count("--include-ext"), 2)
        self.assertIn("--dedupe", command)
        self.assertIn("--skip-plugin-js", command)

    def test_translation_command_preserves_engine_model_and_memory(self):
        self.app.game_path.set(str(self.game_dir))
        self.app.translate_jsonl.set(str(self.scan_jsonl))
        self.app.engine_url.set(DEFAULT_ENGINE_URL)
        self.app.engine_model.set(DEFAULT_ENGINE_MODEL)
        self.app.use_tm.set(True)

        command = self.app.build_translation_command()

        self.assertEqual(command[:2], [sys.executable, str(TRANSLATE_SCRIPT_PATH)])
        self.assertEqual(command[2], str(self.scan_jsonl))
        self.assertEqual(command[command.index("--engine-url") + 1], DEFAULT_ENGINE_URL)
        self.assertEqual(command[command.index("--engine-model") + 1], DEFAULT_ENGINE_MODEL)
        self.assertIn("--tm", command)
        self.assertEqual(command[command.index("--tm") + 1], str(TM_DIR / ("game.jsonl")))

    def test_advanced_sections_hold_only_the_less_used_controls(self):
        self.assertFalse(self.app.prepare_advanced.expanded)
        self.assertFalse(self.app.translate_advanced.expanded)
        prepare_variables = {
            str(widget.cget("textvariable"))
            for widget in self.app.prepare_advanced.content.winfo_children()
            if "textvariable" in widget.keys()
        }
        translate_variables = {
            str(widget.cget("textvariable"))
            for widget in self.app.translate_advanced.content.winfo_children()
            if "textvariable" in widget.keys()
        }

        self.assertIn(str(self.app.extra_ext), prepare_variables)
        self.assertIn(str(self.app.engine_url), translate_variables)
        self.assertTrue(self.app.translate_button.winfo_exists())
        self.assertTrue(self.app.translate_stop_button.winfo_exists())
        self.assertTrue(self.app.progress.winfo_exists())


if __name__ == "__main__":
    unittest.main()
