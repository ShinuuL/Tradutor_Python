# Fluent Night UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remodelar a GUI Tkinter do TradutorDGames como um fluxo Fluent Night em quatro etapas, preservando todos os comportamentos e corrigindo a rolagem no executável.

**Architecture:** A janela deixa de empilhar toda a UI em um Canvas global. Um shell fixo mantém navegação lateral, área central e atividade recente; um controlador puro determina os estados das etapas, enquanto componentes Tkinter/ttk próprios fornecem painéis arredondados, banners, recolhimento e scroll local.

**Tech Stack:** Python 3.14+, biblioteca padrão (`tkinter`, `ttk`, `unittest`), PyInstaller em modo `onedir`, Windows 11.

**Spec:** `docs/superpowers/specs/2026-08-26-fluent-night-ui-design.md`

## Global Constraints

- Não adicionar dependências externas nem assets obrigatórios.
- Não alterar adapters, validators, formatos de relatório ou contratos da CLI.
- Não escrever em pastas reais de jogos durante desenvolvimento ou teste.
- Preservar varredura, parada, tradução, retry, filtros, relatórios, logs, aplicação e restauração.
- Preservar as confirmações modais e a flag explícita de aprovação para qualquer escrita no jogo.
- Usar `#0B111B`, `#101A27`, `#182635`, `#2A4055`, `#0F1A26`, `#EAF4FC`, `#91A6B8`, `#66D4FF`, `#74E6CB`, `#F2C66D` e `#FF7C86` como tokens iniciais.
- Usar Segoe UI na interface e Cascadia Code com fallback Consolas em logs e caminhos.
- Não usar cor como único indicador de estado; combinar texto e marcador.
- Não usar `bind_all("<MouseWheel>", ...)`.
- Usar `py -3.14` nos comandos Windows; se o launcher não localizar o runtime, interromper a execução e instalar/selecionar Python 3.14 antes de continuar.

---

### Task 1: Modelo puro de progressão do fluxo

**Files:**
- Create: `translation_reference/app/ui_state.py`
- Create: `translation_reference/tests/test_ui_state.py`

**Interfaces:**
- Consumes: nenhum módulo da GUI.
- Produces: `Stage`, `StageStatus`, `WorkflowState`, `WorkflowState.can_open(stage)`, `WorkflowState.requirement(stage)`, `mark_scan_started()`, `mark_scan_finished(success)`, `mark_translation_started()`, `mark_translation_finished(success, has_review)`, `mark_apply_finished(success)`.

- [ ] **Step 1: Escrever testes de estado inicial e bloqueios**

```python
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from ui_state import Stage, StageStatus, WorkflowState


class WorkflowStateTests(unittest.TestCase):
    def test_initial_state_only_prepare_is_ready(self):
        state = WorkflowState()
        self.assertIs(state.status(Stage.PREPARE), StageStatus.READY)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.LOCKED)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.LOCKED)
        self.assertIs(state.status(Stage.APPLY), StageStatus.LOCKED)
        self.assertEqual(state.requirement(Stage.TRANSLATE), "Conclua uma varredura para continuar.")
```

- [ ] **Step 2: Escrever testes das transições de sucesso e erro**

```python
    def test_successful_scan_unlocks_translation(self):
        state = WorkflowState()
        state.mark_scan_started()
        self.assertIs(state.status(Stage.PREPARE), StageStatus.RUNNING)
        state.mark_scan_finished(success=True)
        self.assertIs(state.status(Stage.PREPARE), StageStatus.COMPLETE)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.READY)

    def test_translation_with_review_unlocks_review_and_apply(self):
        state = WorkflowState()
        state.mark_scan_finished(success=True)
        state.mark_translation_started()
        state.mark_translation_finished(success=True, has_review=True)
        self.assertIs(state.status(Stage.TRANSLATE), StageStatus.COMPLETE)
        self.assertIs(state.status(Stage.REVIEW), StageStatus.READY)
        self.assertIs(state.status(Stage.APPLY), StageStatus.READY)

    def test_failed_operation_stays_recoverable(self):
        state = WorkflowState()
        state.mark_scan_started()
        state.mark_scan_finished(success=False)
        self.assertIs(state.status(Stage.PREPARE), StageStatus.ERROR)
        self.assertTrue(state.can_open(Stage.PREPARE))
        self.assertFalse(state.can_open(Stage.TRANSLATE))
```

