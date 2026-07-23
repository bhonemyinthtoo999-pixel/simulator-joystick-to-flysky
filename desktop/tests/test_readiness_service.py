from __future__ import annotations

from app.services.device_role_service import ResolvedDeviceRoles
from app.services.joystick_service import JoystickInfo
from app.services.profile_service import ControllerProfile
from app.services.readiness_service import ReadinessService


def joystick(instance_id: int, name: str, guid: str) -> JoystickInfo:
    return JoystickInfo(
        instance_id=instance_id,
        name=name,
        guid=guid,
        axes=4,
        buttons=12,
        hats=1,
        balls=0,
        power_level="wired",
        is_virtual=False,
    )


def test_ready_report_requires_real_controls_calibration_adapter_and_failsafe() -> None:
    stick = joystick(1, "T.16000M Flight Stick", "stick-guid")
    throttle = joystick(2, "TWCS Throttle", "throttle-guid")
    profile = ControllerProfile.create()
    resolved = ResolvedDeviceRoles(
        infos={
            "primary_stick": stick,
            "throttle": throttle,
            "pedals": None,
            "auxiliary": None,
        },
        states={
            "primary_stick": {"axes": [0.0] * 4},
            "throttle": {"axes": [0.0] * 4},
            "pedals": None,
            "auxiliary": None,
        },
        guids={
            "primary_stick": stick.guid,
            "throttle": throttle.guid,
            "pedals": "",
            "auxiliary": "",
        },
    )

    report = ReadinessService.assess(
        profile=profile,
        devices=[stick, throttle],
        resolved=resolved,
        calibrations={stick.guid: [object()], throttle.guid: [object()]},
        adapter_kind="arduino_uno",
        serial_connected=True,
        strict_failsafe_active=False,
        adapter_capabilities={"fast_channels_v1"},
    )

    assert report.ready is True
    assert report.headline == "READY TO USE"
    assert all(item.passed for item in report.items)


def test_missing_calibration_becomes_next_end_user_action() -> None:
    stick = joystick(1, "Flight Stick", "stick-guid")
    profile = ControllerProfile.create()
    resolved = ResolvedDeviceRoles(
        infos={
            "primary_stick": stick,
            "throttle": stick,
            "pedals": None,
            "auxiliary": None,
        },
        states={
            "primary_stick": {"axes": [0.0] * 4},
            "throttle": {"axes": [0.0] * 4},
            "pedals": None,
            "auxiliary": None,
        },
        guids={
            "primary_stick": stick.guid,
            "throttle": stick.guid,
            "pedals": "",
            "auxiliary": "",
        },
    )

    report = ReadinessService.assess(
        profile=profile,
        devices=[stick],
        resolved=resolved,
        calibrations={},
        adapter_kind="arduino_uno",
        serial_connected=True,
        strict_failsafe_active=False,
    )

    assert report.ready is False
    assert report.next_page == "Calibration"
    assert report.next_action == "Calibrate controls"
