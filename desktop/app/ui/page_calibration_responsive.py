from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout, QWidget

from ..services.localization_service import apply_widget_language, normalize_language
from .page_calibration import CalibrationPage as _BaseCalibrationPage


class CalibrationPage(_BaseCalibrationPage):
    """Calibration workflow that reflows on smaller Windows displays."""

    def __init__(self) -> None:
        self._language = "en"
        super().__init__()
        self._steps_layout = self._find_layout_with_widgets(
            self.step_labels[0],
            self.step_labels[-1],
        )
        self._actions_layout = self._find_layout_with_widgets(
            self.start_button,
            self.reset_button,
        )
        self._device_layout = self._find_layout_with_widgets(
            self.device_name,
            self.saved_badge,
        )
        self._apply_responsive_layout()

    def _find_layout_with_widgets(
        self,
        first: QWidget,
        second: QWidget,
    ) -> QBoxLayout | None:
        for layout in self.findChildren(QBoxLayout):
            widgets = {
                layout.itemAt(index).widget()
                for index in range(layout.count())
                if layout.itemAt(index).widget() is not None
            }
            if first in widgets and second in widgets:
                return layout
        return None

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        apply_widget_language(self, self._language)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        narrow = self.width() < 860
        very_narrow = self.width() < 700
        if self._steps_layout is not None:
            self._steps_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if narrow
                else QBoxLayout.Direction.LeftToRight
            )
        if self._actions_layout is not None:
            self._actions_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if narrow
                else QBoxLayout.Direction.LeftToRight
            )
        if self._device_layout is not None:
            self._device_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if very_narrow
                else QBoxLayout.Direction.LeftToRight
            )
