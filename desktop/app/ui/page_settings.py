from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..services.localization_service import (
    SUPPORTED_LANGUAGES,
    apply_widget_language,
    normalize_language,
)
from ..services.settings_service import AppSettings
from .page_common import page_title


class SettingsPage(QWidget):
    save_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._language = "en"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        layout.addWidget(page_title("Settings"))

        intro = QLabel(
            "Choose the app language and tune the realtime control path. Language changes apply immediately after saving."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: palette(mid);")
        layout.addWidget(intro)

        form_card = QFrame()
        form_card.setFrameShape(QFrame.Shape.StyledPanel)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 16, 18, 16)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.language = QComboBox()
        for code, label in SUPPORTED_LANGUAGES:
            self.language.addItem(label, code)

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

        form.addRow("Language", self.language)
        form.addRow(self.demo)
        form.addRow(self.low_latency)
        form.addRow("Realtime output limit", self.realtime_rate)
        form.addRow("UI refresh rate", self.rate)
        form.addRow("Default serial baud", self.baud)
        form.addRow(self.auto_detect_adapter)
        form.addRow(self.auto_connect)
        form.addRow("Diagnostics level", self.log_level)
        form_layout.addLayout(form)
        layout.addWidget(form_card)

        save = QPushButton("Save settings")
        save.setMinimumHeight(40)
        save.clicked.connect(self._save)
        layout.addWidget(save)

        note = QLabel(
            "Low-latency mode separates the realtime joystick-to-Arduino path from heavy dashboard and mapping UI updates. "
            "Arduino firmware 0.3.0 or newer uses a compact binary live-channel frame. Set mapping smoothing to 0 for the most direct stick response."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: palette(mid);")
        layout.addWidget(note)
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        apply_widget_language(self, self._language)

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
        language_index = self.language.findData(normalize_language(settings.language))
        if language_index >= 0:
            self.language.setCurrentIndex(language_index)
        self.set_language(settings.language)

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
            "language": str(self.language.currentData() or "en"),
        }
        self.save_requested.emit(payload)
