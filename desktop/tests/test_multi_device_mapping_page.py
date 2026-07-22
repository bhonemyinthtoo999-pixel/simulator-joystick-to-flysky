from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.joystick_service import JoystickInfo
from app.services.profile_service import ControllerProfile
from app.ui.page_mapping import MappingPage


def _device(instance_id: int, name: str, guid: str, axes: int) -> JoystickInfo:
    return JoystickInfo(
        instance_id=instance_id,
        name=name,
        guid=guid,
        axes=axes,
        buttons=8,
        hats=1,
        balls=0,
        power_level="wired",
        backend="test",
    )


def test_mapping_page_accepts_separate_stick_and_throttle() -> None:
    app = QApplication.instance() or QApplication([])
    page = MappingPage()
    profile = ControllerProfile.create()
    profile.device_bindings["primary_stick"] = "STICK"
    profile.device_bindings["throttle"] = "THROTTLE"
    devices = [
        _device(1, "Thrustmaster T.16000M", "STICK", 3),
        _device(2, "Thrustmaster TWCS Throttle", "THROTTLE", 2),
    ]

    page.set_profile(profile, devices, selected_instance_id=1)

    assert page.device_bindings()["primary_stick"] == "STICK"
    assert page.device_bindings()["throttle"] == "THROTTLE"
    assert page.mappings()[2].source_role == "throttle"
    page.close()
    assert app is not None
