from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.device_handlers import DeviceHandlersMixin
from app.ui.page_dashboard import DashboardPage


_APP = QApplication.instance() or QApplication([])


class CandidateHarness(DeviceHandlersMixin):
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            last_port="COM8",
            auto_connect=True,
        )


def test_dashboard_shows_actual_board_type() -> None:
    page = DashboardPage()

    page.set_adapter_state(
        "arduino_uno",
        "Arduino UNO/Nano ATmega328P",
        "COM8 @ 115200",
    )
    assert page.device_heading.text() == "ARDUINO UNO / NANO"
    assert "ATmega328P" in page.device_value.text()
    assert "D9" in page.device_detail.text()
    assert "COM8" in page.device_detail.text()

    page.set_adapter_state(
        "arduino_mega",
        "Arduino Mega 2560 ATmega2560",
        "COM9 @ 115200",
    )
    assert page.device_heading.text() == "ARDUINO MEGA 2560"
    assert "D11" in page.device_detail.text()

    page.set_adapter_state(
        "simulator",
        "Built-in ESP32-S3 simulator",
    )
    assert page.device_heading.text() == "TEST SIMULATOR"
    assert "no physical board" in page.device_detail.text().casefold()
    page.close()


def test_auto_detection_prefers_last_known_adapter_port() -> None:
    harness = CandidateHarness()
    ports = [
        {
            "device": "COM3",
            "description": "Standard Serial over Bluetooth link",
            "hwid": "BTHENUM",
            "vid": None,
            "pid": None,
        },
        {
            "device": "COM9",
            "description": "USB-SERIAL CH340",
            "hwid": "USB VID:PID=1A86:7523",
            "vid": 0x1A86,
            "pid": 0x7523,
        },
        {
            "device": "COM8",
            "description": "USB Serial Device",
            "hwid": "USB VID:PID=2341:0043",
            "vid": 0x2341,
            "pid": 0x0043,
        },
    ]

    candidates = harness._adapter_port_candidates(ports)
    assert candidates[0] == "COM8"
    assert "COM9" in candidates
    assert "COM3" not in candidates


def test_single_unknown_serial_port_can_still_be_probed() -> None:
    harness = CandidateHarness()
    harness.settings.last_port = ""
    harness.settings.auto_connect = False
    candidates = harness._adapter_port_candidates(
        [
            {
                "device": "COM12",
                "description": "Unknown serial device",
                "hwid": "",
                "vid": None,
                "pid": None,
            }
        ]
    )
    assert candidates == ["COM12"]


assert _APP is not None
