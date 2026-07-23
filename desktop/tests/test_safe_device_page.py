from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.page_device_safe import DevicePage


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_offline_simulator_button_is_disabled_for_physical_adapter() -> None:
    page = DevicePage()
    page.set_connection(True, "COM10 @ 115200")
    page.set_adapter_identity(
        "arduino_uno",
        {"board": "Arduino UNO/Nano ATmega328P", "ppm_gpio": 9},
    )

    assert not page.simulator_button.isEnabled()
    assert "disconnect hardware first" in page.simulator_button.text().casefold()
    assert "protected" in page.simulator_button.toolTip().casefold()
    page.close()


def test_offline_simulator_button_is_available_only_when_disconnected() -> None:
    page = DevicePage()
    page.set_connection(False, "Disconnected")

    assert page.simulator_button.isEnabled()
    assert page.simulator_button.text() == "Offline simulator"
    page.close()
