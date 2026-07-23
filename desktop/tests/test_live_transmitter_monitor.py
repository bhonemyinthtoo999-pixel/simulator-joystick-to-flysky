from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.serial_service import SerialService
from app.ui.transmitter_monitor import LiveTransmitterMonitor


_TEST_APPLICATION = QApplication.instance() or QApplication([])


class _OpenSerial:
    is_open = True

    def close(self) -> None:
        self.is_open = False


def test_live_monitor_uses_final_aetr_values_without_routing_changes() -> None:
    page = LiveTransmitterMonitor()
    page.update_live(
        [1750, 1250, 1900, 1600],
        adapter_kind="arduino_uno",
        connection="COM10 @ 115200",
        streaming=True,
        failsafe=False,
    )

    assert page.canvas._channels == [1750, 1250, 1900, 1600]
    assert page.canvas._link_state == "live"
    assert page.link_badge.text() == "LIVE HARDWARE"
    assert "COM10" in page.link_detail.text()
    page.close()


def test_live_monitor_marks_failsafe_but_keeps_safe_values_visible() -> None:
    page = LiveTransmitterMonitor()
    page.update_live(
        [1500, 1500, 1000, 1500],
        adapter_kind="arduino_uno",
        connection="COM10 @ 115200",
        streaming=True,
        failsafe=True,
    )

    assert page.canvas._link_state == "failsafe"
    assert page.link_badge.text() == "FAILSAFE"
    assert page.canvas._channels[:4] == [1500, 1500, 1000, 1500]
    page.close()


def test_offline_simulator_cannot_replace_an_open_physical_serial_link() -> None:
    service = SerialService()
    physical = _OpenSerial()
    service._serial = physical  # exercise the safety boundary without real hardware
    service._connected_label = "COM10 @ 115200"
    errors: list[str] = []
    service.transport_error.connect(errors.append)

    service.connect_simulator()

    assert service.simulated is False
    assert service._serial is physical
    assert physical.is_open is True
    assert service.connected is True
    assert errors and "physical adapter is active" in errors[-1]
