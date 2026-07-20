from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Simulator Joystick to FlySky desktop app ၏ အဓိက window ဖြစ်သည်။"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulator Joystick to FlySky")
        self.resize(1100, 700)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(220)
        for title in (
            "Dashboard",
            "Joystick Monitor",
            "Channel Mapping",
            "Calibration",
            "Profiles",
            "Firmware",
            "Diagnostics",
            "Settings",
        ):
            QListWidgetItem(title, self.navigation)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_dashboard())
        for title in (
            "Joystick Monitor",
            "Channel Mapping",
            "Calibration",
            "Profiles",
            "Firmware",
            "Diagnostics",
            "Settings",
        ):
            self.pages.addWidget(self._build_placeholder(title))

        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)

        root_layout.addWidget(self.navigation)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Simulator Joystick to FlySky")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel("Universal USB simulator joystick to FlySky trainer adapter")
        subtitle.setStyleSheet("font-size: 14px;")

        status_row = QHBoxLayout()
        status_row.addWidget(self._status_card("ESP32-S3", "Disconnected"))
        status_row.addWidget(self._status_card("Joystick", "Not detected"))
        status_row.addWidget(self._status_card("Profile", "Default"))

        channel_title = QLabel("RC Channel Preview")
        channel_title.setStyleSheet("font-size: 18px; font-weight: 600;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(status_row)
        layout.addWidget(channel_title)

        for channel in range(1, 7):
            row = QHBoxLayout()
            label = QLabel(f"CH{channel}")
            label.setFixedWidth(45)
            value = QLabel("1500")
            value.setFixedWidth(55)
            bar = QProgressBar()
            bar.setRange(1000, 2000)
            bar.setValue(1500)
            bar.setTextVisible(False)
            row.addWidget(label)
            row.addWidget(bar, 1)
            row.addWidget(value)
            layout.addLayout(row)

        layout.addStretch(1)
        return page

    def _status_card(self, heading: str, value: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMinimumHeight(105)
        card_layout = QVBoxLayout(card)

        heading_label = QLabel(heading)
        heading_label.setStyleSheet("font-size: 13px;")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 20px; font-weight: 600;")

        card_layout.addWidget(heading_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch(1)
        return card

    def _build_placeholder(self, title: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(f"{title}\n\nဒီ feature ကို နောက် sprint တွင် ဆက်လက်တည်ဆောက်မည်။")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px;")
        layout.addWidget(label)
        return page
