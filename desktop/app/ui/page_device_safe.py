from __future__ import annotations

from .page_device import DevicePage as _BaseDevicePage


class DevicePage(_BaseDevicePage):
    """Product-safe adapter page that cannot replace a live physical link."""

    def __init__(self) -> None:
        super().__init__()
        self.simulator_button.setToolTip(
            "Offline software adapter for testing without hardware. It is disabled while a physical COM adapter is active."
        )
        self._sync_simulator_button(self.adapter_kind)

    def _apply_adapter_mode(self, kind: str) -> None:
        super()._apply_adapter_mode(kind)
        self._sync_simulator_button(kind)

    def _sync_simulator_button(self, kind: str) -> None:
        if not hasattr(self, "simulator_button"):
            return
        if kind == "disconnected":
            self.simulator_button.setText("Offline simulator")
            self.simulator_button.setEnabled(True)
            self.simulator_button.setToolTip(
                "Start the software-only adapter when no physical Arduino or ESP32 is connected."
            )
        elif kind == "simulator":
            self.simulator_button.setText("Offline simulator active")
            self.simulator_button.setEnabled(False)
            self.simulator_button.setToolTip("Disconnect the simulator before selecting a physical COM port.")
        else:
            self.simulator_button.setText("Offline simulator — disconnect hardware first")
            self.simulator_button.setEnabled(False)
            self.simulator_button.setToolTip(
                "Physical trainer output is protected. Use the Dashboard live transmitter monitor instead."
            )
