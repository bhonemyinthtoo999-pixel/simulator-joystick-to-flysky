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


class DevicePage(QWidget):
    refresh_requested = Signal()
    connect_requested = Signal(str, int)
    simulator_requested = Signal()
    disconnect_requested = Signal()
    hello_requested = Signal()
    upload_requested = Signal()
    reboot_requested = Signal()
    bootloader_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("ESP32-S3 Device & Firmware"))
        help_text = QLabel(
            "Use a real serial port later, or connect the built-in ESP32-S3 simulator now to test handshake, "
            "profile upload, live channels and diagnostics without hardware."
        )
        help_text.setWordWrap(True)
        outer.addWidget(help_text)

        connection_row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        self.baud_combo = QComboBox()
        for baud in (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600):
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.setCurrentText("115200")
        refresh = QPushButton("Refresh")
        connect = QPushButton("Connect serial")
        simulator = QPushButton("Connect simulator")
        disconnect = QPushButton("Disconnect")
        refresh.clicked.connect(self.refresh_requested.emit)
        connect.clicked.connect(lambda: self.connect_requested.emit(self.port_combo.currentData() or "", int(self.baud_combo.currentData())))
        simulator.clicked.connect(self.simulator_requested.emit)
        disconnect.clicked.connect(self.disconnect_requested.emit)
        for widget in (self.port_combo, self.baud_combo, refresh, connect, simulator, disconnect):
            connection_row.addWidget(widget)
        outer.addLayout(connection_row)

        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.device_info = QPlainTextEdit()
        self.device_info.setReadOnly(True)
        self.device_info.setPlainText("No device information yet.")
        action_row = QHBoxLayout()
        for text, callback in (
            ("Handshake", self.hello_requested.emit),
            ("Validate & upload active profile", self.upload_requested.emit),
            ("Reboot", self.reboot_requested.emit),
            ("Enter bootloader", self.bootloader_requested.emit),
        ):
            button = QPushButton(text)
            button.clicked.connect(callback)
            action_row.addWidget(button)
        action_row.addStretch(1)
        outer.addWidget(self.connection_status)
        outer.addLayout(action_row)
        outer.addWidget(self.device_info, 1)

    def set_ports(self, ports: list[dict[str, Any]], preferred: str = "") -> None:
        current = self.port_combo.currentData() or preferred
        self.port_combo.clear()
        for item in ports:
            self.port_combo.addItem(f"{item['device']} — {item['description']}", item["device"])
        target = preferred or current
        for index in range(self.port_combo.count()):
            if self.port_combo.itemData(index) == target:
                self.port_combo.setCurrentIndex(index)
                break

    def set_connection(self, connected: bool, label: str) -> None:
        self.connection_status.setText(("Connected: " if connected else "") + label)

    def show_message(self, title: str, payload: dict[str, Any]) -> None:
        lines = [title]
        lines.extend(f"{key}: {value}" for key, value in payload.items())
        self.device_info.setPlainText("\n".join(lines))