- [ ] **Step 3: Rodar o teste e confirmar a falha esperada**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_state -v`  
Expected: FAIL com `ModuleNotFoundError: No module named 'ui_state'`.

- [ ] **Step 4: Implementar o modelo mínimo**

```python
from dataclasses import dataclass, field
from enum import Enum


class Stage(str, Enum):
    PREPARE = "prepare"
    TRANSLATE = "translate"
    REVIEW = "review"
    APPLY = "apply"


class StageStatus(str, Enum):
    LOCKED = "locked"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class WorkflowState:
    _statuses: dict = field(default_factory=lambda: {
        Stage.PREPARE: StageStatus.READY,
        Stage.TRANSLATE: StageStatus.LOCKED,
        Stage.REVIEW: StageStatus.LOCKED,
        Stage.APPLY: StageStatus.LOCKED,
    })

    def status(self, stage):
        return self._statuses[stage]

    def can_open(self, stage):
        return self.status(stage) is not StageStatus.LOCKED

    def requirement(self, stage):
        messages = {
            Stage.TRANSLATE: "Conclua uma varredura para continuar.",
            Stage.REVIEW: "Conclua uma tradução para revisar os resultados.",
            Stage.APPLY: "Conclua uma tradução válida antes de aplicar.",
        }
        return messages.get(stage, "")

    def mark_scan_started(self):
        self._statuses[Stage.PREPARE] = StageStatus.RUNNING

    def mark_scan_finished(self, success):
        self._statuses[Stage.PREPARE] = StageStatus.COMPLETE if success else StageStatus.ERROR
        if success:
            self._statuses[Stage.TRANSLATE] = StageStatus.READY

    def mark_translation_started(self):
        self._statuses[Stage.TRANSLATE] = StageStatus.RUNNING

    def mark_translation_finished(self, success, has_review):
        self._statuses[Stage.TRANSLATE] = StageStatus.COMPLETE if success else StageStatus.ERROR
        if success and has_review:
            self._statuses[Stage.REVIEW] = StageStatus.READY
            self._statuses[Stage.APPLY] = StageStatus.READY

    def mark_apply_finished(self, success):
        self._statuses[Stage.APPLY] = StageStatus.COMPLETE if success else StageStatus.ERROR
```

- [ ] **Step 5: Rodar os testes do modelo**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_state -v`  
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add translation_reference/app/ui_state.py translation_reference/tests/test_ui_state.py
git commit -m "feat: modelar progressao das etapas da UI"
```

---

### Task 2: Tokens Fluent Night e estilos ttk

**Files:**
- Create: `translation_reference/app/ui_theme.py`
- Create: `translation_reference/tests/test_ui_theme.py`

**Interfaces:**
- Consumes: instância `tk.Misc` ou `ttk.Style`.
- Produces: `COLORS`, `SPACING`, `RADII`, `contrast_ratio(foreground, background) -> float`, `configure_fluent_night(root) -> ttk.Style`, `mono_font(root) -> tuple`.

- [ ] **Step 1: Escrever testes dos tokens e contrastes obrigatórios**

```python
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
```

- [ ] **Step 2: Rodar o teste e confirmar a falha esperada**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_theme -v`  
Expected: FAIL porque `ui_theme` ainda não existe.

- [ ] **Step 3: Implementar tokens e cálculo de contraste**

```python
COLORS = {
    "window": "#0B111B", "surface": "#101A27", "panel": "#182635",
    "border": "#2A4055", "field": "#0F1A26", "text": "#EAF4FC",
    "muted": "#91A6B8", "accent": "#66D4FF", "success": "#74E6CB",
    "warning": "#F2C66D", "error": "#FF7C86",
}
SPACING = {"xs": 4, "sm": 8, "md": 12, "panel": 16, "page": 24}
RADII = {"control": 8, "panel": 14}


def _luminance(hex_color):
    values = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground, background):
    first, second = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)
```

- [ ] **Step 4: Configurar estilos centralizados**

Implementar `configure_fluent_night(root)` com os estilos `App.TFrame`, `Surface.TFrame`, `TLabel`, `Title.TLabel`, `Muted.TLabel`, `TEntry`, `TSpinbox`, `TButton`, `Primary.TButton`, `Danger.TButton`, `TCheckbutton`, `Treeview`, `Treeview.Heading` e `Horizontal.TProgressbar`. Cada `style.map` deve incluir estados `active`, `pressed`, `focus` e `disabled` quando o widget os suporta.

