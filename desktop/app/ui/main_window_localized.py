from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QBoxLayout

from ..services.localization_service import apply_widget_language
from .main_window_product import MainWindow as _ProductMainWindow


class MainWindow(_ProductMainWindow):
    """Final shell that refreshes visible translated status text at UI rate only."""

    def __init__(self) -> None:
        super().__init__()
        self._wizard_firmware_row = self._find_layout_with_widgets(
            self.setup_wizard,
            self.setup_wizard.board_combo,
            self.setup_wizard.port_combo,
        )
        self._wizard_flash_row = self._find_layout_with_widgets(
            self.setup_wizard,
            self.setup_wizard.flash_button,
            self.setup_wizard.cancel_flash_button,
        )
        self._localization_timer = QTimer(self)
        self._localization_timer.setInterval(500)
        self._localization_timer.timeout.connect(self._refresh_visible_language)
        self._localization_timer.start()
        self._apply_wizard_responsive()

    def _refresh_visible_language(self) -> None:
        if self._language != "my":
            return
        current = self.pages.currentWidget()
        if current is not None:
            apply_widget_language(current, self._language)
        if self.setup_wizard.isVisible():
            apply_widget_language(self.setup_wizard, self._language)

    def _apply_wizard_responsive(self) -> None:
        super()._apply_wizard_responsive()
        if not hasattr(self, "_wizard_firmware_row"):
            return
        narrow = self.setup_wizard.width() < 760
        direction = (
            QBoxLayout.Direction.TopToBottom
            if narrow
            else QBoxLayout.Direction.LeftToRight
        )
        if self._wizard_firmware_row is not None:
            self._wizard_firmware_row.setDirection(direction)
        if self._wizard_flash_row is not None:
            self._wizard_flash_row.setDirection(direction)
