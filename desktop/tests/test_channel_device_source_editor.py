from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.joystick_service import JoystickInfo
from app.services.profile_service import ControllerProfile
from app.ui.pages import MappingPage

_APP: QApplication | None = None


def application() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def device(instance_id: int, name: str, guid: str, axes: int) -> JoystickInfo:
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


def test_channel_can_select_a_device_and_one_of_its_axes() -> None:
    application()
    page = MappingPage()
    profile = ControllerProfile.create()
    profile.device_bindings["primary_stick"] = "STICK"
    profile.device_bindings["throttle"] = "THROTTLE"

    page.set_profile(
        profile,
        [
            device(1, "Thrustmaster T.16000M", "STICK", 4),
            device(2, "Thrustmaster TWCS Throttle", "THROTTLE", 3),
        ],
        selected_instance_id=1,
    )

    page.channel_list.setCurrentRow(2)
    throttle_index = page.device_combo.findData("throttle")
    assert throttle_index >= 0
    page.device_combo.setCurrentIndex(throttle_index)
    assert "TWCS Throttle" in page.device_combo.currentText()

    axis_index = -1
    for index in range(page.source_combo.count()):
        data = page.source_combo.itemData(index)
        if data == ("throttle", "axis", 1, "x", 0.0):
            axis_index = index
            break
    assert axis_index >= 0
    page.source_combo.setCurrentIndex(axis_index)

    mapping = page.mappings()[2]
    assert mapping.channel == 3
    assert mapping.source_role == "throttle"
    assert mapping.source_type == "axis"
    assert mapping.source_index == 1
    page.close()
