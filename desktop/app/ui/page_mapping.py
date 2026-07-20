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


class MappingPage(QWidget):
    apply_requested = Signal(object)
    reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.addWidget(page_title("Channel Mapping"))
        help_text = QLabel(
            "Map any axis, button, hat direction or constant to an RC channel. Per-channel endpoints, trim, expo, "
            "smoothing, reversal and failsafe are applied before PPM output."
        )
        help_text.setWordWrap(True)
        outer.addWidget(help_text)
        button_row = QHBoxLayout()
        self.apply_button = QPushButton("Save mapping to active profile")
        self.reset_button = QPushButton("Reset default mapping")
        self.apply_button.clicked.connect(self._emit_apply)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        button_row.addWidget(self.apply_button)
        button_row.addWidget(self.reset_button)
        button_row.addStretch(1)
        outer.addLayout(button_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setHorizontalSpacing(8)
        scroll.setWidget(self.container)
        outer.addWidget(scroll, 1)
        self._rows: list[dict[str, Any]] = []
        self._profile: ControllerProfile | None = None
        self._counts = (0, 0, 0)
        self.preview_values: list[QLabel] = []

    def set_profile(self, profile: ControllerProfile, axes: int, buttons: int, hats: int) -> None:
        self._profile = profile
        self._counts = (axes, buttons, hats)
        clear_layout(self.grid)
        self._rows.clear()
        self.preview_values.clear()
        headings = ("CH", "Name", "Input source", "Mode", "Rev", "Min", "Center", "Max", "Failsafe", "Trim", "Expo", "Smooth", "Live")
        for column, heading in enumerate(headings):
            label = QLabel(heading)
            label.setStyleSheet("font-weight: 600;")
            self.grid.addWidget(label, 0, column)
        for row_index, mapping in enumerate(profile.mappings, start=1):
            row = self._build_row(mapping)
            self._rows.append(row)
            widgets = [
                QLabel(str(mapping.channel)),
                row["name"],
                row["source"],
                row["mode"],
                row["reversed"],
                row["minimum"],
                row["center"],
                row["maximum"],
                row["failsafe"],
                row["trim"],
                row["expo"],
                row["smoothing"],
                row["preview"],
            ]
            for column, widget in enumerate(widgets):
                self.grid.addWidget(widget, row_index, column)
            self.preview_values.append(row["preview"])
        self.apply_button.setEnabled(bool(profile.mappings))

    def _build_row(self, mapping: ChannelMapping) -> dict[str, Any]:
        name = QLineEdit(mapping.name)
        name.setMaximumWidth(95)
        source = QComboBox()
        source.setMinimumWidth(145)
        source.addItem("Disabled / failsafe", ("none", 0, "x", 0.0))
        axes, buttons, hats = self._counts
        for index in range(axes):
            source.addItem(f"Axis {index}", ("axis", index, "x", 0.0))
        for index in range(buttons):
            source.addItem(f"Button {index}", ("button", index, "x", 0.0))
        for index in range(hats):
            source.addItem(f"Hat {index} X", ("hat", index, "x", 0.0))
            source.addItem(f"Hat {index} Y", ("hat", index, "y", 0.0))
        source.addItem("Constant Low", ("constant", 0, "x", -1.0))
        source.addItem("Constant Center", ("constant", 0, "x", 0.0))
        source.addItem("Constant High", ("constant", 0, "x", 1.0))
        wanted = (mapping.source_type, mapping.source_index, mapping.hat_component, float(mapping.constant_value))
        for index in range(source.count()):
            if source.itemData(index) == wanted:
                source.setCurrentIndex(index)
                break

        mode = QComboBox()
        mode.addItem("Centered", "centered")
        mode.addItem("Unipolar", "unipolar")
        mode.setCurrentIndex(1 if mapping.mode == "unipolar" else 0)
        reversed_box = QCheckBox()
        reversed_box.setChecked(mapping.reversed)

        def pulse_spin(value: int) -> QSpinBox:
            spin = QSpinBox()
            spin.setRange(800, 2200)
            spin.setValue(value)
            spin.setSingleStep(5)
            spin.setMaximumWidth(82)
            return spin

        minimum = pulse_spin(mapping.minimum)
        center = pulse_spin(mapping.center)
        maximum = pulse_spin(mapping.maximum)
        failsafe = pulse_spin(mapping.failsafe)
        trim = QSpinBox()
        trim.setRange(-250, 250)
        trim.setValue(mapping.trim)
        trim.setMaximumWidth(72)
        expo = QDoubleSpinBox()
        expo.setRange(0.0, 1.0)
        expo.setSingleStep(0.05)
        expo.setDecimals(2)
        expo.setValue(mapping.expo)
        expo.setMaximumWidth(70)
        smoothing = QDoubleSpinBox()
        smoothing.setRange(0.0, 0.95)
        smoothing.setSingleStep(0.05)
        smoothing.setDecimals(2)
        smoothing.setValue(mapping.smoothing)
        smoothing.setMaximumWidth(70)
        preview = QLabel(str(mapping.center))
        preview.setMinimumWidth(48)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return {
            "channel": mapping.channel,
            "name": name,
            "source": source,
            "mode": mode,
            "reversed": reversed_box,
            "minimum": minimum,
            "center": center,
            "maximum": maximum,
            "failsafe": failsafe,
            "trim": trim,
            "expo": expo,
            "smoothing": smoothing,
            "preview": preview,
        }

    def mappings(self) -> list[ChannelMapping]:
        result: list[ChannelMapping] = []
        for row in self._rows:
            source_type, source_index, component, constant_value = row["source"].currentData()
            result.append(
                ChannelMapping(
                    channel=row["channel"],
                    name=row["name"].text().strip() or f"CH{row['channel']}",
                    source_type=source_type,
                    source_index=source_index,
                    hat_component=component,
                    constant_value=constant_value,
                    mode=row["mode"].currentData(),
                    reversed=row["reversed"].isChecked(),
                    minimum=row["minimum"].value(),
                    center=row["center"].value(),
                    maximum=row["maximum"].value(),
                    failsafe=row["failsafe"].value(),
                    trim=row["trim"].value(),
                    expo=row["expo"].value(),
                    smoothing=row["smoothing"].value(),
                )
            )
        return result

    def update_preview(self, channels: list[int]) -> None:
        for label, value in zip(self.preview_values, channels):
            label.setText(str(int(value)))

    def _emit_apply(self) -> None:
        self.apply_requested.emit(self.mappings())