- [ ] **Step 5: Testar e formatar**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_theme -v`  
Expected: todos PASS.  
Run: `py -3.14 -m compileall -q translation_reference/app/ui_theme.py`  
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add translation_reference/app/ui_theme.py translation_reference/tests/test_ui_theme.py
git commit -m "feat: adicionar tokens e estilos Fluent Night"
```

---

### Task 3: Componentes reutilizáveis e scroll local

**Files:**
- Create: `translation_reference/app/ui_components.py`
- Create: `translation_reference/tests/test_ui_components.py`

**Interfaces:**
- Consumes: `COLORS`, `RADII`, `SPACING`, `Stage`, `StageStatus`.
- Produces: `RoundedPanel`, `CollapsibleSection`, `StatusBanner`, `StageNavigation`, `ScrollableStep`, `bind_local_mousewheel(widget, yview_scroll)`.

- [ ] **Step 1: Escrever smoke tests com skip em ambiente headless**

```python
class ComponentSmokeTests(unittest.TestCase):
    def setUp(self):
        if platform.system() != "Windows" and not os.environ.get("DISPLAY"):
            self.skipTest("Sem display disponivel")
        self.root = tk.Tk()

    def tearDown(self):
        self.root.destroy()

    def test_collapsible_section_hides_and_restores_content(self):
        section = CollapsibleSection(self.root, title="Opções avançadas")
        section.pack()
        self.assertFalse(section.expanded)
        section.toggle()
        self.assertTrue(section.expanded)
        self.assertTrue(section.content.winfo_ismapped())

    def test_scrollable_step_updates_scrollregion(self):
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        ttk.Label(step.content, text="linha\n" * 100).pack()
        self.root.update_idletasks()
        bounds = tuple(map(int, step.canvas.cget("scrollregion").split()))
        self.assertGreater(bounds[3], step.canvas.winfo_height())
```

- [ ] **Step 2: Rodar os testes e confirmar a falha esperada**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_components -v`  
Expected: FAIL porque `ui_components` ainda não existe.

- [ ] **Step 3: Implementar `RoundedPanel` e `CollapsibleSection`**

`RoundedPanel` deve desenhar um polígono suavizado no Canvas e hospedar um `ttk.Frame` em `self.content`. `CollapsibleSection` deve iniciar recolhida, expor `expanded: bool`, `content: ttk.Frame` e atualizar o texto do botão entre `Mostrar opções avançadas` e `Ocultar opções avançadas`.

- [ ] **Step 4: Implementar banner e navegação**

`StatusBanner.set_state(kind, title, detail)` deve aceitar apenas `info`, `success`, `warning` e `error`, sempre mostrando título textual. `StageNavigation.set_status(stage, status)` deve atualizar marcador e rótulo; `set_active(stage)` deve aplicar foco visual sem alterar o estado do fluxo.

- [ ] **Step 5: Implementar `ScrollableStep` sem binding global**

```python
def bind_local_mousewheel(widget, yview_scroll):
    def on_wheel(event):
        units = -1 if event.delta > 0 else 1
        yview_scroll(units, "units")
        return "break"
    widget.bind("<MouseWheel>", on_wheel, add="+")
    for child in widget.winfo_children():
        bind_local_mousewheel(child, yview_scroll)
```

O `<Configure>` de `content` deve executar `canvas.configure(scrollregion=canvas.bbox("all"))`; o `<Configure>` do Canvas deve manter a largura da janela interna igual à largura disponível.

- [ ] **Step 6: Rodar testes e compilação**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_components -v`  
Expected: PASS ou SKIP somente dos testes gráficos quando não houver display.  
Run: `py -3.14 -m compileall -q translation_reference/app/ui_components.py`  
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add translation_reference/app/ui_components.py translation_reference/tests/test_ui_components.py
git commit -m "feat: criar componentes Fluent Night reutilizaveis"
```

---

### Task 4: Shell fixo e controlador de navegação

**Files:**
- Modify: `translation_reference/app/text_scanner_app.py:132-365`
- Modify: `translation_reference/tests/test_app_helpers.py:130-175`

**Interfaces:**
- Consumes: `configure_fluent_night`, `StageNavigation`, `StatusBanner`, `WorkflowState`.
- Produces: `TextScannerApp.show_stage(stage)`, `TextScannerApp._refresh_stage_navigation()`, `self.stage_frames`, `self.activity_banner`.

- [ ] **Step 1: Substituir o teste que exige o Canvas global por regressões do shell**

```python
def test_staged_shell_exists_without_global_scroll_canvas(self):
    if not self._has_display():
        self.skipTest("Sem display disponivel")
    from text_scanner_app import TextScannerApp
    from ui_state import Stage
    app = TextScannerApp()
    self.assertFalse(hasattr(app, "_canvas"))
    self.assertEqual(set(app.stage_frames), set(Stage))
    self.assertEqual(app.active_stage, Stage.PREPARE)
    app.destroy()
