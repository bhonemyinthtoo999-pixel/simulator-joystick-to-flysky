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
        self.low_latency = QCheckBox(
            "Low-latency flight output (recommended for FlySky trainer control)"
        )
        self.low_latency.setToolTip(
            "Polls flight controls more frequently and streams compact binary channel frames when firmware supports them."
        )
        self.realtime_rate = QSpinBox()
        self.realtime_rate.setRange(50, 200)
        self.realtime_rate.setSingleStep(10)
        self.realtime_rate.setSuffix(" Hz")
        self.rate = QSpinBox()
        self.rate.setRange(10, 60)
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
        form.addWidget(self.low_latency, 1, 0, 1, 2)
        form.addWidget(QLabel("Realtime output limit"), 2, 0)
        form.addWidget(self.realtime_rate, 2, 1)
        form.addWidget(QLabel("UI refresh rate"), 3, 0)
        form.addWidget(self.rate, 3, 1)
        form.addWidget(QLabel("Default serial baud"), 4, 0)
        form.addWidget(self.baud, 4, 1)
        form.addWidget(self.auto_detect_adapter, 5, 0, 1, 2)
        form.addWidget(self.auto_connect, 6, 0, 1, 2)
        form.addWidget(QLabel("Diagnostics level"), 7, 0)
        form.addWidget(self.log_level, 7, 1)
        outer.addLayout(form)

        save = QPushButton("Save settings")
        save.clicked.connect(self._save)
        outer.addWidget(save)

        note = QLabel(
            "Low-latency mode separates the realtime joystick-to-Arduino path from heavy dashboard and mapping UI updates. "
            "Arduino firmware 0.3.0 or newer uses a compact binary live-channel frame. Set mapping smoothing to 0 for the most direct stick response."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: palette(mid);")
        outer.addWidget(note)
        outer.addStretch(1)

    def set_settings(self, settings: AppSettings) -> None:
        self.demo.setChecked(settings.demo_joystick_enabled)
        self.low_latency.setChecked(settings.low_latency_mode)
        self.realtime_rate.setValue(settings.realtime_rate_hz)
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
            "low_latency_mode": self.low_latency.isChecked(),
            "realtime_rate_hz": self.realtime_rate.value(),
            "channel_rate_hz": self.rate.value(),
            "serial_baud": int(self.baud.currentData()),
            "auto_detect_adapter": self.auto_detect_adapter.isChecked(),
            "auto_connect": self.auto_connect.isChecked(),
            "log_level": self.log_level.currentText(),
        }
        self.save_requested.emit(payload)
