# -*- coding: utf-8 -*-
"""Caracterização dos comandos preservados pela migração da interface."""

import os
import platform
import sys
import tempfile
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
    MANIFEST_NAME,
    REPORT_CSV_NAME,
    SCRIPT_PATH,
    TM_DIR,
    TRANSLATED_BASE,
    TRANSLATE_SCRIPT_PATH,
    TextScannerApp,
    build_worker_command,
)
from ui_state import Stage, StageStatus  # noqa: E402


class _Value:
    """Minimal ``tk.Variable`` substitute for command construction tests."""

    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FrozenWorkerCommandTests(unittest.TestCase):
    """Frozen GUI commands must target their sibling CLI executables."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(self.temporary.cleanup)
        self.dist = Path(self.temporary.name) / "dist"
        self.gui_executable = self.dist / "TradutorDGames" / "TradutorDGames.exe"
        self.gui_executable.parent.mkdir(parents=True)
        self.gui_executable.write_bytes(b"gui")
        for worker in ("extract_non_english_text", "translate_game_text"):
            executable = self.dist / worker / (worker + ".exe")
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"worker")

    def _frozen_python(self):
        return mock.patch.multiple(
            sys,
            frozen=True,
            executable=str(self.gui_executable),
            create=True,
        )

    def _command_app(self):
        app = TextScannerApp.__new__(TextScannerApp)
        app.game_path = _Value(str(HERE / "fixtures" / "game"))
        app.output_path = _Value(str(HERE / "fixtures" / "frozen_scan"))
        app.extra_ext = _Value("")
        app.max_file_mb = _Value(25)
        app.context_chars = _Value(180)
        app.batch_size = _Value(500)
        app.dedupe = _Value(True)
        app.skip_plugin_js = _Value(True)
        app.translate_jsonl = _Value(str(SCRIPT_PATH))
        app.engine_url = _Value(DEFAULT_ENGINE_URL)
        app.engine_model = _Value(DEFAULT_ENGINE_MODEL)
        app.use_tm = _Value(False)
        return app

    def test_frozen_scan_and_translation_commands_use_sibling_workers(self):
        app = self._command_app()
        with self._frozen_python():
            scan = app.build_command()
            translation = app.build_translation_command()

        self.assertEqual(
            scan[0],
            str(self.dist / "extract_non_english_text" / "extract_non_english_text.exe"),
        )
        self.assertEqual(
            translation[0],
            str(self.dist / "translate_game_text" / "translate_game_text.exe"),
        )
        self.assertNotIn(str(self.gui_executable), scan)
        self.assertNotIn(str(self.gui_executable), translation)

    def test_frozen_worker_command_fails_actionably_when_worker_is_missing(self):
        missing = self.dist / "extract_non_english_text" / "extract_non_english_text.exe"
        missing.unlink()

        with self._frozen_python():
            with self.assertRaisesRegex(ValueError, "extract_non_english_text"):
                build_worker_command("extract_non_english_text", SCRIPT_PATH)

    def test_scan_and_translation_do_not_start_popen_when_frozen_worker_is_missing(self):
        for worker in ("extract_non_english_text", "translate_game_text"):
            (self.dist / worker / (worker + ".exe")).unlink()
        app = self._command_app()
        app._panel_busy = lambda: False

        with (
            self._frozen_python(),
            mock.patch("text_scanner_app.messagebox.showwarning") as warning,
            mock.patch("text_scanner_app.subprocess.Popen") as popen,
        ):
            app.run_scan()
            app.run_translation()

        self.assertEqual(warning.call_count, 2)
        popen.assert_not_called()

    def test_frozen_apply_retry_and_restore_use_translation_worker(self):
        worker = str(self.dist / "translate_game_text" / "translate_game_text.exe")
        game_root = HERE / "fixtures" / "game"
        translated = Path(self.temporary.name) / "translated"
        translated.mkdir()
        (translated / "translated.txt").write_text("translated", encoding="utf-8")
        (translated / REPORT_CSV_NAME).write_text(
            "status,file,line,source,translated\nfailed,a.txt,1,a,b\n",
            encoding="utf-8",
        )
        manifest = translated / MANIFEST_NAME
        manifest.write_text('{"entries": [{"file": "a.txt"}]}', encoding="utf-8")
        commands = []

        app = self._command_app()
        app.translated_dir = translated
        app._panel_busy = lambda: False
        app._translated_dir = lambda: translated
        app._count_translated_files = lambda _directory: 1
        app._find_latest_manifest = lambda: manifest
        app._manifest_entry_count = lambda _manifest: 1
        app.append_log = lambda _message: None
        app._set_stage_feedback = lambda *_args: None
        app._start_panel_command = lambda command, *_args, **_kwargs: commands.append(command)
        app.workflow = mock.Mock()
        app.recommended_stage = None

        with (
            self._frozen_python(),
            mock.patch("text_scanner_app.messagebox.showinfo"),
            mock.patch("text_scanner_app.messagebox.showwarning"),
            mock.patch("text_scanner_app.messagebox.askyesno", return_value=True),
        ):
            app.run_apply()
            app._run_retry()
            app.run_restore()

        self.assertEqual(len(commands), 3)
        self.assertTrue(all(command[0] == worker for command in commands))
        self.assertEqual(commands[0][1], "apply")
        self.assertEqual(commands[1][1], "retry")
        self.assertEqual(commands[2][1], "restore")


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
        try:
            self.app = TextScannerApp()
        except tk.TclError:
            self.skipTest("Probe Tcl/Tk indisponivel")
        self.addCleanup(self.app.destroy)

    def _review_directory(self):
        temporary = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        (directory / REPORT_CSV_NAME).write_text(
            "status,file,line,source,translated\nllm,a.txt,1,original,translated\n",
            encoding="utf-8",
        )
        return directory

    def _make_panel_actions_available(self):
        self.app.workflow.mark_scan_finished(success=True)
        self.app.workflow.mark_translation_finished(success=True, has_review=True)
        self.app._preview_loaded = True
        self.app._retry_available = True

    def test_scan_success_recommends_translation_in_the_banner(self):
        output = self._review_directory() / "scan-output"
        output.with_suffix(".jsonl").write_text("{}\n", encoding="utf-8")
        self.app.output_path.set(str(output))

        with mock.patch("text_scanner_app.messagebox.showinfo") as showinfo:
            self.app._finish_run(0)

        self.assertTrue(self.app.workflow.can_open(Stage.TRANSLATE))
        self.assertEqual(self.app.recommended_stage, Stage.TRANSLATE)
        self.assertEqual(self.app.activity_banner.kind, "success")
        self.assertIn("Traduzir", self.app.activity_banner.detail_label.cget("text"))
        showinfo.assert_not_called()

    def test_scan_exit_zero_without_jsonl_keeps_translation_locked(self):
        self.app.output_path.set("missing-scan-output")

        self.app._finish_run(0)

        self.assertIs(self.app.workflow.status(Stage.PREPARE), StageStatus.ERROR)
        self.assertIs(self.app.workflow.status(Stage.TRANSLATE), StageStatus.LOCKED)
        self.assertIsNone(self.app.recommended_stage)
        self.assertEqual(self.app.activity_banner.kind, "error")

    def test_failed_scan_clears_a_stale_translation_recommendation(self):
        self.app.recommended_stage = Stage.TRANSLATE
        self.app.output_path.set("missing-scan-output")

        self.app._finish_run(1)

        self.assertIsNone(self.app.recommended_stage)

    def test_translation_success_recommends_review_in_the_banner(self):
        review_dir = self._review_directory()
        self.app._progress_total = 1
        with (
            mock.patch.object(self.app, "_translated_dir", return_value=review_dir),
            mock.patch.object(self.app, "_populate_preview_tree"),
            mock.patch.object(self.app, "_refresh_apply_summary"),
            mock.patch.object(self.app, "_count_report_statuses", return_value={}),
            mock.patch("text_scanner_app.messagebox.showinfo") as showinfo,
        ):
            self.app._finish_translation(0, ["PROGRESS 1/1"])

        self.assertTrue(self.app.workflow.can_open(Stage.REVIEW))
        self.assertEqual(self.app.recommended_stage, Stage.REVIEW)
        self.assertEqual(self.app.activity_banner.kind, "success")
        self.assertIn("Revisar", self.app.activity_banner.detail_label.cget("text"))
        showinfo.assert_not_called()

    def test_retry_warning_keeps_apply_available(self):
        review_dir = self._review_directory()
        self._make_panel_actions_available()
        self.app.translated_dir = review_dir
        with (
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

    def test_scan_running_disables_all_panel_starts_but_not_their_stop(self):
        self._make_panel_actions_available()
        self.app.workflow.mark_scan_started()

        self.app._refresh_stage_navigation()

        self.assertEqual(str(self.app.stop_button.cget("state")), "normal")
        self.assertEqual(str(self.app.translate_stop_button.cget("state")), "disabled")
        for button in (
            self.app.translate_button,
            self.app.retry_button,
            self.app.apply_button,
            self.app.restore_button,
        ):
            self.assertEqual(str(button.cget("state")), "disabled")

    def test_panel_command_disables_scan_start_and_keeps_only_its_stop(self):
        self._make_panel_actions_available()
        self.app._panel_command_running = True
        self.app._panel_command_with_progress = True

        self.app._refresh_stage_navigation()

        self.assertEqual(str(self.app.run_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.stop_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.translate_stop_button.cget("state")), "normal")
        for button in (
            self.app.translate_button,
            self.app.retry_button,
            self.app.apply_button,
            self.app.restore_button,
        ):
            self.assertEqual(str(button.cget("state")), "disabled")

    def test_retry_failure_after_start_preserves_preview_and_apply(self):
        self._make_panel_actions_available()
        review_dir = self._review_directory()
        (review_dir / REPORT_CSV_NAME).write_text(
            "status,file,line,source,translated\nfailed,a.txt,1,original,translated\n",
            encoding="utf-8",
        )
        self.app.translate_jsonl.set(str(SCRIPT_PATH))
        self.app.translated_dir = review_dir
        self.app._start_panel_command = mock.Mock()

        self.app._run_retry()

        self.app._finish_retry(1, [])

        self.assertTrue(self.app._preview_loaded)
        self.assertTrue(self.app.workflow.can_open(Stage.APPLY))
        self.assertIs(self.app.workflow.status(Stage.REVIEW), StageStatus.ERROR)

    def test_apply_start_and_warning_status_are_visible(self):
        self._make_panel_actions_available()
        self.app.game_path.set(str(HERE / "fixtures" / "game"))
        self.app.translated_dir = HERE / "fixtures" / "game"
        self.app._count_translated_files = mock.Mock(return_value=1)
        self.app._start_panel_command = mock.Mock()
        with (
            mock.patch("text_scanner_app.messagebox.showinfo"),
            mock.patch("text_scanner_app.messagebox.askyesno", return_value=True),
            mock.patch("text_scanner_app.messagebox.showwarning"),
        ):
            self.app.run_apply()

            self.assertIs(self.app.workflow.status(Stage.APPLY), StageStatus.RUNNING)
            self.assertTrue(self.app._preview_loaded)
            self.app._finish_apply(0, ["Aplicados: 0"], Path("applied_manifest.json"))
        self.assertIs(self.app.workflow.status(Stage.APPLY), StageStatus.WARNING)

    def test_restore_success_uses_banner_without_routine_dialog(self):
        with mock.patch("text_scanner_app.messagebox.showinfo") as showinfo:
            self.app._finish_restore(0, ["Restaurados: 1"], Path("applied_manifest.json"))

        self.assertEqual(self.app.activity_banner.kind, "success")
        showinfo.assert_not_called()

    def test_apply_success_uses_banner_without_routine_dialog(self):
        self.app.workflow.mark_scan_finished(success=True)
        self.app.workflow.mark_translation_finished(success=True, has_review=True)
        self.app._preview_loaded = True

        with mock.patch("text_scanner_app.messagebox.showinfo") as showinfo:
            self.app._finish_apply(0, ["Aplicados: 1"], Path("applied_manifest.json"))

        self.assertIs(self.app.workflow.status(Stage.APPLY), StageStatus.COMPLETE)
        self.assertEqual(self.app.activity_banner.kind, "success")
        showinfo.assert_not_called()

    def test_apply_without_approval_warns_without_showing_success_dialog(self):
        self._make_panel_actions_available()
        with (
            mock.patch("text_scanner_app.messagebox.showwarning") as showwarning,
            mock.patch("text_scanner_app.messagebox.showinfo") as showinfo,
        ):
            self.app._finish_apply(3, [], Path("applied_manifest.json"))

        self.assertIs(self.app.workflow.status(Stage.APPLY), StageStatus.WARNING)
        self.assertEqual(self.app.activity_banner.kind, "warning")
        showwarning.assert_called_once()
        showinfo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
