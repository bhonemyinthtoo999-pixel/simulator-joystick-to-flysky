from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..services.joystick_service import JoystickInfo
from .page_common import clear_layout, page_title


class JoystickPage(QWidget):
    device_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.addWidget(page_title("Joystick Monitor"))

        self.selector = QComboBox()
        self.selector.currentIndexChanged.connect(self._selection_changed)
        self.details = QLabel("Scanning for compatible devices...")
        self.details.setWordWrap(True)
        self.backend_status = QLabel("")
        self.backend_status.setWordWrap(True)
        outer.addWidget(self.selector)
        outer.addWidget(self.details)
        outer.addWidget(self.backend_status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        self.axes_container = QWidget()
        self.axes_layout = QVBoxLayout(self.axes_container)
        self.buttons_container = QWidget()
        self.buttons_layout = QGridLayout(self.buttons_container)
        self.hats_container = QWidget()
        self.hats_layout = QVBoxLayout(self.hats_container)
        content_layout.addWidget(QLabel("Axes"))
        content_layout.addWidget(self.axes_container)
        content_layout.addWidget(QLabel("Buttons"))
        content_layout.addWidget(self.buttons_container)
        content_layout.addWidget(QLabel("Hat switches / D-pad"))
        content_layout.addWidget(self.hats_container)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._infos: dict[int, JoystickInfo] = {}
        self._axis_bars: list[QProgressBar] = []
        self._axis_values: list[QLabel] = []
        self._button_labels: list[QLabel] = []
        self._hat_labels: list[QLabel] = []

    def set_devices(self, devices: list[JoystickInfo], preferred_id: int | None = None) -> int | None:
        self._infos = {device.instance_id: device for device in devices}
        self.selector.blockSignals(True)
        self.selector.clear()
        for device in devices:
            if device.is_virtual:
                suffix = " [Demo]"
            elif device.backend != "SDL":
                suffix = f" [{device.backend}]"
            else:
                suffix = " [SDL]"
            self.selector.addItem(f"{device.name}{suffix}", device.instance_id)
        selected_index = -1
        if devices:
            selected_index = 0
            if preferred_id is not None:
                for index, device in enumerate(devices):
                    if device.instance_id == preferred_id:
                        selected_index = index
                        break
            self.selector.setCurrentIndex(selected_index)
        self.selector.blockSignals(False)
        instance_id = self.selector.itemData(selected_index) if selected_index >= 0 else None
        self.set_selected_device(self._infos.get(instance_id))
        return instance_id

    def set_selected_device(self, info: JoystickInfo | None) -> None:
        clear_layout(self.axes_layout)
        clear_layout(self.buttons_layout)
        clear_layout(self.hats_layout)
        self._axis_bars.clear()
        self._axis_values.clear()
        self._button_labels.clear()
        self._hat_labels.clear()
        if info is None:
            self.details.setText(
                "No compatible joystick is connected. Enable Demo Controller in Settings to test without hardware."
            )
            return
        virtual = "Yes" if info.is_virtual else "No"
        self.details.setText(
            f"{info.name}\nGUID: {info.guid}\nBackend: {info.backend}\n"
            f"Axes: {info.axes} | Buttons: {info.buttons} | Hats: {info.hats} | "
            f"Balls: {info.balls} | Virtual: {virtual}"
        )
        for axis_index in range(info.axes):
            row = QHBoxLayout()
            name = QLabel(f"Axis {axis_index}")
            name.setFixedWidth(65)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(500)
            bar.setTextVisible(False)
            value = QLabel("+0.0000")
            value.setFixedWidth(75)
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

    def update_state(self, state: dict[str, Any]) -> None:
        for index, raw in enumerate(state.get("axes", [])):
            if index < len(self._axis_bars):
                value = float(raw)
                self._axis_bars[index].setValue(max(0, min(1000, round((value + 1.0) * 500))))
                self._axis_values[index].setText(f"{value:+.4f}")
        for index, pressed in enumerate(state.get("buttons", [])):
            if index < len(self._button_labels):
                self._button_labels[index].setText(f"B{index}: {'ON' if pressed else 'OFF'}")
        for index, value in enumerate(state.get("hats", [])):
            if index < len(self._hat_labels):
                self._hat_labels[index].setText(f"Hat {index}: {tuple(value)}")

    def _selection_changed(self, index: int) -> None:
        instance_id = self.selector.itemData(index) if index >= 0 else None
        self.set_selected_device(self._infos.get(instance_id))
        self.device_selected.emit(instance_id)
