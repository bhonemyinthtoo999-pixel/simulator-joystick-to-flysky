from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..services.settings_service import AppSettings
from .page_common import page_title


class SettingsPage(QWidget):
    save_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)
        outer.addWidget(page_title("Settings"))

        form = QGridLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        self.demo = QCheckBox("Enable built-in Demo Flight Joystick")
        self.rate = QSpinBox()
        self.rate.setRange(10, 100)
        self.rate.setSuffix(" Hz")
        self.baud = QComboBox()
        for value in (
            9600,
            19200,
            38400,
            57600,
            115200,
            230400,
            460800,
            921600,
        ):
            self.baud.addItem(str(value), value)

        self.auto_detect_adapter = QCheckBox(
            "Automatically detect and identify Arduino / ESP32 adapter boards"
        )
        self.auto_detect_adapter.setToolTip(
            "The app probes likely USB serial ports and accepts a board only after a valid firmware handshake."
        )
        self.auto_connect = QCheckBox("Prefer the last successful serial port")
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])

        form.addWidget(self.demo, 0, 0, 1, 2)
        form.addWidget(QLabel("Channel update rate"), 1, 0)
        form.addWidget(self.rate, 1, 1)
        form.addWidget(QLabel("Default serial baud"), 2, 0)
        form.addWidget(self.baud, 2, 1)
        form.addWidget(self.auto_detect_adapter, 3, 0, 1, 2)
        form.addWidget(self.auto_connect, 4, 0, 1, 2)
        form.addWidget(QLabel("Diagnostics level"), 5, 0)
        form.addWidget(self.log_level, 5, 1)
        outer.addLayout(form)

        save = QPushButton("Save settings")
        save.clicked.connect(self._save)
        outer.addWidget(save)

        note = QLabel(
            "Adapter auto-detection connects only to likely USB serial devices and confirms UNO/Nano, Mega or ESP32 using the project firmware handshake. The built-in simulator is never selected automatically."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: palette(mid);")
        outer.addWidget(note)
        outer.addStretch(1)

    def set_settings(self, settings: AppSettings) -> None:
        self.demo.setChecked(settings.demo_joystick_enabled)
        self.rate.setValue(settings.channel_rate_hz)
        index = self.baud.findData(settings.serial_baud)
        if index >= 0:
            self.baud.setCurrentIndex(index)
        self.auto_detect_adapter.setChecked(settings.auto_detect_adapter)
        self.auto_connect.setChecked(settings.auto_connect)
        self.log_level.setCurrentText(settings.log_level)

    def _save(self) -> None:
        payload: dict[str, Any] = {
            "demo_joystick_enabled": self.demo.isChecked(),
            "channel_rate_hz": self.rate.value(),
            "serial_baud": int(self.baud.currentData()),
            "auto_detect_adapter": self.auto_detect_adapter.isChecked(),
            "auto_connect": self.auto_connect.isChecked(),
            "log_level": self.log_level.currentText(),
        }
        self.save_requested.emit(payload)
