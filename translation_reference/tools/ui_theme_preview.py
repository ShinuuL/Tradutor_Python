# -*- coding: utf-8 -*-
"""Preview de Temas - TradutorDGames.

Janela Tkinter autonomia (stdlib only) que reproduz o layout de
translation_reference/app/text_scanner_app.py e permite trocar ao vivo
entre 3 direcoes visuais pesquisadas:

  A - Console Fosforo  (terminal CRT verde fosforescente)
  B - Bancada Slate    (cinza-neutro com acento azul)
  C - Oficina Ambar    (grafite quente com acento ambar)

Este script NAO importa nem altera o app existente; serve apenas para o dev
comparar temas antes de aplicar qualquer mudanca em text_scanner_app.py.

Tokens estruturais (grid 4pt), iguais para os 3 temas:
  - padding da raiz ............ 20 px
  - espaco entre paineis ....... 16 px
  - padding interno dos paineis  16 px
  - label -> campo .............   4 px
  - altura da progressbar ...... 10 px
  - altura unica de botoes ..... padding vertical 7 px (todos os estilos)

Tipografia:
  - UI ... Segoe UI / Segoe UI Semibold
  - Mono . Cascadia Code, com fallback Consolas

Estados visiveis por tema: botao "Parar" desabilitado, foco visivel no
primeiro Entry (anel na cor de acento).
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# ---------------------------------------------------------------------------
# Tokens das direcoes (fonte unica de verdade; espelhada no HTML de mockups)
# ---------------------------------------------------------------------------

THEMES = {
    "A": {
        "display": "A - Console Fosforo",
        "bg": "#0B100C",
        "panel": "#121A14",
        "panel_border": "#24352A",
        "header_fg": "#EAFBE8",
        "sub_fg": "#A8BCA6",
        "label_fg": "#D6EAD3",
        "muted_fg": "#8FA892",
        "field_bg": "#0F1711",
        "field_fg": "#D9FBCE",
        "entry_border": "#56785E",
        "accent": "#50FA7B",
        "accent_fg": "#05230F",
        "accent_hover": "#79F09A",
        "btn_bg": "#1B291F",
        "btn_fg": "#EAFBE8",
        "btn_hover": "#24382B",
        "danger_bg": "#A63D3A",
        "danger_fg": "#FFEDEA",
        "danger_hover": "#BF4A46",
        "disabled_bg": "#17211A",
        "disabled_fg": "#66796A",
        "status_bg": "#16221A",
        "status_fg": "#D6EAD3",
        "log_bg": "#070B08",
        "log_fg": "#CFEFC8",
        "sel_bg": "#2C4434",
        "sel_fg": "#EAFBE8",
        "ok": "#50FA7B",
        "warn": "#F1FA8C",
        "err": "#FF6E6E",
        "path": "#8BE9FD",
    },
    "B": {
        "display": "B - Bancada Slate",
        "bg": "#15181D",
        "panel": "#1D222A",
        "panel_border": "#2C333E",
        "header_fg": "#EEF2F7",
        "sub_fg": "#9AA7B8",
        "label_fg": "#D5DCE6",
        "muted_fg": "#8391A3",
        "field_bg": "#232A34",
        "field_fg": "#EDF1F7",
        "entry_border": "#5E6D86",
        "accent": "#4C8DFF",
        "accent_fg": "#0B1B33",
        "accent_hover": "#6BA3FF",
        "btn_bg": "#272F3A",
        "btn_fg": "#EEF2F7",
        "btn_hover": "#323C4A",
        "danger_bg": "#C74E5E",
        "danger_fg": "#FFF0F2",
        "danger_hover": "#DB5F6F",
        "disabled_bg": "#20262E",
        "disabled_fg": "#6B7686",
        "status_bg": "#242C37",
        "status_fg": "#D5DCE6",
        "log_bg": "#14181E",
        "log_fg": "#D9E1EC",
        "sel_bg": "#33415A",
        "sel_fg": "#EEF2F7",
        "ok": "#5BD98A",
        "warn": "#E8C268",
        "err": "#FF7A85",
        "path": "#6EC3FF",
    },
    "C": {
        "display": "C - Oficina Ambar",
        "bg": "#171310",
        "panel": "#211A15",
        "panel_border": "#362A20",
        "header_fg": "#FBF3E6",
        "sub_fg": "#C0AE99",
        "label_fg": "#EBDCC7",
        "muted_fg": "#A5947F",
        "field_bg": "#2A211A",
        "field_fg": "#F8EEDD",
        "entry_border": "#7A654D",
        "accent": "#F5A623",
        "accent_fg": "#241503",
        "accent_hover": "#FFB84D",
        "btn_bg": "#2E251C",
        "btn_fg": "#FBF3E6",
        "btn_hover": "#3A2F23",
        "danger_bg": "#B04A32",
        "danger_fg": "#FFF1EA",
        "danger_hover": "#C95B41",
        "disabled_bg": "#241D17",
        "disabled_fg": "#7D6E5D",
        "status_bg": "#2A211A",
        "status_fg": "#EBDCC7",
        "log_bg": "#120E0B",
        "log_fg": "#F0E4CF",
        "sel_bg": "#46351F",
        "sel_fg": "#FBF3E6",
        "ok": "#A3D160",
        "warn": "#F5C542",
        "err": "#FF7A5C",
        "path": "#8AD8C6",
    },
}

DEFAULT_THEME = "A"

# Grid 4pt compartilhado.
ROOT_PAD = 20          # padding da raiz
PANEL_GAP = 16         # espaco entre paineis
PANEL_PAD = 16         # padding interno dos paineis
LABEL_GAP = 4          # label -> campo
BAR_HEIGHT = 10        # altura da progressbar
BUTTON_PAD_Y = 7       # altura unica de botoes (vertical pad igual em todos)

UI_FONT = ("Segoe UI", 10)
UI_FONT_BOLD = ("Segoe UI Semibold", 10)
HEADER_FONT = ("Segoe UI Semibold", 22)
TITLE_FONT = ("Segoe UI Semibold", 12)


def mono_font():
    """Cascadia Code com fallback Consolas."""
    try:
        available = set(tkfont.families())
    except Exception:
        available = set()
    if "Cascadia Code" in available:
        return ("Cascadia Code", 10)
    return ("Consolas", 10)


class ThemePreviewApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Preview de Temas - TradutorDGames")
        self.geometry("980x840")
        self.minsize(900, 720)

        style = ttk.Style(self)
        style.theme_use("clam")
        self._mono = mono_font()

        self.theme_var = tk.StringVar(value=THEMES[DEFAULT_THEME]["display"])

        self._build_layout()
        self.apply_theme(THEMES[DEFAULT_THEME]["display"])
        self._insert_log_examples()
        self.after(80, self._focus_first_entry)

    # ------------------------------------------------------------------
    # Layout (replica a estrutura do app: header, Entrada, Traduzir, Log)
    # ------------------------------------------------------------------

    def _build_layout(self):
        root = ttk.Frame(self, style="Root.TFrame", padding=ROOT_PAD)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)
        self._root = root

        # Linha do seletor de tema (chrome do preview, nao faz parte do app).
        selector = ttk.Frame(root, style="Root.TFrame")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, PANEL_GAP))
        ttk.Label(selector, text="Tema:", style="Sub.TLabel").pack(side="left")
        self.selector = ttk.Combobox(
            selector,
            textvariable=self.theme_var,
            values=[t["display"] for t in THEMES.values()],
            state="readonly",
            width=26,
            style="Selector.TCombobox",
        )
        self.selector.pack(side="left", padx=(12, 12))
        self.selector.bind("<<ComboboxSelected>>", self._on_theme_selected)
        ttk.Label(selector, text="(troca ao vivo entre as 3 direcoes)", style="SelectorHint.TLabel").pack(
            side="left"
        )

        # Header (igual ao app).
        header = ttk.Frame(root, style="Root.TFrame")
        header.grid(row=1, column=0, sticky="ew", pady=(0, PANEL_GAP))
        ttk.Label(header, text="TradutorDGames Scanner", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Varra pastas de jogos e gere CSV/JSONL com textos candidatos a traducao.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(LABEL_GAP, 0))

        # Painel Entrada.
        form = ttk.Frame(root, style="Panel.TFrame", padding=PANEL_PAD)
        form.grid(row=2, column=0, sticky="ew", pady=(0, PANEL_GAP))
        ttk.Label(form, text="Entrada", style="PanelTitle.TLabel").pack(anchor="w")

        first_entry = self._add_path_field(
            form,
            label="Pasta do jogo",
            value="D:/Jogos/Exemplo",
            button_text="Escolher",
        )
        self._first_entry = first_entry
        self._add_path_field(
            form,
            label="Saida do relatorio",
            value="reports/exemplo_non_english_text",
            button_text="Salvar como",
        )

        options_row = ttk.Frame(form, style="Panel.TFrame")
        options_row.pack(fill="x", pady=(16, 0))
        self._add_small_field(options_row, "Extensoes extras", tk.Entry, {".dat, .bytes"}, hint="Ex.: .dat, .bytes")
        self._add_small_spin(options_row, "Max MB por arquivo", "25")
        self._add_small_spin(options_row, "Caracteres por trecho", "180")
        self._add_small_spin(options_row, "Linhas por lote", "500")

        options_actions = ttk.Frame(form, style="Panel.TFrame")
        options_actions.pack(fill="x", pady=(12, 0))
        checks = ttk.Frame(options_actions, style="Panel.TFrame")
        checks.pack(side="left")
        ttk.Checkbutton(checks, text="Remover repetidos").pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Ignorar plugins JS").pack(side="left")
        actions = ttk.Frame(options_actions, style="Panel.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="Executar varredura", style="Primary.TButton").pack(side="left", padx=(0, 8))
        stop = ttk.Button(actions, text="Parar", style="Danger.TButton", state="disabled")
        stop.pack(side="left")

        # Painel Traduzir.
        translate_panel = ttk.Frame(root, style="Panel.TFrame", padding=PANEL_PAD)
        translate_panel.grid(row=3, column=0, sticky="ew", pady=(0, PANEL_GAP))
        ttk.Label(translate_panel, text="Traduzir", style="PanelTitle.TLabel").pack(anchor="w")

        self._add_path_field(
            translate_panel,
            label="Scan JSONL",
            value="reports/exemplo_non_english_text.jsonl",
            button_text="Escolher",
            top_gap=12,
        )
        self._add_path_field(
            translate_panel,
            label="Pasta do jogo",
            value="D:/Jogos/Exemplo",
            button_text="Escolher",
            top_gap=12,
        )

        engine_row = ttk.Frame(translate_panel, style="Panel.TFrame")
        engine_row.pack(fill="x", pady=(12, 0))
        url_group = self._make_field_group(engine_row, "URL do engine", expand=True)
        url_entry = ttk.Entry(url_group["row"])
        url_entry.insert(0, "http://localhost:11434/v1")
        url_entry.pack(side="left", fill="x", expand=True)
        model_group = self._make_field_group(engine_row, "Modelo")
        model_group["frame"].pack_configure(side="left", padx=(16, 0))
        model_entry = ttk.Entry(model_group["row"])
        model_entry.insert(0, "qwen2.5:7b-instruct")
        model_entry.pack(side="left", fill="x", expand=True)
        ttk.Checkbutton(engine_row, text="Usar memoria de traducao").pack(side="left", padx=(16, 0), pady=(20, 0))

        translate_actions = ttk.Frame(translate_panel, style="Panel.TFrame")
        translate_actions.pack(anchor="e", pady=(16, 0))
        ttk.Button(translate_actions, text="Traduzir", style="Primary.TButton").pack(side="left")
        ttk.Button(translate_actions, text="Parar", style="Danger.TButton", state="disabled").pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(translate_actions, text="Aplicar no jogo", style="Danger.TButton", state="disabled").pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(translate_actions, text="Restaurar backups", style="Danger.TButton").pack(side="left", padx=(8, 0))

        # Progressbar determinada em 62% + status do painel.
        style = ttk.Style(self)
        style.configure("Horizontal.TProgressbar", thickness=BAR_HEIGHT)
        self.progress = ttk.Progressbar(
            translate_panel, orient="horizontal", mode="determinate", maximum=100, value=62
        )
        self.progress.pack(fill="x", pady=(16, LABEL_GAP))
        ttk.Label(
            translate_panel,
            text="62/100 linhas traduzidas - aguardando revisao.",
            style="Muted.TLabel",
        ).pack(anchor="w")

        # Painel Execucao (log).
        body = ttk.Frame(root, style="Panel.TFrame", padding=PANEL_PAD)
        body.grid(row=4, column=0, sticky="nsew")
        ttk.Label(body, text="Execucao", style="PanelTitle.TLabel").pack(anchor="w")
        status = ttk.Label(
            body,
            text="Varredura concluida. Relatorios prontos para revisar.",
            style="Status.TLabel",
        )
        status.pack(fill="x", pady=(12, 10))

        self.log = tk.Text(
            body,
            wrap="word",
            height=10,
            relief="flat",
            padx=12,
            pady=12,
            font=self._mono,
            state="normal",
        )
        self.log.pack(fill="both", expand=True)

        footer = ttk.Frame(body, style="Panel.TFrame")
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Abrir CSV").pack(side="left")
        ttk.Button(footer, text="Abrir JSONL").pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Abrir resumo").pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Limpar log").pack(side="right")

    def _make_field_group(self, parent, label, expand=False):
        group = ttk.Frame(parent, style="Panel.TFrame")
        group.pack(side="left", fill="x", expand=expand)
        ttk.Label(group, text=label).pack(anchor="w", pady=(LABEL_GAP, 0))
        row = ttk.Frame(group, style="Panel.TFrame")
        row.pack(fill="x", pady=(LABEL_GAP, 0))
        return {"frame": group, "row": row}

    def _add_path_field(self, panel, label, value, button_text, top_gap=12):
        group = self._make_field_group(panel, label)
        group["frame"].pack_configure(fill="x", pady=(top_gap, 0))
        entry = ttk.Entry(group["row"])
        entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        ttk.Button(group["row"], text=button_text).pack(side="left")
        return entry

    def _add_small_field(self, parent, label, _kind, values, hint=None):
        group = self._make_field_group(parent, label)
        entry = ttk.Entry(group["row"], width=14)
        for value in values:
            entry.insert(0, value)
        entry.pack(side="left", anchor="w")
        if hint:
            ttk.Label(group["frame"], text=hint, style="Muted.TLabel").pack(anchor="w", pady=(LABEL_GAP, 0))

    def _add_small_spin(self, parent, label, value):
        group = self._make_field_group(parent, label)
        group["frame"].pack_configure(padx=(16, 0))
        spin = ttk.Spinbox(group["row"], from_=1, to=9999, width=8)
        spin.set(value)
        spin.pack(side="left", anchor="w")

    # ------------------------------------------------------------------
    # Temas
    # ------------------------------------------------------------------

    def _on_theme_selected(self, _event=None):
        self.apply_theme(self.theme_var.get())

    def apply_theme(self, display_name):
        theme = next((t for t in THEMES.values() if t["display"] == display_name), None)
        if theme is None:
            raise ValueError("Tema desconhecido: %s" % display_name)
        self.theme_var.set(theme["display"])

        self.configure(bg=theme["bg"])
        style = ttk.Style(self)

        # Frames.
        style.configure("Root.TFrame", background=theme["bg"])
        style.configure(
            "Panel.TFrame",
            background=theme["panel"],
            bordercolor=theme["panel_border"],
            lightcolor=theme["panel_border"],
            darkcolor=theme["panel_border"],
            borderwidth=1,
            relief="solid",
        )

        # Labels.
        style.configure("Header.TLabel", background=theme["bg"], foreground=theme["header_fg"], font=HEADER_FONT)
        style.configure("Sub.TLabel", background=theme["bg"], foreground=theme["sub_fg"], font=UI_FONT)
        style.configure("SelectorHint.TLabel", background=theme["bg"], foreground=theme["muted_fg"], font=("Segoe UI", 9))
        style.configure("PanelTitle.TLabel", background=theme["panel"], foreground=theme["header_fg"], font=TITLE_FONT)
        style.configure("TLabel", background=theme["panel"], foreground=theme["label_fg"], font=UI_FONT)
        style.configure("Muted.TLabel", background=theme["panel"], foreground=theme["muted_fg"], font=("Segoe UI", 9))
        style.configure(
            "Status.TLabel",
            background=theme["status_bg"],
            foreground=theme["status_fg"],
            font=UI_FONT_BOLD,
            padding=(10, 6),
        )

        # Entries / Spinbox (borda >= 3:1 contra o painel; anel de foco no acento).
        for name in ("TEntry", "TSpinbox"):
            style.configure(
                name,
                fieldbackground=theme["field_bg"],
                foreground=theme["field_fg"],
                insertcolor=theme["field_fg"],
                bordercolor=theme["entry_border"],
                lightcolor=theme["entry_border"],
                darkcolor=theme["entry_border"],
            )
            style.map(
                name,
                bordercolor=[
                    ("focus", theme["accent"]),
                    ("disabled", theme["disabled_fg"]),
                ],
                lightcolor=[("focus", theme["accent"])],
                darkcolor=[("focus", theme["accent"])],
                fieldbackground=[("disabled", theme["disabled_bg"])],
                foreground=[("disabled", theme["disabled_fg"])],
            )
        style.configure(
            "TSpinbox",
            fieldbackground=theme["field_bg"],
            foreground=theme["field_fg"],
            arrowcolor=theme["field_fg"],
            background=theme["btn_bg"],
            bordercolor=theme["entry_border"],
            lightcolor=theme["entry_border"],
            darkcolor=theme["entry_border"],
        )
        style.map(
            "TSpinbox",
            fieldbackground=[("disabled", theme["disabled_bg"])],
            foreground=[("disabled", theme["disabled_fg"])],
            bordercolor=[("focus", theme["accent"])],
        )

        # Botoes (altura unica: mesmo font size e BUTTON_PAD_Y em todos).
        style.configure(
            "TButton",
            background=theme["btn_bg"],
            foreground=theme["btn_fg"],
            font=UI_FONT,
            padding=(12, BUTTON_PAD_Y),
            bordercolor=theme["panel_border"],
            lightcolor=theme["btn_bg"],
            darkcolor=theme["btn_bg"],
        )
        style.map(
            "TButton",
            background=[("active", theme["btn_hover"]), ("disabled", theme["disabled_bg"])],
            foreground=[("disabled", theme["disabled_fg"])],
        )
        style.configure(
            "Primary.TButton",
            background=theme["accent"],
            foreground=theme["accent_fg"],
            font=UI_FONT_BOLD,
            padding=(14, BUTTON_PAD_Y),
            bordercolor=theme["accent"],
            lightcolor=theme["accent"],
            darkcolor=theme["accent"],
        )
        style.map(
            "Primary.TButton",
            background=[("active", theme["accent_hover"]), ("disabled", theme["disabled_bg"])],
            foreground=[("disabled", theme["disabled_fg"])],
        )
        style.configure(
            "Danger.TButton",
            background=theme["danger_bg"],
            foreground=theme["danger_fg"],
            font=UI_FONT_BOLD,
            padding=(12, BUTTON_PAD_Y),
            bordercolor=theme["danger_bg"],
            lightcolor=theme["danger_bg"],
            darkcolor=theme["danger_bg"],
        )
        style.map(
            "Danger.TButton",
            background=[("active", theme["danger_hover"]), ("disabled", theme["disabled_bg"])],
            foreground=[("disabled", theme["disabled_fg"])],
        )

        # Checkbutton.
        style.configure(
            "TCheckbutton",
            background=theme["panel"],
            foreground=theme["label_fg"],
            font=UI_FONT,
            focuscolor=theme["panel"],
        )
        style.map(
            "TCheckbutton",
            background=[("active", theme["panel"])],
            indicatorcolor=[("selected", theme["accent"]), ("!selected", theme["field_bg"])],
            indicatormargin=[],
        )

        # Combobox do seletor.
        style.configure(
            "Selector.TCombobox",
            fieldbackground=theme["field_bg"],
            foreground=theme["field_fg"],
            background=theme["btn_bg"],
            arrowcolor=theme["field_fg"],
            bordercolor=theme["entry_border"],
            lightcolor=theme["entry_border"],
            darkcolor=theme["entry_border"],
        )
        style.map(
            "Selector.TCombobox",
            fieldbackground=[("readonly", theme["field_bg"]), ("focus", theme["field_bg"])],
            foreground=[("readonly", theme["field_fg"])],
            bordercolor=[("focus", theme["accent"])],
            arrowcolor=[("active", theme["accent"])],
        )

        # Progressbar (barra de 10px, preenchida em 62%).
        style.configure(
            "Horizontal.TProgressbar",
            background=theme["accent"],
            lightcolor=theme["accent"],
            darkcolor=theme["accent"],
            troughcolor=theme["field_bg"],
            bordercolor=theme["panel_border"],
            thickness=BAR_HEIGHT,
        )

        # Log mono colorido por tag.
        if getattr(self, "log", None) is not None:
            self.log.configure(
                bg=theme["log_bg"],
                fg=theme["log_fg"],
                insertbackground=theme["log_fg"],
                selectbackground=theme["sel_bg"],
                selectforeground=theme["sel_fg"],
            )
            self.log.tag_configure("base", foreground=theme["log_fg"])
            self.log.tag_configure("SUCCESS", foreground=theme["ok"])
            self.log.tag_configure("WARN", foreground=theme["warn"])
            self.log.tag_configure("ERROR", foreground=theme["err"])
            self.log.tag_configure("PATH", foreground=theme["path"])

    def _focus_first_entry(self):
        try:
            self._first_entry.focus_set()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Log de exemplo (inserido uma vez; cores trocam com o tema)
    # ------------------------------------------------------------------

    def _insert_log_examples(self):
        lines = [
            ("base", '> python extract_non_english_text.py "D:/Jogos/Exemplo" --out reports/exemplo --dedupe'),
            ("PATH", "Pasta do jogo: D:/Jogos/Exemplo"),
            ("PATH", "Saida: reports/exemplo_non_english_text.jsonl"),
            ("base", "--- Resultado da varredura ---"),
            ("SUCCESS", "128 textos candidatos encontrados em 42 arquivos"),
            ("WARN", "Arquivo grande ignorado: movies/intro.mp4 (512 MB > 25 MB)"),
            ("ERROR", "Falha ao ler data/Map009.json: permissao negada"),
            ("base", "--- Traducao ---"),
            ("PATH", "Engine: http://localhost:11434/v1 (modelo qwen2.5:7b-instruct)"),
            ("SUCCESS", "Memoria de traducao: 61/100 linhas reutilizadas"),
            ("PROGRESS", "PROGRESS 62/100 linhas"),
            ("WARN", "3 linhas marcadas como needs_review"),
            ("ERROR", "Linha 87 falhou apos 3 tentativas (timeout)"),
            ("SUCCESS", "Relatorios gerados: CSV, JSONL e resumo MD"),
        ]
        for kind, text in lines:
            tag = kind if kind in ("SUCCESS", "WARN", "ERROR", "PATH") else "base"
            if tag == "base":
                self.log.insert("end", text + "\n", ("base",))
            else:
                self.log.insert("end", "[%s] " % kind, (tag,))
                self.log.insert("end", text + "\n", ("base",))
        self.log.see("end")


def main():
    # Nitidez de texto em Windows (melhor esforco, sem dependencias).
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = ThemePreviewApp()
    app.mainloop()


if __name__ == "__main__":
    main()
