from __future__ import annotations

from app.services.device_role_service import DeviceRoleResolver
from app.services.joystick_service import JoystickInfo


def _device(instance_id: int, name: str, guid: str, axes: int = 4) -> JoystickInfo:
    return JoystickInfo(
        instance_id=instance_id,
        name=name,
        guid=guid,
        axes=axes,
        buttons=12,
        hats=1,
        balls=0,
        power_level="wired",
        backend="test",
    )


def test_auto_roles_prefer_named_separate_throttle() -> None:
    stick = _device(1, "Thrustmaster T.16000M", "STICK")
    throttle = _device(2, "Thrustmaster TWCS Throttle", "THROTTLE", axes=2)
    snapshots = {
        1: {"guid": "STICK", "axes": [0.0, 0.0, 0.0, 0.0]},
        2: {"guid": "THROTTLE", "axes": [-1.0, 0.0]},
    }

    resolved = DeviceRoleResolver.resolve({}, [stick, throttle], snapshots, selected_instance_id=1)

    assert resolved.infos["primary_stick"] == stick
    assert resolved.infos["throttle"] == throttle
    assert resolved.states["throttle"] is snapshots[2]


def test_exact_guid_binding_overrides_name_detection() -> None:
    stick = _device(1, "Primary Stick", "STICK")
    second = _device(2, "Generic USB Controller", "MANUAL", axes=1)
    resolved = DeviceRoleResolver.resolve(
        {"primary_stick": "STICK", "throttle": "MANUAL"},
        [stick, second],
        {1: {"axes": [0.0] * 4}, 2: {"axes": [-1.0]}},
    )

    assert resolved.guids["primary_stick"] == "STICK"
    assert resolved.guids["throttle"] == "MANUAL"
