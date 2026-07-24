from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services.device_role_service import ROLE_LABELS, ROLE_ORDER
from ..services.joystick_service import JoystickInfo
from ..services.profile_service import ControllerProfile
from .page_mapping_product import MappingPage as _ProductMappingPage


class MappingPage(_ProductMappingPage):
    """Final desktop mapping workspace sized for a 1366x768 product window."""

    def __init__(self) -> None:
        self._final_mapping_ready = False
        self._compact_identity: QGroupBox | None = None
        super().__init__()
        self._build_compact_identity_editor()
        self._rebuild_final_editor_grid()
        self._configure_channel_grid()
        self._final_mapping_ready = True
        self._apply_final_layout()

    @staticmethod
    def _clear_layout(layout: QBoxLayout | QGridLayout | None) -> None:
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if isinstance(child_layout, (QBoxLayout, QGridLayout)):
                MappingPage._clear_layout(child_layout)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-size: 10px; font-weight: 750;")
        return label

    def _build_compact_identity_editor(self) -> None:
        scroll = getattr(self, "_editor_scroll", None)
        content = scroll.widget() if isinstance(scroll, QScrollArea) else None
        if content is None:
            return

        groups = {group.title(): group for group in content.findChildren(QGroupBox)}
        old_identity = groups.get("Channel and source")
        if old_identity is None:
            return

        compact = QGroupBox("Channel and source")
        compact.setObjectName("compactChannelSource")
        grid = QGridLayout(compact)
        grid.setContentsMargins(12, 9, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        for widget in (
            self.name_edit,
            self.device_combo,
            self.source_combo,
            self.learn_button,
            self.learn_status,
            self.mode_combo,
            self.reverse_box,
        ):
            widget.setMinimumWidth(0)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.learn_button.setMinimumWidth(102)
        self.learn_button.setMaximumWidth(122)
        self.reverse_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.learn_status.setMaximumHeight(34)
        self.learn_status.setStyleSheet("font-size: 9px; color: palette(mid);")

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(7)
        input_row.addWidget(self.source_combo, 1)
        input_row.addWidget(self.learn_button)

        behavior_row = QHBoxLayout()
        behavior_row.setContentsMargins(0, 0, 0, 0)
        behavior_row.setSpacing(9)
        behavior_row.addWidget(self.mode_combo, 1)
        behavior_row.addWidget(self.reverse_box)

        grid.addWidget(self._field_label("Channel name"), 0, 0)
        grid.addWidget(self.name_edit, 0, 1, 1, 3)
        grid.addWidget(self._field_label("Device"), 1, 0)
        grid.addWidget(self.device_combo, 1, 1)
        grid.addWidget(self._field_label("Input"), 1, 2)
        grid.addLayout(input_row, 1, 3)
        grid.addWidget(self._field_label("Input behavior"), 2, 0)
        grid.addLayout(behavior_row, 2, 1)
        grid.addWidget(self.learn_status, 2, 2, 1, 2)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(3, 4)

        old_identity.hide()
        self._compact_identity = compact

    def _rebuild_final_editor_grid(self) -> None:
        scroll = getattr(self, "_editor_scroll", None)
        content = scroll.widget() if isinstance(scroll, QScrollArea) else None
        if content is None or not isinstance(content.layout(), QVBoxLayout):
            return
        editor_layout = content.layout()
        self._clear_layout(editor_layout)
        editor_layout.setContentsMargins(12, 8, 12, 10)
        editor_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.channel_heading.setStyleSheet("font-size: 20px; font-weight: 800;")
        self.channel_badge.setMinimumWidth(72)
        self.channel_badge.setMaximumWidth(82)
        header.addWidget(self.channel_heading)
        header.addStretch(1)
        header.addWidget(self.channel_badge)
        editor_layout.addLayout(header)

        groups = {group.title(): group for group in content.findChildren(QGroupBox)}
        quick = groups.get("Quick setup")
        endpoints = groups.get("Output endpoints and safety")
        tuning = groups.get("Response tuning")
        preview = groups.get("Live combined preview")

        if self._compact_identity is not None:
            editor_layout.addWidget(self._compact_identity)

        lower = QGridLayout()
        lower.setContentsMargins(0, 0, 0, 0)
        lower.setHorizontalSpacing(8)
        lower.setVerticalSpacing(6)
        if quick is not None:
            quick.setMaximumHeight(72)
            lower.addWidget(quick, 0, 0)
        if tuning is not None:
            tuning.setMaximumHeight(112)
            lower.addWidget(tuning, 0, 1)
        if endpoints is not None:
            endpoints.setMaximumHeight(116)
            lower.addWidget(endpoints, 1, 0)
        if preview is not None:
            preview.setMaximumHeight(116)
            lower.addWidget(preview, 1, 1)
        lower.setColumnStretch(0, 3)
        lower.setColumnStretch(1, 2)
        editor_layout.addLayout(lower)

        for group in (quick, endpoints, tuning, preview):
            if group is None or group.layout() is None:
                continue
            group.layout().setContentsMargins(9, 7, 9, 8)
            group.layout().setSpacing(4)

        self.live_value.setStyleSheet("font-size: 20px; font-weight: 850;")
        self.live_bar.setMinimumHeight(16)
        self.live_bar.setMaximumHeight(18)
        self.raw_input_label.setMaximumHeight(28)
        self.raw_input_label.setStyleSheet("font-size: 9px; color: palette(mid);")

    def _configure_channel_grid(self) -> None:
        self.channel_list.setViewMode(QListView.ViewMode.IconMode)
        self.channel_list.setFlow(QListView.Flow.LeftToRight)
        self.channel_list.setWrapping(True)
        self.channel_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.channel_list.setMovement(QListView.Movement.Static)
        self.channel_list.setWordWrap(True)
        self.channel_list.setUniformItemSizes(True)
        self.channel_list.setSpacing(3)
        self.channel_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.channel_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _update_channel_grid_size(self) -> None:
        viewport_width = max(320, self.channel_list.viewport().width())
        card_width = max(150, int((viewport_width - 13) / 2))
        grid_size = QSize(card_width, 68)
        self.channel_list.setGridSize(grid_size)
        for index in range(self.channel_list.count()):
            item = self.channel_list.item(index)
            if item is not None:
                item.setSizeHint(grid_size)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _compact_role_statuses(self) -> None:
        for role in ROLE_ORDER:
            status = self._role_status.get(role)
            if status is None:
                continue
            info = self._resolved_infos.get(role)
            status.setText(info.name if info is not None else "Not resolved")
            status.setMaximumHeight(15)
            status.setStyleSheet("font-size: 8px; color: palette(mid);")
            status.setToolTip(
                f"{ROLE_LABELS[role]}: {info.name} — {info.axes} axes, {info.buttons} buttons"
                if info is not None
                else f"{ROLE_LABELS[role]} is not resolved"
            )

    def _resolve_role_infos(self) -> None:
        super()._resolve_role_infos()
        self._compact_role_statuses()

    def set_profile(
        self,
        profile: ControllerProfile,
        devices: list[JoystickInfo],
        selected_instance_id: int | None,
    ) -> None:
        super().set_profile(profile, devices, selected_instance_id)
        self._compact_role_statuses()
        self._update_channel_grid_size()
        self._apply_final_layout()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if self._final_mapping_ready:
            self._apply_final_layout()

    def _apply_responsive_layout(self) -> None:
        if getattr(self, "_final_mapping_ready", False):
            self._apply_final_layout()
        else:
            super()._apply_responsive_layout()

    def _apply_final_layout(self) -> None:
        splitter = getattr(self, "_splitter", None)
        if not isinstance(splitter, QSplitter):
            return

        outer = self.layout()
        if isinstance(outer, QVBoxLayout):
            outer.setContentsMargins(14, 10, 14, 10)
            outer.setSpacing(5)

        role_panel = getattr(self, "_role_panel", None)
        if role_panel is not None:
            role_panel.setMaximumHeight(154)
        self.auto_panel.setMaximumHeight(34)
        self.auto_instruction.hide()
        auto_layout = self.auto_panel.layout()
        if auto_layout is not None:
            auto_layout.setContentsMargins(9, 3, 9, 3)

        wide = self.width() >= 930
        channel_panel = getattr(self, "_channel_panel", None)
        editor_scroll = getattr(self, "_editor_scroll", None)
        if wide:
            splitter.setOrientation(Qt.Orientation.Horizontal)
            if channel_panel is not None:
                channel_panel.setMinimumWidth(390)
                channel_panel.setMaximumWidth(470)
                channel_panel.setMaximumHeight(16777215)
            if isinstance(editor_scroll, QScrollArea):
                editor_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                if editor_scroll.widget() is not None:
                    editor_scroll.widget().setMinimumWidth(0)
            splitter.setSizes([410, max(620, self.width() - 430)])
        else:
            splitter.setOrientation(Qt.Orientation.Vertical)
            if channel_panel is not None:
                channel_panel.setMinimumWidth(0)
                channel_panel.setMaximumWidth(16777215)
                channel_panel.setMaximumHeight(330)
            if isinstance(editor_scroll, QScrollArea):
                editor_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            splitter.setSizes([300, 520])

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._update_channel_grid_size()
