"""Design tokens and the shared Fluent Night ttk theme."""

from tkinter import font as tkfont
from tkinter import ttk


COLORS = {
    "window": "#0B111B",
    "surface": "#101A27",
    "panel": "#182635",
    "border": "#38536A",
    "field": "#0C1723",
    "text": "#EAF4FC",
    "muted": "#91A6B8",
    "accent": "#66D4FF",
    "success": "#74E6CB",
    "warning": "#F2C66D",
    "error": "#FF7C86",
}
SPACING = {"xs": 4, "sm": 8, "md": 12, "panel": 16, "page": 24}
RADII = {"control": 8, "panel": 14}


def _luminance(hex_color):
    values = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground, background):
    """Return the WCAG relative contrast ratio of two ``#RRGGBB`` colors."""
    first, second = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


def configure_fluent_night(root):
    """Configure and return the shared ttk style for *root*."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except ttk.TclError:
        pass

    c = COLORS
    style.configure(".", background=c["surface"], foreground=c["text"], font=("Segoe UI", 10))
    style.configure("App.TFrame", background=c["window"])
    style.configure("Surface.TFrame", background=c["surface"])
    style.configure(
        "Panel.TFrame",
        background=c["panel"],
        bordercolor=c["panel"],
        lightcolor=c["panel"],
        darkcolor=c["panel"],
        relief="flat",
        borderwidth=0,
    )
    style.configure("TLabel", background=c["surface"], foreground=c["text"])
    style.configure("Title.TLabel", background=c["surface"], foreground=c["text"], font=("Segoe UI Semibold", 16))
    style.configure("Muted.TLabel", background=c["surface"], foreground=c["muted"])
    style.configure("Panel.TLabel", background=c["panel"], foreground=c["text"])
    style.configure("PanelTitle.TLabel", background=c["panel"], foreground=c["text"], font=("Segoe UI Semibold", 18))
    style.configure("PanelMuted.TLabel", background=c["panel"], foreground=c["muted"])

    style.configure(
        "TEntry",
        fieldbackground=c["field"],
        foreground=c["text"],
        insertcolor=c["accent"],
        bordercolor=c["border"],
        lightcolor=c["border"],
        darkcolor=c["border"],
        padding=(SPACING["sm"], 7),
    )
    style.map("TEntry", bordercolor=[("focus", c["accent"]), ("disabled", c["border"])])
    style.configure("TSpinbox", fieldbackground=c["field"], foreground=c["text"], arrowsize=14, padding=(SPACING["sm"], 6))
    style.map(
        "TSpinbox",
        fieldbackground=[("pressed", c["border"]), ("active", c["field"]), ("focus", c["field"]), ("disabled", c["surface"])],
        foreground=[("disabled", c["muted"]), ("focus", c["text"])],
    )

    button_base = {
        "background": c["panel"],
        "foreground": c["text"],
        "bordercolor": c["border"],
        "lightcolor": c["border"],
        "darkcolor": c["border"],
        "padding": (SPACING["md"], 8),
        "relief": "flat",
    }
    style.configure("TButton", **button_base)
    style.map(
        "TButton",
        background=[("pressed", c["border"]), ("active", c["border"]), ("disabled", c["surface"])],
        foreground=[("disabled", c["muted"]), ("focus", c["text"])],
        bordercolor=[("focus", c["accent"]), ("pressed", c["accent"])],
    )
    style.configure("Primary.TButton", background=c["accent"], foreground=c["window"], bordercolor=c["accent"])
    style.map(
        "Primary.TButton",
        background=[("pressed", c["success"]), ("active", c["success"]), ("disabled", c["surface"])],
        foreground=[("disabled", c["muted"]), ("focus", c["window"])],
        bordercolor=[("focus", c["text"]), ("pressed", c["success"])],
    )
    style.configure("Danger.TButton", background=c["error"], foreground=c["window"], bordercolor=c["error"])
    style.map(
        "Danger.TButton",
        background=[("pressed", c["warning"]), ("active", c["warning"]), ("disabled", c["surface"])],
        foreground=[("disabled", c["muted"]), ("focus", c["window"])],
        bordercolor=[("focus", c["text"]), ("pressed", c["warning"])],
    )

    style.configure("TCheckbutton", background=c["surface"], foreground=c["text"], padding=SPACING["xs"])
    style.map(
        "TCheckbutton",
        background=[("pressed", c["border"]), ("active", c["surface"]), ("focus", c["surface"]), ("disabled", c["surface"])],
        foreground=[("disabled", c["muted"]), ("active", c["accent"]), ("focus", c["text"])],
    )
    style.configure("Treeview", background=c["field"], fieldbackground=c["field"], foreground=c["text"], rowheight=28)
    style.map(
        "Treeview",
        background=[("selected", c["accent"]), ("disabled", c["surface"]), ("active", c["field"]), ("pressed", c["border"]), ("focus", c["field"])],
        foreground=[("selected", c["window"]), ("disabled", c["muted"]), ("focus", c["text"])],
    )
    style.configure("Treeview.Heading", background=c["panel"], foreground=c["text"], relief="flat", padding=SPACING["sm"])
    style.map(
        "Treeview.Heading",
        background=[("active", c["border"]), ("pressed", c["border"]), ("focus", c["border"]), ("disabled", c["surface"])],
        foreground=[("disabled", c["muted"]), ("focus", c["text"])],
    )
    style.configure("Horizontal.TProgressbar", background=c["accent"], troughcolor=c["field"], bordercolor=c["border"], thickness=10)
    style.map("Horizontal.TProgressbar", background=[("disabled", c["muted"]), ("active", c["success"])])
    return style


def mono_font(root):
    """Return a readable monospace font tuple, preferring Cascadia Code."""
    try:
        available = set(tkfont.families(root))
    except Exception:
        available = set()
    return ("Cascadia Code" if "Cascadia Code" in available else "Consolas", 10)
