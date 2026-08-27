# -*- coding: utf-8 -*-
"""Testes offline das helpers puras do painel Traduzir (B3).

Cobertura:
- load_preview_rows: le CSV utf-8-sig, limita a 500 linhas, trata erro;
- filter_preview_rows: filtra por status ou retorna todas ("todos");
- count_report_statuses: conta ocorrencias por status;
- estimate_eta: estima ETA a partir de amostras de progresso.

Funcoes puras de modulo: nao instancia Tk nem abre janela.
"""
import csv
import os
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest import mock
from pathlib import Path
from tkinter import ttk

HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from text_scanner_app import (  # noqa: E402
    count_report_statuses,
    estimate_eta,
    filter_preview_rows,
    load_preview_rows,
)
from ui_state import Stage  # noqa: E402


class GlobalWheelBindingTests(unittest.TestCase):
    def test_ui_sources_do_not_register_or_remove_global_wheel_bindings(self):
        """Wheel handling must remain scoped to the widget receiving input."""
        for source_name in ("text_scanner_app.py", "ui_components.py"):
            source = (APP_DIR / source_name).read_text(encoding="utf-8")
            self.assertNotIn("bind_all", source)
            self.assertNotIn("unbind_all", source)


def _write_csv(path, rows, fieldnames=None):
    """Escreve um CSV de teste no caminho indicado."""
    if fieldnames is None:
        fieldnames = ["item_id", "status", "file", "line", "source", "translated"]
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class LoadPreviewRowsTests(unittest.TestCase):
    def test_reads_rows_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "report.csv"
            _write_csv(csv_path, [
                {"item_id": "1", "status": "tm_hit", "file": "a.txt", "line": "1", "source": "ola", "translated": "hello"},
                {"item_id": "2", "status": "llm", "file": "b.txt", "line": "2", "source": "mundo", "translated": "world"},
            ])
            rows = load_preview_rows(csv_path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["status"], "tm_hit")
            self.assertEqual(rows[1]["translated"], "world")

    def test_respects_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "report.csv"
            rows_data = [
                {"item_id": str(i), "status": "llm", "file": "f.txt", "line": str(i), "source": "s", "translated": "t"}
                for i in range(10)
            ]
            _write_csv(csv_path, rows_data)
            rows = load_preview_rows(csv_path, limit=3)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[2]["item_id"], "2")

    def test_returns_empty_for_missing_file(self):
        rows = load_preview_rows(Path("/nao/existe/report.csv"))
        self.assertEqual(rows, [])

    def test_returns_empty_for_empty_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "empty.csv"
            csv_path.write_text("item_id,status,file,line,source,translated\n", encoding="utf-8-sig")
            rows = load_preview_rows(csv_path)
            self.assertEqual(rows, [])

    def test_handles_bom_utf8sig(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bom.csv"
            content = "\ufeffitem_id,status,file,line,source,translated\n1,tm_hit,a.txt,1,ola,hello\n"
            csv_path.write_text(content, encoding="utf-8")
            rows = load_preview_rows(csv_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "ola")


class FilterPreviewRowsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"status": "tm_hit", "source": "a"},
            {"status": "llm", "source": "b"},
            {"status": "needs_review", "source": "c"},
            {"status": "failed", "source": "d"},
            {"status": "tm_hit", "source": "e"},
        ]

    def test_todos_returns_all(self):
        result = filter_preview_rows(self.rows, "todos")
        self.assertEqual(len(result), 5)

    def test_empty_string_returns_all(self):
        result = filter_preview_rows(self.rows, "")
        self.assertEqual(len(result), 5)

    def test_none_returns_all(self):
        result = filter_preview_rows(self.rows, None)
        self.assertEqual(len(result), 5)

    def test_filters_by_status(self):
        result = filter_preview_rows(self.rows, "tm_hit")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r["status"] == "tm_hit" for r in result))

    def test_filters_case_insensitive(self):
        result = filter_preview_rows(self.rows, "LLM")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "llm")

    def test_empty_list_returns_empty(self):
        result = filter_preview_rows([], "tm_hit")
        self.assertEqual(result, [])

    def test_no_match_returns_empty(self):
        result = filter_preview_rows(self.rows, "success")
        self.assertEqual(result, [])


