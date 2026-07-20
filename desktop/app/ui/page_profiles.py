from __future__ import annotations

from dataclasses import asdict
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from ..services.channel_mapping_service import ChannelMapping
from ..services.diagnostics_service import DiagnosticEntry
from ..services.joystick_service import JoystickInfo
from ..services.profile_service import ControllerProfile
from ..services.settings_service import AppSettings
from .page_common import clear_layout, page_title


class ProfilesPage(QWidget):
    profile_selected = Signal(object)
    create_requested = Signal(str)
    duplicate_requested = Signal()
    delete_requested = Signal()
    activate_requested = Signal()
    save_details_requested = Signal(str, str)
    import_requested = Signal()
    export_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("Profiles"))
        content = QHBoxLayout()
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._selected)
        left.addWidget(self.list, 1)
        create_row = QHBoxLayout()
        self.new_name = QLineEdit("New profile")
        create_button = QPushButton("Create")
        create_button.clicked.connect(lambda: self.create_requested.emit(self.new_name.text()))
        create_row.addWidget(self.new_name)
        create_row.addWidget(create_button)
        left.addLayout(create_row)

        right = QVBoxLayout()
        self.active_label = QLabel("Active profile: —")
        self.name_edit = QLineEdit()
        self.guid_edit = QLineEdit("*")
        self.guid_edit.setToolTip("Use * for any joystick, or bind to one joystick GUID.")
        right.addWidget(self.active_label)
        right.addWidget(QLabel("Profile name"))
        right.addWidget(self.name_edit)
        right.addWidget(QLabel("Device GUID (* = universal)"))
        right.addWidget(self.guid_edit)
        button_grid = QGridLayout()
        actions = [
            ("Save details", lambda: self.save_details_requested.emit(self.name_edit.text(), self.guid_edit.text()), 0, 0),
            ("Set active", self.activate_requested.emit, 0, 1),
            ("Duplicate", self.duplicate_requested.emit, 1, 0),
            ("Delete", self.delete_requested.emit, 1, 1),
            ("Import JSON", self.import_requested.emit, 2, 0),
            ("Export JSON", self.export_requested.emit, 2, 1),
        ]
        for text, callback, row, column in actions:
            button = QPushButton(text)
            button.clicked.connect(callback)
            button_grid.addWidget(button, row, column)
        right.addLayout(button_grid)
        right.addStretch(1)
        content.addLayout(left, 1)
        content.addLayout(right, 1)
        outer.addLayout(content, 1)
        self._profiles: dict[str, ControllerProfile] = {}
        self._active_id: str | None = None

    def set_profiles(self, profiles: list[ControllerProfile], active_id: str | None, selected_id: str | None = None) -> None:
        self._profiles = {profile.profile_id: profile for profile in profiles}
        self._active_id = active_id
        self.list.blockSignals(True)
        self.list.clear()
        target_row = 0
        for row, profile in enumerate(profiles):
            prefix = "★ " if profile.profile_id == active_id else ""
            item = QListWidgetItem(prefix + profile.name)
            item.setData(Qt.ItemDataRole.UserRole, profile.profile_id)
            self.list.addItem(item)
            if profile.profile_id == (selected_id or active_id):
                target_row = row
        if profiles:
            self.list.setCurrentRow(target_row)
        self.list.blockSignals(False)
        profile = profiles[target_row] if profiles else None
        self._show(profile)
        active = self._profiles.get(active_id or "")
        self.active_label.setText(f"Active profile: {active.name if active else '—'}")

    def selected_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        profile_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self._show(self._profiles.get(profile_id))
        self.profile_selected.emit(profile_id)

    def _show(self, profile: ControllerProfile | None) -> None:
        self.name_edit.setText(profile.name if profile else "")
        self.guid_edit.setText(profile.device_guid if profile else "*")
