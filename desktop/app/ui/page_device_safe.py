from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QBoxLayout, QWidget

from ..services.localization_service import (
    apply_widget_language,
    normalize_language,
    text,
)
from .page_device import DevicePage as _BaseDevicePage


class DevicePage(_BaseDevicePage):
    """Product-safe responsive adapter page with bilingual end-user controls."""

    def __init__(self) -> None:
        self._language = "en"
        super().__init__()
        self._connection_row = self._find_layout_with_widget(self.port_combo)
        self._command_row = self._find_layout_with_widget(self.handshake_button)
        self._failsafe_row = self._find_layout_with_widget(self.failsafe_button)
        self._sync_simulator_button(self.adapter_kind)
        self._apply_responsive_layout()

    def _find_layout_with_widget(self, target: QWidget) -> QBoxLayout | None:
        for layout in self.findChildren(QBoxLayout):
            for index in range(layout.count()):
                if layout.itemAt(index).widget() is target:
                    return layout
        return None

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        self._sync_simulator_button(self.adapter_kind)
        apply_widget_language(self, self._language)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        narrow = width < 850
        compact = width < 1080
        if self._connection_row is not None:
            self._connection_row.setDirection(
                QBoxLayout.Direction.TopToBottom
                if narrow
                else QBoxLayout.Direction.LeftToRight
            )
        if self._command_row is not None:
            self._command_row.setDirection(
                QBoxLayout.Direction.TopToBottom
                if compact
                else QBoxLayout.Direction.LeftToRight
            )
        if self._failsafe_row is not None:
            self._failsafe_row.setDirection(
                QBoxLayout.Direction.TopToBottom
                if narrow
                else QBoxLayout.Direction.LeftToRight
            )
        self.port_combo.setMinimumWidth(0 if narrow else 310)

    def _apply_adapter_mode(self, kind: str) -> None:
        super()._apply_adapter_mode(kind)
        self._sync_simulator_button(kind)

    def _sync_simulator_button(self, kind: str) -> None:
        if not hasattr(self, "simulator_button"):
            return
        if kind == "disconnected":
            self.simulator_button.setText(text("Offline simulator", self._language))
            self.simulator_button.setEnabled(True)
            self.simulator_button.setToolTip(
                "Start the software-only adapter when no physical Arduino or ESP32 is connected."
                if self._language == "en"
                else "Physical Arduino သို့မဟုတ် ESP32 မချိတ်ထားချိန်တွင်သာ software simulator ကိုစတင်ပါ။"
            )
        elif kind == "simulator":
            self.simulator_button.setText(text("Offline simulator active", self._language))
            self.simulator_button.setEnabled(False)
            self.simulator_button.setToolTip(
                "Disconnect the simulator before selecting a physical COM port."
                if self._language == "en"
                else "Physical COM port မရွေးမီ simulator ကို disconnect လုပ်ပါ။"
            )
        else:
            self.simulator_button.setText(
                text("Offline simulator — disconnect hardware first", self._language)
            )
            self.simulator_button.setEnabled(False)
            self.simulator_button.setToolTip(
                "Physical trainer output is protected. Use the Dashboard live transmitter monitor instead."
                if self._language == "en"
                else "Physical trainer output ကိုကာကွယ်ထားသည်။ Dashboard ရှိ live transmitter monitor ကိုသုံးပါ။"
            )

    def set_connection(self, connected: bool, label: str) -> None:
        super().set_connection(connected, label)
        apply_widget_language(self, self._language)

    def set_adapter_identity(self, kind: str, payload: dict[str, Any]) -> None:
        super().set_adapter_identity(kind, payload)
        apply_widget_language(self, self._language)

    def update_adapter_status(self, payload: dict[str, Any]) -> None:
        super().update_adapter_status(payload)
        apply_widget_language(self, self._language)

    def set_failsafe_test_state(
        self,
        stage: str,
        message: str,
        progress: int,
        expected: list[int] | None = None,
        actual: list[int] | None = None,
    ) -> None:
        super().set_failsafe_test_state(
            stage,
            message,
            progress,
            expected,
            actual,
        )
        apply_widget_language(self, self._language)