```

- [ ] **Step 2: Rodar o teste e confirmar a falha esperada**

Run: `py -3.14 -m unittest translation_reference.tests.test_app_helpers.GuiSmokeTests.test_staged_shell_exists_without_global_scroll_canvas -v`  
Expected: FAIL porque o app ainda cria `_canvas` e não possui `stage_frames`.

- [ ] **Step 3: Centralizar inicialização de tema e estado**

No `__init__`, criar `self.workflow = WorkflowState()`, `self.active_stage = Stage.PREPARE`, chamar `configure_fluent_night(self)` e manter todas as variáveis Tk e referências de processo já existentes.

- [ ] **Step 4: Trocar `_build_layout` pelo shell fixo**

Usar `self.grid_rowconfigure(0, weight=1)` e `self.grid_columnconfigure(1, weight=1)`. Posicionar `StageNavigation` na coluna 0, uma `ttk.Frame` central na coluna 1 e `StatusBanner` na linha inferior da coluna 1. Criar quatro frames e guardá-los em `self.stage_frames`.

- [ ] **Step 5: Implementar navegação bloqueada e ativa**

```python
def show_stage(self, stage):
    if not self.workflow.can_open(stage):
        self.activity_banner.set_state("info", "Etapa ainda não disponível", self.workflow.requirement(stage))
        return False
    self.stage_frames[self.active_stage].grid_remove()
    self.active_stage = stage
    self.stage_frames[stage].grid()
    self.stage_navigation.set_active(stage)
    return True
```

- [ ] **Step 6: Remover `_on_canvas_configure`, `_on_mousewheel` e o `bind_all`**

Confirmar com: `rg -n "bind_all|_on_canvas_configure|_on_mousewheel" translation_reference/app/text_scanner_app.py`  
Expected: nenhum resultado.

- [ ] **Step 7: Rodar smoke tests**

Run: `py -3.14 -m unittest translation_reference.tests.test_app_helpers.GuiSmokeTests -v`  
Expected: todos PASS.

- [ ] **Step 8: Commit**

```bash
git add translation_reference/app/text_scanner_app.py translation_reference/tests/test_app_helpers.py
git commit -m "refactor: adotar shell fixo com navegacao em etapas"
```

---

### Task 5: Migrar as etapas Preparar e Traduzir

**Files:**
- Modify: `translation_reference/app/text_scanner_app.py:342-552`
- Create: `translation_reference/tests/test_ui_commands.py`

**Interfaces:**
- Consumes: frames de `self.stage_frames`, handlers `choose_game_folder`, `choose_output_file`, `run_scan`, `stop_scan`, `choose_scan_jsonl`, `run_translation`, `stop_translation`.
- Produces: `_build_prepare_stage(parent)`, `_build_translate_stage(parent)`, `prepare_advanced`, `translate_advanced`.

- [ ] **Step 1: Escrever testes de compatibilidade dos comandos**

Instanciar o app apenas quando houver display, preencher as variáveis e verificar que `build_command()` e `build_translation_command()` mantêm executável, script, paths, flags `--dedupe`, `--skip-plugin-js`, `--tm`, engine URL e modelo.

```python
self.assertIn("--dedupe", app.build_command())
self.assertIn("--skip-plugin-js", app.build_command())
self.assertIn("--engine-url", app.build_translation_command())
self.assertIn("--engine-model", app.build_translation_command())
```

- [ ] **Step 2: Rodar os testes antes da migração**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_commands -v`  
Expected: PASS, registrando o contrato funcional atual.

- [ ] **Step 3: Construir a etapa Preparar**

