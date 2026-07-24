from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QSplitter

from ..services.localization_service import apply_widget_language, normalize_language
from .page_mapping_device_editor import MappingPage as _BaseMappingPage


class MappingPage(_BaseMappingPage):
    """Channel mapping editor that stacks panels on narrow windows."""

    def __init__(self) -> None:
        self._language = "en"
        super().__init__()
        self._splitter = self.findChild(QSplitter)
        self._apply_responsive_layout()

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        apply_widget_language(self, self._language)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        splitter = self._splitter
        if splitter is None:
            return
        narrow = self.width() < 1050
        orientation = Qt.Orientation.Vertical if narrow else Qt.Orientation.Horizontal
        if splitter.orientation() != orientation:
            splitter.setOrientation(orientation)
        channel_panel = splitter.widget(0)
        editor_scroll = splitter.widget(1)
        if narrow:
            channel_panel.setMaximumWidth(16777215)
            channel_panel.setMinimumWidth(0)
            if isinstance(editor_scroll, QScrollArea) and editor_scroll.widget() is not None:
                editor_scroll.widget().setMinimumWidth(0)
            splitter.setSizes([280, 620])
        else:
            channel_panel.setMinimumWidth(270)
            channel_panel.setMaximumWidth(390)
            if isinstance(editor_scroll, QScrollArea) and editor_scroll.widget() is not None:
                editor_scroll.widget().setMinimumWidth(650)
            splitter.setSizes([310, 820])