class CountReportStatusesTests(unittest.TestCase):
    def test_counts_each_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "report.csv"
            _write_csv(csv_path, [
                {"item_id": "1", "status": "tm_hit", "file": "a.txt", "line": "1", "source": "x", "translated": "y"},
                {"item_id": "2", "status": "llm", "file": "b.txt", "line": "2", "source": "x", "translated": "y"},
                {"item_id": "3", "status": "tm_hit", "file": "c.txt", "line": "3", "source": "x", "translated": "y"},
                {"item_id": "4", "status": "failed", "file": "d.txt", "line": "4", "source": "x", "translated": "y"},
            ])
            counts = count_report_statuses(csv_path)
            self.assertEqual(counts["tm_hit"], 2)
            self.assertEqual(counts["llm"], 1)
            self.assertEqual(counts["failed"], 1)

    def test_returns_empty_dict_for_missing_file(self):
        counts = count_report_statuses(Path("/nao/existe.csv"))
        self.assertEqual(counts, {})

    def test_handles_empty_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "empty.csv"
            csv_path.write_text("item_id,status,file,line,source,translated\n", encoding="utf-8-sig")
            counts = count_report_statuses(csv_path)
            self.assertEqual(counts, {})


class EstimateEtaTests(unittest.TestCase):
    def test_empty_string_when_less_than_two_samples(self):
        t = time.time()
        self.assertEqual(estimate_eta([(t, 10)], 10, 100), "")
        self.assertEqual(estimate_eta([], 10, 100), "")

    def test_empty_string_when_done_ge_total(self):
        t = time.time()
        history = [(t - 1, 50), (t, 100)]
        self.assertEqual(estimate_eta(history, 100, 100), "")
        self.assertEqual(estimate_eta(history, 110, 100), "")

    def test_empty_string_when_done_le_zero(self):
        t = time.time()
        history = [(t - 1, 0), (t, 0)]
        self.assertEqual(estimate_eta(history, 0, 100), "")

    def test_empty_string_when_total_le_zero(self):
        t = time.time()
        history = [(t - 1, 5), (t, 10)]
        self.assertEqual(estimate_eta(history, 10, 0), "")

    def test_returns_eta_string_with_valid_samples(self):
        t = time.time()
        # 10 done in 10 seconds => rate 1/s, 90 remaining => 90s = 01:30
        history = [(t - 10, 10), (t, 20)]
        result = estimate_eta(history, 20, 100)
        self.assertEqual(result, "ETA 01:20")

    def test_formats_as_mm_ss(self):
        t = time.time()
        # 1 done in 1s => rate 1/s, 59 remaining => 59s = 00:59
        history = [(t - 1, 1), (t, 2)]
        result = estimate_eta(history, 2, 61)
        self.assertEqual(result, "ETA 00:59")

    def test_empty_string_when_dt_zero(self):
        history = [(100.0, 10), (100.0, 20)]
        self.assertEqual(estimate_eta(history, 20, 100), "")

    def test_empty_string_when_dd_zero(self):
        t = time.time()
        history = [(t - 1, 10), (t, 10)]
        self.assertEqual(estimate_eta(history, 10, 100), "")

    def test_uses_last_two_samples(self):
        t = time.time()
        history = [(t - 20, 0), (t - 10, 10), (t, 20)]
        # Last two: (t-10, 10) to (t, 20) => 10 in 10s => 1/s
        # remaining = 80 => 80s = 01:20
        result = estimate_eta(history, 20, 100)
        self.assertEqual(result, "ETA 01:20")


