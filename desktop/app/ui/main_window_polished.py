from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget

from .main_window_localized import MainWindow as _LocalizedMainWindow
from .product_theme import ProductThemeController


class MainWindow(_LocalizedMainWindow):
    """Final product shell with colorful raised controls and card depth."""

    def __init__(self) -> None:
        self._theme_controller: ProductThemeController | None = None
        super().__init__()
        app = QApplication.instance()
        if app is not None:
            self._theme_controller = ProductThemeController(app, self)
        self.navigation.currentRowChanged.connect(
            lambda _row: QTimer.singleShot(0, self._polish_visible_ui)
        )
        self._polish_visible_ui()

    def _apply_language(self) -> None:
        super()._apply_language()
        if self._theme_controller is not None:
            QTimer.singleShot(0, self._polish_visible_ui)

    def _refresh_visible_language(self) -> None:
        super()._refresh_visible_language()
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
