from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..services.readiness_service import ReadinessReport
from .page_common import clear_layout


class DashboardPage(QWidget):
    """Product-facing overview with one clear readiness state and next action."""

    setup_requested = Signal()
    action_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Simulator Joystick to FlySky")
        title.setStyleSheet("font-size: 29px; font-weight: 750;")
        self.subtitle = QLabel(
            "USB flight controls → safe AETR mapping → detected adapter → FlySky trainer port"
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: palette(mid); font-size: 12px;")

        self.hero = QFrame()
        self.hero.setObjectName("readinessHero")
        self.hero.setStyleSheet(
            "QFrame#readinessHero { border: 1px solid palette(midlight); border-radius: 14px; "
            "background: palette(base); }"
        )
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(18)
        hero_text = QVBoxLayout()
        self.readiness_eyebrow = QLabel("SYSTEM READINESS")
        self.readiness_eyebrow.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: palette(mid); letter-spacing: 1px;"
        )
        self.readiness_title = QLabel("CHECKING SETUP…")
        self.readiness_title.setStyleSheet("font-size: 30px; font-weight: 800;")
        self.readiness_summary = QLabel("Detecting controls and adapter hardware.")
        self.readiness_summary.setWordWrap(True)
        self.readiness_summary.setStyleSheet("font-size: 13px;")
        hero_text.addWidget(self.readiness_eyebrow)
        hero_text.addWidget(self.readiness_title)
        hero_text.addWidget(self.readiness_summary)
        self.readiness_button = QPushButton("Continue setup")
        self.readiness_button.setMinimumHeight(42)
        self.readiness_button.setMinimumWidth(180)
        self.readiness_button.clicked.connect(self._emit_next_action)
        self.setup_button = QPushButton("Setup guide")
        self.setup_button.clicked.connect(self.setup_requested.emit)
        hero_actions = QVBoxLayout()
        hero_actions.addWidget(self.readiness_button)
        hero_actions.addWidget(self.setup_button)
        hero_actions.addStretch(1)
        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(hero_actions)
        self._next_page = "Setup"

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

        checklist_header = QLabel("Setup checklist")
        checklist_header.setStyleSheet("font-size: 18px; font-weight: 650;")
        self.checklist_container = QWidget()
        self.checklist_layout = QGridLayout(self.checklist_container)
        self.checklist_layout.setContentsMargins(0, 0, 0, 0)
        self.checklist_layout.setHorizontalSpacing(12)
        self.checklist_layout.setVerticalSpacing(10)

        channel_header = QLabel("Live RC channel output")
        channel_header.setStyleSheet("font-size: 18px; font-weight: 650;")
        self.channel_container = QWidget()
        self.channel_layout = QVBoxLayout(self.channel_container)
        self.channel_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_bars: list[QProgressBar] = []
        self.channel_values: list[QLabel] = []
        self.set_channels([1500] * 8)

        self.safety_value = QLabel(
            "Failsafe armed: output is clamped to the active profile limits."
        )
        self.safety_value.setWordWrap(True)
        self.safety_value.setStyleSheet(
            "padding: 10px 12px; border: 1px solid palette(midlight); border-radius: 8px;"
        )

        layout.addWidget(title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.hero)
        layout.addLayout(status_row)
        layout.addWidget(checklist_header)
        layout.addWidget(self.checklist_container)
        layout.addWidget(channel_header)
        layout.addWidget(self.channel_container)
        layout.addWidget(self.safety_value)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)

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

    def _emit_next_action(self) -> None:
        if self._next_page == "Setup":
            self.setup_requested.emit()
        else:
            self.action_requested.emit(self._next_page)

    def set_readiness(self, report: ReadinessReport) -> None:
        self._next_page = report.next_page
        self.readiness_title.setText(report.headline)
        self.readiness_summary.setText(report.summary)
        self.readiness_button.setText(report.next_action)
        if report.ready:
            self.readiness_eyebrow.setText("FLIGHT BRIDGE STATUS")
            self.hero.setStyleSheet(
                "QFrame#readinessHero { border: 2px solid #2e9b63; border-radius: 14px; "
                "background: palette(base); }"
            )
            self.readiness_title.setStyleSheet(
                "font-size: 30px; font-weight: 800; color: #238453;"
            )
        else:
            self.readiness_eyebrow.setText("SETUP ASSISTANT")
            self.hero.setStyleSheet(
                "QFrame#readinessHero { border: 2px solid #c68a24; border-radius: 14px; "
                "background: palette(base); }"
            )
            self.readiness_title.setStyleSheet(
                "font-size: 30px; font-weight: 800; color: #a66b10;"
            )

        clear_layout(self.checklist_layout)
        for index, item in enumerate(report.items):
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setMinimumHeight(94)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            state_text = "READY" if item.passed else "ACTION NEEDED"
            state = QLabel(state_text)
            state.setStyleSheet(
                "font-size: 9px; font-weight: 750; color: "
                + ("#238453;" if item.passed else "#a66b10;")
            )
            title = QLabel(item.title)
            title.setStyleSheet("font-size: 14px; font-weight: 650;")
            title.setWordWrap(True)
            detail = QLabel(item.detail)
            detail.setWordWrap(True)
            detail.setStyleSheet("font-size: 10px; color: palette(mid);")
            card_layout.addWidget(state)
            card_layout.addWidget(title)
            card_layout.addWidget(detail)
            self.checklist_layout.addWidget(card, index // 3, index % 3)

    def set_adapter_state(
        self,
        kind: str,
        board: str = "",
        connection: str = "",
    ) -> None:
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
