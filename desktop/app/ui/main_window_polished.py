from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QWidget

from .main_window_localized import MainWindow as _LocalizedMainWindow
from .theme_presets import DynamicProductThemeController, normalize_theme


class MainWindow(_LocalizedMainWindow):
    """Final product shell with selectable themes and polished typography."""

    def __init__(self) -> None:
        self._theme_controller: DynamicProductThemeController | None = None
        super().__init__()
        app = QApplication.instance()
        if app is not None:
            self._theme_controller = DynamicProductThemeController(
                app,
                self,
                getattr(self.settings, "color_theme", "aurora"),
            )
        self._apply_shell_accents()
        self._polish_brand()
        self._apply_about_credit()
        self.navigation.currentRowChanged.connect(
            lambda _row: QTimer.singleShot(0, self._polish_visible_ui)
        )
        self._polish_visible_ui()

    def _apply_shell_accents(self) -> None:
        controller = self._theme_controller
        if controller is None:
            return
        colors = controller.colors
        self.navigation_panel.setStyleSheet(
            "QFrame#productNavigationPanel { border: 0; "
            f"border-right: 1px solid {colors['primary']}; "
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {colors['nav_start']}, stop:0.52 {colors['nav_middle']}, "
            f"stop:1 {colors['nav_end']}); }}"
        )

    def _polish_brand(self) -> None:
        if not hasattr(self, "navigation_brand"):
            return
        self.navigation_brand.setText("Simulator Joystick → FlySky")
        self.navigation_brand.setWordWrap(False)
        self.navigation_brand.setToolTip("Simulator Joystick to FlySky")
        self.navigation_brand.setStyleSheet(
            "font-size: 13px; font-weight: 800; color: #ffffff;"
        )

    def _apply_about_credit(self) -> None:
        help_page = getattr(self, "help_page", None)
        about = getattr(help_page, "about_text", None)
        if about is None:
            return
        current = about.text()
        if "Myanmar Aero Hobbyist Association" in current:
            return
        if getattr(self, "_language", "en") == "my":
            credit = (
                "\n\nဤဆော့ဖ်ဝဲကို မြန်မာနိုင်ငံလေကြောင်းဝါသနာရှင်များအသင်း "
                "(Myanmar Aero Hobbyist Association — MAHA) အတွက် BMH မှ "
                "ရေးသားဖန်တီးထားခြင်းဖြစ်သည်။"
            )
        else:
            credit = (
                "\n\nDeveloped by BMH for the Myanmar Aero Hobbyist Association (MAHA)."
            )
        about.setText(current + credit)

    def _apply_application_font(self, language: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        available = set(QFontDatabase.families())
        if language == "my":
            candidates = (
                "Noto Sans Myanmar",
                "Myanmar Text",
                "Pyidaungsu",
                "Padauk",
                "Segoe UI",
            )
        else:
            candidates = ("Segoe UI", app.font().family())
        family = next((name for name in candidates if name in available), app.font().family())
        font = QFont(family, 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(font)

    def _apply_language(self) -> None:
        super()._apply_language()
        self._polish_brand()
        self._apply_about_credit()
        if self._theme_controller is not None:
            QTimer.singleShot(0, self._polish_visible_ui)

    def _save_settings(self, payload: dict[str, object]) -> None:
        requested_theme = normalize_theme(
            payload.get("color_theme", getattr(self.settings, "color_theme", "aurora"))
        )
        super()._save_settings(payload)
        self.settings.color_theme = requested_theme
        try:
            self.settings_store.save(self.settings)
        except OSError:
            pass
        controller = self._theme_controller
        if controller is not None:
            controller.apply_theme(requested_theme)
            self._apply_shell_accents()
            self._polish_brand()
            self._polish_visible_ui()
            monitor = getattr(self.dashboard_page, "transmitter_monitor", None)
            canvas = getattr(monitor, "canvas", None)
            if isinstance(canvas, QWidget):
                canvas.update()

    def _apply_responsive_layout(self) -> None:
        super()._apply_responsive_layout()
        if not hasattr(self, "navigation_panel"):
            return
        width = max(1, self.width())
        panel_width = 170 if width < 820 else 210 if width < 1080 else 255
        self.navigation_panel.setFixedWidth(panel_width)
        self._polish_brand()

    def _refresh_visible_language(self) -> None:
        super()._refresh_visible_language()
        self._polish_brand()
        self._apply_about_credit()
        if self._theme_controller is not None:
            self._theme_controller.polish_tree(self.pages.currentWidget())
            if self.setup_wizard.isVisible():
                self._theme_controller.polish_tree(self.setup_wizard)
            if self.validation_wizard.isVisible():
                self._theme_controller.polish_tree(self.validation_wizard)

    def _polish_visible_ui(self) -> None:
        controller = self._theme_controller
        if controller is None:
            return
        controller.polish_tree(self)
        current = self.pages.currentWidget()
        if isinstance(current, QWidget):
            controller.polish_tree(current)
        if self.setup_wizard.isVisible():
            controller.polish_tree(self.setup_wizard)
        if self.validation_wizard.isVisible():
            controller.polish_tree(self.validation_wizard)
