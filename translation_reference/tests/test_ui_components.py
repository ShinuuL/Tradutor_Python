import os
import platform
import sys
import tkinter as tk
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from ui_components import (
    CollapsibleSection,
    RoundedPanel,
    ScrollableStep,
    StageNavigation,
    StatusBanner,
)
from ui_state import Stage, StageStatus


class ComponentSmokeTests(unittest.TestCase):
    def setUp(self):
        if platform.system() != "Windows" and not os.environ.get("DISPLAY"):
            self.skipTest("Sem display disponivel")
        self.root = tk.Tk()
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


if __name__ == "__main__":
    unittest.main()
