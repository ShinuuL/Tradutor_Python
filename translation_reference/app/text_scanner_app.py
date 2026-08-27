import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from ui_components import CollapsibleSection, ScrollableStep, StageNavigation, StatusBanner
from ui_state import Stage, WorkflowState
from ui_theme import SPACING, configure_fluent_night, mono_font


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "translation_reference" / "scripts" / "extract_non_english_text.py"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "non_english_text_report"
TRANSLATE_SCRIPT_PATH = PROJECT_ROOT / "translation_reference" / "scripts" / "translate_game_text.py"
DEFAULT_ENGINE_URL = "http://localhost:11434/v1"
DEFAULT_ENGINE_MODEL = "qwen2.5:7b-instruct"
TRANSLATED_BASE = PROJECT_ROOT / "reports" / "translated"
TM_DIR = PROJECT_ROOT / "reports" / "tm"
REPORT_CSV_NAME = "translation_report.csv"
MANIFEST_NAME = "applied_manifest.json"
NON_GAME_FILES = frozenset({"translation_report.csv", "translation_report.md", MANIFEST_NAME})
STATUS_ORDER = ("tm_hit", "llm", "needs_review", "failed")
PROGRESS_RE = re.compile(r"^PROGRESS\s+(\d+)\s*/\s*(\d+)\s*$")
APPLIED_COUNT_RE = re.compile(r"^Aplicados:\s*(\d+)")


def parse_applied_count(output_lines):
    """Extrai N da linha "Aplicados: N ..." do stdout do apply; None se ausente."""
    for line in output_lines or []:
        match = APPLIED_COUNT_RE.match((line or "").strip())
        if match:
            return int(match.group(1))
    return None


def classify_apply_result(code, applied_count):
    """Classifica o resultado do apply para a UI (funcao pura, testavel).

    - "no_approval": exit 3 (sem aprovacao);
    - "error": qualquer outro codigo != 0;
    - "warning": exit 0 mas N==0 ou contagem ausente (nada confirma escrita);
    - "success": exit 0 com N > 0.
    """
    if code == 3:
        return "no_approval"
    if code != 0:
        return "error"
    if applied_count:
        return "success"
    return "warning"


# ------------------------------------------------------------------
# Helpers puras - B3 (preview, filtro, contagem, ETA)
# ------------------------------------------------------------------


def load_preview_rows(csv_path, limit=500):
    """Le o CSV de traducao e retorna ate *limit* linhas como list[dict].

    Codificacao utf-8-sig para ignorar BOM.  Retorna lista vazia se
    o arquivo nao existir ou estiver vazio.
    """
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(row)
                if len(rows) >= limit:
                    break
    except (OSError, UnicodeDecodeError):
        pass
    return rows


def filter_preview_rows(rows, status):
    """Filtra *rows* por campo ``status``.

    Se *status* for ``"todos"`` (ou vazio), retorna todas as linhas.
    Comparacao case-insensitive.
    """
    if not status or status == "todos":
        return list(rows)
    status_lower = status.lower()
    return [r for r in rows if (r.get("status") or "").lower() == status_lower]


