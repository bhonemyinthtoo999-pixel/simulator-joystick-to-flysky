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


class DiagnosticsPage(QWidget):
    clear_requested = Signal()
    export_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("Diagnostics"))
        top = QHBoxLayout()
        self.stats_label = QLabel("Protocol: no traffic")
        clear = QPushButton("Clear")
        export = QPushButton("Export log")
        clear.clicked.connect(self.clear_requested.emit)
        export.clicked.connect(self.export_requested.emit)
        top.addWidget(self.stats_label, 1)
        top.addWidget(clear)
        top.addWidget(export)
        outer.addLayout(top)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(2000)
        outer.addWidget(self.log, 1)

    def add_entry(self, entry: DiagnosticEntry) -> None:
        self.log.appendPlainText(entry.format())

    def clear(self) -> None:
        self.log.clear()

    def set_stats(self, stats: dict[str, Any]) -> None:
        self.stats_label.setText(
            "Protocol — "
            f"TX frames: {stats.get('tx_frames', 0)} | RX frames: {stats.get('frames_received', 0)} | "
            f"CRC errors: {stats.get('crc_errors', 0)} | Format errors: {stats.get('format_errors', 0)} | "
            f"TX bytes: {stats.get('tx_bytes', 0)} | RX bytes: {stats.get('rx_bytes', 0)}"
        )
