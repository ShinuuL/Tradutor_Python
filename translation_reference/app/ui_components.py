"""Reusable Fluent Night interface components."""

import tkinter as tk
from tkinter import ttk

from ui_state import Stage, StageStatus
from ui_theme import COLORS, RADII, SPACING


def bind_local_mousewheel(widget, yview_scroll):
    """Bind mouse-wheel scrolling to *widget* and its current descendants."""
    widget._local_mousewheel_yview = yview_scroll
    if not getattr(widget, "_has_local_mousewheel", False):
        def on_wheel(event, target=widget):
            units = -1 if event.delta > 0 else 1
            target._local_mousewheel_yview(units, "units")
            return "break"

        widget.bind("<MouseWheel>", on_wheel, add="+")
        widget._has_local_mousewheel = True
    for child in widget.winfo_children():
        bind_local_mousewheel(child, yview_scroll)


class CollapsibleSection(ttk.Frame):
    """A compact section whose optional content starts hidden."""

    def __init__(self, master, *, title):
        super().__init__(master, style="Surface.TFrame")
        self.title = title
        self.expanded = False
        self.toggle_button = ttk.Button(
            self,
            text=f"Mostrar {self.title.lower()}",
            command=self.toggle,
        )
        self.toggle_button.pack(anchor="w")
        self.content = ttk.Frame(self, style="Surface.TFrame")

    def toggle(self):
        """Show or hide the optional content."""
        self.expanded = not self.expanded
        if self.expanded:
            self.content.pack(fill="x", pady=(SPACING["sm"], 0))
            self.toggle_button.configure(text=f"Ocultar {self.title.lower()}")
            self._refresh_ancestor_mousewheel_bindings()
        else:
            self.content.pack_forget()
            self.toggle_button.configure(text=f"Mostrar {self.title.lower()}")

    def _refresh_ancestor_mousewheel_bindings(self):
        widget = self
        while widget.winfo_parent():
            widget = widget.nametowidget(widget.winfo_parent())
            refresh = getattr(widget, "_refresh_local_mousewheel", None)
            if refresh:
                refresh()
                return