Mover os mesmos `textvariable`, `variable` e `command` para `_build_prepare_stage`. Manter pasta e relatório visíveis; colocar `extra_ext`, `max_file_mb`, `context_chars`, `batch_size`, `dedupe` e `skip_plugin_js` dentro de `self.prepare_advanced.content`.

- [ ] **Step 4: Construir a etapa Traduzir**

Manter scan JSONL, pasta, modelo, memória, progresso e botões visíveis. Colocar `engine_url` dentro de `self.translate_advanced.content`. Preservar os atributos `translate_button`, `translate_stop_button`, `progress` e `translate_status_text` usados pelos callbacks existentes.

- [ ] **Step 5: Rodar testes de comandos e smoke**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_commands translation_reference.tests.test_app_helpers.GuiSmokeTests -v`  
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add translation_reference/app/text_scanner_app.py translation_reference/tests/test_ui_commands.py
git commit -m "feat: migrar preparo e traducao para etapas Fluent Night"
```

---

### Task 6: Migrar Revisar, Aplicar e o log completo

**Files:**
- Modify: `translation_reference/app/text_scanner_app.py:537-628,1144-1259`
- Modify: `translation_reference/tests/test_app_helpers.py`

**Interfaces:**
- Consumes: `_preview_rows`, `_preview_filter`, `_update_tree_display`, `_run_retry`, `run_apply`, `run_restore`, `open_report`, `clear_log`.
- Produces: `_build_review_stage(parent)`, `_build_apply_stage(parent)`, `open_full_log()`, `self._preview_tree`, `self.apply_summary`.

- [ ] **Step 1: Escrever smoke test dos controles preservados**

```python
expected = (
    "retry_button", "apply_button", "restore_button", "_preview_tree",
    "_filter_combo", "log", "open_csv_button", "open_jsonl_button",
)
for name in expected:
    self.assertTrue(hasattr(app, name), name)
```

- [ ] **Step 2: Rodar o teste e confirmar a falha durante a migração**

Run: `py -3.14 -m unittest translation_reference.tests.test_app_helpers.GuiSmokeTests.test_functional_controls_survive_remodel -v`  
Expected: FAIL até os painéis novos exporem todos os atributos.

- [ ] **Step 3: Construir a etapa Revisar**

Mover filtro, contador, Treeview e scrollbar vertical para `_build_review_stage`. Preservar os IDs de coluna `status`, `file`, `line`, `source` e `translated`, além das chamadas a `_on_filter_change` e `_run_retry`.

- [ ] **Step 4: Construir a etapa Aplicar**

Criar resumo textual ligado a `StringVar`, mantendo `apply_button` e `restore_button`. Exibir aviso permanente com texto “Aplicar e restaurar modificam arquivos do jogo e exigem confirmação.”

- [ ] **Step 5: Transformar o log principal em atividade compacta**

Preservar `self.log` como `tk.Text` dentro de um `tk.Toplevel` criado e imediatamente ocultado com `withdraw()` durante `_build_layout`, para que `append_log()` continue funcionando antes da primeira abertura. `open_full_log()` chama `deiconify()`, `lift()` e `focus_set()`. Fechar a janela executa `withdraw()` em vez de destruir o widget. A faixa inferior mostra apenas `self.status`; ações “Abrir log” e “Limpar log” continuam disponíveis.

- [ ] **Step 6: Rodar testes de preview e smoke**

Run: `py -3.14 -m unittest translation_reference.tests.test_app_helpers -v`  
Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add translation_reference/app/text_scanner_app.py translation_reference/tests/test_app_helpers.py
git commit -m "feat: migrar revisao aplicacao e logs para novas etapas"
```

---

### Task 7: Integrar estados, banners e passagem para a próxima etapa

**Files:**
- Modify: `translation_reference/app/text_scanner_app.py:695-939,1014-1143,1252-1259`
- Modify: `translation_reference/tests/test_ui_state.py`
- Modify: `translation_reference/tests/test_ui_commands.py`

**Interfaces:**
- Consumes: `WorkflowState`, `StageNavigation`, `StatusBanner`.
- Produces: `_set_stage_feedback(stage, kind, title, detail)`, `_recommend_next_stage(stage)`.

- [ ] **Step 1: Testar o mapeamento de conclusão para a próxima etapa**

```python
def test_scan_success_recommends_translation(self):
    app._finish_run(0)
    self.assertTrue(app.workflow.can_open(Stage.TRANSLATE))
    self.assertEqual(app.recommended_stage, Stage.TRANSLATE)


