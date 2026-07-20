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


class SettingsPage(QWidget):
    save_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("Settings"))
        form = QGridLayout()
        self.demo = QCheckBox("Enable built-in Demo Flight Joystick")
        self.rate = QSpinBox()
        self.rate.setRange(10, 100)
        self.rate.setSuffix(" Hz")
        self.baud = QComboBox()
        for value in (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600):
            self.baud.addItem(str(value), value)
        self.auto_connect = QCheckBox("Auto-connect to last serial port")
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addWidget(self.demo, 0, 0, 1, 2)
        form.addWidget(QLabel("Channel update rate"), 1, 0)
        form.addWidget(self.rate, 1, 1)
        form.addWidget(QLabel("Default serial baud"), 2, 0)
        form.addWidget(self.baud, 2, 1)
        form.addWidget(self.auto_connect, 3, 0, 1, 2)
        form.addWidget(QLabel("Diagnostics level"), 4, 0)
        form.addWidget(self.log_level, 4, 1)
        outer.addLayout(form)
        save = QPushButton("Save settings")
        save.clicked.connect(self._save)
        outer.addWidget(save)
        note = QLabel(
            "Demo mode is enabled by default so every desktop feature can be tested before the physical joystick and ESP32-S3 arrive."
        )
        note.setWordWrap(True)
        outer.addWidget(note)
        outer.addStretch(1)

    def set_settings(self, settings: AppSettings) -> None:
        self.demo.setChecked(settings.demo_joystick_enabled)
        self.rate.setValue(settings.channel_rate_hz)
        index = self.baud.findData(settings.serial_baud)
        if index >= 0:
            self.baud.setCurrentIndex(index)
        self.auto_connect.setChecked(settings.auto_connect)
        self.log_level.setCurrentText(settings.log_level)

    def _save(self) -> None:
        self.save_requested.emit(
            {
                "demo_joystick_enabled": self.demo.isChecked(),
                "channel_rate_hz": self.rate.value(),
                "serial_baud": int(self.baud.currentData()),
                "auto_connect": self.auto_connect.isChecked(),
                "log_level": self.log_level.currentText(),
            }
        )
