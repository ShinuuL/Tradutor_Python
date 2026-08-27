import os
import platform
import sys
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from ui_components import (
    CollapsibleSection,
    RoundedPanel,
    ScrollableStep,
    StageNavigation,
    StatusBanner,
    _linux_wheel_units,
    _windows_wheel_units,
    bind_local_mousewheel,
)
from ui_state import Stage, StageStatus


class ComponentSmokeTests(unittest.TestCase):
    def setUp(self):
        if platform.system() != "Windows" and not os.environ.get("DISPLAY"):
            self.skipTest("Sem display disponivel")
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk indisponível: {error}")
        self.addCleanup(self.root.destroy)

    def test_collapsible_section_hides_and_restores_content(self):
        section = CollapsibleSection(self.root, title="Opções avançadas")
        section.pack()
        self.assertFalse(section.expanded)

        section.toggle()
        self.root.update()

        self.assertTrue(section.expanded)
        self.assertTrue(section.content.winfo_ismapped())
        self.assertEqual(section.toggle_button.cget("text"), "Ocultar opções avançadas")

        section.toggle()

        self.assertFalse(section.expanded)
        self.assertFalse(section.content.winfo_ismapped())
        self.assertEqual(section.toggle_button.cget("text"), "Mostrar opções avançadas")

    def test_scrollable_step_updates_scrollregion(self):
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        tk.Label(step.content, text="linha\n" * 100).pack()
        self.root.update_idletasks()

        bounds = tuple(map(int, step.canvas.cget("scrollregion").split()))

        self.assertGreater(bounds[3], step.canvas.winfo_height())

    def test_rounded_panel_hosts_content_over_a_smoothed_background(self):
        panel = RoundedPanel(self.root)
        panel.pack(fill="both", expand=True)
        tk.Label(panel.content, text="Conteúdo").pack()
        self.root.update()

        background = panel.canvas.find_withtag("rounded_background")

        self.assertEqual(len(background), 1)
        self.assertEqual(panel.canvas.type(background[0]), "polygon")
        self.assertEqual(panel.canvas.itemcget(background[0], "smooth"), "true")
        self.assertTrue(panel.content.winfo_ismapped())

    def test_rounded_panel_insets_content_window_from_visible_corners(self):
        panel = RoundedPanel(self.root)
        panel.pack(fill="both", expand=True)
        self.root.update()

        x, y = panel.canvas.coords(panel._content_window)
        width = int(float(panel.canvas.itemcget(panel._content_window, "width")))
        height = int(float(panel.canvas.itemcget(panel._content_window, "height")))

        self.assertGreater(x, 0)
        self.assertGreater(y, 0)
        self.assertLess(width, panel.canvas.winfo_width())
        self.assertLess(height, panel.canvas.winfo_height())

    def test_status_banner_shows_textual_state_and_rejects_unknown_kind(self):
        banner = StatusBanner(self.root)
        banner.pack(fill="x")

        banner.set_state("warning", "Atenção", "Há opções pendentes.")

        self.assertEqual(banner.kind, "warning")
        self.assertEqual(banner.title_label.cget("text"), "Atenção")
        self.assertEqual(banner.detail_label.cget("text"), "Há opções pendentes.")
        with self.assertRaises(ValueError):
            banner.set_state("unknown", "Estado", "")

    def test_stage_navigation_updates_status_without_changing_flow_on_activation(self):
        navigation = StageNavigation(self.root)
        navigation.pack(fill="x")
        navigation.set_status(Stage.PREPARE, StageStatus.READY)

        navigation.set_active(Stage.TRANSLATE)

        self.assertIs(navigation.statuses[Stage.PREPARE], StageStatus.READY)
        self.assertIs(navigation.active_stage, Stage.TRANSLATE)
        self.assertNotEqual(navigation.markers[Stage.PREPARE].cget("text"), "")
        self.assertNotEqual(navigation.labels[Stage.TRANSLATE].cget("text"), "")

    def test_scrollable_step_binds_mousewheel_to_late_and_expanded_children(self):
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        late_child = tk.Label(step.content, text="Criado depois")
        late_child.pack()
        section = CollapsibleSection(step.content, title="Avançado")
        section.pack(fill="x")
        expanded_child = tk.Label(section.content, text="Também depois")
        expanded_child.pack()
        self.root.update()

        section.toggle()
        self.root.update()

        self.assertTrue(late_child.bind("<MouseWheel>"))
        self.assertTrue(expanded_child.bind("<MouseWheel>"))

    def test_scrollable_step_binds_late_child_in_fixed_size_subtree(self):
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        fixed_subtree = tk.Frame(step.content, width=240, height=80)
        fixed_subtree.pack(fill="none")
        fixed_subtree.pack_propagate(False)
        self.root.update()

        late_child = tk.Label(fixed_subtree, text="Mapeado sem redimensionar o pai")
        late_child.pack()
        self.root.update()

        self.assertTrue(late_child.bind("<MouseWheel>"))

    def test_scrollable_step_removes_toplevel_map_binding_when_destroyed(self):
        step = ScrollableStep(self.root)
        binding_id = step._map_binding_id
        self.assertIn(binding_id, self.root.bind("<Map>"))

        step.destroy()

        self.assertNotIn(binding_id, self.root.bind("<Map>"))

    def test_mousewheel_event_calls_yview_scroll(self):
        container = tk.Frame(self.root)
        container.pack()
        child = tk.Label(container, text="Rolável")
        child.pack()
        calls = []

        bind_local_mousewheel(container, lambda units, mode: calls.append((units, mode)))
        self.root.update()
        child.event_generate("<MouseWheel>", delta=120)
        self.root.update()

        self.assertEqual(calls, [(-1, "units")])

    def test_wheel_unit_helpers_validate_missing_zero_and_unrecognized_events(self):
        """Malformed wheel events are ignored without being treated as downward scrolling."""
        self.assertEqual(_windows_wheel_units(SimpleNamespace(delta=120)), -1)
        self.assertEqual(_windows_wheel_units(SimpleNamespace(delta=-120)), 1)
        self.assertIsNone(_windows_wheel_units(SimpleNamespace()))
        self.assertIsNone(_windows_wheel_units(SimpleNamespace(delta=0)))
        self.assertIsNone(_windows_wheel_units(SimpleNamespace(delta="-120")))

        self.assertEqual(_linux_wheel_units(SimpleNamespace(num=4)), -1)
        self.assertEqual(_linux_wheel_units(SimpleNamespace(num=5)), 1)
        self.assertIsNone(_linux_wheel_units(SimpleNamespace()))
        self.assertIsNone(_linux_wheel_units(SimpleNamespace(num=0)))
        self.assertIsNone(_linux_wheel_units(SimpleNamespace(num=6)))

    def test_zero_delta_mousewheel_does_not_move_a_real_scrollable_step(self):
        self.root.geometry("420x260")
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        body = tk.Label(step.content, text="linha\n" * 100)
        body.pack(anchor="w")
        self.root.update()
        step.canvas.yview_moveto(0)
        before = step.canvas.yview()[0]

        body.event_generate("<MouseWheel>", delta=0)
        self.root.update()

        self.assertEqual(step.canvas.yview()[0], before)

    def test_valid_local_wheel_events_scroll_and_stop_later_widget_bindings(self):
        container = tk.Frame(self.root)
        container.pack()
        child = tk.Label(container, text="Rolável")
        child.pack()
        scrolls = []
        later_bindings = []
        bind_local_mousewheel(container, lambda units, mode: scrolls.append((units, mode)))
        child.bind("<MouseWheel>", lambda _event: later_bindings.append("windows"), add="+")
        child.bind("<Button-4>", lambda _event: later_bindings.append("linux"), add="+")
        self.root.update()

        child.event_generate("<MouseWheel>", delta=-120)
        child.event_generate("<Button-4>")
        self.root.update()

        self.assertEqual(scrolls, [(1, "units"), (-1, "units")])
        self.assertEqual(later_bindings, [])

    def test_scrollable_step_scrolls_only_its_content_for_windows_and_linux_wheel_events(self):
        """A generic descendant scrolls the step with either platform event."""
        self.root.geometry("420x260")
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        body = tk.Label(step.content, text="linha\n" * 100)
        body.pack(anchor="w")
        self.root.update()
        step.canvas.yview_moveto(0)

        before_windows = step.canvas.yview()[0]
        body.event_generate("<MouseWheel>", delta=-120)
        self.root.update()
        after_windows = step.canvas.yview()[0]

        body.event_generate("<Button-4>")
        self.root.update()
        after_linux_up = step.canvas.yview()[0]
        body.event_generate("<Button-5>")
        self.root.update()
        after_linux_down = step.canvas.yview()[0]

        self.assertGreater(after_windows, before_windows)
        self.assertLess(after_linux_up, after_windows)
        self.assertGreater(after_linux_down, after_linux_up)

    def test_scrollable_step_preserves_text_widget_native_wheel_scrolling(self):
        """A scrollable child keeps its own class binding instead of scrolling the step."""
        self.root.geometry("420x260")
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        text = tk.Text(step.content, height=6)
        text.insert("1.0", "linha\n" * 100)
        text.pack(fill="x")
        tk.Label(step.content, text="preenchimento\n" * 100).pack(anchor="w")
        self.root.update()
        step.canvas.yview_moveto(0)
        text.yview_moveto(0)

        step_before = step.canvas.yview()[0]
        text_before = text.yview()[0]
        text.event_generate("<MouseWheel>", delta=-120)
        self.root.update()

        self.assertEqual(step.canvas.yview()[0], step_before)
        self.assertGreater(text.yview()[0], text_before)

    def test_scrollable_step_resize_synchronizes_content_width(self):
        step = ScrollableStep(self.root)
        step.pack(fill="both", expand=True)
        self.root.geometry("640x320")
        self.root.update()

        width = int(float(step.canvas.itemcget(step._content_window, "width")))

        self.assertEqual(width, step.canvas.winfo_width())

    def test_collapsible_section_uses_supplied_title_in_toggle_text(self):
        section = CollapsibleSection(self.root, title="Configurações extras")
        section.pack()

        self.assertEqual(section.toggle_button.cget("text"), "Mostrar configurações extras")
        section.toggle()
        self.assertEqual(section.toggle_button.cget("text"), "Ocultar configurações extras")


if __name__ == "__main__":
    unittest.main()