def test_translation_success_recommends_review(self):
    with mock.patch.object(app, "_populate_preview_tree"):
        app._progress_total = 1
        app._finish_translation(0, ["PROGRESS 1/1"])
    self.assertTrue(app.workflow.can_open(Stage.REVIEW))
    self.assertEqual(app.recommended_stage, Stage.REVIEW)
```

- [ ] **Step 2: Rodar os testes e confirmar a falha esperada**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_commands -v`  
Expected: FAIL porque `recommended_stage` ainda não é atualizado.

- [ ] **Step 3: Marcar início e conclusão em todos os handlers**

- `run_scan` chama `mark_scan_started()`.
- `_finish_run` chama `mark_scan_finished(code == 0)`.
- `run_translation` chama `mark_translation_started()`.
- `_finish_translation` chama `mark_translation_finished(code == 0, csv_path.is_file())`.
- `_finish_apply` chama `mark_apply_finished(outcome == "success")`.
- `_finish_retry` atualiza Revisar para `READY`, `WARNING` ou `ERROR` sem bloquear Aplicar se já estava liberada.

- [ ] **Step 4: Adicionar banners integrados**

Sucesso deve informar a próxima etapa, erro deve apontar o log e warning deve informar o que ainda precisa de revisão. `messagebox.showinfo` de conclusão rotineira será substituído pelo banner; `messagebox.showwarning/showerror` impeditivos e as confirmações destrutivas permanecem.

- [ ] **Step 5: Atualizar estados de botões e navegação em um único método**

`_refresh_stage_navigation()` deve iterar por `Stage`, chamar `stage_navigation.set_status(stage, workflow.status(stage))` e habilitar/desabilitar ações com base no mesmo estado, evitando regras duplicadas em cada callback.

- [ ] **Step 6: Rodar testes do fluxo e regressão completa da app**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_state translation_reference.tests.test_ui_commands translation_reference.tests.test_app_helpers -v`  
Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add translation_reference/app/text_scanner_app.py translation_reference/tests/test_ui_state.py translation_reference/tests/test_ui_commands.py
git commit -m "feat: integrar feedback e progressao entre etapas"
```

---

### Task 8: Regressões de scroll, redimensionamento e teclado

**Files:**
- Modify: `translation_reference/tests/test_ui_components.py`
- Modify: `translation_reference/tests/test_app_helpers.py`
- Modify: `translation_reference/app/ui_components.py`
- Modify: `translation_reference/app/text_scanner_app.py`

**Interfaces:**
- Consumes: `ScrollableStep`, Treeview e Toplevel do log.
- Produces: comportamento verificável de scroll local e foco.

- [ ] **Step 1: Adicionar teste que proíbe bindings globais**

```python
source = Path(APP_DIR / "text_scanner_app.py").read_text(encoding="utf-8")
self.assertNotIn("bind_all", source)
self.assertNotIn("unbind_all", source)
```

- [ ] **Step 2: Adicionar teste de wheel sobre Treeview**

Criar 50 linhas, registrar `first_before = app._preview_tree.yview()[0]`, gerar `event_generate("<MouseWheel>", delta=-120)`, chamar `update()` e verificar que `app._preview_tree.yview()[0] > first_before`.

- [ ] **Step 3: Adicionar teste de dimensão mínima e reflow**

Definir `app.geometry("900x650")`, abrir cada etapa, chamar `update_idletasks()` e verificar que cada frame central permanece dentro da largura e altura da janela. Textos e botões críticos devem ter `winfo_rootx() + winfo_width() <= app.winfo_rootx() + app.winfo_width()`.

- [ ] **Step 4: Adicionar teste da ordem básica de foco**

Verificar que botões de navegação, primeiro campo da etapa e ação primária aceitam `focus_set()` e que o foco não cai em um Canvas decorativo.

- [ ] **Step 5: Rodar testes e corrigir somente as falhas observadas**

Run: `py -3.14 -m unittest translation_reference.tests.test_ui_components translation_reference.tests.test_app_helpers -v`  
Expected: todos PASS; testes gráficos podem ser SKIP apenas em ambiente sem display.

- [ ] **Step 6: Executar formatter e análise disponível**

