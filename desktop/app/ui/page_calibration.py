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


class CalibrationPage(QWidget):
    start_requested = Signal()
    center_requested = Signal()
    save_requested = Signal()
    reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("Joystick Calibration"))
        help_text = QLabel(
            "Start calibration, move every control through its full range, release spring-centered controls, "
            "capture center, then save. Demo Controller can be used to test this workflow."
        )
        help_text.setWordWrap(True)
        outer.addWidget(help_text)

        row = QHBoxLayout()
        self.start_button = QPushButton("Start calibration")
        self.center_button = QPushButton("Capture center")
        self.save_button = QPushButton("Save calibration")
        self.reset_button = QPushButton("Reset saved calibration")
        self.start_button.clicked.connect(self.start_requested.emit)
        self.center_button.clicked.connect(self.center_requested.emit)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        for button in (self.start_button, self.center_button, self.save_button, self.reset_button):
            row.addWidget(button)
        row.addStretch(1)
        outer.addLayout(row)

        self.status = QLabel("Connect and select a joystick first.")
        outer.addWidget(self.status)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        outer.addWidget(scroll, 1)
        self._rows: list[tuple[QLabel, QLabel, QLabel, QLabel]] = []
        self.set_buttons(False, False, False)

    def set_device(self, info: JoystickInfo | None, saved: list[Any] | None = None) -> None:
        clear_layout(self.grid)
        self._rows.clear()
        if info is None:
            self.status.setText("Connect and select a joystick first.")
            self.set_buttons(False, False, False)
            return
        for column, heading in enumerate(("Axis", "Raw", "Minimum", "Center", "Maximum")):
            label = QLabel(heading)
            label.setStyleSheet("font-weight: 600;")
            self.grid.addWidget(label, 0, column)
        saved = saved or []
        for axis in range(info.axes):
            raw = QLabel("+0.0000")
            minimum = QLabel(f"{saved[axis].minimum:+.4f}" if axis < len(saved) else "—")
            center = QLabel(f"{saved[axis].center:+.4f}" if axis < len(saved) else "—")
            maximum = QLabel(f"{saved[axis].maximum:+.4f}" if axis < len(saved) else "—")
            self.grid.addWidget(QLabel(f"Axis {axis}"), axis + 1, 0)
            self.grid.addWidget(raw, axis + 1, 1)
            self.grid.addWidget(minimum, axis + 1, 2)
            self.grid.addWidget(center, axis + 1, 3)
            self.grid.addWidget(maximum, axis + 1, 4)
            self._rows.append((raw, minimum, center, maximum))
        self.status.setText("Saved calibration loaded." if saved else "No saved calibration for this device.")
        self.set_buttons(True, False, bool(saved))

    def update_values(
        self,
        axes: list[float],
        minimum: list[float] | None = None,
        center: list[float] | None = None,
        maximum: list[float] | None = None,
    ) -> None:
        for index, value in enumerate(axes):
            if index >= len(self._rows):
                break
            raw_label, minimum_label, center_label, maximum_label = self._rows[index]
            raw_label.setText(f"{float(value):+.4f}")
            if minimum is not None and index < len(minimum):
                minimum_label.setText("—" if minimum[index] == float("inf") else f"{minimum[index]:+.4f}")
            if center is not None and index < len(center):
                center_label.setText(f"{center[index]:+.4f}")
            if maximum is not None and index < len(maximum):
                maximum_label.setText("—" if maximum[index] == float("-inf") else f"{maximum[index]:+.4f}")

    def set_buttons(self, connected: bool, active: bool, saved: bool) -> None:
        self.start_button.setEnabled(connected and not active)
        self.center_button.setEnabled(connected and active)
        self.save_button.setEnabled(connected and active)
        self.reset_button.setEnabled(connected and saved)
