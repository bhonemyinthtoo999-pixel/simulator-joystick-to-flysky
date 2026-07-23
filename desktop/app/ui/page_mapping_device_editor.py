from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QFormLayout, QLayout, QWidget

from ..services.channel_mapping_service import ChannelMapping
from ..services.device_role_service import ROLE_LABELS, ROLE_ORDER
from .page_mapping import MappingPage as BaseMappingPage


class MappingPage(BaseMappingPage):
    """Channel editor with explicit device-role and input selectors.

    The profile stores logical roles so mappings remain portable when USB ports
    change. Selector text also shows the currently resolved physical device,
    making it clear which controller supplies each RC channel.
    """

    def __init__(self) -> None:
        super().__init__()

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(250)
        self.device_combo.setToolTip(
            "Choose which bound USB device supplies this RC channel. "
            "Bind physical controllers in Device role binding above."
        )
        self.source_combo.setMinimumWidth(230)
        self.source_combo.setToolTip(
            "Choose an axis, button or hat from the selected device."
        )

        located = self._find_form_row_for_widget(self.source_combo)
        if located is None:
            raise RuntimeError("Unable to locate the channel source form row")
        source_form, source_row = located
        label_item = source_form.itemAt(
            source_row,
            QFormLayout.ItemRole.LabelRole,
        )
        if label_item is not None and label_item.widget() is not None:
            label_item.widget().setText("Input")
        source_form.insertRow(source_row, "Device", self.device_combo)

        self.device_combo.currentIndexChanged.connect(self._channel_device_changed)
        self.learn_status.setText(
            "Select a device and one of its inputs, or use Learn Input."
        )
        self._set_editor_enabled(False)

    @classmethod
    def _find_form_row_for_widget(
        cls,
        target: QWidget,
    ) -> tuple[QFormLayout, int] | None:
        parent = target.parentWidget()
        while parent is not None:
            layout = parent.layout()
            if isinstance(layout, QFormLayout):
                for row in range(layout.rowCount()):
                    field_item = layout.itemAt(
                        row,
                        QFormLayout.ItemRole.FieldRole,
                    )
                    if field_item is not None and cls._item_contains_widget(
                        field_item,
                        target,
                    ):
                        return layout, row
            parent = parent.parentWidget()
        return None

    @classmethod
    def _item_contains_widget(cls, item: Any, target: QWidget) -> bool:
        if item.widget() is target:
            return True
        child_layout = item.layout()
        return cls._layout_contains_widget(child_layout, target)

    @classmethod
    def _layout_contains_widget(
        cls,
        layout: QLayout | None,
        target: QWidget,
    ) -> bool:
        if layout is None:
            return False
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target:
                return True
            if cls._layout_contains_widget(item.layout(), target):
                return True
        return False

    def _set_editor_enabled(self, enabled: bool) -> None:
        super()._set_editor_enabled(enabled)
        if hasattr(self, "device_combo"):
            self.device_combo.setEnabled(enabled)

    def _populate_sources(
        self,
        wanted: tuple[str, str, int, str, float] | None = None,
    ) -> None:
        """Populate device and input selectors independently."""

        wanted_role = wanted[0] if wanted is not None else "primary_stick"

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for role in ROLE_ORDER:
            info = self._resolved_infos.get(role)
            if info is None:
                text = f"{ROLE_LABELS[role]} — not bound / unavailable"
            else:
                text = f"{ROLE_LABELS[role]} — {info.name}"
            self.device_combo.addItem(text, role)

        role_index = self.device_combo.findData(wanted_role)
        self.device_combo.setCurrentIndex(max(0, role_index))
        selected_role = str(
            self.device_combo.currentData() or "primary_stick"
        )
        self.device_combo.blockSignals(False)

        self._populate_inputs_for_role(selected_role, wanted)

    def _populate_inputs_for_role(
        self,
        role: str,
        wanted: tuple[str, str, int, str, float] | None = None,
    ) -> None:
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem(
            "Disabled — use failsafe",
            (role, "none", 0, "x", 0.0),
        )

        info = self._resolved_infos.get(role)
        if info is not None:
            for index in range(info.axes):
                self.source_combo.addItem(
                    f"Axis {index}",
                    (role, "axis", index, "x", 0.0),
                )
            for index in range(info.buttons):
                self.source_combo.addItem(
                    f"Button {index}",
                    (role, "button", index, "x", 0.0),
                )
            for index in range(info.hats):
                self.source_combo.addItem(
                    f"Hat {index} horizontal",
                    (role, "hat", index, "x", 0.0),
                )
                self.source_combo.addItem(
                    f"Hat {index} vertical",
                    (role, "hat", index, "y", 0.0),
                )

        self.source_combo.insertSeparator(self.source_combo.count())
        self.source_combo.addItem(
            "Constant low",
            (role, "constant", 0, "x", -1.0),
        )
        self.source_combo.addItem(
            "Constant center",
            (role, "constant", 0, "x", 0.0),
        )
        self.source_combo.addItem(
            "Constant high",
            (role, "constant", 0, "x", 1.0),
        )

        selected = False
        if wanted is not None and wanted[0] == role:
            selected = self._set_source_data(wanted)
            if not selected:
                (
                    _wanted_role,
                    source_type,
                    source_index,
                    component,
                    constant,
                ) = wanted
                self.source_combo.addItem(
                    f"Saved {source_type} {source_index} — unavailable",
                    (role, source_type, source_index, component, constant),
                )
                self.source_combo.setCurrentIndex(
                    self.source_combo.count() - 1
                )
                selected = True

        if not selected:
            first_axis = self._find_first_input("axis")
            self.source_combo.setCurrentIndex(
                first_axis if first_axis >= 0 else 0
            )

        self.source_combo.blockSignals(False)

    def _find_first_input(self, source_type: str) -> int:
        for index in range(self.source_combo.count()):
            data = self.source_combo.itemData(index)
            if (
                isinstance(data, tuple)
                and len(data) == 5
                and data[1] == source_type
            ):
                return index
        return -1

    def _channel_device_changed(self, _index: int) -> None:
        if self._updating_editor or not (
            0 <= self._current_index < len(self._mappings)
        ):
            return

        current = self._mappings[self._current_index]
        role = str(
            self.device_combo.currentData() or "primary_stick"
        )
        wanted = (
            role,
            current.source_type,
            current.source_index,
            current.hat_component,
            float(current.constant_value),
        )
        self._populate_inputs_for_role(role, wanted)
        self.learn_status.setText(
            f"Using {self.device_combo.currentText()}. "
            "Choose one of its inputs."
        )
        self._editor_changed()

    def _load_editor(self, mapping: ChannelMapping) -> None:
        super()._load_editor(mapping)
        self.learn_status.setText(
            "Device and input are selected independently. "
            "Learn Input can detect both."
        )

    def _clear_editor(self) -> None:
        super()._clear_editor()
        if hasattr(self, "device_combo"):
            self.device_combo.clear()

    def channel_source_summary(self) -> dict[str, Any]:
        """Expose the selected source for UI tests and diagnostics."""

        return {
            "role": self.device_combo.currentData(),
            "device_text": self.device_combo.currentText(),
            "input_text": self.source_combo.currentText(),
            "source": self.source_combo.currentData(),
        }
