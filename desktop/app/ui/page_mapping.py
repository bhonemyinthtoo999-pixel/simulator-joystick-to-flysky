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
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..services.auto_mapping_service import AutoMapCapture, AutoMappingSession
from ..services.channel_mapping_service import ChannelMapping
from ..services.device_role_service import (
    AUTO_DEVICE_GUID,
    ROLE_LABELS,
    ROLE_ORDER,
    DeviceRoleResolver,
    default_device_bindings,
)
from ..services.joystick_service import JoystickInfo
from ..services.profile_service import ControllerProfile
from .page_common import page_title


class MappingPage(QWidget):
    """Multi-device channel editor with role binding and AETR safety."""

    apply_requested = Signal(object)
    reset_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._profile: ControllerProfile | None = None
        self._devices: list[JoystickInfo] = []
        self._selected_instance_id: int | None = None
        self._bindings = default_device_bindings()
        self._resolved_infos: dict[str, JoystickInfo | None] = {}
        self._mappings: list[ChannelMapping] = []
        self._current_index = -1
        self._updating_editor = False
        self._updating_bindings = False
        self._live_channels: list[int] = []
        self._latest_role_states: dict[str, dict[str, Any] | None] = {}
        self._learn_baseline: dict[str, dict[str, Any]] | None = None
        self._learning = False
        self._auto_session: AutoMappingSession | None = None
        self._role_combos: dict[str, QComboBox] = {}
        self._role_status: dict[str, QLabel] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(10)
        outer.addWidget(page_title("Channel Mapping"))

        subtitle = QLabel(
            "Bind each USB controller to a logical role, then combine stick, throttle, pedals and auxiliary controls into one RC output."
        )
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        toolbar = QHBoxLayout()
        self.context_label = QLabel("No active profile")
        self.context_label.setStyleSheet("font-weight: 600;")
        self.save_status = QLabel("")
        self.save_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.auto_map_button = QPushButton("Auto-map AETR")
        self.apply_button = QPushButton("Save changes")
        self.reset_button = QPushButton("Reset AETR defaults")
        self.auto_map_button.clicked.connect(self._toggle_auto_mapping)
        self.apply_button.clicked.connect(self._emit_apply)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        toolbar.addWidget(self.context_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.save_status)
        toolbar.addWidget(self.auto_map_button)
        toolbar.addWidget(self.reset_button)
        toolbar.addWidget(self.apply_button)
        outer.addLayout(toolbar)

        outer.addWidget(self._build_role_panel())

        self.auto_panel = QFrame()
        self.auto_panel.setFrameShape(QFrame.Shape.StyledPanel)
        auto_layout = QHBoxLayout(self.auto_panel)
        auto_layout.setContentsMargins(12, 8, 12, 8)
        self.auto_progress = QLabel("Cross-device auto mapping is ready.")
        self.auto_progress.setStyleSheet("font-weight: 700;")
        self.auto_instruction = QLabel(
            "The wizard watches every role-bound device and never assigns the same role/axis pair twice."
        )
        self.auto_instruction.setWordWrap(True)
        auto_layout.addWidget(self.auto_progress)
        auto_layout.addWidget(self.auto_instruction, 1)
        outer.addWidget(self.auto_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_channel_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([310, 820])
        outer.addWidget(splitter, 1)

        self._connect_editor_changes()
        self._set_editor_enabled(False)

    def _build_role_panel(self) -> QGroupBox:
        group = QGroupBox("Device role binding")
        grid = QGridLayout(group)
        explanation = QLabel(
            "Auto-detect works for most HOTAS sets. Bind exact devices when the stick and throttle arrive as separate USB controllers."
        )
        explanation.setWordWrap(True)
        grid.addWidget(explanation, 0, 0, 1, 4)
        for column, role in enumerate(ROLE_ORDER):
            label = QLabel(ROLE_LABELS[role])
            label.setStyleSheet("font-weight: 600;")
            combo = QComboBox()
            combo.setMinimumWidth(210)
            status = QLabel("Not resolved")
            status.setWordWrap(True)
            status.setStyleSheet("font-size: 11px;")
            combo.currentIndexChanged.connect(lambda _index, selected_role=role: self._binding_changed(selected_role))
            grid.addWidget(label, 1, column)
            grid.addWidget(combo, 2, column)
            grid.addWidget(status, 3, column)
            self._role_combos[role] = combo
            self._role_status[role] = status

        self.strict_failsafe_box = QCheckBox(
            "Strict AETR failsafe: if any Roll/Pitch/Throttle/Yaw source disappears, set all CH1–CH4 to failsafe"
        )
        self.strict_failsafe_box.setChecked(True)
        self.strict_failsafe_box.toggled.connect(lambda _checked: self._mark_unsaved())
        grid.addWidget(self.strict_failsafe_box, 4, 0, 1, 4)
        return group

    def _build_channel_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setMinimumWidth(270)
        panel.setMaximumWidth(390)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        heading = QLabel("Combined RC Channels")
        heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        hint = QLabel("Every row shows device role, input source and live output.")
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
        content.setMinimumWidth(650)
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

        identity_group = QGroupBox("Channel and source")
        identity_form = QFormLayout(identity_group)
        identity_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Roll, Pitch, Throttle, Yaw or AUX")
        identity_form.addRow("Channel name", self.name_edit)

        source_row = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.learn_button = QPushButton("Learn Input")
        self.learn_button.clicked.connect(self._toggle_learning)
        source_row.addWidget(self.source_combo, 1)
        source_row.addWidget(self.learn_button)
        identity_form.addRow("Role + input", source_row)
        self.learn_status = QLabel("Choose a role-bound source manually or use Learn Input.")
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
            ("Minimum", self.minimum_spin, "Normally 1000 µs"),
            ("Center", self.center_spin, "Normally 1500 µs"),
            ("Maximum", self.maximum_spin, "Normally 2000 µs"),
            ("Failsafe", self.failsafe_spin, "Used when source is missing"),
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

        preview_group = QGroupBox("Live combined preview")
        preview_layout = QVBoxLayout(preview_group)
        self.live_value = QLabel("1500 µs")
        self.live_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.live_value.setStyleSheet("font-size: 28px; font-weight: 700;")
        self.live_bar = QProgressBar()
        self.live_bar.setRange(800, 2200)
        self.live_bar.setValue(1500)
        self.live_bar.setTextVisible(False)
        self.live_bar.setMinimumHeight(24)
        self.raw_input_label = QLabel("Raw input: waiting for role-bound device data")
        self.raw_input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.live_value)
        preview_layout.addWidget(self.live_bar)
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

    def set_profile(
        self,
        profile: ControllerProfile,
        devices: list[JoystickInfo],
        selected_instance_id: int | None,
    ) -> None:
        previous_channel = self._current_index
        self._profile = profile
        self._devices = list(devices)
        self._selected_instance_id = selected_instance_id
        self._bindings = default_device_bindings()
        self._bindings.update(profile.device_bindings)
        self._mappings = [replace(mapping) for mapping in profile.mappings]
        self._current_index = -1
        self._learning = False
        self._learn_baseline = None
        self._cancel_auto_mapping("Cross-device auto mapping is ready.")
        self.save_status.setText("")
        self.strict_failsafe_box.setChecked(profile.strict_aetr_failsafe)
        self._populate_role_bindings()
        self._resolve_role_infos()
        self._refresh_context()

        self.channel_list.blockSignals(True)
        self.channel_list.clear()
        for index, _mapping in enumerate(self._mappings):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, index)
            item.setSizeHint(QSize(250, 62))
            self.channel_list.addItem(item)
            self._refresh_channel_item(index)
        self.channel_list.blockSignals(False)

        has_mappings = bool(self._mappings)
        self.apply_button.setEnabled(has_mappings)
        self._update_auto_map_enabled()
        self._set_editor_enabled(has_mappings)
        if self._mappings:
            selected = min(max(previous_channel, 0), len(self._mappings) - 1)
            self.channel_list.setCurrentRow(selected)
        else:
            self._clear_editor()

    def mappings(self) -> list[ChannelMapping]:
        self._save_current_editor()
        return [replace(mapping) for mapping in self._mappings]

    def device_bindings(self) -> dict[str, str]:
        return dict(self._bindings)

    def strict_aetr_failsafe(self) -> bool:
        return self.strict_failsafe_box.isChecked()

    def update_preview(self, channels: list[int]) -> None:
        self._live_channels = [int(value) for value in channels]
        for index in range(len(self._mappings)):
            self._refresh_channel_item(index)
        self._refresh_selected_live_preview()

    def update_input_states(self, role_states: dict[str, dict[str, Any] | None]) -> None:
        self._latest_role_states = dict(role_states)
        self._refresh_raw_input_label()

        if self._auto_session is not None:
            capture = self._auto_session.observe(role_states)
            if capture is not None:
                self._apply_auto_capture(capture)
                if self._auto_session.complete:
                    self.auto_progress.setText("AETR auto mapping complete")
                    self.auto_instruction.setText(
                        "Roll, Pitch, Throttle and Yaw were captured across the bound devices. Verify live output, then save changes."
                    )
                    self.auto_map_button.setText("Auto-map again")
                    self._auto_session = None
                else:
                    step = self._auto_session.current_step
                    self.auto_progress.setText(self._auto_session.progress_text)
                    self.auto_instruction.setText(
                        f"Captured {ROLE_LABELS[capture.source_role]} Axis {capture.axis_index} for {capture.step.name}. "
                        f"Release the control, then {step.prompt.lower()}."
                    )

        if not self._learning or self._learn_baseline is None:
            return
        learned = self._detect_changed_source(self._learn_baseline, role_states)
        if learned is None:
            return
        role, source_type, source_index, component, constant_value, description = learned
        self._set_source_data((role, source_type, source_index, component, constant_value))
        self._learning = False
        self._learn_baseline = None
        self.learn_button.setText("Learn Input")
        self.learn_status.setText(f"Detected: {description}")
        self._editor_changed()

    def _populate_role_bindings(self) -> None:
        self._updating_bindings = True
        for role, combo in self._role_combos.items():
            combo.clear()
            combo.addItem("Auto-detect", AUTO_DEVICE_GUID)
            for device in self._devices:
                suffix = "Demo" if device.is_virtual else device.backend
                combo.addItem(f"{device.name} [{suffix}]", device.guid)
            wanted = self._bindings.get(role, AUTO_DEVICE_GUID)
            index = combo.findData(wanted)
            if index < 0 and wanted != AUTO_DEVICE_GUID:
                combo.addItem(f"Unavailable saved device ({wanted})", wanted)
                index = combo.count() - 1
            combo.setCurrentIndex(max(0, index))
        self._updating_bindings = False

    def _binding_changed(self, role: str) -> None:
        if self._updating_bindings:
            return
        combo = self._role_combos[role]
        self._bindings[role] = str(combo.currentData() or AUTO_DEVICE_GUID)
        self._resolve_role_infos()
        self._refresh_context()
        if 0 <= self._current_index < len(self._mappings):
            current = self._mappings[self._current_index]
            wanted = self._mapping_source_tuple(current)
            self._populate_sources(wanted)
        for index in range(len(self._mappings)):
            self._refresh_channel_item(index)
        self._update_auto_map_enabled()
        self._mark_unsaved()

    def _resolve_role_infos(self) -> None:
        resolved = DeviceRoleResolver.resolve(
            self._bindings,
            self._devices,
            selected_instance_id=self._selected_instance_id,
        )
        self._resolved_infos = resolved.infos
        for role in ROLE_ORDER:
            info = self._resolved_infos.get(role)
            self._role_status[role].setText(
                f"Resolved: {info.name}\n{info.axes} axes, {info.buttons} buttons"
                if info is not None
                else "Not resolved"
            )

    def _refresh_context(self) -> None:
        profile_name = self._profile.name if self._profile else "No profile"
        connected = len([device for device in self._devices if not device.is_virtual])
        self.context_label.setText(f"Profile: {profile_name}   •   Physical USB devices: {connected}")

    def _update_auto_map_enabled(self) -> None:
        total_axes = sum(info.axes for info in self._resolved_infos.values() if info is not None)
        self.auto_map_button.setEnabled(len(self._mappings) >= 4 and total_axes >= 4)

    def _toggle_auto_mapping(self) -> None:
        if self._auto_session is not None:
            self._cancel_auto_mapping("Auto mapping cancelled. Existing draft mappings were kept.")
            return
        if len(self._mappings) < 4:
            QMessageBox.warning(self, "Not enough channels", "The active profile needs at least four channels.")
            return
        total_axes = sum(len((state or {}).get("axes", [])) for state in self._latest_role_states.values())
        if total_axes < 4:
            QMessageBox.warning(
                self,
                "Role-bound input unavailable",
                "Bind the stick and throttle roles, move both devices once, then start auto mapping.",
            )
            return
        session = AutoMappingSession()
        try:
            session.start(self._latest_role_states)
        except ValueError as exc:
            QMessageBox.warning(self, "Auto mapping unavailable", str(exc))
            return
        self._learning = False
        self._learn_baseline = None
        self.learn_button.setText("Learn Input")
        self._auto_session = session
        self.auto_map_button.setText("Cancel auto-map")
        self.auto_progress.setText(session.progress_text)
        step = session.current_step
        self.auto_instruction.setText(f"Release all controls, wait briefly, then {step.prompt.lower()}.")

    def _cancel_auto_mapping(self, message: str) -> None:
        if self._auto_session is not None:
            self._auto_session.cancel()
        self._auto_session = None
        self.auto_map_button.setText("Auto-map AETR")
        self.auto_progress.setText(message)
        self.auto_instruction.setText(
            "The wizard watches every role-bound device and never assigns the same role/axis pair twice."
        )

    def _apply_auto_capture(self, capture: AutoMapCapture) -> None:
        index = capture.step.channel_index
        if not 0 <= index < len(self._mappings):
            return
        current = self._mappings[index]
        self._mappings[index] = replace(
            current,
            name=capture.step.name,
            source_role=capture.source_role,
            source_type="axis",
            source_index=capture.axis_index,
            hat_component="x",
            constant_value=0.0,
            mode=capture.step.mode,
            reversed=capture.reversed,
            minimum=1000,
            center=1500,
            maximum=2000,
            failsafe=capture.step.failsafe,
            trim=0,
            expo=0.0,
            smoothing=0.0,
        )
        self._refresh_channel_item(index)
        if self._current_index == index:
            self._load_editor(self._mappings[index])
        self.save_status.setText("Unsaved cross-device AETR mapping")

    def _populate_sources(self, wanted: tuple[str, str, int, str, float] | None = None) -> None:
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem("Disabled — use failsafe", ("primary_stick", "none", 0, "x", 0.0))
        for role in ROLE_ORDER:
            info = self._resolved_infos.get(role)
            if info is None:
                continue
            label = ROLE_LABELS[role]
            self.source_combo.insertSeparator(self.source_combo.count())
            for index in range(info.axes):
                self.source_combo.addItem(
                    f"{label} / {info.name} — Axis {index}",
                    (role, "axis", index, "x", 0.0),
                )
            for index in range(info.buttons):
                self.source_combo.addItem(
                    f"{label} / {info.name} — Button {index}",
                    (role, "button", index, "x", 0.0),
                )
            for index in range(info.hats):
                self.source_combo.addItem(
                    f"{label} / {info.name} — Hat {index} horizontal",
                    (role, "hat", index, "x", 0.0),
                )
                self.source_combo.addItem(
                    f"{label} / {info.name} — Hat {index} vertical",
                    (role, "hat", index, "y", 0.0),
                )
        self.source_combo.insertSeparator(self.source_combo.count())
        self.source_combo.addItem("Constant low", ("primary_stick", "constant", 0, "x", -1.0))
        self.source_combo.addItem("Constant center", ("primary_stick", "constant", 0, "x", 0.0))
        self.source_combo.addItem("Constant high", ("primary_stick", "constant", 0, "x", 1.0))

        if wanted is not None and not self._set_source_data(wanted):
            role, source_type, source_index, component, constant_value = wanted
            self.source_combo.addItem(
                f"Saved {ROLE_LABELS.get(role, role)} {source_type} {source_index} — unavailable",
                (role, source_type, source_index, component, constant_value),
            )
            self.source_combo.setCurrentIndex(self.source_combo.count() - 1)
        self.source_combo.blockSignals(False)

    def _set_source_data(self, wanted: tuple[str, str, int, str, float]) -> bool:
        for index in range(self.source_combo.count()):
            if self.source_combo.itemData(index) == wanted:
                self.source_combo.setCurrentIndex(index)
                return True
        return False

    @staticmethod
    def _mapping_source_tuple(mapping: ChannelMapping) -> tuple[str, str, int, str, float]:
        return (
            mapping.source_role,
            mapping.source_type,
            mapping.source_index,
            mapping.hat_component,
            float(mapping.constant_value),
        )

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
        self._populate_sources(self._mapping_source_tuple(mapping))
        self.mode_combo.setCurrentIndex(1 if mapping.mode == "unipolar" else 0)
        self.reverse_box.setChecked(mapping.reversed)
        self.minimum_spin.setValue(mapping.minimum)
        self.center_spin.setValue(mapping.center)
        self.maximum_spin.setValue(mapping.maximum)
        self.failsafe_spin.setValue(mapping.failsafe)
        self.trim_spin.setValue(mapping.trim)
        self.expo_spin.setValue(mapping.expo)
        self.smoothing_spin.setValue(mapping.smoothing)
        self.learn_status.setText("Choose a role-bound source manually or use Learn Input.")
        self._updating_editor = False
        self._refresh_selected_live_preview()
        self._refresh_raw_input_label()

    def _save_current_editor(self) -> None:
        if self._updating_editor or not (0 <= self._current_index < len(self._mappings)):
            return
        current = self._mappings[self._current_index]
        source_data = self.source_combo.currentData()
        if not isinstance(source_data, tuple) or len(source_data) != 5:
            source_data = self._mapping_source_tuple(current)
        role, source_type, source_index, component, constant_value = source_data
        self._mappings[self._current_index] = replace(
            current,
            name=self.name_edit.text().strip() or f"CH{current.channel}",
            source_role=str(role),
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
        self._mark_unsaved()

    def _mark_unsaved(self) -> None:
        if not self._updating_bindings:
            self.save_status.setText("Unsaved changes")

    def _refresh_channel_item(self, index: int) -> None:
        if not (0 <= index < len(self._mappings)):
            return
        item = self.channel_list.item(index)
        if item is None:
            return
        mapping = self._mappings[index]
        value = self._live_channels[index] if index < len(self._live_channels) else mapping.failsafe
        text = f"CH{mapping.channel}  {mapping.name}\n{self._source_description(mapping)}   •   {value} µs"
        if item.text() != text:
            item.setText(text)

    def _refresh_selected_live_preview(self) -> None:
        if not (0 <= self._current_index < len(self._mappings)):
            return
        mapping = self._mappings[self._current_index]
        value = self._live_channels[self._current_index] if self._current_index < len(self._live_channels) else mapping.failsafe
        value = max(800, min(2200, int(value)))
        self.live_value.setText(f"{value} µs")
        self.live_bar.setValue(value)

    def _refresh_raw_input_label(self) -> None:
        if not (0 <= self._current_index < len(self._mappings)):
            self.raw_input_label.setText("Raw input: no channel selected")
            return
        mapping = self._mappings[self._current_index]
        state = self._latest_role_states.get(mapping.source_role) or {}
        role_label = ROLE_LABELS.get(mapping.source_role, mapping.source_role)
        try:
            if mapping.source_type == "axis":
                value = float(state.get("axes", [])[mapping.source_index])
                self.raw_input_label.setText(f"Raw input: {role_label} Axis {mapping.source_index} = {value:+.4f}")
            elif mapping.source_type == "button":
                pressed = bool(state.get("buttons", [])[mapping.source_index])
                self.raw_input_label.setText(
                    f"Raw input: {role_label} Button {mapping.source_index} = {'ON' if pressed else 'OFF'}"
                )
            elif mapping.source_type == "hat":
                value = state.get("hats", [])[mapping.source_index]
                self.raw_input_label.setText(f"Raw input: {role_label} Hat {mapping.source_index} = {tuple(value)}")
            elif mapping.source_type == "constant":
                self.raw_input_label.setText(f"Raw input: Constant = {mapping.constant_value:+.1f}")
            else:
                self.raw_input_label.setText("Raw input: disabled — failsafe is active")
        except (IndexError, TypeError, ValueError):
            self.raw_input_label.setText(f"Raw input: {role_label} source is unavailable")

    @staticmethod
    def _source_description(mapping: ChannelMapping) -> str:
        role = ROLE_LABELS.get(mapping.source_role, mapping.source_role)
        if mapping.source_type == "axis":
            return f"{role} / Axis {mapping.source_index}"
        if mapping.source_type == "button":
            return f"{role} / Button {mapping.source_index}"
        if mapping.source_type == "hat":
            return f"{role} / Hat {mapping.source_index} {mapping.hat_component.upper()}"
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
        if not any(self._latest_role_states.values()):
            self.learn_status.setText("No role-bound joystick data yet. Move the devices and try again.")
            return
        if self._auto_session is not None:
            self._cancel_auto_mapping("Auto mapping cancelled because single-channel learning started.")
        self._learning = True
        self._learn_baseline = self._copy_role_states(self._latest_role_states)
        self.learn_button.setText("Cancel Learn")
        self.learn_status.setText("Move one control on any bound USB device now…")

    @staticmethod
    def _copy_role_states(
        states: dict[str, dict[str, Any] | None]
    ) -> dict[str, dict[str, Any]]:
        copied: dict[str, dict[str, Any]] = {}
        for role, state in states.items():
            if not state:
                continue
            copied[role] = {
                "axes": list(state.get("axes", [])),
                "buttons": list(state.get("buttons", [])),
                "hats": [tuple(value) for value in state.get("hats", [])],
            }
        return copied

    @staticmethod
    def _detect_changed_source(
        baseline: dict[str, dict[str, Any]],
        states: dict[str, dict[str, Any] | None],
    ) -> tuple[str, str, int, str, float, str] | None:
        strongest: tuple[str, int, float] | None = None
        for role in ROLE_ORDER:
            before = baseline.get(role, {})
            state = states.get(role) or {}
            before_axes = before.get("axes", [])
            axes = state.get("axes", [])
            for index in range(min(len(before_axes), len(axes))):
                change = abs(float(axes[index]) - float(before_axes[index]))
                if strongest is None or change > strongest[2]:
                    strongest = (role, index, change)
        if strongest is not None and strongest[2] >= 0.15:
            role, index, _change = strongest
            return (role, "axis", index, "x", 0.0, f"{ROLE_LABELS[role]} Axis {index}")

        for role in ROLE_ORDER:
            before = baseline.get(role, {})
            state = states.get(role) or {}
            before_buttons = before.get("buttons", [])
            buttons = state.get("buttons", [])
            for index in range(min(len(before_buttons), len(buttons))):
                if bool(buttons[index]) and not bool(before_buttons[index]):
                    return (role, "button", index, "x", 0.0, f"{ROLE_LABELS[role]} Button {index}")
            before_hats = before.get("hats", [])
            hats = state.get("hats", [])
            for index in range(min(len(before_hats), len(hats))):
                previous = tuple(before_hats[index])
                current = tuple(hats[index])
                if current != previous and current != (0, 0):
                    component = "x" if abs(int(current[0])) >= abs(int(current[1])) else "y"
                    return (role, "hat", index, component, 0.0, f"{ROLE_LABELS[role]} Hat {index} {component.upper()}")
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
        self.channel_heading.setText("Select a channel")
        self.channel_badge.setText("")
        self.name_edit.clear()
        self.source_combo.clear()
        self.live_value.setText("1500 µs")
        self.live_bar.setValue(1500)
        self.raw_input_label.setText("Raw input: no channel selected")
        self._updating_editor = False

    def _emit_apply(self) -> None:
        mappings = self.mappings()
        errors: list[str] = []
        for mapping in mappings:
            errors.extend(f"CH{mapping.channel}: {error}" for error in mapping.validate())
        if errors:
            QMessageBox.warning(self, "Invalid channel mapping", "\n".join(errors[:12]))
            return
        self.apply_requested.emit(
            {
                "mappings": mappings,
                "device_bindings": self.device_bindings(),
                "strict_aetr_failsafe": self.strict_aetr_failsafe(),
            }
        )
        self.save_status.setText("Saved")