class ScrollableStep(ttk.Frame):
    """A step container that scrolls only while its own widgets receive input."""

    def __init__(self, master):
        super().__init__(master, style="Surface.TFrame")
        self.canvas = tk.Canvas(
            self,
            background=COLORS["surface"],
            highlightthickness=0,
            borderwidth=0,
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = ttk.Frame(self.canvas, style="Surface.TFrame", padding=SPACING["panel"])
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._update_scrollregion, add="+")
        self.content.bind("<Configure>", self._refresh_local_mousewheel_bindings, add="+")
        self.canvas.bind("<Configure>", self._fit_content_width, add="+")
        self.content._refresh_local_mousewheel = self._refresh_local_mousewheel_bindings
        self._toplevel = self.winfo_toplevel()
        self._map_binding_id = self._toplevel.bind("<Map>", self._on_descendant_map, add="+")
        self.bind("<Destroy>", self._remove_toplevel_map_binding, add="+")
        self._refresh_local_mousewheel_bindings()

    def _update_scrollregion(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_content_width(self, event):
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _refresh_local_mousewheel_bindings(self, _event=None):
        bind_local_mousewheel(self.content, self.canvas.yview_scroll)

    def _on_descendant_map(self, event):
        if self._contains_widget(event.widget):
            self._refresh_local_mousewheel_bindings()

    def _contains_widget(self, widget):
        while widget.winfo_parent():
            if widget is self:
                return True
            widget = widget.nametowidget(widget.winfo_parent())
        return widget is self

    def _remove_toplevel_map_binding(self, event):
        if event.widget is self and self._map_binding_id:
            self._toplevel.unbind("<Map>", self._map_binding_id)
            self._map_binding_id = None


class RoundedPanel(ttk.Frame):
    """A panel with a smooth Canvas background and a standard ttk content frame."""

    def __init__(self, master, *, padding=SPACING["panel"]):
        super().__init__(master, style="Panel.TFrame")
        self.canvas = tk.Canvas(
            self,
            background=COLORS["panel"],
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.content = ttk.Frame(self.canvas, style="Panel.TFrame", padding=padding)
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self._redraw, add="+")

    def _redraw(self, event):
        width, height = event.width, event.height
        radius = min(RADII["panel"], width // 2, height // 2)
        inset = max(1, radius)
        points = (
            radius, 0,
            width - radius, 0,
            width, 0,
            width, radius,
            width, height - radius,
            width, height,
            width - radius, height,
            radius, height,
            0, height,
            0, height - radius,
            0, radius,
            0, 0,
        )
        self.canvas.delete("rounded_background")
        self.canvas.create_polygon(
            points,
            fill=COLORS["panel"],
            outline=COLORS["border"],
            smooth=True,
            tags="rounded_background",
        )
        self.canvas.tag_lower("rounded_background")
        self.canvas.coords(self._content_window, inset, inset)
        self.canvas.itemconfigure(
            self._content_window,
            width=max(0, width - (inset * 2)),
            height=max(0, height - (inset * 2)),
        )


class StatusBanner(tk.Frame):
    """A concise message banner for informational and workflow states."""

    _COLORS = {
        "info": COLORS["accent"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["error"],
    }

    def __init__(self, master):
        super().__init__(master, background=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        self.kind = "info"
        self.marker = tk.Frame(self, background=self._COLORS[self.kind], width=SPACING["xs"])
        self.marker.pack(side="left", fill="y")
        text = tk.Frame(self, background=COLORS["panel"])
        text.pack(side="left", fill="x", expand=True, padx=SPACING["md"], pady=SPACING["sm"])
        self.title_label = tk.Label(
            text,
            anchor="w",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Segoe UI Semibold", 10),
        )
        self.title_label.pack(fill="x")
        self.detail_label = tk.Label(
            text,
            anchor="w",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            justify="left",
            wraplength=680,
        )
        self.detail_label.pack(fill="x")
        self.set_state("info", "Informação", "")

    def set_state(self, kind, title, detail):
        """Display a banner state, title, and optional supporting detail."""
        if kind not in self._COLORS:
            raise ValueError(f"Tipo de status inválido: {kind}")
        self.kind = kind
        self.marker.configure(background=self._COLORS[kind])
        self.title_label.configure(text=str(title) or "Informação")
        self.detail_label.configure(text=str(detail))


class StageNavigation(ttk.Frame):
    """A visual summary of workflow stages and their statuses."""

    _STAGE_NAMES = {
        Stage.PREPARE: "Preparar",
        Stage.TRANSLATE: "Traduzir",
        Stage.REVIEW: "Revisar",
        Stage.APPLY: "Aplicar",
    }
    _STATUS_NAMES = {
        StageStatus.LOCKED: "Bloqueada",
        StageStatus.READY: "Pronta",
        StageStatus.RUNNING: "Em andamento",
        StageStatus.COMPLETE: "Concluída",
        StageStatus.WARNING: "Atenção",
        StageStatus.ERROR: "Erro",
    }
    _STATUS_MARKERS = {
        StageStatus.LOCKED: ("•", COLORS["muted"]),
        StageStatus.READY: ("○", COLORS["accent"]),
        StageStatus.RUNNING: ("◌", COLORS["accent"]),
        StageStatus.COMPLETE: ("✓", COLORS["success"]),
        StageStatus.WARNING: ("!", COLORS["warning"]),
        StageStatus.ERROR: ("×", COLORS["error"]),
    }

    def __init__(self, master, *, orientation="horizontal"):
        super().__init__(master, style="Surface.TFrame")
        if orientation not in {"horizontal", "vertical"}:
            raise ValueError("orientation deve ser 'horizontal' ou 'vertical'")
        self.orientation = orientation
        self.statuses = {stage: StageStatus.LOCKED for stage in Stage}
        self.active_stage = None
        self.rows = {}
        self.markers = {}
        self.labels = {}
        for stage in Stage:
            row = tk.Frame(self, background=COLORS["surface"])
            if self.orientation == "vertical":
                row.pack(fill="x", padx=SPACING["xs"], pady=(0, SPACING["xs"]))
            else:
                row.pack(side="left", fill="x", expand=True, padx=(0, SPACING["xs"]))
            marker = tk.Label(row, width=2, background=COLORS["surface"], foreground=COLORS["muted"])
            marker.pack(side="left", padx=(SPACING["sm"], SPACING["xs"]), pady=SPACING["sm"])
            label = tk.Label(row, anchor="w", background=COLORS["surface"], foreground=COLORS["text"])
            label.pack(side="left", fill="x", expand=True, pady=SPACING["sm"])
            self.rows[stage] = row
            self.markers[stage] = marker
            self.labels[stage] = label
            self._render_stage(stage)

    def set_status(self, stage, status):
        """Update a stage's visual marker and text."""
        self.statuses[stage] = status
        self._render_stage(stage)

    def set_active(self, stage):
        """Highlight *stage* without changing its workflow status."""
        self.active_stage = stage
        for current_stage in Stage:
            self._render_stage(current_stage)

    def _render_stage(self, stage):
        status = self.statuses[stage]
        marker, marker_color = self._STATUS_MARKERS[status]
        active = stage is self.active_stage
        background = COLORS["panel"] if active else COLORS["surface"]
        self.rows[stage].configure(background=background)
        self.markers[stage].configure(text=marker, foreground=marker_color, background=background)
        self.labels[stage].configure(
            text=f"{self._STAGE_NAMES[stage]} — {self._STATUS_NAMES[status]}",
            background=background,
            foreground=COLORS["accent"] if active else COLORS["text"],
        )
