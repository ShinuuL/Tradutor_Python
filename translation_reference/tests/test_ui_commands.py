# -*- coding: utf-8 -*-
"""Caracterização dos comandos preservados pela migração da interface."""

import os
import platform
import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock
from tkinter import ttk


HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from text_scanner_app import (  # noqa: E402
    DEFAULT_ENGINE_MODEL,
    DEFAULT_ENGINE_URL,
    SCRIPT_PATH,
    TM_DIR,
    TRANSLATED_BASE,
    TRANSLATE_SCRIPT_PATH,
    TextScannerApp,
)
from ui_state import Stage, StageStatus  # noqa: E402


class UiCommandCharacterizationTests(unittest.TestCase):
    """The widget layout may move, but its CLI contract must not."""

    _CALLBACKS = (
        "choose_game_folder",
        "choose_output_file",
        "run_scan",
        "stop_scan",
        "choose_scan_jsonl",
        "run_translation",
        "stop_translation",
    )

    @classmethod
    def _has_display(cls):
        if platform.system() == "Windows":
            return True
        return os.environ.get("DISPLAY") is not None

    def setUp(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        self.callback_calls = []
        for callback_name in self._CALLBACKS:
            patcher = mock.patch.object(
                TextScannerApp,
                callback_name,
                self._record_callback(callback_name),
            )
            patcher.start()
            self.addCleanup(patcher.stop)
        try:
            self.app = TextScannerApp()
        except tk.TclError:
            self.skipTest("Probe Tcl/Tk indisponivel")

        self.game_dir = HERE / "fixtures" / "game"
        self.scan_jsonl = SCRIPT_PATH
        self.addCleanup(self.app.destroy)

    def _record_callback(self, callback_name):
        def callback(_app):
            self.callback_calls.append(callback_name)

        return callback

    @staticmethod
    def _descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from UiCommandCharacterizationTests._descendants(child)

    @staticmethod
    def _is_descendant_of(widget, ancestor):
        current = widget
        while True:
            if current is ancestor:
                return True
            parent_name = current.winfo_parent()
            if not parent_name:
                return False
            current = current.nametowidget(parent_name)

    @classmethod
    def _widget_variables(cls, widget):
        variables = set()
        keys = widget.keys()
        for option in ("textvariable", "variable"):
            if option in keys:
                value = str(widget.cget(option))
                if value:
                    variables.add(value)
        return variables

    @classmethod
    def _control_variables(cls, widget):
        return {
            variable
            for child in cls._descendants(widget)
            for variable in cls._widget_variables(child)
        }

    @classmethod
    def _buttons_with_text(cls, widget, text):
        return [
            child
            for child in cls._descendants(widget)
            if isinstance(child, ttk.Button) and child.cget("text") == text
        ]

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
        include_extensions = [
            command[index + 1]
            for index, item in enumerate(command)
            if item == "--include-ext"
        ]
        self.assertEqual(include_extensions, [".rpy", ".txt"])
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
        self.assertEqual(command[command.index("--out-dir") + 1], str(TRANSLATED_BASE / "game"))
        self.assertEqual(command[command.index("--engine-url") + 1], DEFAULT_ENGINE_URL)
        self.assertEqual(command[command.index("--engine-model") + 1], DEFAULT_ENGINE_MODEL)
        self.assertIn("--tm", command)
        self.assertEqual(command[command.index("--tm") + 1], str(TM_DIR / ("game.jsonl")))

    def test_advanced_sections_hold_required_controls_recursively(self):
        self.assertFalse(self.app.prepare_advanced.expanded)
        self.assertFalse(self.app.translate_advanced.expanded)
        prepare_variables = self._control_variables(self.app.prepare_advanced.content)
        translate_variables = self._control_variables(self.app.translate_advanced.content)
        prepare_visible_variables = {
            variable
            for widget in self._descendants(self.app.stage_frames[Stage.PREPARE].content)
            if not self._is_descendant_of(widget, self.app.prepare_advanced.content)
            for variable in self._widget_variables(widget)
        }
        translate_visible_variables = {
            variable
            for widget in self._descendants(self.app.stage_frames[Stage.TRANSLATE].content)
            if not self._is_descendant_of(widget, self.app.translate_advanced.content)
            for variable in self._widget_variables(widget)
        }

        prepare_advanced_variables = {
            str(self.app.extra_ext),
            str(self.app.max_file_mb),
            str(self.app.context_chars),
            str(self.app.batch_size),
            str(self.app.dedupe),
            str(self.app.skip_plugin_js),
        }
        self.assertTrue(prepare_advanced_variables.issubset(prepare_variables))
        self.assertTrue(prepare_advanced_variables.isdisjoint(prepare_visible_variables))
        self.assertIn(str(self.app.engine_url), translate_variables)
        self.assertNotIn(str(self.app.engine_model), translate_variables)
        self.assertNotIn(str(self.app.use_tm), translate_variables)
        self.assertNotIn(str(self.app.engine_url), translate_visible_variables)
        self.assertTrue({
            str(self.app.game_path),
            str(self.app.output_path),
        }.issubset(prepare_visible_variables))
        self.assertTrue({
            str(self.app.translate_jsonl),
            str(self.app.game_path),
            str(self.app.engine_model),
            str(self.app.use_tm),
            str(self.app.translate_status_text),
        }.issubset(translate_visible_variables))
        for control in (
            self.app.run_button,
            self.app.stop_button,
        ):
            self.assertFalse(self._is_descendant_of(control, self.app.prepare_advanced.content))
        for control in (
            self.app.translate_button,
            self.app.translate_stop_button,
            self.app.progress,
        ):
            self.assertFalse(self._is_descendant_of(control, self.app.translate_advanced.content))

    def test_visible_stage_controls_invoke_original_callback_slots(self):
        prepare = self.app.stage_frames[Stage.PREPARE].content
        translate = self.app.stage_frames[Stage.TRANSLATE].content

        self._buttons_with_text(prepare, "Escolher")[0].invoke()
        self._buttons_with_text(prepare, "Salvar como")[0].invoke()
        self.app.run_button.invoke()
        self.app.stop_button.configure(state="normal")
        self.app.stop_button.invoke()

        self.app.workflow.mark_scan_finished(success=True)
        self.app._refresh_stage_navigation()
        translate_selectors = self._buttons_with_text(translate, "Escolher")
        self.assertEqual(len(translate_selectors), 2)
        for selector in translate_selectors:
            selector.invoke()
        self.app.translate_button.invoke()
        self.app.translate_stop_button.configure(state="normal")
        self.app.translate_stop_button.invoke()

        self.assertEqual(
            self.callback_calls,
            [
                "choose_game_folder",
                "choose_output_file",
                "run_scan",
                "stop_scan",
                "choose_scan_jsonl",
                "choose_game_folder",
                "run_translation",
                "stop_translation",
            ],
        )


class WorkflowCallbackTests(unittest.TestCase):
    """Workflow feedback remains observable without launching real commands."""

    @classmethod
    def _has_display(cls):
        if platform.system() == "Windows":
            return True
        return os.environ.get("DISPLAY") is not None

    def setUp(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        self.messageboxes = mock.patch.multiple(
            "text_scanner_app.messagebox",
            showinfo=mock.DEFAULT,
            showwarning=mock.DEFAULT,
            showerror=mock.DEFAULT,
            askyesno=mock.DEFAULT,
        )
        self.messagebox_mocks = self.messageboxes.start()
        self.addCleanup(self.messageboxes.stop)
        self.subprocess_popen = mock.patch("text_scanner_app.subprocess.Popen").start()
        self.addCleanup(self.subprocess_popen.stop)
        try:
            self.app = TextScannerApp()
        except tk.TclError:
            self.skipTest("Probe Tcl/Tk indisponivel")
        self.addCleanup(self.app.destroy)

    def test_scan_success_recommends_translation_in_the_banner(self):
        self.app.output_path.set("scan-output")

        self.app._finish_run(0)

        self.assertTrue(self.app.workflow.can_open(Stage.TRANSLATE))
        self.assertEqual(self.app.recommended_stage, Stage.TRANSLATE)
        self.assertEqual(self.app.activity_banner.kind, "success")
        self.assertIn("Traduzir", self.app.activity_banner.detail_label.cget("text"))
        self.messagebox_mocks["showinfo"].assert_not_called()

    def test_translation_success_recommends_review_in_the_banner(self):
        self.app._progress_total = 1
        with (
            mock.patch.object(self.app, "_translated_dir", return_value=Path("translated-output")),
            mock.patch.object(Path, "is_file", return_value=True),
            mock.patch.object(self.app, "_populate_preview_tree"),
            mock.patch.object(self.app, "_refresh_apply_summary"),
            mock.patch.object(self.app, "_count_report_statuses", return_value={}),
        ):
            self.app._finish_translation(0, ["PROGRESS 1/1"])

        self.assertTrue(self.app.workflow.can_open(Stage.REVIEW))
        self.assertEqual(self.app.recommended_stage, Stage.REVIEW)
        self.assertEqual(self.app.activity_banner.kind, "success")
        self.assertIn("Revisar", self.app.activity_banner.detail_label.cget("text"))
        self.messagebox_mocks["showinfo"].assert_not_called()

    def test_retry_warning_keeps_apply_available(self):
        self.app.workflow.mark_scan_finished(success=True)
        self.app.workflow.mark_translation_finished(success=True, has_review=True)
        self.app.translated_dir = Path("translated-output")
        with (
            mock.patch.object(Path, "is_file", return_value=True),
            mock.patch.object(self.app, "_populate_preview_tree"),
            mock.patch.object(
                self.app,
                "_count_report_statuses",
                return_value={"needs_review": 1, "failed": 0},
            ),
        ):
            self.app._finish_retry(0, [])

        self.assertEqual(self.app.workflow.status(Stage.REVIEW).value, "warning")
        self.assertTrue(self.app.workflow.can_open(Stage.APPLY))
        self.assertEqual(self.app.activity_banner.kind, "warning")

    def test_apply_success_uses_banner_without_routine_dialog(self):
        self.app.workflow.mark_scan_finished(success=True)
        self.app.workflow.mark_translation_finished(success=True, has_review=True)
        self.app._preview_loaded = True

        self.app._finish_apply(0, ["Aplicados: 1"], Path("applied_manifest.json"))

        self.assertIs(self.app.workflow.status(Stage.APPLY), StageStatus.COMPLETE)
        self.assertEqual(self.app.activity_banner.kind, "success")
        self.messagebox_mocks["showinfo"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
