from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .page_common import page_title


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
        self._transport_label = ""
        self._adapter_kind = "disconnected"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("Adapter & Firmware"))

        self.help_text = QLabel(
            "Select a serial port and click Connect selected COM. The app identifies Arduino UNO/Nano, "
            "Arduino Mega 2560 or ESP32-S3 automatically after the handshake. The no-hardware simulator "
            "is an ESP32-S3 test target only; selecting a COM port does not replace an existing simulator connection."
        )
        self.help_text.setWordWrap(True)
        outer.addWidget(self.help_text)

        connection_row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(300)
        self.baud_combo = QComboBox()
        for baud in (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600):
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.setCurrentText("115200")

        self.refresh_button = QPushButton("Refresh ports")
        self.connect_button = QPushButton("Connect selected COM")
        self.simulator_button = QPushButton("Connect test simulator")
        self.disconnect_button = QPushButton("Disconnect")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.connect_button.clicked.connect(
            lambda: self.connect_requested.emit(
                self.port_combo.currentData() or "",
                int(self.baud_combo.currentData()),
            )
        )
        self.simulator_button.clicked.connect(self.simulator_requested.emit)
        self.disconnect_button.clicked.connect(self.disconnect_requested.emit)
        for widget in (
            self.port_combo,
            self.baud_combo,
            self.refresh_button,
            self.connect_button,
            self.simulator_button,
            self.disconnect_button,
        ):
            connection_row.addWidget(widget)
        outer.addLayout(connection_row)

        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.adapter_status = QLabel("Adapter: not identified")
        self.adapter_status.setWordWrap(True)
        self.adapter_status.setStyleSheet("padding: 6px 0; font-size: 14px;")

        self.device_info = QPlainTextEdit()
        self.device_info.setReadOnly(True)
        self.device_info.setPlainText("No device information yet.")

        action_row = QHBoxLayout()
        self.handshake_button = QPushButton("Handshake / identify board")
        self.upload_button = QPushButton("Validate & upload ESP32 profile")
        self.reboot_button = QPushButton("Reboot adapter")
        self.bootloader_button = QPushButton("Enter ESP32 bootloader")
        self.handshake_button.clicked.connect(self.hello_requested.emit)
        self.upload_button.clicked.connect(self.upload_requested.emit)
        self.reboot_button.clicked.connect(self.reboot_requested.emit)
        self.bootloader_button.clicked.connect(self.bootloader_requested.emit)
        for button in (
            self.handshake_button,
            self.upload_button,
            self.reboot_button,
            self.bootloader_button,
        ):
            action_row.addWidget(button)
        action_row.addStretch(1)

        outer.addWidget(self.connection_status)
        outer.addWidget(self.adapter_status)
        outer.addLayout(action_row)
        outer.addWidget(self.device_info, 1)
        self._apply_adapter_mode("disconnected")

    @property
    def adapter_kind(self) -> str:
        return self._adapter_kind

    @property
    def supports_profile_upload(self) -> bool:
        return self._adapter_kind in {"esp32", "simulator"}

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
        self._transport_label = label if connected else ""
        if not connected:
            self.connection_status.setText("Disconnected")
            self.adapter_status.setText("Adapter: not identified")
            self.device_info.setPlainText("No device information yet.")
            self._apply_adapter_mode("disconnected")
            return

        if "simulator" in label.casefold():
            self.connection_status.setText("Connected: no-hardware test simulator")
            self.adapter_status.setText(
                "Adapter: ESP32-S3 simulator • no physical Arduino or ESP32 board is connected"
            )
            self._apply_adapter_mode("simulator")
        else:
            self.connection_status.setText(f"Serial open: {label}")
            self.adapter_status.setText(
                "Adapter: identifying board… wait for the automatic handshake or click Handshake / identify board."
            )
            self._apply_adapter_mode("serial_unknown")

    def set_adapter_identity(self, kind: str, payload: dict[str, Any]) -> None:
        board = str(payload.get("board", "Unknown serial adapter"))
        mode = str(payload.get("mode", ""))
        ppm_gpio = payload.get("ppm_gpio")
        self._apply_adapter_mode(kind)

        if kind == "simulator":
            self.connection_status.setText("Connected: no-hardware test simulator")
            note = "ESP32-S3 simulator • no physical firmware output"
        elif self._transport_label:
            self.connection_status.setText(f"Connected: {board} via {self._transport_label}")
            note = board
        else:
            self.connection_status.setText(f"Connected: {board}")
            note = board

        details: list[str] = [note]
        if kind == "arduino_uno":
            details.extend(("desktop stream bridge", "PPM output D9", "profile stays on PC", "maximum 8 channels"))
        elif kind == "arduino_mega":
            details.extend(("desktop stream bridge", "PPM output D11", "profile stays on PC", "maximum 12 channels"))
        elif kind == "arduino":
            details.extend(("Arduino desktop stream bridge", "profile stays on PC"))
        elif kind == "esp32":
            details.extend(("standalone USB-host adapter", "profile upload available"))
        elif kind == "simulator":
            details.append("profile upload is simulated for software testing")
        else:
            details.append("unknown serial adapter; only safe common commands are enabled")
        if ppm_gpio is not None and not any("PPM output" in item for item in details):
            details.append(f"PPM GPIO {ppm_gpio}")
        if mode:
            details.append(f"mode: {mode}")
        self.adapter_status.setText("Adapter: " + " • ".join(details))

    def _apply_adapter_mode(self, kind: str) -> None:
        self._adapter_kind = kind
        connected = kind != "disconnected"
        identified = kind not in {"disconnected", "serial_unknown"}
        esp32_mode = kind in {"esp32", "simulator"}

        self.handshake_button.setEnabled(connected)
        self.reboot_button.setEnabled(identified)
        self.upload_button.setVisible(esp32_mode)
        self.upload_button.setEnabled(esp32_mode)
        self.bootloader_button.setVisible(kind == "esp32")
        self.bootloader_button.setEnabled(kind == "esp32")
        self.disconnect_button.setEnabled(connected)

    def show_message(self, title: str, payload: dict[str, Any]) -> None:
        lines = [title]
        lines.extend(f"{key}: {value}" for key, value in payload.items())
        self.device_info.setPlainText("\n".join(lines))
