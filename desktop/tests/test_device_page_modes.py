from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.device_handlers import DeviceHandlersMixin
from app.ui.page_device import DevicePage


# Keep one strong Python reference for the entire test module. Constructing a
# QApplication in a helper and discarding the return value can destroy the Qt
# application before the following QWidget is created on CPython/PySide6.
_TEST_APPLICATION = QApplication.instance() or QApplication([])


def application() -> QApplication:
    return _TEST_APPLICATION


def test_uno_identity_hides_esp32_only_actions() -> None:
    app = application()
    page = DevicePage()
    page.set_connection(True, "COM8 @ 115200")
    assert "identifying" in page.adapter_status.text().casefold()

    page.set_adapter_identity(
        "arduino_uno",
        {
            "board": "Arduino UNO/Nano ATmega328P",
            "mode": "desktop_bridge",
            "ppm_gpio": 9,
            "capabilities": ["ppm", "desktop_stream", "failsafe", "stream_only"],
        },
    )

    assert page.adapter_kind == "arduino_uno"
    assert "PPM output D9" in page.adapter_status.text()
    assert "profile stays on PC" in page.adapter_status.text()
    assert page.upload_button.isHidden()
    assert page.bootloader_button.isHidden()
    assert page.handshake_button.isEnabled()
    assert page.reboot_button.isEnabled()
    page.close()
    assert app is not None


def test_simulator_is_explicitly_a_test_target() -> None:
    app = application()
    page = DevicePage()
    page.set_connection(True, "Built-in ESP32-S3 simulator")

    assert page.adapter_kind == "simulator"
    assert page.supports_profile_upload is True
    assert "no physical Arduino" in page.adapter_status.text()
    assert not page.upload_button.isHidden()
    assert page.bootloader_button.isHidden()
    page.close()
    assert app is not None


def test_adapter_classification_distinguishes_boards() -> None:
    assert DeviceHandlersMixin._classify_adapter(
        {"board": "Arduino UNO/Nano ATmega328P", "capabilities": ["stream_only"]}
    ) == "arduino_uno"
    assert DeviceHandlersMixin._classify_adapter(
        {"board": "Arduino Mega 2560 ATmega2560", "capabilities": ["stream_only"]}
    ) == "arduino_mega"
    assert DeviceHandlersMixin._classify_adapter(
        {"board": "ESP32-S3 N16R8", "capabilities": ["usb_hid_host", "profiles"]}
    ) == "esp32"
