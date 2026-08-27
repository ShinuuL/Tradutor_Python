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
from pathlib import Path

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

    def test_stage_navigation_blocks_locked_stage_until_workflow_unlocks_it(self):
        if not self._has_display():
            self.skipTest("Sem display disponivel")
        from ui_state import Stage
        app = self._create_app_or_skip()
        self.assertFalse(app.show_stage(Stage.TRANSLATE))
        self.assertEqual(app.active_stage, Stage.PREPARE)
        self.assertEqual(app.activity_banner.title_label.cget("text"), "Etapa ainda não disponível")
        app.workflow.mark_scan_finished(True)
        app._refresh_stage_navigation()
        self.assertTrue(app.show_stage(Stage.TRANSLATE))
        self.assertEqual(app.active_stage, Stage.TRANSLATE)
        app.destroy()


if __name__ == "__main__":
    unittest.main()
