from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.device_handlers import DeviceHandlersMixin
from app.ui.page_device import DevicePage


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def application() -> QApplication:
    return _TEST_APPLICATION


def test_uno_identity_shows_d9_monitor_and_safety_gates_failsafe() -> None:
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
    assert page.ppm_card.value.text() == "D9"
    assert "PPM output D9" in page.adapter_status.text()
    assert "profile stays on PC" in page.adapter_status.text()
    assert page.upload_button.isHidden()
    assert page.bootloader_button.isHidden()
    assert page.handshake_button.isEnabled()
    assert page.status_button.isEnabled()
    assert page.reboot_button.isEnabled()
    assert not page.failsafe_button.isEnabled()

    page.failsafe_confirm.setChecked(True)
    assert page.failsafe_button.isEnabled()
    assert not page.failsafe_abort_button.isEnabled()
    page.close()
    assert app is not None


def test_channel_monitor_compares_desktop_and_adapter_values() -> None:
    application()
    page = DevicePage()
    page.set_connection(True, "COM8 @ 115200")
    page.set_adapter_identity("arduino_uno", {"board": "Arduino UNO/Nano ATmega328P", "ppm_gpio": 9})
    page.update_desktop_channels([1500, 1475, 1000, 1520], True)
    page.update_adapter_status(
        {
            "stream_active": True,
            "failsafe_active": False,
            "stream_age_ms": 12,
            "ppm_active": True,
            "channels": [1500, 1475, 1000, 1520],
        }
    )

    assert page.stream_card.value.text() == "ACTIVE"
    assert "12 ms" in page.stream_card.detail.text()
    assert page.health_card.value.text() == "HEALTHY"
    assert page._channel_rows[0].result.text() == "MATCH"
    assert page._channel_rows[2].received.text() == "1000 µs"
    page.close()


def test_failsafe_result_state_shows_expected_and_received_values() -> None:
    application()
    page = DevicePage()
    page.set_connection(True, "COM8 @ 115200")
    page.set_adapter_identity("arduino_uno", {"board": "Arduino UNO/Nano ATmega328P", "ppm_gpio": 9})
    page.set_failsafe_test_state(
        "pass",
        "PASS — Arduino communication failsafe verified.",
        100,
        [1500, 1500, 1000, 1500],
        [1500, 1500, 1000, 1500],
    )
    assert page.failsafe_progress.value() == 100
    assert "PASS" in page.failsafe_status.text()
    assert "Received: CH1 1500" in page.failsafe_expected.text()
    page.close()


def test_simulator_is_explicitly_a_no_hardware_test_target() -> None:
    app = application()
    page = DevicePage()
    page.set_connection(True, "Built-in ESP32-S3 simulator")

    assert page.adapter_kind == "simulator"
    assert page.supports_profile_upload is True
    assert "no physical Arduino" in page.adapter_status.text()
    assert not page.upload_button.isHidden()
    assert page.bootloader_button.isHidden()
    assert not page.failsafe_button.isEnabled()
    page.failsafe_confirm.setChecked(True)
    assert page.failsafe_button.isEnabled()
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
