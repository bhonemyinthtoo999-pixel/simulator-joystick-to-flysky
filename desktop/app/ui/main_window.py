from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..services.joystick_service import JoystickInfo, JoystickService


class MainWindow(QMainWindow):
    """Simulator Joystick to FlySky desktop app main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulator Joystick to FlySky")
        self.resize(1100, 700)

        self._device_infos: dict[int, JoystickInfo] = {}
        self._selected_instance_id: int | None = None
        self._axis_bars: list[QProgressBar] = []
        self._axis_values: list[QLabel] = []
        self._button_labels: list[QLabel] = []
        self._hat_labels: list[QLabel] = []

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
        self.pages.addWidget(self._build_joystick_monitor())
        for title in (
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

        self.joystick_service = JoystickService()
        self.joystick_service.devices_changed.connect(self._on_devices_changed)
        self.joystick_service.state_changed.connect(self._on_state_changed)
        self.joystick_service.backend_error.connect(self._on_backend_error)
        self.joystick_service.start()

    def closeEvent(self, event: Any) -> None:
        self.joystick_service.stop()
        super().closeEvent(event)

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Simulator Joystick to FlySky")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel("Universal USB simulator joystick to FlySky trainer adapter")

        status_row = QHBoxLayout()
        status_row.addWidget(self._status_card("ESP32-S3", "Disconnected"))
        joystick_card, self.dashboard_joystick_value = self._status_card_with_value(
            "Joystick", "Scanning..."
        )
        status_row.addWidget(joystick_card)
        status_row.addWidget(self._status_card("Profile", "Default"))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(status_row)
        layout.addWidget(QLabel("Open Joystick Monitor to inspect live axes, buttons and hats."))
        layout.addStretch(1)
        return page

    def _build_joystick_monitor(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Joystick Monitor")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.device_selector = QComboBox()
        self.device_selector.currentIndexChanged.connect(self._on_selected_device_changed)
        self.device_details = QLabel("Scanning for compatible devices...")
        self.device_details.setWordWrap(True)
        self.backend_status = QLabel("")
        self.backend_status.setWordWrap(True)

        outer.addWidget(title)
        outer.addWidget(self.device_selector)
        outer.addWidget(self.device_details)
        outer.addWidget(self.backend_status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        self.axes_container = QWidget()
        self.axes_layout = QVBoxLayout(self.axes_container)
        content_layout.addWidget(QLabel("Axes"))
        content_layout.addWidget(self.axes_container)

        self.buttons_container = QWidget()
        self.buttons_layout = QGridLayout(self.buttons_container)
        content_layout.addWidget(QLabel("Buttons"))
        content_layout.addWidget(self.buttons_container)

        self.hats_container = QWidget()
        self.hats_layout = QVBoxLayout(self.hats_container)
        content_layout.addWidget(QLabel("Hat switches / D-pad"))
        content_layout.addWidget(self.hats_container)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        return page

    def _status_card(self, heading: str, value: str) -> QFrame:
        card, _ = self._status_card_with_value(heading, value)
        return card

    def _status_card_with_value(self, heading: str, value: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setMinimumHeight(105)
        card_layout = QVBoxLayout(card)
        heading_label = QLabel(heading)
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        value_label.setWordWrap(True)
        card_layout.addWidget(heading_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch(1)
        return card, value_label

    def _on_devices_changed(self, devices: list[JoystickInfo]) -> None:
        previous_id = self._selected_instance_id
        self._device_infos = {device.instance_id: device for device in devices}
        self.device_selector.blockSignals(True)
        self.device_selector.clear()
        for device in devices:
            self.device_selector.addItem(device.name, device.instance_id)
        self.device_selector.blockSignals(False)

        if not devices:
            self._selected_instance_id = None
            self.dashboard_joystick_value.setText("Not detected")
            self.device_details.setText("No SDL-compatible joystick is connected.")
            self._rebuild_monitor(None)
            return

        selected_index = 0
        if previous_id is not None:
            for index, device in enumerate(devices):
                if device.instance_id == previous_id:
                    selected_index = index
                    break
        self.device_selector.setCurrentIndex(selected_index)
        self._on_selected_device_changed(selected_index)
        self.dashboard_joystick_value.setText(
            devices[0].name if len(devices) == 1 else f"{len(devices)} devices"
        )

    def _on_selected_device_changed(self, index: int) -> None:
        instance_id = self.device_selector.itemData(index) if index >= 0 else None
        self._selected_instance_id = instance_id
        info = self._device_infos.get(instance_id)
        if info is None:
            self._rebuild_monitor(None)
            return
        self.device_details.setText(
            f"{info.name}\nGUID: {info.guid}\n"
            f"Axes: {info.axes} | Buttons: {info.buttons} | Hats: {info.hats} | Balls: {info.balls}"
        )
        self._rebuild_monitor(info)

    def _on_state_changed(self, snapshots: dict[int, dict[str, Any]]) -> None:
        if self._selected_instance_id is None:
            return
        state = snapshots.get(self._selected_instance_id)
        if state is None:
            return
        for index, raw in enumerate(state["axes"]):
            if index < len(self._axis_bars):
                scaled = round((float(raw) + 1.0) * 500)
                self._axis_bars[index].setValue(max(0, min(1000, scaled)))
                self._axis_values[index].setText(f"{float(raw):+.4f}")
        for index, pressed in enumerate(state["buttons"]):
            if index < len(self._button_labels):
                self._button_labels[index].setText(f"B{index}: {'ON' if pressed else 'OFF'}")
        for index, value in enumerate(state["hats"]):
            if index < len(self._hat_labels):
                self._hat_labels[index].setText(f"Hat {index}: {tuple(value)}")

    def _on_backend_error(self, message: str) -> None:
        self.backend_status.setText(message)

    def _rebuild_monitor(self, info: JoystickInfo | None) -> None:
        self._clear_layout(self.axes_layout)
        self._clear_layout(self.buttons_layout)
        self._clear_layout(self.hats_layout)
        self._axis_bars.clear()
        self._axis_values.clear()
        self._button_labels.clear()
        self._hat_labels.clear()
        if info is None:
            return

        for axis_index in range(info.axes):
            row = QHBoxLayout()
            name = QLabel(f"Axis {axis_index}")
            name.setFixedWidth(65)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(500)
            bar.setTextVisible(False)
            value = QLabel("+0.0000")
            value.setFixedWidth(70)
            row.addWidget(name)
            row.addWidget(bar, 1)
            row.addWidget(value)
            self.axes_layout.addLayout(row)
            self._axis_bars.append(bar)
            self._axis_values.append(value)

        for button_index in range(info.buttons):
            label = QLabel(f"B{button_index}: OFF")
            label.setFrameShape(QFrame.Shape.StyledPanel)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.buttons_layout.addWidget(label, button_index // 6, button_index % 6)
            self._button_labels.append(label)

        for hat_index in range(info.hats):
            label = QLabel(f"Hat {hat_index}: (0, 0)")
            self.hats_layout.addWidget(label)
            self._hat_labels.append(label)

    @staticmethod
    def _clear_layout(layout: Any) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            widget = item.widget()
            if child_layout is not None:
                MainWindow._clear_layout(child_layout)
            if widget is not None:
                widget.deleteLater()

    def _build_placeholder(self, title: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(f"{title}\n\nThis feature will be implemented in a later sprint.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return page
