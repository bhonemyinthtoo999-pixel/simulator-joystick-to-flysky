from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .page_common import page_title


class StatusCard(QFrame):
    def __init__(self, title: str, value: str, detail: str = "") -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(98)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(3)
        caption = QLabel(title.upper())
        caption.setStyleSheet("font-size: 10px; font-weight: 700; color: palette(mid);")
        self.value = QLabel(value)
        self.value.setWordWrap(True)
        self.value.setStyleSheet("font-size: 17px; font-weight: 700;")
        self.detail = QLabel(detail)
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("font-size: 11px; color: palette(mid);")
        layout.addWidget(caption)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)
        layout.addStretch(1)


class ChannelCompareRow(QWidget):
    def __init__(self, channel: int) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        name = QLabel(f"CH{channel}")
        name.setStyleSheet("font-weight: 700;")
        self.desktop = QLabel("—")
        self.received = QLabel("—")
        self.result = QLabel("WAIT")
        self.result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result.setMinimumWidth(64)
        layout.addWidget(name, 0, 0)
        layout.addWidget(self.desktop, 0, 1)
        layout.addWidget(self.received, 0, 2)
        layout.addWidget(self.result, 0, 3)

    def update_values(self, desktop: int | None, received: int | None) -> None:
        self.desktop.setText(f"{desktop} µs" if desktop is not None else "—")
        self.received.setText(f"{received} µs" if received is not None else "—")
        if desktop is None or received is None:
            self.result.setText("WAIT")
            self.result.setStyleSheet("font-weight: 700; padding: 3px;")
            return
        difference = abs(int(desktop) - int(received))
        if difference <= 5:
            self.result.setText("MATCH")
            self.result.setStyleSheet("font-weight: 700; padding: 3px; color: #14804a;")
        else:
            self.result.setText(f"Δ {difference}")
            self.result.setStyleSheet("font-weight: 700; padding: 3px; color: #b54708;")


