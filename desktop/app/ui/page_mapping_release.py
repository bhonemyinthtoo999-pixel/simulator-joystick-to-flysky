from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
)

from .page_mapping_final import MappingPage as _FinalMappingPage


class MappingPage(_FinalMappingPage):
    """Release mapping layout with all primary controls visible at 1366x768."""

    def __init__(self) -> None:
        super().__init__()
        self._compact_endpoints = self._make_compact_endpoints()
        self._compact_tuning = self._make_compact_tuning()
        self._tighten_identity_row()
        self._rebuild_release_editor()
        self._apply_final_layout()

    @staticmethod
    def _small_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 9px; font-weight: 750;")
        return label

    def _make_compact_endpoints(self) -> QGroupBox:
        group = QGroupBox("Output endpoints & failsafe")
        grid = QGridLayout(group)
        grid.setContentsMargins(9, 7, 9, 8)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(3)
        controls = (
            ("Minimum", self.minimum_spin),
            ("Center", self.center_spin),
            ("Maximum", self.maximum_spin),
            ("Failsafe", self.failsafe_spin),
        )
        for column, (title, control) in enumerate(controls):
            control.setMinimumWidth(0)
            grid.addWidget(self._small_label(title), 0, column)
            grid.addWidget(control, 1, column)
            grid.setColumnStretch(column, 1)
        group.setMaximumHeight(82)
        return group

    def _make_compact_tuning(self) -> QGroupBox:
        group = QGroupBox("Response tuning")
        grid = QGridLayout(group)
        grid.setContentsMargins(9, 7, 9, 8)
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(3)
        controls = (
            ("Trim", self.trim_spin),
            ("Expo", self.expo_spin),
            ("Smoothing", self.smoothing_spin),
        )
        for column, (title, control) in enumerate(controls):
            control.setMinimumWidth(0)
            grid.addWidget(self._small_label(title), 0, column)
            grid.addWidget(control, 1, column)
            grid.setColumnStretch(column, 1)
        group.setMaximumHeight(82)
        return group

    def _tighten_identity_row(self) -> None:
        compact = getattr(self, "_compact_identity", None)
        grid = compact.layout() if compact is not None else None
        if not isinstance(grid, QGridLayout):
            return
        # Keep the mode selector flexible and give Reverse its own column.
        grid.addWidget(self.reverse_box, 2, 2)
        grid.addWidget(self.learn_status, 2, 3)
        self.reverse_box.setText("Reverse")
        self.learn_status.setWordWrap(False)
        self.learn_status.setMaximumHeight(24)
        compact.setMaximumHeight(126)

    def _rebuild_release_editor(self) -> None:
        scroll = getattr(self, "_editor_scroll", None)
        content = scroll.widget() if isinstance(scroll, QScrollArea) else None
        if content is None or not isinstance(content.layout(), QVBoxLayout):
            return
        editor_layout = content.layout()
        self._clear_layout(editor_layout)
        editor_layout.setContentsMargins(11, 7, 11, 8)
        editor_layout.setSpacing(5)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(7)
        header.addWidget(self.channel_heading)
        header.addStretch(1)
        header.addWidget(self.channel_badge)
        editor_layout.addLayout(header)

        if self._compact_identity is not None:
            editor_layout.addWidget(self._compact_identity)

        groups = {group.title(): group for group in content.findChildren(QGroupBox)}
        quick = groups.get("Quick setup")
        preview = groups.get("Live combined preview")
        old_endpoints = groups.get("Output endpoints and safety")
        old_tuning = groups.get("Response tuning")
        if old_endpoints is not None and old_endpoints is not self._compact_endpoints:
            old_endpoints.hide()
        if old_tuning is not None and old_tuning is not self._compact_tuning:
            old_tuning.hide()

        lower = QGridLayout()
        lower.setContentsMargins(0, 0, 0, 0)
        lower.setHorizontalSpacing(7)
        lower.setVerticalSpacing(5)
        if quick is not None:
            quick.setMaximumHeight(68)
            lower.addWidget(quick, 0, 0)
        lower.addWidget(self._compact_tuning, 0, 1)
        lower.addWidget(self._compact_endpoints, 1, 0)
        if preview is not None:
            preview.setMaximumHeight(82)
            lower.addWidget(preview, 1, 1)
        lower.setColumnStretch(0, 3)
        lower.setColumnStretch(1, 2)
        editor_layout.addLayout(lower)

        self.live_value.setStyleSheet("font-size: 18px; font-weight: 850;")
        self.live_bar.setMinimumHeight(13)
        self.live_bar.setMaximumHeight(15)
        self.raw_input_label.setMaximumHeight(19)

    def _update_channel_grid_size(self) -> None:
        viewport_width = max(320, self.channel_list.viewport().width())
        card_width = max(150, int((viewport_width - 13) / 2))
        grid_size = QSize(card_width, 58)
        self.channel_list.setGridSize(grid_size)
        for index in range(self.channel_list.count()):
            item = self.channel_list.item(index)
            if item is not None:
                item.setSizeHint(grid_size)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

    def _apply_final_layout(self) -> None:
        super()._apply_final_layout()
        role_panel = getattr(self, "_role_panel", None)
        if role_panel is not None:
            role_panel.setMaximumHeight(146)
        self.auto_panel.setMaximumHeight(31)
