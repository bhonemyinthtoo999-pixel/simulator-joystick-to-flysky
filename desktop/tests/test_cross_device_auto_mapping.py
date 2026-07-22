from __future__ import annotations

from app.services.auto_mapping_service import AutoMappingSession


def test_cross_device_auto_mapping_captures_stick_and_throttle() -> None:
    session = AutoMappingSession(threshold=0.2, arm_delay_s=0.1)
    neutral = {
        "primary_stick": {"axes": [0.0, 0.0, 0.0]},
        "throttle": {"axes": [-1.0]},
    }
    session.start(neutral, now=0.0)

    roll = session.observe(
        {"primary_stick": {"axes": [0.8, 0.0, 0.0]}, "throttle": {"axes": [-1.0]}},
        now=0.2,
    )
    assert roll is not None
    assert (roll.source_role, roll.axis_index, roll.reversed) == ("primary_stick", 0, False)

    session.observe(neutral, now=0.25)
    pitch = session.observe(
        {"primary_stick": {"axes": [0.0, 0.7, 0.0]}, "throttle": {"axes": [-1.0]}},
        now=0.4,
    )
    assert pitch is not None
    assert (pitch.source_role, pitch.axis_index) == ("primary_stick", 1)

    session.observe(neutral, now=0.45)
    throttle = session.observe(
        {"primary_stick": {"axes": [0.0, 0.0, 0.0]}, "throttle": {"axes": [1.0]}},
        now=0.6,
    )
    assert throttle is not None
    assert (throttle.source_role, throttle.axis_index) == ("throttle", 0)

    session.observe(neutral, now=0.65)
    yaw = session.observe(
        {"primary_stick": {"axes": [0.0, 0.0, -0.8]}, "throttle": {"axes": [-1.0]}},
        now=0.8,
    )
    assert yaw is not None
    assert (yaw.source_role, yaw.axis_index, yaw.reversed) == ("primary_stick", 2, True)
    assert session.complete is True
