from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel

from ..services.joystick_service import JoystickInfo
from .page_joystick import JoystickPage as _BaseJoystickPage


class JoystickPage(_BaseJoystickPage):
    """Joystick monitor with clear green pressed-switch feedback."""

    def set_selected_device(self, info: JoystickInfo | None) -> None:
        super().set_selected_device(info)
        for label in self._button_labels:
            label.setMinimumHeight(34)
            self._style_button(label, pressed=False)

    def update_state(self, state: dict[str, Any]) -> None:
        super().update_state(state)
        for index, pressed in enumerate(state.get("buttons", [])):
            if index < len(self._button_labels):
                label = self._button_labels[index]
                label.setText(f"B{index}: {'ON' if pressed else 'OFF'}")
                self._style_button(label, bool(pressed))

    @staticmethod
    def _style_button(label: QLabel, pressed: bool) -> None:
        label.setProperty("joystickPressed", pressed)
        if pressed:
            label.setStyleSheet(
                "QLabel { color: #065f46; background: #d1fae5; "
                "border: 2px solid #34d399; border-radius: 8px; "
                "font-weight: 850; padding: 6px 8px; }"
            )
            label.setToolTip("Joystick switch is pressed")
        else:
            label.setStyleSheet(
                "QLabel { color: palette(text); background: palette(base); "
                "border: 1px solid palette(midlight); border-radius: 8px; "
                "font-weight: 650; padding: 6px 8px; }"
            )
            label.setToolTip("Joystick switch is released")
