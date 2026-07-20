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


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Simulator Joystick to FlySky")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        subtitle = QLabel("Universal simulator joystick → ESP32-S3 → FlySky trainer adapter")

        status_row = QHBoxLayout()
        device_card, self.device_value = self._status_card("ESP32-S3", "Disconnected")
        joystick_card, self.joystick_value = self._status_card("Joystick", "Scanning...")
        profile_card, self.profile_value = self._status_card("Profile", "Default")
        status_row.addWidget(device_card)
        status_row.addWidget(joystick_card)
        status_row.addWidget(profile_card)

        channel_header = QLabel("Live RC channel output")
        channel_header.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.channel_container = QWidget()
        self.channel_layout = QVBoxLayout(self.channel_container)
        self.channel_bars: list[QProgressBar] = []
        self.channel_values: list[QLabel] = []
        self.set_channels([1500] * 8)

        self.safety_value = QLabel("Failsafe armed: output is clamped to the active profile limits.")
        self.safety_value.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(status_row)
        layout.addWidget(channel_header)
        layout.addWidget(self.channel_container)
        layout.addWidget(self.safety_value)
        layout.addStretch(1)

    @staticmethod
    def _status_card(heading: str, value: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMinimumHeight(105)
        card_layout = QVBoxLayout(card)
        heading_label = QLabel(heading)
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 19px; font-weight: 600;")
        value_label.setWordWrap(True)
        card_layout.addWidget(heading_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch(1)
        return card, value_label

    def set_channels(self, channels: list[int]) -> None:
        clear_layout(self.channel_layout)
        self.channel_bars.clear()
        self.channel_values.clear()
        for index, pulse in enumerate(channels):
            row = QHBoxLayout()
            label = QLabel(f"CH{index + 1}")
            label.setFixedWidth(45)
            bar = QProgressBar()
            bar.setRange(800, 2200)
            bar.setTextVisible(False)
            value = QLabel(str(int(pulse)))
            value.setFixedWidth(55)
            row.addWidget(label)
            row.addWidget(bar, 1)
            row.addWidget(value)
            self.channel_layout.addLayout(row)
            self.channel_bars.append(bar)
            self.channel_values.append(value)
        self.update_channels(channels)

    def update_channels(self, channels: list[int]) -> None:
        if len(channels) != len(self.channel_bars):
            self.set_channels(channels)
            return
        for bar, label, pulse in zip(self.channel_bars, self.channel_values, channels):
            bar.setValue(int(pulse))
            label.setText(str(int(pulse)))