Run: `py -3.14 -m compileall -q translation_reference/app translation_reference/tests`  
Expected: exit 0.  
Run: `prettier --check docs/superpowers/specs/2026-08-26-fluent-night-ui-design.md docs/superpowers/plans/2026-08-26-fluent-night-ui.md`  
Expected: exit 0; se Prettier não estiver instalado, registrar a indisponibilidade sem instalar dependência no projeto.  
Executar diagnóstico LSP nos quatro módulos alterados se o harness disponibilizar LSP; expected: zero erros.

- [ ] **Step 7: Commit**

```bash
git add translation_reference/app/ui_components.py translation_reference/app/text_scanner_app.py translation_reference/tests/test_ui_components.py translation_reference/tests/test_app_helpers.py
git commit -m "test: cobrir scroll redimensionamento e teclado"
```

---

### Task 9: Empacotamento e verificação final no `.exe`

**Files:**
- Modify: `translation_reference/build/build_app.spec:20-54`
- Modify: `translation_reference/build/README_BUILD.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `ui_state`, `ui_theme`, `ui_components`, `TextScannerApp`.
- Produces: `dist/TradutorDGames/TradutorDGames.exe` verificado.

- [ ] **Step 1: Declarar imports da UI no spec do PyInstaller**

Adicionar a `hiddenimports`:

```python
"ui_components",
"ui_state",
"ui_theme",
```

- [ ] **Step 2: Rodar toda a suíte antes do build**

Run: `py -3.14 -m unittest discover -s translation_reference/tests -p "test_*.py" -v`  
Expected: todos os testes executáveis PASS; somente skips documentados por display ou fixture opcional.

- [ ] **Step 3: Construir a aplicação**

Run: `py -3.14 translation_reference/build/build.py --target app`  
Expected: exit 0 e arquivo `dist/TradutorDGames/TradutorDGames.exe` existente.

- [ ] **Step 4: Executar smoke manual seguro no `.exe`**

Abrir `dist/TradutorDGames/TradutorDGames.exe` e verificar, sem acionar “Aplicar no jogo”:

1. janela inicia em Preparar;
2. Opções avançadas abre e fecha sem salto de layout;
3. tentativa de abrir etapa bloqueada mostra requisito dentro da UI;
4. redimensionamento até 900×650 não cria scroll global nem corta ações;
5. wheel sobre Revisar move somente a tabela;
6. wheel sobre o log completo move somente o log;
7. Tab percorre navegação, campos e ação primária com foco visível;
8. fechar e reabrir o log não perde mensagens.

- [ ] **Step 5: Executar fluxo controlado com fixtures**

Selecionar `translation_reference/tests/fixtures/game` como origem e gravar relatórios somente em `reports/`. Verificar transições Preparar → Traduzir → Revisar. Não executar aplicação nem restauração contra uma pasta real de jogo.

- [ ] **Step 6: Capturar evidências visuais**

Capturar a janela em 980×840 e 900×650 nos estados inicial, operação em andamento, conclusão e erro. Comparar hierarquia, contraste, alinhamento, foco e ausência de clipping com o mockup Fluent Night.

- [ ] **Step 7: Atualizar documentação de uso e build**

No README principal, substituir a descrição da GUI por “fluxo em quatro etapas: Preparar, Traduzir, Revisar e Aplicar”. No README de build, registrar que o smoke do `.exe` deve incluir scroll local e navegação por teclado.

- [ ] **Step 8: Rodar verificação final**

Run: `git diff --check`  
Expected: nenhum erro.  
Run: `py -3.14 -m unittest discover -s translation_reference/tests -p "test_*.py" -v`  
Expected: suíte verde.  
Run: `py -3.14 translation_reference/build/build.py --target app`  
Expected: build verde.

- [ ] **Step 9: Commit**

```bash
git add README.md translation_reference/build/README_BUILD.md translation_reference/build/build_app.spec
git commit -m "build: validar interface Fluent Night no executavel"
```

---

## Completion Gate

- Todos os nove tasks possuem commits independentes e revisáveis.
- A suíte completa passa após o último commit.
- O `.exe` abre e percorre as quatro etapas sem scroll global.
- Treeview e log respondem à roda do mouse sem movimentar outro componente.
- Mensagens de progressão aparecem dentro da UI.
- Confirmações de aplicar e restaurar permanecem modais e protegidas.
- Nenhuma tradução foi escrita em pasta real de jogo durante a verificação.
