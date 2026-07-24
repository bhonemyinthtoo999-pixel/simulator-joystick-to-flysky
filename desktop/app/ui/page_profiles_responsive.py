from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout, QLayout, QWidget

from ..services.localization_service import apply_widget_language, normalize_language
from .page_profiles import ProfilesPage as _BaseProfilesPage


class ProfilesPage(_BaseProfilesPage):
    """Profile manager that stacks its columns on narrow windows."""

    def __init__(self) -> None:
        self._language = "en"
        super().__init__()
        self._content_layout = self._find_layout_containing(
            self.layout(),
            self.list,
            self.name_edit,
        )
        self._apply_responsive_layout()

    @classmethod
    def _layout_contains(cls, layout: QLayout | None, target: QWidget) -> bool:
        if layout is None:
            return False
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target:
                return True
            if cls._layout_contains(item.layout(), target):
                return True
        return False

    @classmethod
    def _find_layout_containing(
        cls,
        layout: QLayout | None,
        first: QWidget,
        second: QWidget,
    ) -> QBoxLayout | None:
        if layout is None:
            return None
        if isinstance(layout, QBoxLayout) and cls._layout_contains(layout, first) and cls._layout_contains(layout, second):
            for index in range(layout.count()):
                child = layout.itemAt(index).layout()
                if child is not None and cls._layout_contains(child, first) and cls._layout_contains(child, second):
                    nested = cls._find_layout_containing(child, first, second)
                    if nested is not None:
                        return nested
            return layout
        for index in range(layout.count()):
            nested = cls._find_layout_containing(layout.itemAt(index).layout(), first, second)
            if nested is not None:
                return nested
        return None

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        apply_widget_language(self, self._language)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        if self._content_layout is None:
            return
        self._content_layout.setDirection(
            QBoxLayout.Direction.TopToBottom
            if self.width() < 850
            else QBoxLayout.Direction.LeftToRight
        )