def count_report_statuses(csv_path):
    """Conta ocorrencias de cada status no CSV de traducao (funcao pura).

    Retorna ``{nome_status: contagem}``.  Silenciosamente retorna dict
    vazio em caso de erro de leitura.
    """
    counts = {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                status = (row.get("status") or "").strip() or "desconhecido"
                counts[status] = counts.get(status, 0) + 1
    except OSError:
        pass
    return counts


def estimate_eta(history, done, total):
    """Estima o tempo restante a partir de amostras de progresso.

    *history* e uma lista de ``(timestamp, done)``.  Retorna string
    ``"ETA mm:ss"`` ou ``""`` se houver menos de 2 amostras ou se a
    traducao ja estiver concluida.
    """
    if done <= 0 or total <= 0 or done >= total:
        return ""
    if len(history) < 2:
        return ""
    t1, d1 = history[-2]
    t2, d2 = history[-1]
    dt = t2 - t1
    dd = d2 - d1
    if dt <= 0 or dd <= 0:
        return ""
    remaining = total - done
    seconds = remaining * dt / dd
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return "ETA %02d:%02d" % (minutes, secs)


class TextScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TradutorDGames Scanner")
        self.geometry("980x840")
        self.minsize(820, 560)

        self.game_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(DEFAULT_REPORT))
        self.extra_ext = tk.StringVar()
        self.max_file_mb = tk.IntVar(value=25)
        self.context_chars = tk.IntVar(value=180)
        self.batch_size = tk.IntVar(value=500)
        self.dedupe = tk.BooleanVar(value=True)
        self.skip_plugin_js = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Pronto para varrer uma pasta de jogo.")
        self.translate_status_text = tk.StringVar(value="Pronto para traduzir.")
        self.last_csv = None
        self.last_jsonl = None
        self.last_summary = None
        self.process = None

        # Estado do painel Traduzir (Fase 3).
        self.translate_jsonl = tk.StringVar()
        self.engine_url = tk.StringVar(value=DEFAULT_ENGINE_URL)
        self.engine_model = tk.StringVar(value=DEFAULT_ENGINE_MODEL)
        self.use_tm = tk.BooleanVar(value=True)
        self.translate_process = None
        self.translated_dir = None
        self._progress_total = None
        self._preview_rows = []
        self._preview_loaded = False
        self._eta_history = []
        self.workflow = WorkflowState()
        self.active_stage = Stage.PREPARE

        configure_fluent_night(self)
        self._build_layout()
        self.status.trace_add("write", self._sync_activity_banner)
        self._sync_activity_banner()

    def _build_layout(self):
        """Build the fixed workflow shell and place existing controls by stage."""
        self.configure(bg="#0B111B")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.stage_navigation = StageNavigation(self, orientation="vertical")
        self.stage_navigation.grid(row=0, column=0, sticky="ns", padx=(SPACING["page"], SPACING["md"]), pady=SPACING["page"])
        for stage in Stage:
            for widget in (
                self.stage_navigation.rows[stage],
                self.stage_navigation.markers[stage],
                self.stage_navigation.labels[stage],
            ):
                widget.configure(cursor="hand2")
                widget.bind("<Button-1>", lambda _event, target=stage: self.show_stage(target), add="+")

        stage_host = ttk.Frame(self, style="Surface.TFrame")
        stage_host.grid(row=0, column=1, sticky="nsew", padx=(0, SPACING["page"]), pady=SPACING["page"])
        stage_host.grid_rowconfigure(0, weight=1)
        stage_host.grid_columnconfigure(0, weight=1)
        self.stage_frames = {}
        for stage in Stage:
            frame = ScrollableStep(stage_host)
            frame.grid(row=0, column=0, sticky="nsew")
            self.stage_frames[stage] = frame
            if stage is not self.active_stage:
                frame.grid_remove()

        activity = ttk.Frame(self, style="Surface.TFrame")
        activity.grid(row=1, column=1, sticky="ew", padx=(0, SPACING["page"]), pady=(0, SPACING["page"]))
        activity.columnconfigure(0, weight=1)
        self.activity_banner = StatusBanner(activity)
        self.activity_banner.grid(row=0, column=0, sticky="ew")
        self._activity_actions = ttk.Frame(activity, style="Surface.TFrame")
        self._activity_actions.grid(row=0, column=1, sticky="e", padx=(SPACING["sm"], 0))
        self.open_full_log_button = ttk.Button(
            self._activity_actions,
            text="Abrir log",
            command=self.open_full_log,
            cursor="hand2",
        )
        self.open_full_log_button.pack(side="left")
        self.clear_log_button = ttk.Button(
            self._activity_actions,
            text="Limpar log",
            command=self.clear_log,
            cursor="hand2",
        )
        self.clear_log_button.pack(side="left", padx=(SPACING["sm"], 0))

        self._build_log_window()
        self._build_prepare_stage(self.stage_frames[Stage.PREPARE].content)
        self._build_translate_stage(self.stage_frames[Stage.TRANSLATE].content)
        self._build_review_stage(self.stage_frames[Stage.REVIEW].content)
        self._build_apply_stage(self.stage_frames[Stage.APPLY].content)
        self._refresh_stage_navigation()

    def _build_log_window(self):
        """Create the persistent full-log window without showing it yet."""
        self._log_window = tk.Toplevel(self)
        self._log_window.title("Log completo — TradutorDGames")
        self._log_window.geometry("820x560")
        self._log_window.minsize(560, 320)
        self._log_window.configure(bg="#0B111B")
        self._log_window.columnconfigure(0, weight=1)
        self._log_window.rowconfigure(0, weight=1)
        log_frame = ttk.Frame(self._log_window, style="Panel.TFrame", padding=SPACING["panel"])
        log_frame.grid(row=0, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(
            log_frame,
            wrap="word",
            bg="#0F1A26",
            fg="#EAF4FC",
            insertbackground="#EAF4FC",
            relief="flat",
            highlightthickness=0,
            padx=12,
            pady=12,
            font=mono_font(self),
        )
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll.grid(row=0, column=1, sticky="ns")
        self._log_window.protocol("WM_DELETE_WINDOW", self._hide_full_log)
        self._log_window.withdraw()

    def _hide_full_log(self):
        """Keep the log widget alive when its window is closed."""
        self._log_window.withdraw()

    def open_full_log(self):
        """Show and focus the persistent full-log window."""
        self._log_window.deiconify()
        self._log_window.lift()
        self._log_window.focus_set()

    @staticmethod
    def _stage_title(parent, title, detail):
        ttk.Label(parent, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text=detail, style="Muted.TLabel").pack(anchor="w", pady=(SPACING["xs"], SPACING["panel"]))

    def _build_prepare_stage(self, parent):
        self._stage_title(parent, "Preparar", "Escolha a pasta e configure a varredura somente leitura.")
        form = ttk.Frame(parent, style="Panel.TFrame", padding=SPACING["panel"])
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Pasta do jogo").grid(row=0, column=0, sticky="w", pady=(0, SPACING["xs"]))
        ttk.Entry(form, textvariable=self.game_path).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Button(form, text="Escolher", command=self.choose_game_folder, cursor="hand2").grid(row=1, column=2, sticky="ew")
        ttk.Label(form, text="Saída do relatório").grid(row=2, column=0, sticky="w", pady=(SPACING["md"], SPACING["xs"]))
        ttk.Entry(form, textvariable=self.output_path).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Button(form, text="Salvar como", command=self.choose_output_file, cursor="hand2").grid(row=3, column=2, sticky="ew")

        actions = ttk.Frame(form, style="Panel.TFrame")
        actions.grid(row=4, column=0, columnspan=3, sticky="e", pady=(SPACING["panel"], 0))
        self.run_button = ttk.Button(actions, text="Executar varredura", style="Primary.TButton", command=self.run_scan, cursor="hand2")
        self.run_button.pack(side="left", padx=(0, SPACING["sm"]))
        self.stop_button = ttk.Button(actions, text="Parar", style="Danger.TButton", command=self.stop_scan, state="disabled", cursor="hand2")
        self.stop_button.pack(side="left")

        self.prepare_advanced = CollapsibleSection(parent, title="Opções avançadas")
        self.prepare_advanced.pack(fill="x", pady=(SPACING["panel"], 0))
        options = self.prepare_advanced.content
        for column in range(4):
            options.columnconfigure(column, weight=1)
        ttk.Label(options, text="Extensões extras").grid(row=0, column=0, sticky="w")
        ttk.Entry(options, textvariable=self.extra_ext).grid(row=1, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Label(options, text="Max. MB por arquivo").grid(row=0, column=1, sticky="w")
        ttk.Spinbox(options, from_=1, to=500, textvariable=self.max_file_mb, width=8).grid(row=1, column=1, sticky="w")
        ttk.Label(options, text="Caracteres por trecho").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(options, from_=60, to=1000, increment=20, textvariable=self.context_chars, width=8).grid(row=1, column=2, sticky="w")
        ttk.Label(options, text="Linhas por lote").grid(row=0, column=3, sticky="w")
        ttk.Spinbox(options, from_=50, to=5000, increment=50, textvariable=self.batch_size, width=8).grid(row=1, column=3, sticky="w")
        checks = ttk.Frame(options, style="Panel.TFrame")
        checks.grid(row=2, column=0, columnspan=4, sticky="w", pady=(SPACING["sm"], 0))
        ttk.Checkbutton(checks, text="Remover repetidos", variable=self.dedupe).pack(side="left", padx=(0, SPACING["md"]))
        ttk.Checkbutton(checks, text="Ignorar plugins JS", variable=self.skip_plugin_js).pack(side="left")

    def _build_translate_stage(self, parent):
        self._stage_title(parent, "Traduzir", "Selecione a varredura e execute a tradução.")
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=SPACING["panel"])
        panel.pack(fill="x")
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="Scan JSONL").grid(row=0, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.translate_jsonl).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Button(panel, text="Escolher", command=self.choose_scan_jsonl, cursor="hand2").grid(row=1, column=2, sticky="ew")
        ttk.Label(panel, text="Pasta do jogo").grid(row=2, column=0, sticky="w", pady=(SPACING["md"], SPACING["xs"]))
        ttk.Entry(panel, textvariable=self.game_path).grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Button(panel, text="Escolher", command=self.choose_game_folder, cursor="hand2").grid(row=3, column=2, sticky="ew")
        ttk.Label(panel, text="Modelo").grid(row=4, column=0, sticky="w", pady=(SPACING["md"], SPACING["xs"]))
        ttk.Entry(panel, textvariable=self.engine_model).grid(row=5, column=0, columnspan=2, sticky="ew", padx=(0, SPACING["sm"]))
        ttk.Checkbutton(panel, text="Usar memória de tradução", variable=self.use_tm).grid(row=5, column=2, sticky="w")
        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.grid(row=6, column=0, columnspan=3, sticky="e", pady=(SPACING["panel"], 0))
        self.translate_button = ttk.Button(actions, text="Traduzir", style="Primary.TButton", command=self.run_translation, cursor="hand2")
        self.translate_button.pack(side="left")
        self.translate_stop_button = ttk.Button(actions, text="Parar", style="Danger.TButton", command=self.stop_translation, state="disabled", cursor="hand2")
        self.translate_stop_button.pack(side="left", padx=(SPACING["sm"], 0))
        self.progress = ttk.Progressbar(panel, orient="horizontal", mode="determinate", maximum=1, value=0)
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(SPACING["panel"], SPACING["xs"]))
        ttk.Label(panel, textvariable=self.translate_status_text, style="Muted.TLabel").grid(row=8, column=0, columnspan=3, sticky="w")

        self.translate_advanced = CollapsibleSection(parent, title="Opções avançadas")
        self.translate_advanced.pack(fill="x", pady=(SPACING["panel"], 0))
        options = self.translate_advanced.content
        options.columnconfigure(0, weight=1)
        ttk.Label(options, text="URL do engine").grid(row=0, column=0, sticky="w")
        ttk.Entry(options, textvariable=self.engine_url).grid(row=1, column=0, sticky="ew")

    def _build_review_stage(self, parent):
        self._stage_title(parent, "Revisar", "Confira os resultados e retraduza itens pendentes.")
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=SPACING["panel"])
        panel.pack(fill="both", expand=True)
        filter_row = ttk.Frame(panel, style="Panel.TFrame")
        filter_row.pack(fill="x")
        self._preview_filter = tk.StringVar(value="todos")
        self._filter_combo = ttk.Combobox(filter_row, textvariable=self._preview_filter, values=["todos", "tm_hit", "llm", "needs_review", "failed"], state="readonly", width=16)
        self._filter_combo.pack(side="left")
        self._filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        self._tree_counter = ttk.Label(filter_row, text="", style="Muted.TLabel")
        self._tree_counter.pack(side="left", padx=(SPACING["md"], 0))
        self.retry_button = ttk.Button(filter_row, text="Retraduzir falhas", command=self._run_retry, state="disabled", cursor="hand2")
        self.retry_button.pack(side="right")
        report_row = ttk.Frame(panel, style="Panel.TFrame")
        report_row.pack(fill="x", pady=(SPACING["sm"], 0))
        self.open_csv_button = ttk.Button(report_row, text="Abrir CSV", command=lambda: self.open_report(self.last_csv), cursor="hand2")
        self.open_csv_button.pack(side="left")
        self.open_jsonl_button = ttk.Button(report_row, text="Abrir JSONL", command=lambda: self.open_report(self.last_jsonl), cursor="hand2")
        self.open_jsonl_button.pack(side="left", padx=(SPACING["sm"], 0))
        self.open_summary_button = ttk.Button(report_row, text="Abrir resumo", command=lambda: self.open_report(self.last_summary), cursor="hand2")
        self.open_summary_button.pack(side="left", padx=(SPACING["sm"], 0))
        tree_frame = ttk.Frame(panel, style="Panel.TFrame")
        tree_frame.pack(fill="both", expand=True, pady=(SPACING["sm"], 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        columns = ("status", "file", "line", "source", "translated")
        self._preview_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for name, label, width in (("status", "Status", 90), ("file", "Arquivo", 160), ("line", "Linha", 50), ("source", "Original", 250), ("translated", "Tradução", 250)):
            self._preview_tree.heading(name, text=label)
            self._preview_tree.column(name, width=width, minwidth=40, anchor="e" if name == "line" else "w")
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self._preview_tree.yview)
        self._preview_tree.configure(yscrollcommand=tree_scroll.set)
        self._preview_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")

    def _build_apply_stage(self, parent):
        self._stage_title(parent, "Aplicar", "Confirme a gravação apenas depois de revisar a tradução.")
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=SPACING["panel"])
        panel.pack(fill="x")
        self.apply_summary = tk.StringVar()
        self.game_path.trace_add("write", self._refresh_apply_summary)
        self._refresh_apply_summary()
        ttk.Label(panel, textvariable=self.apply_summary, style="Muted.TLabel", justify="left", wraplength=620).pack(anchor="w")
        ttk.Label(
            panel,
            text="Aplicar e restaurar modificam arquivos do jogo e exigem confirmação.",
            style="Muted.TLabel",
            justify="left",
            wraplength=620,
        ).pack(anchor="w", pady=(SPACING["md"], 0))
        actions = ttk.Frame(panel, style="Panel.TFrame")
        actions.pack(anchor="w", pady=(SPACING["panel"], 0))
        self.apply_button = ttk.Button(actions, text="Aplicar no jogo", style="Danger.TButton", command=self.run_apply, state="disabled", cursor="hand2")
        self.apply_button.pack(side="left")
        self.restore_button = ttk.Button(actions, text="Restaurar backups", style="Danger.TButton", command=self.run_restore, cursor="hand2")
        self.restore_button.pack(side="left", padx=(SPACING["sm"], 0))

    def _refresh_apply_summary(self, *_args):
        """Show the currently selected game folder and translated output safely."""
        destination = self.game_path.get().strip()
        destination_text = destination or "nenhuma pasta do jogo selecionada."
        translated_dir = self.translated_dir
        source_text = "nenhuma tradução concluída."
        file_count = 0
        if translated_dir:
            source_text = str(translated_dir)
            try:
                if translated_dir.is_dir():
                    file_count = self._count_translated_files(translated_dir)
            except (AttributeError, OSError, TypeError, ValueError):
                pass
        self.apply_summary.set(
            "Destino: %s\nOrigem: %s\nArquivos traduzidos: %d."
            % (destination_text, source_text, file_count)
        )

    def _refresh_stage_navigation(self):
        for stage in Stage:
            self.stage_navigation.set_status(stage, self.workflow.status(stage))
        self.stage_navigation.set_active(self.active_stage)

    def show_stage(self, stage):
        if not self.workflow.can_open(stage):
            self.activity_banner.set_state("info", "Etapa ainda não disponível", self.workflow.requirement(stage))
            return False
        self.stage_frames[self.active_stage].grid_remove()
        self.active_stage = stage
        self.stage_frames[stage].grid()
        self.stage_navigation.set_active(stage)
        return True

    def _sync_activity_banner(self, *_args):
        if hasattr(self, "activity_banner"):
            self.activity_banner.set_state("info", "Atividade", self.status.get())

    def choose_game_folder(self):
        selected = filedialog.askdirectory(title="Escolha a pasta do jogo", mustexist=True)
        if selected:
            self.game_path.set(selected)
            if self.output_path.get() == str(DEFAULT_REPORT):
                safe_name = Path(selected).name or "jogo"
                self.output_path.set(str(PROJECT_ROOT / "reports" / f"{safe_name}_non_english_text"))

    def choose_output_file(self):
        selected = filedialog.asksaveasfilename(
            title="Salvar relatorio como",
            initialdir=str(PROJECT_ROOT / "reports"),
            initialfile="non_english_text_report.csv",
            defaultextension=".csv",
            filetypes=(("CSV", "*.csv"), ("JSONL", "*.jsonl"), ("Todos", "*.*")),
        )
        if selected:
            self.output_path.set(str(Path(selected).with_suffix("")))

    def build_command(self):
        game = self.game_path.get().strip()
        output = self.output_path.get().strip()
        if not game:
            raise ValueError("Escolha uma pasta de jogo antes de executar.")
        if not output:
            raise ValueError("Escolha um caminho de saida para o relatorio.")

        command = [
            sys.executable,
            str(SCRIPT_PATH),
            game,
            "--out",
            output,
            "--max-file-mb",
            str(self.max_file_mb.get()),
            "--context",
            str(self.context_chars.get()),
            "--batch-size",
            str(self.batch_size.get()),
        ]

        for ext in self.extra_ext.get().replace(";", ",").split(","):
            ext = ext.strip()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = "." + ext
            command.extend(["--include-ext", ext])

        if self.dedupe.get():
            command.append("--dedupe")
        if self.skip_plugin_js.get():
            command.append("--skip-plugin-js")

        return command

    def run_scan(self):
        try:
            command = self.build_command()
        except ValueError as exc:
            messagebox.showwarning("Configuracao incompleta", str(exc), parent=self)
            return

        self.clear_log()
        self.append_log("> " + " ".join(f'"{part}"' if " " in part else part for part in command))
        self.status.set("Varredura em andamento...")
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        thread = threading.Thread(target=self._run_worker, args=(command,), daemon=True)
        thread.start()

    def _run_worker(self, command):
        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in self.process.stdout:
                self.after(0, self.append_log, line.rstrip())
            code = self.process.wait()
            self.after(0, self._finish_run, code)
        except Exception as exc:
            self.after(0, self.append_log, f"Falha ao executar: {exc}")
            self.after(0, self._finish_run, 1)
        finally:
            self.process = None

    def _finish_run(self, code):
        output = Path(self.output_path.get())
        self.last_csv = output.with_suffix(".csv")
        self.last_jsonl = output.with_suffix(".jsonl")
        self.last_summary = output.with_suffix(".summary.md")
        success = code == 0 and self.last_jsonl.exists()
        if success:
            self.translate_jsonl.set(str(self.last_jsonl))
        if success:
            self.status.set("Varredura concluida. Relatorios prontos para revisar.")
        else:
            self.status.set(f"Varredura terminou com erro. Codigo: {code}")
        self.run_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def stop_scan(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.append_log("Parada solicitada pelo usuario.")

    # ------------------------------------------------------------------
    # Painel Traduzir (Fase 3)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_command(command):
        return " ".join(f'"{part}"' if " " in part else part for part in command)

    def choose_scan_jsonl(self):
        selected = filedialog.askopenfilename(
            title="Escolha o JSONL da varredura",
            initialdir=str(PROJECT_ROOT / "reports"),
            filetypes=(("JSONL", "*.jsonl"), ("Todos", "*.*")),
        )
        if selected:
            self.translate_jsonl.set(selected)

    def _game_name(self):
        return Path(self.game_path.get().strip()).name or "jogo"

    def _translated_dir(self):
        return TRANSLATED_BASE / self._game_name()

    def build_translation_command(self):
        scan = self.translate_jsonl.get().strip()
        game = self.game_path.get().strip()
        if not scan:
            raise ValueError("Escolha o arquivo JSONL da varredura antes de traduzir.")
        if not Path(scan).is_file():
            raise ValueError("Arquivo de scan nao encontrado: %s" % scan)
        if not game:
            raise ValueError("Escolha a pasta do jogo antes de traduzir.")

        command = [
            sys.executable,
            str(TRANSLATE_SCRIPT_PATH),
            scan,
            "--out-dir",
            str(self._translated_dir()),
            "--engine-url",
            self.engine_url.get().strip() or DEFAULT_ENGINE_URL,
            "--engine-model",
            self.engine_model.get().strip() or DEFAULT_ENGINE_MODEL,
        ]
        if self.use_tm.get():
            command.extend(["--tm", str(TM_DIR / ("%s.jsonl" % self._game_name()))])
        return command

    def run_translation(self):
        if self._panel_busy():
            messagebox.showinfo("Operacao em andamento", "Aguarde o termino da operacao atual do painel Traduzir.", parent=self)
            return
        try:
            command = self.build_translation_command()
        except ValueError as exc:
            messagebox.showwarning("Configuracao incompleta", str(exc), parent=self)
            return

        self.translated_dir = None
        self.append_log("--- Traducao ---")
        self._start_panel_command(
            command,
            self._finish_translation,
            "Traducao em andamento...",
            with_progress=True,
        )

    def _panel_busy(self):
        return bool(self.translate_process and self.translate_process.poll() is None)

    def _start_panel_command(self, command, on_finish, busy_label, with_progress):
        self.append_log("> " + self._format_command(command))
        self.status.set(busy_label)
        self.translate_button.configure(state="disabled")
        self.apply_button.configure(state="disabled")
        self.restore_button.configure(state="disabled")
        self.retry_button.configure(state="disabled")
        self.translate_stop_button.configure(state="normal" if with_progress else "disabled")
        self._progress_total = None
        self._preview_loaded = False
        self._eta_history = []
        if with_progress:
            self.progress.configure(value=0)
            self.translate_status_text.set("Aguardando primeira linha PROGRESS...")
        thread = threading.Thread(
            target=self._panel_worker,
            args=(command, on_finish, with_progress),
            daemon=True,
        )
        thread.start()

    def _panel_worker(self, command, on_finish, with_progress):
        output_lines = []
        try:
            env = dict(os.environ, PYTHONUNBUFFERED="1")
            self.translate_process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            for line in self.translate_process.stdout:
                text = line.rstrip()
                output_lines.append(text)
                self.after(0, self.append_log, text)
                if with_progress:
                    self.after(0, self._observe_progress_line, text)
            code = self.translate_process.wait()
            self.after(0, self._collect_finish, on_finish, code, output_lines)
        except Exception as exc:
            self.after(0, self.append_log, f"Falha ao executar: {exc}")
            self.after(0, self._collect_finish, on_finish, 1, output_lines)
        finally:
            self.translate_process = None

    def _collect_finish(self, on_finish, code, output_lines):
        try:
            on_finish(code, output_lines)
        finally:
            self.translate_button.configure(state="normal")
            self.translate_stop_button.configure(state="disabled")
            self.restore_button.configure(state="normal")
            if self._preview_loaded:
                self.apply_button.configure(state="normal")

    def _observe_progress_line(self, text):
        match = PROGRESS_RE.match(text.strip())
        if not match:
            return
        done, total = int(match.group(1)), int(match.group(2))
        if self._progress_total != total:
            self._progress_total = total
            self.progress.configure(maximum=total)
        self.progress.configure(value=min(done, total))
        self._eta_history.append((time.time(), done))
        model_name = self.engine_model.get().strip() or DEFAULT_ENGINE_MODEL
        eta_str = estimate_eta(self._eta_history, done, total)
        parts = ["Modelo: %s" % model_name, "%d/%d linhas" % (done, total)]
        if eta_str:
            parts.append(eta_str)
        self.translate_status_text.set(" | ".join(parts))

    def _finish_translation(self, code, output_lines):
        out_dir = self._translated_dir()
        if code != 0:
            message = "Traducao terminou com erro. Codigo: %s" % code
            self.translate_status_text.set(message)
            self.status.set(message + " Verifique o log.")
            return
        self.translated_dir = out_dir
        self._refresh_apply_summary()
        if self._progress_total is not None:
            self.progress.configure(value=self._progress_total)
        self._populate_preview_tree(out_dir / REPORT_CSV_NAME)
        model_name = self.engine_model.get().strip() or DEFAULT_ENGINE_MODEL
        total = self._progress_total or 0
        eta_str = estimate_eta(self._eta_history, total, total)
        parts = ["Modelo: %s" % model_name, "%d/%d linhas" % (total, total)]
        if eta_str:
            parts.append(eta_str)
        self.translate_status_text.set(" | ".join(parts))
        self.status.set("Traducao concluida. Revise o resumo e use Aplicar no jogo quando desejar.")
        counts = count_report_statuses(out_dir / REPORT_CSV_NAME)
        retryable = counts.get("needs_review", 0) + counts.get("failed", 0)
        self.retry_button.configure(state="normal" if retryable > 0 else "disabled")
        summary = "\n".join("- %s: %d" % (name, counts.get(name, 0)) for name in STATUS_ORDER)
        messagebox.showinfo(
            "Traducao concluida",
            "Resumo por status:\n%s\n\nRelatorio: %s\n\nO botao \"Aplicar no jogo\" foi habilitado."
            % (summary, out_dir / REPORT_CSV_NAME),
            parent=self,
        )

    @staticmethod
    def _count_report_statuses(csv_path):
        counts = {}
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    status = (row.get("status") or "").strip() or "desconhecido"
                    counts[status] = counts.get(status, 0) + 1
        except OSError:
            pass
        return counts

    def stop_translation(self):
        if self._panel_busy():
            self.translate_process.terminate()
            self.append_log("Parada solicitada pelo usuario.")

    def run_apply(self):
        if self._panel_busy():
            messagebox.showinfo("Operacao em andamento", "Aguarde o termino da operacao atual do painel Traduzir.", parent=self)
            return
        game_root = self.game_path.get().strip()
        translated_dir = self.translated_dir or self._translated_dir()
        if not game_root:
            messagebox.showwarning("Configuracao incompleta", "Escolha a pasta do jogo antes de aplicar.", parent=self)
            return
        if not Path(game_root).is_dir():
            messagebox.showwarning("Pasta nao encontrada", "A pasta do jogo nao existe:\n%s" % game_root, parent=self)
            return
        if not translated_dir.is_dir():
            messagebox.showwarning("Nada para aplicar", "Execute uma traducao com sucesso antes de aplicar.", parent=self)
            return

        file_count = self._count_translated_files(translated_dir)
        if file_count == 0:
            messagebox.showwarning(
                "Nada para aplicar",
                "Nenhum arquivo traduzido encontrado em:\n%s" % translated_dir,
                parent=self,
            )
            return

        messagebox.showinfo(
            "Aplicar traducoes",
            "Destino: %s\nOrigem: %s\nArquivos que serao substituidos: %d"
            % (game_root, translated_dir, file_count),
            parent=self,
        )
        if not messagebox.askyesno(
            "Confirmar aplicacao",
            "Isto vai SOBRESCREVER arquivos do jogo. Backups .bak serao criados. Confirmar?",
            parent=self,
        ):
            self.append_log("Aplicacao cancelada pelo usuario.")
            return

        manifest_path = translated_dir / MANIFEST_NAME
        command = [
            sys.executable,
            str(TRANSLATE_SCRIPT_PATH),
            "apply",
            "--translated-dir",
            str(translated_dir),
            "--game-root",
            game_root,
            "--i-approve-write-game-files",
        ]
        self.append_log("--- Aplicar no jogo ---")
        self._start_panel_command(
            command,
            lambda code, lines: self._finish_apply(code, lines, manifest_path),
            "Aplicando traducoes no jogo...",
            with_progress=False,
        )

    @staticmethod
    def _count_translated_files(translated_dir):
        count = 0
        for path in Path(translated_dir).rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(Path(translated_dir)).as_posix()
            if rel in NON_GAME_FILES or rel.endswith(".tmp"):
                continue
            count += 1
        return count

    def _finish_apply(self, code, output_lines, manifest_path):
        applied_count = parse_applied_count(output_lines)
        outcome = classify_apply_result(code, applied_count)
        applied_line = next((line for line in output_lines if line.startswith("Aplicados:")), "")
        self.append_log("Manifesto de aplicacao: %s" % manifest_path)
        if outcome == "success":
            self.status.set("Traducao aplicada no jogo. Backups .bak registrados no manifesto.")
            messagebox.showinfo(
                "Aplicacao concluida",
                "%s\n\nManifesto: %s" % (applied_line or "Arquivos aplicados no jogo.", manifest_path),
                parent=self,
            )
        elif outcome == "warning":
            # Exit 0 nao garante escrita: com N==0 nada mudou no jogo
            # (ex.: todos os arquivos protegidos porque o jogo mudou desde
            # o backup). Avisar, nunca mostrar sucesso.
            detail = applied_line or (
                "O CLI terminou sem informar quantos arquivos foram aplicados."
            )
            self.status.set("Nada foi aplicado no jogo. Verifique o log e o manifesto.")
            messagebox.showwarning(
                "Nada foi aplicado",
                "%s\n\nNenhum arquivo do jogo foi modificado.\n"
                "Motivos comuns: arquivos do jogo alterados desde o backup "
                "(protegidos) ou pasta traduzida sem arquivos compativeis.\n\n"
                "Manifesto: %s\nConsulte o log para o motivo de cada arquivo."
                % (detail, manifest_path),
                parent=self,
            )
        elif outcome == "no_approval":
            self.status.set("Aplicacao sem aprovacao. Nada foi gravado.")
            messagebox.showwarning(
                "Aplicacao interrompida",
                "O CLI saiu com codigo 3 (sem aprovacao). Nada foi gravado.",
                parent=self,
            )
        else:
            self.status.set("Aplicacao terminou com erro. Codigo: %s" % code)
            messagebox.showerror(
                "Falha na aplicacao",
                "%s\nCodigo de saida: %s\nVerifique o log para detalhes." % (applied_line, code),
                parent=self,
            )

    def _find_latest_manifest(self):
        base = TRANSLATED_BASE
        if not base.is_dir():
            return None
        direct = base / self._game_name() / MANIFEST_NAME
        if direct.is_file():
            return direct
        try:
            candidates = [path for path in base.glob("*/%s" % MANIFEST_NAME) if path.is_file()]
        except OSError:
            return None
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    @staticmethod
    def _manifest_entry_count(manifest_path):
        try:
            doc = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            return -1
        if not isinstance(doc, dict):
            return -1
        entries = doc.get("entries") or []
        return len([entry for entry in entries if isinstance(entry, dict) and entry.get("file")])

    def run_restore(self):
        if self._panel_busy():
            messagebox.showinfo("Operacao em andamento", "Aguarde o termino da operacao atual do painel Traduzir.", parent=self)
            return
        manifest_path = self._find_latest_manifest()
        if manifest_path is None:
            messagebox.showinfo(
                "Nenhum backup encontrado",
                "Nenhum %s encontrado em:\n%s" % (MANIFEST_NAME, TRANSLATED_BASE),
                parent=self,
            )
            return
        entry_count = self._manifest_entry_count(manifest_path)
        if entry_count < 0:
            messagebox.showwarning("Manifesto invalido", "Nao foi possivel ler o manifesto:\n%s" % manifest_path, parent=self)
            return
        if entry_count == 0:
            messagebox.showinfo("Nada para restaurar", "O manifesto nao possui backups registrados.", parent=self)
            return
        if not messagebox.askyesno(
            "Restaurar backups",
            "%d arquivo(s) serao restaurados a partir dos backups .bak.\nManifesto: %s\n\nConfirmar restauracao?"
            % (entry_count, manifest_path),
            parent=self,
        ):
            self.append_log("Restauracao cancelada pelo usuario.")
            return

        command = [
            sys.executable,
            str(TRANSLATE_SCRIPT_PATH),
            "restore",
            "--manifest",
            str(manifest_path),
        ]
        self.append_log("--- Restaurar backups ---")
        self._start_panel_command(
            command,
            lambda code, lines: self._finish_restore(code, lines, manifest_path),
            "Restaurando backups do jogo...",
            with_progress=False,
        )

    def _finish_restore(self, code, output_lines, manifest_path):
        restored_line = next((line for line in output_lines if line.startswith("Restaurados:")), "")
        if code == 0:
            self.status.set("Backups restaurados com sucesso.")
            messagebox.showinfo(
                "Restauracao concluida",
                "%s\n\nManifesto: %s" % (restored_line or "Arquivos originais recuperados.", manifest_path),
                parent=self,
            )
        else:
            self.status.set("Restauracao terminou com erro. Codigo: %s" % code)
            messagebox.showerror(
                "Falha na restauracao",
                "%s\nCodigo de saida: %s\nVerifique o log para detalhes." % (restored_line, code),
                parent=self,
            )

    def open_report(self, path):
        if not path or not Path(path).exists():
            messagebox.showinfo("Relatorio nao encontrado", "Execute uma varredura primeiro.", parent=self)
            return
        os.startfile(Path(path))

    def append_log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def clear_log(self):
        self.log.delete("1.0", "end")

    # ------------------------------------------------------------------
    # B3a - Preview Treeview
    # ------------------------------------------------------------------

    def _populate_preview_tree(self, csv_path):
        """Carrega o CSV de traducao e popula o Treeview de preview."""
        self._preview_rows = load_preview_rows(csv_path)
        self._preview_loaded = True
        self._preview_filter.set("todos")
        self._update_tree_display()

    def _on_filter_change(self, _event=None):
        """Repopula o Treeview ao mudar o filtro de status."""
        self._update_tree_display()

    def _update_tree_display(self):
        """Popula o Treeview com base no filtro atual e atualiza o contador."""
        for item in self._preview_tree.get_children():
            self._preview_tree.delete(item)
        status_filter = self._preview_filter.get()
        filtered = filter_preview_rows(self._preview_rows, status_filter)
        total_rows = len(self._preview_rows)
        shown = 0
        for row in filtered:
            self._preview_tree.insert(
                "",
                "end",
                values=(
                    row.get("status", ""),
                    row.get("file", ""),
                    row.get("line", ""),
                    (row.get("source") or "")[:120],
                    (row.get("translated") or "")[:120],
                ),
            )
            shown += 1
        hidden = total_rows - shown
        if hidden > 0:
            self._tree_counter.configure(text="...e %d mais" % hidden)
        else:
            self._tree_counter.configure(text="%d linhas" % shown)

    # ------------------------------------------------------------------
    # B3b - Retraduzir falhas
    # ------------------------------------------------------------------

    def _run_retry(self):
        """Monta e executa o subcomando retry para falhas/pendencias."""
        if self._panel_busy():
            messagebox.showinfo("Operacao em andamento", "Aguarde o termino da operacao atual do painel Traduzir.", parent=self)
            return
        scan = self.translate_jsonl.get().strip()
        out_dir = self.translated_dir or self._translated_dir()
        if not scan or not Path(scan).is_file():
            messagebox.showwarning("Configuracao incompleta", "Selecione o JSONL da varredura primeiro.", parent=self)
            return
        if not out_dir.is_dir():
            messagebox.showwarning("Nada para retraduzir", "Execute uma traducao primeiro.", parent=self)
            return
        csv_path = out_dir / REPORT_CSV_NAME
        if not csv_path.is_file():
            messagebox.showwarning("Relatorio nao encontrado", "CSV de traducao nao encontrado:\n%s" % csv_path, parent=self)
            return
        counts = count_report_statuses(csv_path)
        retryable = counts.get("needs_review", 0) + counts.get("failed", 0)
        if retryable == 0:
            messagebox.showinfo("Nada para retraduzir", "Nenhum item com status needs_review ou failed.", parent=self)
            return

        command = [
            sys.executable,
            str(TRANSLATE_SCRIPT_PATH),
            "retry",
            "--scan",
            scan,
            "--out-dir",
            str(out_dir),
            "--statuses",
            "needs_review,failed",
            "--force-engine",
            "--engine-url",
            self.engine_url.get().strip() or DEFAULT_ENGINE_URL,
            "--engine-model",
            self.engine_model.get().strip() or DEFAULT_ENGINE_MODEL,
        ]
        if self.use_tm.get():
            command.extend(["--tm", str(TM_DIR / ("%s.jsonl" % self._game_name()))])
        self.append_log("--- Retraduzir falhas ---")
        self._start_panel_command(
            command,
            self._finish_retry,
            "Retraduzindo %d item(s)..." % retryable,
            with_progress=True,
        )

    def _finish_retry(self, code, output_lines):
        """Callback ao termino do retry: atualiza preview e status."""
        out_dir = self.translated_dir or self._translated_dir()
        csv_path = out_dir / REPORT_CSV_NAME
        if code == 0 and csv_path.is_file():
            self._populate_preview_tree(csv_path)
            counts = count_report_statuses(csv_path)
            retryable = counts.get("needs_review", 0) + counts.get("failed", 0)
            self.retry_button.configure(state="normal" if retryable > 0 else "disabled")
            self.status.set("Retraducao concluida. %d item(s) restante(s)." % retryable)
        elif code == 0:
            self.status.set("Retraducao concluida.")
        else:
            self.status.set("Retraducao terminou com erro. Codigo: %s" % code)


if __name__ == "__main__":
    app = TextScannerApp()
    app.mainloop()
