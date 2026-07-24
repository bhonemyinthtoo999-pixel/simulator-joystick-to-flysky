from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout, QLayout, QScrollArea, QWidget

from ..services.localization_service import apply_widget_language, normalize_language
from ..services.readiness_service import ReadinessReport
from .page_dashboard import DashboardPage as _BaseDashboardPage


class DashboardPage(_BaseDashboardPage):
    """Responsive product dashboard with runtime English/Burmese switching."""

    def __init__(self) -> None:
        self._language = "en"
        self._last_adapter_state: tuple[str, str, str] = ("disconnected", "", "")
        super().__init__()
        self._status_cards = (
            self.device_heading.parentWidget(),
            self.joystick_heading.parentWidget(),
            self.profile_heading.parentWidget(),
        )
        self._status_layout = self._find_box_layout_with_widgets(self._status_cards)
        self._content_layout = self._find_content_layout()
        self._last_checklist_columns = 0
        self._apply_responsive_layout()

    def _find_content_layout(self) -> QLayout | None:
        scroll = self.findChild(QScrollArea)
        content = scroll.widget() if scroll is not None else None
        return content.layout() if content is not None else None

    def _find_box_layout_with_widgets(
        self,
        widgets: tuple[QWidget | None, ...],
    ) -> QBoxLayout | None:
        targets = {widget for widget in widgets if widget is not None}
        for layout in self.findChildren(QBoxLayout):
            contained = {
                layout.itemAt(index).widget()
                for index in range(layout.count())
                if layout.itemAt(index).widget() is not None
            }
            if targets and targets.issubset(contained):
                return layout
        return None

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        apply_widget_language(self, self._language)
        kind, board, connection = self._last_adapter_state
        self.set_adapter_state(kind, board=board, connection=connection)

    def set_readiness(self, report: ReadinessReport) -> None:
        super().set_readiness(report)
        apply_widget_language(self, self._language)
        self._apply_responsive_layout()

    def set_adapter_state(
        self,
        kind: str,
        board: str = "",
        connection: str = "",
    ) -> None:
        self._last_adapter_state = (kind, board, connection)
        super().set_adapter_state(kind, board=board, connection=connection)
        apply_widget_language(self, self._language)

    def update_transmitter(
        self,
        channels: list[int],
        *,
        adapter_kind: str,
        connection: str,
        streaming: bool,
        failsafe: bool,
    ) -> None:
        super().update_transmitter(
            channels,
            adapter_kind=adapter_kind,
            connection=connection,
            streaming=streaming,
            failsafe=failsafe,
        )
        # This section has only a few widgets, so translating after its UI-rate
        # update is inexpensive and keeps dynamic LIVE/FAILSAFE text bilingual.
        apply_widget_language(self.transmitter_monitor, self._language)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        narrow = width < 820
        compact = width < 1080

        hero_layout = self.hero.layout()
        if isinstance(hero_layout, QBoxLayout):
            hero_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if narrow
                else QBoxLayout.Direction.LeftToRight
            )

        if self._status_layout is not None:
            self._status_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if compact
                else QBoxLayout.Direction.LeftToRight
            )

        columns = 1 if narrow else 2 if compact else 3
        self._reflow_checklist(columns)

        if self._content_layout is not None:
            margin = 14 if narrow else 20 if compact else 28
            self._content_layout.setContentsMargins(margin, 18, margin, 20)

        canvas = self.transmitter_monitor.canvas
        canvas.setMinimumHeight(250 if narrow else 290 if compact else 330)
        self.readiness_button.setMinimumWidth(0 if narrow else 180)

    def _reflow_checklist(self, columns: int) -> None:
        if columns == self._last_checklist_columns:
            return
        widgets: list[QWidget] = []
        while self.checklist_layout.count():
            item = self.checklist_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widgets.append(widget)
        for index, widget in enumerate(widgets):
            self.checklist_layout.addWidget(widget, index // columns, index % columns)
        for column in range(3):
            self.checklist_layout.setColumnStretch(column, 1 if column < columns else 0)
        self._last_checklist_columns = columns
