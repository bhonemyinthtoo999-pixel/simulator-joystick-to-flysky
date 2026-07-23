from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from .page_common import clear_layout


class DashboardPage(QWidget):
    """Live system overview driven by the detected adapter handshake."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Simulator Joystick to FlySky")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        self.subtitle = QLabel(
            "USB flight controls → Desktop AETR mixer → detected adapter → FlySky trainer port"
        )
        self.subtitle.setWordWrap(True)

        status_row = QHBoxLayout()
        (
            device_card,
            self.device_heading,
            self.device_value,
            self.device_detail,
        ) = self._status_card(
            "Adapter board",
            "Scanning…",
            "Looking for an Arduino or ESP32 serial adapter",
        )
        (
            joystick_card,
            self.joystick_heading,
            self.joystick_value,
            self.joystick_detail,
        ) = self._status_card(
            "Flight controls",
            "Scanning…",
            "Stick, throttle, pedals and auxiliary USB devices",
        )
        (
            profile_card,
            self.profile_heading,
            self.profile_value,
            self.profile_detail,
        ) = self._status_card(
            "Active profile",
            "Default",
            "Multi-device calibration, mapping and failsafe settings",
        )
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

        self.safety_value = QLabel(
            "Failsafe armed: output is clamped to the active profile limits."
        )
        self.safety_value.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(self.subtitle)
        layout.addLayout(status_row)
        layout.addWidget(channel_header)
        layout.addWidget(self.channel_container)
        layout.addWidget(self.safety_value)
        layout.addStretch(1)

        self.set_adapter_state("disconnected")

    @staticmethod
    def _status_card(
        heading: str,
        value: str,
        detail: str,
    ) -> tuple[QFrame, QLabel, QLabel, QLabel]:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMinimumHeight(118)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(4)

        heading_label = QLabel(heading.upper())
        heading_label.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: palette(mid);"
        )
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 19px; font-weight: 700;")
        value_label.setWordWrap(True)
        detail_label = QLabel(detail)
        detail_label.setStyleSheet("font-size: 11px; color: palette(mid);")
        detail_label.setWordWrap(True)

        card_layout.addWidget(heading_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(detail_label)
        card_layout.addStretch(1)
        return card, heading_label, value_label, detail_label

    def set_adapter_state(
        self,
        kind: str,
        board: str = "",
        connection: str = "",
    ) -> None:
        """Show the actual connected adapter instead of an ESP32 placeholder."""

        clean_board = board.strip()
        clean_connection = connection.strip()

        if kind == "arduino_uno":
            heading = "Arduino UNO / Nano"
            value = clean_board or "Arduino UNO/Nano ATmega328P"
            detail = "USB serial bridge • PPM output D9 • up to 8 channels"
        elif kind == "arduino_mega":
            heading = "Arduino Mega 2560"
            value = clean_board or "Arduino Mega 2560 ATmega2560"
            detail = "USB serial bridge • PPM output D11 • up to 12 channels"
        elif kind == "arduino":
            heading = "Arduino bridge"
            value = clean_board or "Arduino desktop stream bridge"
            detail = "Board identified as an Arduino-compatible serial bridge"
        elif kind == "esp32":
            heading = "ESP32-S3"
            value = clean_board or "ESP32-S3 USB Host adapter"
            detail = "Standalone USB-host adapter • profile upload available"
        elif kind == "simulator":
            heading = "Test simulator"
            value = clean_board or "Built-in ESP32-S3 simulator"
            detail = "Software-only test target • no physical board or PPM output"
        elif kind == "serial_unknown":
            heading = "Serial adapter"
            value = "Identifying board…"
            detail = clean_connection or "Waiting for the firmware handshake"
        elif kind == "probe_failed":
            heading = "Adapter board"
            value = "No compatible board responded"
            detail = "Open Adapter / Firmware to select a COM port manually"
        else:
            heading = "Adapter board"
            value = "Not connected"
            detail = "Scanning serial ports for Arduino UNO/Nano, Mega or ESP32-S3"

        if clean_connection and kind not in {"serial_unknown", "disconnected"}:
            detail = f"{detail} • {clean_connection}"

        self.device_heading.setText(heading.upper())
        self.device_value.setText(value)
        self.device_detail.setText(detail)

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
        for bar, label, pulse in zip(
            self.channel_bars,
            self.channel_values,
            channels,
        ):
            bar.setValue(int(pulse))
            label.setText(str(int(pulse)))
