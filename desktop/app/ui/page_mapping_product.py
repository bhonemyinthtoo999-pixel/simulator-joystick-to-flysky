from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services.profile_service import ControllerProfile
from ..services.joystick_service import JoystickInfo
from .page_mapping_responsive import MappingPage as _ResponsiveMappingPage


class MappingPage(_ResponsiveMappingPage):
    """Wide mapping workspace that shows channels and the complete editor together."""

    def __init__(self) -> None:
        super().__init__()
        self._product_layout_ready = False
        self._editor_scroll: QScrollArea | None = None
        self._channel_panel: QWidget | None = None
        self._role_panel: QGroupBox | None = None
        self._rebuild_editor_workspace()
        self._compact_mapping_header()
        self._product_layout_ready = True
        self._apply_product_layout()

    @staticmethod
    def _contains_widget(layout: QLayout | None, target: QWidget) -> bool:
        if layout is None:
            return False
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target:
                return True
            if MappingPage._contains_widget(item.layout(), target):
                return True
        return False

    def _rebuild_editor_workspace(self) -> None:
        splitter = self._splitter
        if not isinstance(splitter, QSplitter):
            return
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        self._channel_panel = splitter.widget(0)
        candidate = splitter.widget(1)
        self._editor_scroll = candidate if isinstance(candidate, QScrollArea) else None

        channel_panel = self._channel_panel
        if channel_panel is not None:
            channel_panel.setMinimumWidth(380)
            channel_panel.setMaximumWidth(520)
            channel_layout = channel_panel.layout()
            if isinstance(channel_layout, QVBoxLayout):
                channel_layout.setContentsMargins(15, 14, 15, 14)
                channel_layout.setSpacing(7)
            self.channel_list.setSpacing(1)
            self.channel_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.channel_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll = self._editor_scroll
        if scroll is None or scroll.widget() is None:
            return
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        content = scroll.widget()
        content.setMinimumWidth(0)
        editor_layout = content.layout()
        if not isinstance(editor_layout, QVBoxLayout):
            return

        header_layout: QLayout | None = None
        while editor_layout.count():
            item = editor_layout.takeAt(0)
            child_layout = item.layout()
            if child_layout is not None and self._contains_widget(
                child_layout,
                self.channel_heading,
            ):
                header_layout = child_layout

        groups = {
            group.title(): group
            for group in content.findChildren(QGroupBox)
        }
        identity = groups.get("Channel and source")
        quick = groups.get("Quick setup")
        endpoints = groups.get("Output endpoints and safety")
        tuning = groups.get("Response tuning")
        preview = groups.get("Live combined preview")

        editor_layout.setContentsMargins(15, 12, 15, 14)
        editor_layout.setSpacing(8)
        if header_layout is not None:
            editor_layout.addLayout(header_layout)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        if identity is not None:
            grid.addWidget(identity, 0, 0, 1, 2)
        if quick is not None:
            grid.addWidget(quick, 1, 0)
        if tuning is not None:
            grid.addWidget(tuning, 1, 1)
        if endpoints is not None:
            grid.addWidget(endpoints, 2, 0, 1, 2)
        if preview is not None:
            grid.addWidget(preview, 3, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        editor_layout.addLayout(grid)

        for group in (identity, quick, endpoints, tuning, preview):
            if group is None:
                continue
            layout = group.layout()
            if layout is not None:
                layout.setContentsMargins(11, 10, 11, 10)
                layout.setSpacing(6)

        if identity is not None and isinstance(identity.layout(), QFormLayout):
            form = identity.layout()
            form.setHorizontalSpacing(12)
            form.setVerticalSpacing(6)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if tuning is not None and isinstance(tuning.layout(), QFormLayout):
            form = tuning.layout()
            form.setHorizontalSpacing(12)
            form.setVerticalSpacing(6)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        self.name_edit.setMinimumWidth(0)
        self.device_combo.setMinimumWidth(220)
        self.source_combo.setMinimumWidth(180)
        self.mode_combo.setMinimumWidth(190)
        self.learn_status.setMaximumHeight(38)
        self.raw_input_label.setMaximumHeight(34)
        self.live_value.setStyleSheet("font-size: 23px; font-weight: 800;")
        self.live_bar.setMinimumHeight(18)
        self.live_bar.setMaximumHeight(22)

    def _compact_mapping_header(self) -> None:
        outer = self.layout()
        if isinstance(outer, QVBoxLayout):
            outer.setContentsMargins(18, 13, 18, 14)
            outer.setSpacing(7)

        for group in self.findChildren(QGroupBox):
            if group.title() != "Device role binding":
                continue
            self._role_panel = group
            role_layout = group.layout()
            if isinstance(role_layout, QGridLayout):
                role_layout.setContentsMargins(12, 9, 12, 9)
                role_layout.setHorizontalSpacing(9)
                role_layout.setVerticalSpacing(3)
            group.setMaximumHeight(188)
            break

        for combo in self._role_combos.values():
            combo.setMinimumWidth(150)
        for status in self._role_status.values():
            status.setStyleSheet("font-size: 9px; color: palette(mid);")
            status.setMaximumHeight(30)

        self.strict_failsafe_box.setStyleSheet("font-size: 10px; font-weight: 650;")
        self.auto_panel.setMaximumHeight(52)
        auto_layout = self.auto_panel.layout()
        if isinstance(auto_layout, QHBoxLayout):
            auto_layout.setContentsMargins(10, 6, 10, 6)
            auto_layout.setSpacing(9)
        self.auto_progress.setStyleSheet("font-size: 10px; font-weight: 800;")
        self.auto_instruction.setStyleSheet("font-size: 9px; color: palette(mid);")

    def set_profile(
        self,
        profile: ControllerProfile,
        devices: list[JoystickInfo],
        selected_instance_id: int | None,
    ) -> None:
        super().set_profile(profile, devices, selected_instance_id)
        for index in range(self.channel_list.count()):
            self.channel_list.item(index).setSizeHint(QSize(330, 44))
        self._apply_product_layout()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if self._product_layout_ready:
            self._apply_product_layout()

    def _apply_responsive_layout(self) -> None:
        if getattr(self, "_product_layout_ready", False):
            self._apply_product_layout()
        else:
            super()._apply_responsive_layout()

    def _apply_product_layout(self) -> None:
        splitter = self._splitter
        if not isinstance(splitter, QSplitter):
            return
        narrow = self.width() < 1030
        if narrow:
            splitter.setOrientation(Qt.Orientation.Vertical)
            if self._channel_panel is not None:
                self._channel_panel.setMinimumWidth(0)
                self._channel_panel.setMaximumWidth(16777215)
                self._channel_panel.setMaximumHeight(275)
            if self._editor_scroll is not None:
                self._editor_scroll.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )
                self._editor_scroll.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
            splitter.setSizes([250, 560])
        else:
            splitter.setOrientation(Qt.Orientation.Horizontal)
            if self._channel_panel is not None:
                self._channel_panel.setMinimumWidth(380)
                self._channel_panel.setMaximumWidth(520)
                self._channel_panel.setMaximumHeight(16777215)
            if self._editor_scroll is not None:
                self._editor_scroll.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
                self._editor_scroll.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
            splitter.setSizes([425, max(720, self.width() - 455)])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