class RunTranslationSummaryTests(unittest.TestCase):
    def test_run_translation_clears_stale_apply_summary_before_starting(self):
        from text_scanner_app import TextScannerApp
        from ui_state import Stage, StageStatus, WorkflowState

        class Value:
            def __init__(self, value=""):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        app = TextScannerApp.__new__(TextScannerApp)
        app.game_path = Value("C:/jogos/exemplo")
        app.apply_summary = Value()
        previous_dir = mock.MagicMock()
        previous_dir.is_dir.return_value = True
        previous_dir.__str__.return_value = "C:/relatorios/anterior"
        app.translated_dir = previous_dir
        app._count_translated_files = mock.Mock(return_value=8)
        app._refresh_apply_summary = TextScannerApp._refresh_apply_summary.__get__(app)
        app._refresh_apply_summary()
        self.assertIn("Arquivos traduzidos: 8.", app.apply_summary.get())

        app.translate_process = None
        app.workflow = WorkflowState()
        app._refresh_stage_navigation = mock.Mock()
        app._set_stage_feedback = mock.Mock()
        app.build_translation_command = mock.Mock(return_value=["translate"])
        app.append_log = mock.Mock()
        app._start_panel_command = mock.Mock()
        TextScannerApp.run_translation(app)

        self.assertIsNone(app.translated_dir)
        self.assertIs(app.workflow.status(Stage.TRANSLATE), StageStatus.RUNNING)
        self.assertEqual(
            app.apply_summary.get(),
            "Destino: C:/jogos/exemplo\n"
            "Origem: nenhuma tradução concluída.\n"
            "Arquivos traduzidos: 0.",
        )
        app._start_panel_command.assert_called_once()


