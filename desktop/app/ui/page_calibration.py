from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
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

from ..services.joystick_service import JoystickInfo
from .page_common import clear_layout, page_title


class CalibrationPage(QWidget):
    start_requested = Signal()
    center_requested = Signal()
    save_requested = Signal()
    reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)
        outer.addWidget(page_title("Joystick Calibration"))

        help_text = QLabel(
            "Calibration learns the real minimum, center and maximum of every axis. "
            "This removes offset, uneven travel and old-controller range errors before RC channel mapping."
        )
        help_text.setWordWrap(True)
        outer.addWidget(help_text)

        device_card = QFrame()
        device_card.setFrameShape(QFrame.Shape.StyledPanel)
        device_layout = QHBoxLayout(device_card)
        self.device_name = QLabel("No joystick selected")
        self.device_name.setStyleSheet("font-size: 17px; font-weight: 700;")
        self.device_details = QLabel("")
        self.saved_badge = QLabel("Not calibrated")
        self.saved_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.saved_badge.setMinimumWidth(120)
        self.saved_badge.setStyleSheet(
            "padding: 5px 10px; border: 1px solid palette(mid); border-radius: 5px;"
        )
        device_text = QVBoxLayout()
        device_text.addWidget(self.device_name)
        device_text.addWidget(self.device_details)
        device_layout.addLayout(device_text, 1)
        device_layout.addWidget(self.saved_badge)
        outer.addWidget(device_card)

        steps = QHBoxLayout()
        self.step_labels: list[QLabel] = []
        for number, text in enumerate(
            ("Start", "Move every control", "Release to neutral", "Save"),
            start=1,
        ):
            label = QLabel(f"{number}. {text}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumHeight(34)
            label.setStyleSheet(
                "padding: 6px; border: 1px solid palette(mid); border-radius: 5px;"
            )
            steps.addWidget(label, 1)
            self.step_labels.append(label)
        outer.addLayout(steps)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("Start calibration")
        self.center_button = QPushButton("Capture neutral / center")
        self.save_button = QPushButton("Save calibration")
        self.reset_button = QPushButton("Reset saved calibration")
        self.start_button.clicked.connect(self.start_requested.emit)
        self.center_button.clicked.connect(self.center_requested.emit)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        for button in (
            self.start_button,
            self.center_button,
            self.save_button,
            self.reset_button,
        ):
            action_row.addWidget(button)
        action_row.addStretch(1)
        outer.addLayout(action_row)

        self.status = QLabel("Connect and select a joystick first.")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(38)
        self.status.setStyleSheet(
            "font-weight: 600; padding: 8px; border: 1px solid palette(mid); border-radius: 5px;"
        )
        outer.addWidget(self.status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(12, 12, 12, 12)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.container)
        outer.addWidget(scroll, 1)

        self._rows: list[dict[str, Any]] = []
        self._active = False
        self.set_buttons(False, False, False)
        self._set_step(0)

    def set_device(self, info: JoystickInfo | None, saved: list[Any] | None = None) -> None:
        clear_layout(self.grid)
        self._rows.clear()
        self._active = False
        saved = saved or []

        if info is None:
            self.device_name.setText("No joystick selected")
            self.device_details.setText("")
            self.saved_badge.setText("Not calibrated")
            self.status.setText("Connect and select a joystick first.")
            self.set_buttons(False, False, False)
            self._set_step(0)
            return

        self.device_name.setText(info.name)
        self.device_details.setText(
            f"Backend: {info.backend}   •   GUID: {info.guid}   •   {info.axes} axes"
        )
        self.saved_badge.setText("Calibration saved" if saved else "Not calibrated")

        headings = (
            "Axis",
            "Live position",
            "Raw",
            "Minimum",
            "Center",
            "Maximum",
            "Captured range",
        )
        for column, heading in enumerate(headings):
            label = QLabel(heading)
            label.setStyleSheet("font-weight: 700;")
            self.grid.addWidget(label, 0, column)

        for axis in range(info.axes):
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(500)
            bar.setTextVisible(False)
            bar.setMinimumWidth(240)
            bar.setMinimumHeight(20)

            raw = QLabel("+0.0000")
            minimum = QLabel(f"{saved[axis].minimum:+.4f}" if axis < len(saved) else "—")
            center = QLabel(f"{saved[axis].center:+.4f}" if axis < len(saved) else "—")
            maximum = QLabel(f"{saved[axis].maximum:+.4f}" if axis < len(saved) else "—")
            coverage = QLabel(
                f"{max(0.0, saved[axis].maximum - saved[axis].minimum):.3f}"
                if axis < len(saved)
                else "0.000"
            )

            self.grid.addWidget(QLabel(f"Axis {axis}"), axis + 1, 0)
            self.grid.addWidget(bar, axis + 1, 1)
            self.grid.addWidget(raw, axis + 1, 2)
            self.grid.addWidget(minimum, axis + 1, 3)
            self.grid.addWidget(center, axis + 1, 4)
            self.grid.addWidget(maximum, axis + 1, 5)
            self.grid.addWidget(coverage, axis + 1, 6)
            self._rows.append(
                {
                    "bar": bar,
                    "raw": raw,
                    "minimum": minimum,
                    "center": center,
                    "maximum": maximum,
                    "coverage": coverage,
                }
            )

        self.status.setText(
            "Saved calibration loaded. Start again only when you want to replace it."
            if saved
            else "Ready. Start calibration, then move every axis through its full physical range."
        )
        self.set_buttons(True, False, bool(saved))
        self._set_step(1)

    def update_values(
        self,
        axes: list[float],
        minimum: list[float] | None = None,
        center: list[float] | None = None,
        maximum: list[float] | None = None,
    ) -> None:
        for index, value in enumerate(axes):
            if index >= len(self._rows):
                break
            row = self._rows[index]
            numeric = max(-1.0, min(1.0, float(value)))
            row["bar"].setValue(round((numeric + 1.0) * 500.0))
            row["raw"].setText(f"{float(value):+.4f}")

            if minimum is not None and index < len(minimum):
                low = minimum[index]
                row["minimum"].setText("—" if low == float("inf") else f"{low:+.4f}")
            if center is not None and index < len(center):
                row["center"].setText(f"{center[index]:+.4f}")
            if maximum is not None and index < len(maximum):
                high = maximum[index]
                row["maximum"].setText("—" if high == float("-inf") else f"{high:+.4f}")

            if minimum is not None and maximum is not None:
                low = minimum[index] if index < len(minimum) else float("inf")
                high = maximum[index] if index < len(maximum) else float("-inf")
                coverage = 0.0 if low == float("inf") or high == float("-inf") else max(0.0, high - low)
                row["coverage"].setText(f"{coverage:.3f}")
                if self._active:
                    row["coverage"].setStyleSheet(
                        "font-weight: 700;" if coverage >= 1.5 else "font-weight: 700; color: #b36b00;"
                    )

    def set_buttons(self, connected: bool, active: bool, saved: bool) -> None:
        self._active = active
        self.start_button.setEnabled(connected and not active)
        self.center_button.setEnabled(connected and active)
        self.save_button.setEnabled(connected and active)
        self.reset_button.setEnabled(connected and saved)
        if not connected:
            self._set_step(0)
        elif active:
            self._set_step(2)
        else:
            self._set_step(1)

    def _set_step(self, step: int) -> None:
        for index, label in enumerate(self.step_labels, start=1):
            if index == step:
                label.setStyleSheet(
                    "font-weight: 700; padding: 6px; border: 2px solid palette(highlight); border-radius: 5px;"
                )
            else:
                label.setStyleSheet(
                    "padding: 6px; border: 1px solid palette(mid); border-radius: 5px;"
                )
