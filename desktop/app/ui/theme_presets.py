from __future__ import annotations

from typing import Final

from PySide6.QtWidgets import QApplication, QWidget

from .product_theme import DARK_QSS, LIGHT_QSS, ProductThemeController


THEME_CHOICES: Final[tuple[tuple[str, str], ...]] = (
    ("aurora", "Aurora Purple"),
    ("ocean", "Ocean Blue"),
    ("emerald", "Emerald Green"),
    ("sunset", "Sunset Orange"),
    ("rose", "Rose Pink"),
)

_THEME_COLORS: Final[dict[str, dict[str, str]]] = {
    "aurora": {
        "primary": "#4f46e5", "primary_light": "#818cf8", "primary_dark": "#312e81",
        "secondary": "#06b6d4", "accent": "#a855f7", "soft": "#eef2ff",
        "page_start": "#edf4ff", "page_end": "#fff4fb", "nav_start": "#172554",
        "nav_middle": "#312e81", "nav_end": "#581c87", "success": "#10b981",
    },
    "ocean": {
        "primary": "#0284c7", "primary_light": "#38bdf8", "primary_dark": "#075985",
        "secondary": "#06b6d4", "accent": "#2563eb", "soft": "#e0f2fe",
        "page_start": "#eaf8ff", "page_end": "#edf4ff", "nav_start": "#082f49",
        "nav_middle": "#0c4a6e", "nav_end": "#164e63", "success": "#10b981",
    },
    "emerald": {
        "primary": "#059669", "primary_light": "#34d399", "primary_dark": "#065f46",
        "secondary": "#14b8a6", "accent": "#22c55e", "soft": "#d1fae5",
        "page_start": "#ecfdf5", "page_end": "#effdf8", "nav_start": "#052e2b",
        "nav_middle": "#064e3b", "nav_end": "#14532d", "success": "#16a34a",
    },
    "sunset": {
        "primary": "#ea580c", "primary_light": "#fb923c", "primary_dark": "#9a3412",
        "secondary": "#f59e0b", "accent": "#ef4444", "soft": "#ffedd5",
        "page_start": "#fff7ed", "page_end": "#fff1f2", "nav_start": "#431407",
        "nav_middle": "#7c2d12", "nav_end": "#881337", "success": "#10b981",
    },
    "rose": {
        "primary": "#db2777", "primary_light": "#f472b6", "primary_dark": "#9d174d",
        "secondary": "#a855f7", "accent": "#e11d48", "soft": "#fce7f3",
        "page_start": "#fff1f7", "page_end": "#fdf2ff", "nav_start": "#4c0519",
        "nav_middle": "#831843", "nav_end": "#581c87", "success": "#10b981",
    },
}


def normalize_theme(value: object) -> str:
    clean = str(value or "aurora").strip().casefold().replace(" ", "_")
    aliases = {
        "purple": "aurora", "aurora_purple": "aurora",
        "blue": "ocean", "ocean_blue": "ocean",
        "green": "emerald", "emerald_green": "emerald",
        "orange": "sunset", "sunset_orange": "sunset",
        "pink": "rose", "rose_pink": "rose",
    }
    clean = aliases.get(clean, clean)
    return clean if clean in _THEME_COLORS else "aurora"


def theme_colors(value: object) -> dict[str, str]:
    return dict(_THEME_COLORS[normalize_theme(value)])


def _overlay_qss(colors: dict[str, str], *, dark: bool) -> str:
    primary = colors["primary"]
    light = colors["primary_light"]
    dark_primary = colors["primary_dark"]
    secondary = colors["secondary"]
    accent = colors["accent"]
    soft = colors["soft"]
    page_start = colors["page_start"]
    page_end = colors["page_end"]
    nav_start = colors["nav_start"]
    nav_middle = colors["nav_middle"]
    nav_end = colors["nav_end"]

    page_background = (
        f"stop:0 #0b1220, stop:0.52 {nav_start}, stop:1 #161020"
        if dark
        else f"stop:0 {page_start}, stop:0.52 #f8fafc, stop:1 {page_end}"
    )
    card_background = "rgba(20, 29, 48, 242)" if dark else "rgba(255, 255, 255, 242)"
    field_background = "#111827" if dark else "#ffffff"
    field_text = "#e5e7eb" if dark else "#172033"
    secondary_text = light if dark else dark_primary
    ghost_background = "rgba(30, 41, 59, 210)" if dark else "rgba(255,255,255,210)"

    return f"""
QWidget#productAppRoot {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {page_background});
}}
QFrame#productNavigationPanel {{
    border: 0; border-right: 1px solid {primary};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {nav_start}, stop:0.52 {nav_middle}, stop:1 {nav_end});
}}
QFrame#productNavigationPanel QListWidget::item:selected {{
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {secondary}, stop:0.52 {primary}, stop:1 {accent});
}}
QFrame[uiCard="true"], QGroupBox[uiCard="true"] {{
    background: {card_background}; border: 1px solid {light};
}}
QGroupBox::title {{ color: {light if dark else dark_primary}; }}
QPushButton {{
    border-color: {dark_primary};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {light}, stop:0.48 {primary}, stop:1 {dark_primary});
}}
QPushButton:hover {{
    border-color: {primary};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {secondary}, stop:0.5 {light}, stop:1 {primary});
}}
QPushButton:pressed {{ background: {dark_primary}; }}
QPushButton[buttonRole="secondary"] {{
    color: {secondary_text}; border-color: {light};
    background: {soft if not dark else '#172033'};
}}
QPushButton[buttonRole="secondary"]:hover {{
    color: {field_text}; border-color: {primary};
    background: {light if dark else soft};
}}
QPushButton[buttonRole="ghost"] {{
    color: {field_text}; border-color: {light}; background: {ghost_background};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
    color: {field_text}; background: {field_background}; border-color: {light};
    selection-background-color: {primary};
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QPlainTextEdit:hover {{
    border-color: {primary};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
    border: 2px solid {primary};
}}
QListWidget::item:hover {{ background: {soft if not dark else nav_middle}; }}
QListWidget::item:selected {{
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {secondary}, stop:0.5 {primary}, stop:1 {accent});
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {secondary}, stop:0.5 {primary}, stop:1 {accent});
}}
QCheckBox::indicator:checked {{ border-color: {primary}; background: {primary}; }}
QScrollBar::handle:vertical {{ background: {light}; }}
QScrollBar::handle:vertical:hover {{ background: {primary}; }}
QToolTip {{ background: {nav_start}; border-color: {primary}; }}
"""


class DynamicProductThemeController(ProductThemeController):
    """Product theme controller with user-selectable accent presets."""

    def __init__(
        self,
        app: QApplication,
        root: QWidget,
        theme_name: object = "aurora",
    ) -> None:
        self.theme_name = normalize_theme(theme_name)
        self.colors = theme_colors(self.theme_name)
        super().__init__(app, root)
        self.apply_theme(self.theme_name)

    def apply_theme(self, theme_name: object) -> str:
        self.theme_name = normalize_theme(theme_name)
        self.colors = theme_colors(self.theme_name)
        self.app.setProperty("simjoyColorTheme", self.theme_name)
        self.app.setProperty("simjoyThemePalette", dict(self.colors))
        base = DARK_QSS if self.dark else LIGHT_QSS
        self.app.setStyleSheet(base + _overlay_qss(self.colors, dark=self.dark))
        self.polish_tree(self.root)
        self.root.update()
        for widget in self.root.findChildren(QWidget):
            widget.update()
        self.app.processEvents()
        return self.theme_name