class GuiSmokeTests(unittest.TestCase):
    """Smoke tests da GUI: instanciar, rodar mainloop curto, destruir.

    Pula automaticamente se nao houver display disponivel (CI/headless).
    """

    @classmethod
    def _has_display(cls):
        import platform
        if platform.system() == "Windows":
            return True
        return os.environ.get("DISPLAY") is not None

    def _create_app_or_skip(self):
        from text_scanner_app import TextScannerApp
        try:
            return TextScannerApp()
        except tk.TclError:
            self.skipTest("Probe Tcl/Tk indisponivel")

    @staticmethod
    def _descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from GuiSmokeTests._descendants(child)

    def _first_widget(self, root, widget_type):
        return next(widget for widget in self._descendants(root) if isinstance(widget, widget_type))

    def _assert_within_app(self, app, widget):
        self.assertTrue(widget.winfo_ismapped(), widget)
        self.assertGreaterEqual(widget.winfo_rootx(), app.winfo_rootx(), widget)
        self.assertGreaterEqual(widget.winfo_rooty(), app.winfo_rooty(), widget)
        self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), app.winfo_rootx() + app.winfo_width(), widget)
        self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), app.winfo_rooty() + app.winfo_height(), widget)

    def test_app_creates_and_destroys(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.after(1500, app.destroy)
        app.mainloop()
        # Se chegou aqui sem excecao, o smoke passou

    def test_staged_shell_exists_without_global_scroll_canvas(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        from ui_state import Stage
        app = self._create_app_or_skip()
        self.assertFalse(hasattr(app, "_canvas"))
        self.assertEqual(set(app.stage_frames), set(Stage))
        self.assertEqual(app.active_stage, Stage.PREPARE)
        app.destroy()

    def test_stage_navigation_button_blocks_locked_stage_until_workflow_unlocks_it(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        from ui_state import Stage
        app = self._create_app_or_skip()
        app.update()
        app.stage_navigation.labels[Stage.TRANSLATE].event_generate("<Button-1>")
        app.update()
        self.assertEqual(app.active_stage, Stage.PREPARE)
        self.assertEqual(app.activity_banner.title_label.cget("text"), "Etapa ainda não disponível")
        self.assertEqual(app.activity_banner.detail_label.cget("text"), "Conclua uma varredura para continuar.")
        app.workflow.mark_scan_finished(True)
        app._refresh_stage_navigation()
        app.stage_navigation.labels[Stage.TRANSLATE].event_generate("<Button-1>")
        app.update()
        self.assertEqual(app.active_stage, Stage.TRANSLATE)
        app.destroy()

    def test_stage_navigation_uses_vertical_rows_in_the_shell(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        from ui_state import Stage
        app = self._create_app_or_skip()
        app.update()
        prepare = app.stage_navigation.rows[Stage.PREPARE]
        translate = app.stage_navigation.rows[Stage.TRANSLATE]
        self.assertEqual(prepare.winfo_x(), translate.winfo_x())
        self.assertGreater(translate.winfo_y(), prepare.winfo_y())
        app.destroy()

    def test_review_treeview_wheel_moves_only_the_treeview(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.workflow.mark_scan_finished(True)
        app.workflow.mark_translation_finished(True, True)
        app._refresh_stage_navigation()
        app.show_stage(Stage.REVIEW)
        for number in range(80):
            app._preview_tree.insert("", "end", values=("llm", f"arquivo-{number}.txt", number, "origem", "tradução"))
        app.update()
        app._preview_tree.yview_moveto(0)
        review_before = app.stage_frames[Stage.REVIEW].canvas.yview()[0]
        tree_before = app._preview_tree.yview()[0]

        app._preview_tree.event_generate("<MouseWheel>", delta=-120)
        app.update()

        self.assertGreater(app._preview_tree.yview()[0], tree_before)
        self.assertEqual(app.stage_frames[Stage.REVIEW].canvas.yview()[0], review_before)
        app.destroy()

    def test_stages_reflow_critical_content_inside_a_900_by_650_window(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.geometry("900x650")
        app.workflow.mark_scan_finished(True)
        app.workflow.mark_translation_finished(True, True)
        app._refresh_stage_navigation()
        critical = {
            Stage.PREPARE: app.run_button,
            Stage.TRANSLATE: app.translate_button,
            Stage.REVIEW: app.retry_button,
            Stage.APPLY: app.apply_button,
        }
        for stage, action in critical.items():
            self.assertTrue(app.show_stage(stage))
            app.update_idletasks()
            app.update()
            self._assert_within_app(app, app.stage_frames[stage])
            self._assert_within_app(app, action)
        app.destroy()

    def test_navigation_fields_and_primary_actions_are_focusable_but_step_canvas_is_not(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.update()
        app.focus_force()
        app.update()
        navigation = app.stage_navigation.labels[Stage.PREPARE]
        first_field = self._first_widget(app.stage_frames[Stage.PREPARE].content, ttk.Entry)

        for widget in (navigation, first_field, app.run_button):
            widget.focus_set()
            app.update()
            self.assertIs(app.focus_get(), widget)
        self.assertTrue(bool(navigation.cget("takefocus")))
        self.assertEqual(app.stage_frames[Stage.PREPARE].canvas.cget("takefocus"), "0")
        app.destroy()

    def test_focused_navigation_label_opens_an_available_stage_on_return(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.workflow.mark_scan_finished(True)
        app._refresh_stage_navigation()
        navigation = app.stage_navigation.labels[Stage.TRANSLATE]
        app.update()
        app.focus_force()
        navigation.focus_set()
        app.update()

        navigation.event_generate("<Return>")
        app.update()

        self.assertEqual(app.active_stage, Stage.TRANSLATE)
        app.destroy()

    def test_full_log_keeps_wheel_and_focus_local_to_its_text_widget(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        for number in range(100):
            app.append_log(f"registro {number}")
        app.open_full_log()
        app.update()
        app._log_window.focus_force()
        app.update()
        app.log.yview_moveto(0)
        before = app.log.yview()[0]
        app.log.focus_set()
        app.log.event_generate("<MouseWheel>", delta=-120)
        app.update()

        self.assertIs(app.focus_get(), app.log)
        self.assertGreater(app.log.yview()[0], before)
        app.destroy()

    def test_functional_controls_survive_remodel(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        expected = (
            "retry_button", "apply_button", "restore_button", "_preview_tree",
            "_filter_combo", "log", "open_csv_button", "open_jsonl_button",
            "apply_summary",
        )
        for name in expected:
            self.assertTrue(hasattr(app, name), name)
        self.assertEqual(
            tuple(app._preview_tree.cget("columns")),
            ("status", "file", "line", "source", "translated"),
        )
        self.assertTrue(app._filter_combo.bind("<<ComboboxSelected>>"))
        self.assertIsInstance(app.apply_summary, tk.StringVar)
        app.destroy()

    def test_activity_actions_are_visible_initially_and_invoke_callbacks(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        from text_scanner_app import TextScannerApp
        with mock.patch.object(TextScannerApp, "open_full_log") as open_full_log, mock.patch.object(
            TextScannerApp, "clear_log"
        ) as clear_log:
            app = self._create_app_or_skip()
            app.update()
            self.assertTrue(app._activity_actions.winfo_ismapped())
            self.assertTrue(app.open_full_log_button.winfo_ismapped())
            self.assertTrue(app.clear_log_button.winfo_ismapped())
            self.assertIs(app.open_full_log_button.master, app._activity_actions)
            self.assertIs(app.clear_log_button.master, app._activity_actions)

            def is_descendant(widget, ancestor):
                while widget is not ancestor and getattr(widget, "master", None) is not None:
                    widget = widget.master
                return widget is ancestor

            for report_button in (app.open_csv_button, app.open_jsonl_button, app.open_summary_button):
                self.assertTrue(is_descendant(report_button, app.stage_frames[Stage.REVIEW].content))

            app.workflow.mark_scan_finished(True)
            app.workflow.mark_translation_finished(True, True)
            app._refresh_stage_navigation()
            for stage in Stage:
                self.assertTrue(app.show_stage(stage))
                app.update()
                self.assertTrue(app._activity_actions.winfo_ismapped(), stage)
                self.assertTrue(app.open_full_log_button.winfo_ismapped(), stage)
                self.assertTrue(app.clear_log_button.winfo_ismapped(), stage)

            app.open_full_log_button.invoke()
            app.clear_log_button.invoke()
        open_full_log.assert_called_once_with()
        clear_log.assert_called_once_with()
        app.destroy()

    def test_apply_summary_has_safe_placeholders_and_real_translation_details(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        self.assertEqual(
            app.apply_summary.get(),
            "Destino: nenhuma pasta do jogo selecionada.\n"
            "Origem: nenhuma tradução concluída.\n"
            "Arquivos traduzidos: 0.",
        )
        app.game_path.set("C:/jogos/exemplo")
        translated_dir = mock.MagicMock()
        translated_dir.is_dir.return_value = True
        translated_dir.__str__.return_value = "C:/relatorios/exemplo"
        app.translated_dir = translated_dir
        with mock.patch.object(app, "_count_translated_files", return_value=3) as count_files:
            app._refresh_apply_summary()
        count_files.assert_called_once_with(translated_dir)
        self.assertEqual(
            app.apply_summary.get(),
            "Destino: C:/jogos/exemplo\n"
            "Origem: C:/relatorios/exemplo\n"
            "Arquivos traduzidos: 3.",
        )
        app.destroy()

    def test_apply_summary_refreshes_after_folder_selection_and_translation_success(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        with mock.patch("text_scanner_app.filedialog.askdirectory", return_value="C:/jogos/exemplo"):
            app.choose_game_folder()
        self.assertIn("Destino: C:/jogos/exemplo", app.apply_summary.get())

        translated_dir = mock.MagicMock()
        translated_dir.is_dir.return_value = True
        translated_dir.__str__.return_value = "C:/relatorios/exemplo"
        translated_dir.__truediv__.return_value = translated_dir
        with mock.patch.object(app, "_translated_dir", return_value=translated_dir), mock.patch.object(
            app, "_count_translated_files", return_value=4
        ) as count_files, mock.patch.object(app, "_populate_preview_tree"), mock.patch.object(
            app, "_count_report_statuses", return_value={}
        ), mock.patch("text_scanner_app.messagebox.showinfo"):
            app._finish_translation(0, [])
        self.assertEqual(
            app.apply_summary.get(),
            "Destino: C:/jogos/exemplo\n"
            "Origem: C:/relatorios/exemplo\n"
            "Arquivos traduzidos: 4.",
        )
        count_files.assert_called_once_with(translated_dir)
        app.destroy()

    def test_run_translation_clears_stale_apply_summary_before_starting(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.game_path.set("C:/jogos/exemplo")
        previous_dir = mock.MagicMock()
        previous_dir.is_dir.return_value = True
        previous_dir.__str__.return_value = "C:/relatorios/anterior"
        app.translated_dir = previous_dir
        with mock.patch.object(app, "_count_translated_files", return_value=8):
            app._refresh_apply_summary()
        self.assertIn("Arquivos traduzidos: 8.", app.apply_summary.get())

        with mock.patch.object(app, "build_translation_command", return_value=["translate"]), mock.patch.object(
            app, "append_log"
        ), mock.patch.object(app, "_start_panel_command") as start_command:
            app.run_translation()

        self.assertIsNone(app.translated_dir)
        self.assertEqual(
            app.apply_summary.get(),
            "Destino: C:/jogos/exemplo\n"
            "Origem: nenhuma tradução concluída.\n"
            "Arquivos traduzidos: 0.",
        )
        start_command.assert_called_once()
        app.destroy()

    def test_review_control_callbacks_remain_connected(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        from text_scanner_app import TextScannerApp
        with mock.patch.object(TextScannerApp, "_run_retry") as run_retry:
            app = self._create_app_or_skip()
            app.retry_button.configure(state="normal")
            app.retry_button.invoke()
        run_retry.assert_called_once_with()
        app.destroy()

    def test_full_log_is_created_hidden_and_can_receive_early_entries(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        self.assertIsInstance(app.log, tk.Text)
        self.assertEqual(app._log_window.state(), "withdrawn")
        app.append_log("registro antes de abrir")
        self.assertIn("registro antes de abrir", app.log.get("1.0", "end"))
        with mock.patch.object(app._log_window, "deiconify") as deiconify, mock.patch.object(
            app._log_window, "lift"
        ) as lift, mock.patch.object(app._log_window, "focus_set") as focus_set:
            app.open_full_log()
        deiconify.assert_called_once_with()
        lift.assert_called_once_with()
        focus_set.assert_called_once_with()
        app.destroy()

    def test_log_close_protocol_withdraws_without_destroying_widget(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app._log_window.deiconify()
        close_handler = app._log_window.protocol("WM_DELETE_WINDOW")
        app._log_window.tk.call(close_handler)
        self.assertTrue(app._log_window.winfo_exists())
        self.assertEqual(app._log_window.state(), "withdrawn")
        app.destroy()

    def test_apply_stage_shows_permanent_safety_notice(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()

        def labels(widget):
            found = []
            if isinstance(widget, (tk.Label, ttk.Label)):
                found.append(widget.cget("text"))
            for child in widget.winfo_children():
                found.extend(labels(child))
            return found

        self.assertIn(
            "Aplicar e restaurar modificam arquivos do jogo e exigem confirmação.",
            labels(app.stage_frames[Stage.APPLY]),
        )
        app.destroy()

    def test_apply_and_restore_keep_confirmation_dialogs_with_safe_mocks(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        app = self._create_app_or_skip()
        app.game_path.set("C:/jogo-de-teste")
        translated_dir = mock.MagicMock()
        translated_dir.is_dir.return_value = True
        app.translated_dir = translated_dir
        with mock.patch("text_scanner_app.Path") as path_type, mock.patch.object(
            app, "_count_translated_files", return_value=1
        ), mock.patch("text_scanner_app.messagebox.showinfo"), mock.patch(
            "text_scanner_app.messagebox.askyesno", return_value=False
        ) as confirm_apply, mock.patch.object(app, "_start_panel_command") as start_apply:
            path_type.return_value.is_dir.return_value = True
            app.run_apply()
        confirm_apply.assert_called_once()
        start_apply.assert_not_called()

        with mock.patch.object(app, "_find_latest_manifest", return_value=Path("manifest.json")), mock.patch.object(
            app, "_manifest_entry_count", return_value=1
        ), mock.patch("text_scanner_app.messagebox.askyesno", return_value=False) as confirm_restore, mock.patch.object(
            app, "_start_panel_command"
        ) as start_restore:
            app.run_restore()
        confirm_restore.assert_called_once()
        start_restore.assert_not_called()
        app.destroy()


if __name__ == "__main__":
    unittest.main()
