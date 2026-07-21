from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services.channel_mapping_service import ChannelMapping
from ..services.profile_service import ControllerProfile
from .page_common import page_title


class MappingPage(QWidget):
    """Focused channel editor with live preview and input-learning support."""

    apply_requested = Signal(object)
    reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._profile: ControllerProfile | None = None
        self._counts = (0, 0, 0)
        self._mappings: list[ChannelMapping] = []
        self._current_index = -1
        self._updating_editor = False
        self._live_channels: list[int] = []
        self._latest_input_state: dict[str, Any] = {}
        self._learn_baseline: dict[str, Any] | None = None
        self._learning = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(12)
        outer.addWidget(page_title("Channel Mapping"))

        subtitle = QLabel(
            "Select one RC channel, assign a joystick control, then tune its output. "
            "Use Learn Input to identify an axis, button or hat automatically."
        )
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        toolbar = QHBoxLayout()
        self.context_label = QLabel("No active profile")
        self.context_label.setStyleSheet("font-weight: 600;")
        self.save_status = QLabel("")
        self.save_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.apply_button = QPushButton("Save changes")
        self.reset_button = QPushButton("Reset defaults")
        self.apply_button.clicked.connect(self._emit_apply)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        toolbar.addWidget(self.context_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.save_status)
        toolbar.addWidget(self.reset_button)
        toolbar.addWidget(self.apply_button)
        outer.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_channel_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 820])
        outer.addWidget(splitter, 1)

        self._connect_editor_changes()
        self._set_editor_enabled(False)

    def _build_channel_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(370)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)

        heading = QLabel("RC Channels")
        heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        hint = QLabel("Choose a channel to edit. Live output is shown on every row.")
        hint.setWordWrap(True)

        self.channel_list = QListWidget()
        self.channel_list.setSpacing(3)
        self.channel_list.currentRowChanged.connect(self._on_channel_selected)

        layout.addWidget(heading)
        layout.addWidget(hint)
        layout.addWidget(self.channel_list, 1)
        return panel

    def _build_editor_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)

        content = QWidget()
        content.setMinimumWidth(620)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        self.channel_heading = QLabel("Select a channel")
        self.channel_heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        self.channel_badge = QLabel("")
        self.channel_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_badge.setMinimumWidth(80)
        self.channel_badge.setStyleSheet("padding: 5px 10px; border: 1px solid palette(mid); border-radius: 5px;")
        header_row.addWidget(self.channel_heading)
        header_row.addStretch(1)
        header_row.addWidget(self.channel_badge)
        layout.addLayout(header_row)

        identity_group = QGroupBox("Channel and input")
        identity_form = QFormLayout(identity_group)
        identity_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Example: Roll, Pitch, Throttle, Yaw")
        identity_form.addRow("Channel name", self.name_edit)

        source_row = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.learn_button = QPushButton("Learn Input")
        self.learn_button.clicked.connect(self._toggle_learning)
        source_row.addWidget(self.source_combo, 1)
        source_row.addWidget(self.learn_button)
        identity_form.addRow("Input source", source_row)

        self.learn_status = QLabel("Select a source manually or use Learn Input.")
        self.learn_status.setWordWrap(True)
        identity_form.addRow("", self.learn_status)

        mode_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Centered stick (-1 to +1)", "centered")
        self.mode_combo.addItem("Throttle / slider (low to high)", "unipolar")
        self.reverse_box = QCheckBox("Reverse direction")
        mode_row.addWidget(self.mode_combo, 1)
        mode_row.addWidget(self.reverse_box)
        identity_form.addRow("Input behavior", mode_row)
        layout.addWidget(identity_group)

        quick_group = QGroupBox("Quick setup")
        quick_layout = QHBoxLayout(quick_group)
        centered_button = QPushButton("Centered stick")
        throttle_button = QPushButton("Throttle")
        switch_button = QPushButton("Two-position switch")
        centered_button.clicked.connect(self._apply_centered_preset)
        throttle_button.clicked.connect(self._apply_throttle_preset)
        switch_button.clicked.connect(self._apply_switch_preset)
        quick_layout.addWidget(centered_button)
        quick_layout.addWidget(throttle_button)
        quick_layout.addWidget(switch_button)
        quick_layout.addStretch(1)
        layout.addWidget(quick_group)

        endpoints_group = QGroupBox("Output endpoints and safety")
        endpoints_layout = QGridLayout(endpoints_group)
        self.minimum_spin = self._pulse_spin()
        self.center_spin = self._pulse_spin()
        self.maximum_spin = self._pulse_spin()
        self.failsafe_spin = self._pulse_spin()
        endpoint_widgets = (
            ("Minimum", self.minimum_spin, "Low command, normally 1000 µs"),
            ("Center", self.center_spin, "Neutral command, normally 1500 µs"),
            ("Maximum", self.maximum_spin, "High command, normally 2000 µs"),
            ("Failsafe", self.failsafe_spin, "Used when the source is missing"),
        )
        for column, (title, widget, hint_text) in enumerate(endpoint_widgets):
            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: 600;")
            hint_label = QLabel(hint_text)
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet("font-size: 11px;")
            endpoints_layout.addWidget(title_label, 0, column)
            endpoints_layout.addWidget(widget, 1, column)
            endpoints_layout.addWidget(hint_label, 2, column)
        layout.addWidget(endpoints_group)

        tuning_group = QGroupBox("Response tuning")
        tuning_form = QFormLayout(tuning_group)
        self.trim_spin = QSpinBox()
        self.trim_spin.setRange(-250, 250)
        self.trim_spin.setSingleStep(5)
        self.trim_spin.setSuffix(" µs")

        self.expo_spin = QDoubleSpinBox()
        self.expo_spin.setRange(0.0, 1.0)
        self.expo_spin.setSingleStep(0.05)
        self.expo_spin.setDecimals(2)

        self.smoothing_spin = QDoubleSpinBox()
        self.smoothing_spin.setRange(0.0, 0.95)
        self.smoothing_spin.setSingleStep(0.05)
        self.smoothing_spin.setDecimals(2)

        tuning_form.addRow("Trim", self.trim_spin)
        tuning_form.addRow("Expo", self.expo_spin)
        tuning_form.addRow("Smoothing", self.smoothing_spin)
        layout.addWidget(tuning_group)

        preview_group = QGroupBox("Live preview")
        preview_layout = QVBoxLayout(preview_group)
        self.live_value = QLabel("1500 µs")
        self.live_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_value.setStyleSheet("font-size: 28px; font-weight: 700;")
        self.live_bar = QProgressBar()
        self.live_bar.setRange(800, 2200)
        self.live_bar.setValue(1500)
        self.live_bar.setTextVisible(False)
        self.live_bar.setMinimumHeight(24)
        scale = QHBoxLayout()
        scale.addWidget(QLabel("800"))
        scale.addStretch(1)
        scale.addWidget(QLabel("1500"))
        scale.addStretch(1)
        scale.addWidget(QLabel("2200 µs"))
        self.raw_input_label = QLabel("Raw input: waiting for joystick data")
        self.raw_input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.live_value)
        preview_layout.addWidget(self.live_bar)
        preview_layout.addLayout(scale)
        preview_layout.addWidget(self.raw_input_label)
        layout.addWidget(preview_group)
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _pulse_spin() -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(800, 2200)
        spin.setSingleStep(5)
        spin.setSuffix(" µs")
        spin.setMinimumWidth(115)
        return spin

    def _connect_editor_changes(self) -> None:
        self.name_edit.textChanged.connect(self._editor_changed)
        self.source_combo.currentIndexChanged.connect(self._editor_changed)
        self.mode_combo.currentIndexChanged.connect(self._editor_changed)
        self.reverse_box.toggled.connect(self._editor_changed)
        for spin in (
            self.minimum_spin,
            self.center_spin,
            self.maximum_spin,
            self.failsafe_spin,
            self.trim_spin,
            self.expo_spin,
            self.smoothing_spin,
        ):
            spin.valueChanged.connect(self._editor_changed)

    def set_profile(self, profile: ControllerProfile, axes: int, buttons: int, hats: int) -> None:
        previous_channel = self._current_index
        self._profile = profile
        self._counts = (axes, buttons, hats)
        self._mappings = [replace(mapping) for mapping in profile.mappings]
        self._current_index = -1
        self._learning = False
        self._learn_baseline = None
        self.save_status.setText("")
        self.context_label.setText(
            f"Profile: {profile.name}   •   Inputs: {axes} axes, {buttons} buttons, {hats} hats"
        )

        self.channel_list.blockSignals(True)
        self.channel_list.clear()
        for index, mapping in enumerate(self._mappings):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setSizeHint(QSize(230, 58))
            self.channel_list.addItem(item)
            self._refresh_channel_item(index)
        self.channel_list.blockSignals(False)

        self.apply_button.setEnabled(bool(self._mappings))
        self._set_editor_enabled(bool(self._mappings))
        if self._mappings:
            selected = min(max(previous_channel, 0), len(self._mappings) - 1)
            self.channel_list.setCurrentRow(selected)
        else:
            self._clear_editor()

    def mappings(self) -> list[ChannelMapping]:
        self._save_current_editor()
        return [replace(mapping) for mapping in self._mappings]

    def update_preview(self, channels: list[int]) -> None:
        self._live_channels = [int(value) for value in channels]
        for index in range(len(self._mappings)):
            self._refresh_channel_item(index)
        self._refresh_selected_live_preview()

    def update_input_state(self, state: dict[str, Any]) -> None:
        self._latest_input_state = state
        self._refresh_raw_input_label()
        if not self._learning or self._learn_baseline is None:
            return

        learned = self._detect_changed_source(self._learn_baseline, state)
        if learned is None:
            return
        source_type, source_index, component, constant_value, description = learned
        self._set_source_data((source_type, source_index, component, constant_value))
        self._learning = False
        self._learn_baseline = None
        self.learn_button.setText("Learn Input")
        self.learn_status.setText(f"Detected: {description}")
        self._editor_changed()

    def _populate_sources(self, wanted: tuple[str, int, str, float] | None = None) -> None:
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem("Disabled — use failsafe", ("none", 0, "x", 0.0))

        axes, buttons, hats = self._counts
        if axes:
            self.source_combo.insertSeparator(self.source_combo.count())
            for index in range(axes):
                self.source_combo.addItem(f"Axis {index}", ("axis", index, "x", 0.0))
        if buttons:
            self.source_combo.insertSeparator(self.source_combo.count())
            for index in range(buttons):
                self.source_combo.addItem(f"Button {index}", ("button", index, "x", 0.0))
        if hats:
            self.source_combo.insertSeparator(self.source_combo.count())
            for index in range(hats):
                self.source_combo.addItem(f"Hat {index} — horizontal", ("hat", index, "x", 0.0))
                self.source_combo.addItem(f"Hat {index} — vertical", ("hat", index, "y", 0.0))

        self.source_combo.insertSeparator(self.source_combo.count())
        self.source_combo.addItem("Constant low", ("constant", 0, "x", -1.0))
        self.source_combo.addItem("Constant center", ("constant", 0, "x", 0.0))
        self.source_combo.addItem("Constant high", ("constant", 0, "x", 1.0))

        if wanted is not None and not self._set_source_data(wanted):
            source_type, source_index, component, constant_value = wanted
            label = f"Saved {source_type} {source_index} — device input unavailable"
            self.source_combo.addItem(label, (source_type, source_index, component, constant_value))
            self.source_combo.setCurrentIndex(self.source_combo.count() - 1)
        self.source_combo.blockSignals(False)

    def _set_source_data(self, wanted: tuple[str, int, str, float]) -> bool:
        for index in range(self.source_combo.count()):
            if self.source_combo.itemData(index) == wanted:
                self.source_combo.setCurrentIndex(index)
                return True
        return False

    def _on_channel_selected(self, index: int) -> None:
        if index == self._current_index:
            return
        self._save_current_editor()
        self._current_index = index
        self._learning = False
        self._learn_baseline = None
        self.learn_button.setText("Learn Input")
        if 0 <= index < len(self._mappings):
            self._load_editor(self._mappings[index])
        else:
            self._clear_editor()

    def _load_editor(self, mapping: ChannelMapping) -> None:
        self._updating_editor = True
        self.channel_heading.setText(mapping.name or f"Channel {mapping.channel}")
        self.channel_badge.setText(f"CH {mapping.channel}")
        self.name_edit.setText(mapping.name)
        wanted = (
            mapping.source_type,
            mapping.source_index,
            mapping.hat_component,
            float(mapping.constant_value),
        )
        self._populate_sources(wanted)
        self.mode_combo.setCurrentIndex(1 if mapping.mode == "unipolar" else 0)
        self.reverse_box.setChecked(mapping.reversed)
        self.minimum_spin.setValue(mapping.minimum)
        self.center_spin.setValue(mapping.center)
        self.maximum_spin.setValue(mapping.maximum)
        self.failsafe_spin.setValue(mapping.failsafe)
        self.trim_spin.setValue(mapping.trim)
        self.expo_spin.setValue(mapping.expo)
        self.smoothing_spin.setValue(mapping.smoothing)
        self.learn_status.setText("Select a source manually or use Learn Input.")
        self._updating_editor = False
        self._refresh_selected_live_preview()
        self._refresh_raw_input_label()

    def _save_current_editor(self) -> None:
        if self._updating_editor or not (0 <= self._current_index < len(self._mappings)):
            return
        current = self._mappings[self._current_index]
        source_data = self.source_combo.currentData()
        if not isinstance(source_data, tuple) or len(source_data) != 4:
            source_data = (
                current.source_type,
                current.source_index,
                current.hat_component,
                current.constant_value,
            )
        source_type, source_index, component, constant_value = source_data
        self._mappings[self._current_index] = replace(
            current,
            name=self.name_edit.text().strip() or f"CH{current.channel}",
            source_type=source_type,
            source_index=int(source_index),
            hat_component=component,
            constant_value=float(constant_value),
            mode=str(self.mode_combo.currentData()),
            reversed=self.reverse_box.isChecked(),
            minimum=self.minimum_spin.value(),
            center=self.center_spin.value(),
            maximum=self.maximum_spin.value(),
            failsafe=self.failsafe_spin.value(),
            trim=self.trim_spin.value(),
            expo=float(self.expo_spin.value()),
            smoothing=float(self.smoothing_spin.value()),
        )

    def _editor_changed(self, *_: Any) -> None:
        if self._updating_editor:
            return
        self._save_current_editor()
        if 0 <= self._current_index < len(self._mappings):
            mapping = self._mappings[self._current_index]
            self.channel_heading.setText(mapping.name)
            self._refresh_channel_item(self._current_index)
            self._refresh_raw_input_label()
        self.save_status.setText("Unsaved changes")

    def _refresh_channel_item(self, index: int) -> None:
        if not (0 <= index < len(self._mappings)):
            return
        item = self.channel_list.item(index)
        if item is None:
            return
        mapping = self._mappings[index]
        value = self._live_channels[index] if index < len(self._live_channels) else mapping.failsafe
        source = self._source_description(mapping)
        text = f"CH{mapping.channel}  {mapping.name}\n{source}   •   {value} µs"
        if item.text() != text:
            item.setText(text)

    def _refresh_selected_live_preview(self) -> None:
        if not (0 <= self._current_index < len(self._mappings)):
            return
        mapping = self._mappings[self._current_index]
        value = (
            self._live_channels[self._current_index]
            if self._current_index < len(self._live_channels)
            else mapping.failsafe
        )
        value = max(800, min(2200, int(value)))
        self.live_value.setText(f"{value} µs")
        self.live_bar.setValue(value)

    def _refresh_raw_input_label(self) -> None:
        if not (0 <= self._current_index < len(self._mappings)):
            self.raw_input_label.setText("Raw input: no channel selected")
            return
        mapping = self._mappings[self._current_index]
        state = self._latest_input_state
        try:
            if mapping.source_type == "axis":
                value = float(state.get("axes", [])[mapping.source_index])
                self.raw_input_label.setText(f"Raw input: Axis {mapping.source_index} = {value:+.4f}")
            elif mapping.source_type == "button":
                pressed = bool(state.get("buttons", [])[mapping.source_index])
                self.raw_input_label.setText(
                    f"Raw input: Button {mapping.source_index} = {'ON' if pressed else 'OFF'}"
                )
            elif mapping.source_type == "hat":
                value = state.get("hats", [])[mapping.source_index]
                self.raw_input_label.setText(f"Raw input: Hat {mapping.source_index} = {tuple(value)}")
            elif mapping.source_type == "constant":
                self.raw_input_label.setText(f"Raw input: Constant = {mapping.constant_value:+.1f}")
            else:
                self.raw_input_label.setText("Raw input: disabled — failsafe is active")
        except (IndexError, TypeError, ValueError):
            self.raw_input_label.setText("Raw input: selected source is unavailable")

    @staticmethod
    def _source_description(mapping: ChannelMapping) -> str:
        if mapping.source_type == "axis":
            return f"Axis {mapping.source_index}"
        if mapping.source_type == "button":
            return f"Button {mapping.source_index}"
        if mapping.source_type == "hat":
            return f"Hat {mapping.source_index} {mapping.hat_component.upper()}"
        if mapping.source_type == "constant":
            return f"Constant {mapping.constant_value:+.1f}"
        return "Disabled"

    def _toggle_learning(self) -> None:
        if self._learning:
            self._learning = False
            self._learn_baseline = None
            self.learn_button.setText("Learn Input")
            self.learn_status.setText("Input learning cancelled.")
            return
        if not self._latest_input_state:
            self.learn_status.setText("No joystick data yet. Move the joystick and try again.")
            return
        self._learning = True
        self._learn_baseline = {
            "axes": list(self._latest_input_state.get("axes", [])),
            "buttons": list(self._latest_input_state.get("buttons", [])),
            "hats": [tuple(value) for value in self._latest_input_state.get("hats", [])],
        }
        self.learn_button.setText("Cancel Learn")
        self.learn_status.setText("Move one axis, press one button, or move the D-pad now…")

    @staticmethod
    def _detect_changed_source(
        baseline: dict[str, Any], state: dict[str, Any]
    ) -> tuple[str, int, str, float, str] | None:
        before_axes = baseline.get("axes", [])
        axes = state.get("axes", [])
        strongest_axis = -1
        strongest_change = 0.0
        for index in range(min(len(before_axes), len(axes))):
            change = abs(float(axes[index]) - float(before_axes[index]))
            if change > strongest_change:
                strongest_change = change
                strongest_axis = index
        if strongest_axis >= 0 and strongest_change >= 0.15:
            return ("axis", strongest_axis, "x", 0.0, f"Axis {strongest_axis}")

        before_buttons = baseline.get("buttons", [])
        buttons = state.get("buttons", [])
        for index in range(min(len(before_buttons), len(buttons))):
            if bool(buttons[index]) and not bool(before_buttons[index]):
                return ("button", index, "x", 0.0, f"Button {index}")

        before_hats = baseline.get("hats", [])
        hats = state.get("hats", [])
        for index in range(min(len(before_hats), len(hats))):
            before = tuple(before_hats[index])
            current = tuple(hats[index])
            if current != before and current != (0, 0):
                component = "x" if abs(int(current[0])) >= abs(int(current[1])) else "y"
                return ("hat", index, component, 0.0, f"Hat {index} {component.upper()}")
        return None

    def _apply_centered_preset(self) -> None:
        self.mode_combo.setCurrentIndex(0)
        self.minimum_spin.setValue(1000)
        self.center_spin.setValue(1500)
        self.maximum_spin.setValue(2000)
        self.failsafe_spin.setValue(1500)
        self.trim_spin.setValue(0)
        self.expo_spin.setValue(0.0)
        self.smoothing_spin.setValue(0.0)

    def _apply_throttle_preset(self) -> None:
        self.mode_combo.setCurrentIndex(1)
        self.minimum_spin.setValue(1000)
        self.center_spin.setValue(1500)
        self.maximum_spin.setValue(2000)
        self.failsafe_spin.setValue(1000)
        self.trim_spin.setValue(0)
        self.expo_spin.setValue(0.0)
        self.smoothing_spin.setValue(0.0)

    def _apply_switch_preset(self) -> None:
        self.mode_combo.setCurrentIndex(0)
        self.minimum_spin.setValue(1000)
        self.center_spin.setValue(1500)
        self.maximum_spin.setValue(2000)
        self.failsafe_spin.setValue(1000)
        self.trim_spin.setValue(0)
        self.expo_spin.setValue(0.0)
        self.smoothing_spin.setValue(0.0)

    def _set_editor_enabled(self, enabled: bool) -> None:
        for widget in (
            self.name_edit,
            self.source_combo,
            self.learn_button,
            self.mode_combo,
            self.reverse_box,
            self.minimum_spin,
            self.center_spin,
            self.maximum_spin,
            self.failsafe_spin,
            self.trim_spin,
            self.expo_spin,
            self.smoothing_spin,
        ):
            widget.setEnabled(enabled)

    def _clear_editor(self) -> None:
        self._updating_editor = True
        self.channel_heading.setText("No channel available")
        self.channel_badge.setText("")
        self.name_edit.clear()
        self.source_combo.clear()
        self.live_value.setText("—")
        self.raw_input_label.setText("Raw input: unavailable")
        self._updating_editor = False
        self._set_editor_enabled(False)

    def _emit_apply(self) -> None:
        self._save_current_editor()
        self.apply_requested.emit(self.mappings())