class DevicePage(QWidget):
    refresh_requested = Signal()
    connect_requested = Signal(str, int)
    simulator_requested = Signal()
    disconnect_requested = Signal()
    hello_requested = Signal()
    upload_requested = Signal()
    reboot_requested = Signal()
    bootloader_requested = Signal()
    failsafe_test_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._transport_label = ""
        self._adapter_kind = "disconnected"
        self._desktop_channels: list[int] = []
        self._received_channels: list[int] = []
        self._last_status_at: float | None = None
        self._channel_rows: list[ChannelCompareRow] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(10)
        outer.addWidget(page_title("Adapter & Firmware"))

        subtitle = QLabel(
            "Connect an Arduino or ESP32 adapter, verify the live channel stream, then run the guided communication failsafe test before wiring the trainer port."
        )
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 6, 8)
        body.setSpacing(12)
        body.addWidget(self._build_connection_card())
        body.addLayout(self._build_status_cards())
        body.addWidget(self._build_output_monitor())
        body.addWidget(self._build_failsafe_card())
        body.addWidget(self._build_details_card())
        body.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._age_timer = QTimer(self)
        self._age_timer.setInterval(250)
        self._age_timer.timeout.connect(self._refresh_status_age)
        self._age_timer.start()
        self._apply_adapter_mode("disconnected")

    def _build_connection_card(self) -> QGroupBox:
        group = QGroupBox("Connection")
        layout = QVBoxLayout(group)
        layout.setSpacing(9)

        row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(310)
        self.baud_combo = QComboBox()
        for baud in (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600):
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.setCurrentText("115200")
        self.refresh_button = QPushButton("Refresh")
        self.connect_button = QPushButton("Connect COM")
        self.simulator_button = QPushButton("Test simulator")
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
        row.addWidget(self.port_combo, 1)
        row.addWidget(self.baud_combo)
        row.addWidget(self.refresh_button)
        row.addWidget(self.connect_button)
        row.addWidget(self.simulator_button)
        row.addWidget(self.disconnect_button)
        layout.addLayout(row)

        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.adapter_status = QLabel("No adapter identified")
        self.adapter_status.setWordWrap(True)
        self.adapter_status.setStyleSheet("font-size: 12px; color: palette(mid);")
        layout.addWidget(self.connection_status)
        layout.addWidget(self.adapter_status)

        actions = QHBoxLayout()
        self.handshake_button = QPushButton("Identify board")
        self.upload_button = QPushButton("Upload ESP32 profile")
        self.reboot_button = QPushButton("Reboot adapter")
        self.bootloader_button = QPushButton("ESP32 bootloader")
        self.handshake_button.clicked.connect(self.hello_requested.emit)
        self.upload_button.clicked.connect(self.upload_requested.emit)
        self.reboot_button.clicked.connect(self.reboot_requested.emit)
        self.bootloader_button.clicked.connect(self.bootloader_requested.emit)
        actions.addWidget(self.handshake_button)
        actions.addWidget(self.upload_button)
        actions.addWidget(self.reboot_button)
        actions.addWidget(self.bootloader_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        return group

    def _build_status_cards(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(10)
        self.board_card = StatusCard("Board", "Not connected", "Waiting for handshake")
        self.stream_card = StatusCard("Desktop stream", "Stopped", "No live channel packets")
        self.ppm_card = StatusCard("PPM output", "Unknown", "Connect and identify a board")
        self.health_card = StatusCard("Last adapter status", "—", "No status packet received")
        for column, card in enumerate((self.board_card, self.stream_card, self.ppm_card, self.health_card)):
            grid.addWidget(card, 0, column)
            grid.setColumnStretch(column, 1)
        return grid

    def _build_output_monitor(self) -> QGroupBox:
        group = QGroupBox("Desktop → adapter channel monitor")
        layout = QVBoxLayout(group)
        heading = QGridLayout()
        heading.addWidget(QLabel("CHANNEL"), 0, 0)
        heading.addWidget(QLabel("DESKTOP TARGET"), 0, 1)
        heading.addWidget(QLabel("ADAPTER RECEIVED"), 0, 2)
        heading.addWidget(QLabel("RESULT"), 0, 3)
        heading.setColumnStretch(1, 1)
        heading.setColumnStretch(2, 1)
        layout.addLayout(heading)
        for channel in range(1, 9):
            row = ChannelCompareRow(channel)
            self._channel_rows.append(row)
            layout.addWidget(row)
        hint = QLabel(
            "MATCH means the adapter-reported value is within 5 µs of the active desktop output. Arduino status normally refreshes once per second."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: palette(mid);")
        layout.addWidget(hint)
        return group

    def _build_failsafe_card(self) -> QGroupBox:
        group = QGroupBox("Guided Arduino communication failsafe test")
        layout = QVBoxLayout(group)
        warning = QLabel(
            "Disconnect motor power and remove propellers first. The test pauses LIVE_CHANNELS for more than 700 ms and verifies CH1=1500, CH2=1500, CH3=1000, CH4=1500 from the Arduino status response."
        )
        warning.setWordWrap(True)
        self.failsafe_progress = QProgressBar()
        self.failsafe_progress.setRange(0, 100)
        self.failsafe_progress.setValue(0)
        self.failsafe_status = QLabel("Connect and identify an Arduino bridge to enable this test.")
        self.failsafe_status.setWordWrap(True)
        self.failsafe_button = QPushButton("Run failsafe test")
        self.failsafe_button.clicked.connect(self.failsafe_test_requested.emit)
        layout.addWidget(warning)
        layout.addWidget(self.failsafe_progress)
        layout.addWidget(self.failsafe_status)
        layout.addWidget(self.failsafe_button, 0, Qt.AlignmentFlag.AlignLeft)
        return group

    def _build_details_card(self) -> QGroupBox:
        group = QGroupBox("Protocol details")
        layout = QVBoxLayout(group)
        self.device_info = QPlainTextEdit()
        self.device_info.setReadOnly(True)
        self.device_info.setMaximumHeight(170)
        self.device_info.setPlainText("No device information yet.")
        layout.addWidget(self.device_info)
        return group

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
        self._received_channels = []
        self._last_status_at = None
        if not connected:
            self.connection_status.setText("Disconnected")
            self.adapter_status.setText("No adapter identified")
            self.board_card.value.setText("Not connected")
            self.board_card.detail.setText("Waiting for serial connection")
            self.stream_card.value.setText("Stopped")
            self.ppm_card.value.setText("Unknown")
            self.health_card.value.setText("—")
            self.health_card.detail.setText("No status packet received")
            self.device_info.setPlainText("No device information yet.")
            self._apply_adapter_mode("disconnected")
            self._refresh_channel_rows()
            return

        if "simulator" in label.casefold():
            self.connection_status.setText("Connected to test simulator")
            self.adapter_status.setText("No physical adapter is connected; output is simulated in software.")
            self._apply_adapter_mode("simulator")
        else:
            self.connection_status.setText(f"Serial open: {label}")
            self.adapter_status.setText("Identifying board…")
            self._apply_adapter_mode("serial_unknown")

    def set_adapter_identity(self, kind: str, payload: dict[str, Any]) -> None:
        board = str(payload.get("board", "Unknown serial adapter"))
        mode = str(payload.get("mode", ""))
        ppm_gpio = payload.get("ppm_gpio")
        self._apply_adapter_mode(kind)
        self.board_card.value.setText(board)
        self.board_card.detail.setText(mode or "Handshake complete")

        if kind == "simulator":
            self.connection_status.setText("Connected to test simulator")
            self.adapter_status.setText("ESP32-S3 software simulator • no physical PPM output")
            self.ppm_card.value.setText("Simulated")
            self.ppm_card.detail.setText("No GPIO waveform")
        else:
            self.connection_status.setText(
                f"Connected: {board}" + (f" via {self._transport_label}" if self._transport_label else "")
            )
            if kind == "arduino_uno":
                self.adapter_status.setText("Arduino desktop bridge • profile stays on PC • maximum 8 channels")
                self.ppm_card.value.setText("D9")
                self.ppm_card.detail.setText("Timer1 PPM • 22.5 ms frame")
            elif kind == "arduino_mega":
                self.adapter_status.setText("Arduino desktop bridge • profile stays on PC • maximum 12 channels")
                self.ppm_card.value.setText("D11")
                self.ppm_card.detail.setText("Timer1 PPM output")
            elif kind == "esp32":
                self.adapter_status.setText("Standalone USB-host adapter • profile upload available")
                self.ppm_card.value.setText(f"GPIO {ppm_gpio}" if ppm_gpio is not None else "Configured GPIO")
                self.ppm_card.detail.setText("RMT PPM output")
            else:
                self.adapter_status.setText("Unknown serial adapter • safe common commands only")
                self.ppm_card.value.setText(f"GPIO {ppm_gpio}" if ppm_gpio is not None else "Unknown")

    def update_desktop_channels(self, channels: list[int], streaming: bool) -> None:
        self._desktop_channels = [int(value) for value in channels]
        self.stream_card.value.setText("ACTIVE" if streaming else "PAUSED")
        self.stream_card.detail.setText(
            f"{len(channels)} channels from active profile" if streaming else "LIVE_CHANNELS temporarily stopped"
        )
        self._refresh_channel_rows()

    def update_adapter_status(self, payload: dict[str, Any]) -> None:
        channels = payload.get("channels", [])
        if isinstance(channels, list):
            self._received_channels = [int(value) for value in channels]
        self._last_status_at = time.monotonic()
        active = bool(payload.get("joystick_connected", False))
        ppm_active = bool(payload.get("ppm_active", False))
        self.health_card.value.setText("HEALTHY" if ppm_active else "CHECK")
        self.health_card.detail.setText("Status received now")
        self.ppm_card.detail.setText(
            (self.ppm_card.detail.text().split(" • ")[0] + (" • active" if ppm_active else " • inactive"))
        )
        if self._adapter_kind.startswith("arduino"):
            self.stream_card.value.setText("ACTIVE" if active else "FAILSAFE")
            self.stream_card.detail.setText(
                "Arduino is receiving desktop packets" if active else "Arduino communication timeout is active"
            )
        self._refresh_channel_rows()

    def set_failsafe_test_state(self, stage: str, message: str, progress: int) -> None:
        self.failsafe_status.setText(message)
        self.failsafe_progress.setValue(max(0, min(100, progress)))
        running = stage in {"arming", "waiting", "verifying"}
        self.failsafe_button.setEnabled(not running and self._adapter_kind in {"arduino_uno", "arduino_mega", "arduino"})
        if stage == "pass":
            self.failsafe_status.setStyleSheet("font-weight: 700; color: #14804a;")
        elif stage == "fail":
            self.failsafe_status.setStyleSheet("font-weight: 700; color: #b42318;")
        else:
            self.failsafe_status.setStyleSheet("font-weight: 600;")

    def _refresh_status_age(self) -> None:
        if self._last_status_at is None:
            return
        age = max(0.0, time.monotonic() - self._last_status_at)
        self.health_card.detail.setText(f"Last status {age:.1f} s ago")
        if age > 2.5:
            self.health_card.value.setText("STALE")

    def _refresh_channel_rows(self) -> None:
        for index, row in enumerate(self._channel_rows):
            desktop = self._desktop_channels[index] if index < len(self._desktop_channels) else None
            received = self._received_channels[index] if index < len(self._received_channels) else None
            row.update_values(desktop, received)

    def _apply_adapter_mode(self, kind: str) -> None:
        self._adapter_kind = kind
        connected = kind != "disconnected"
        identified = kind not in {"disconnected", "serial_unknown"}
        esp32_mode = kind in {"esp32", "simulator"}
        arduino_mode = kind in {"arduino_uno", "arduino_mega", "arduino"}
        self.handshake_button.setEnabled(connected)
        self.reboot_button.setEnabled(identified)
        self.upload_button.setVisible(esp32_mode)
        self.upload_button.setEnabled(esp32_mode)
        self.bootloader_button.setVisible(kind == "esp32")
        self.bootloader_button.setEnabled(kind == "esp32")
        self.disconnect_button.setEnabled(connected)
        self.failsafe_button.setEnabled(arduino_mode)
        if not arduino_mode:
            self.failsafe_status.setText("Connect and identify an Arduino bridge to enable this test.")
            self.failsafe_progress.setValue(0)

    def show_message(self, title: str, payload: dict[str, Any]) -> None:
        lines = [title]
        lines.extend(f"{key}: {value}" for key, value in payload.items())
        self.device_info.setPlainText("\n".join(lines))
