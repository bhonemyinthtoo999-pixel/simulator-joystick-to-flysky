from __future__ import annotations

import pytest

from app.services.auto_mapping_service import AutoMappingSession


def state(*axes: float) -> dict[str, object]:
    return {"axes": list(axes), "buttons": [], "hats": []}


def test_auto_mapping_assigns_unique_axes_and_detects_reverse() -> None:
    session = AutoMappingSession(threshold=0.2, arm_delay_s=0.0)
    session.start(state(0.0, 0.0, -1.0, 0.0), now=0.0)

    roll = session.observe(state(0.0, 0.8, -1.0, 0.0), now=0.1)
    assert roll is not None
    assert roll.step.name == "Roll"
    assert roll.axis_index == 1
    assert roll.reversed is False

    pitch = session.observe(state(-0.7, 0.8, -1.0, 0.0), now=0.2)
    assert pitch is not None
    assert pitch.step.name == "Pitch"
    assert pitch.axis_index == 0
    assert pitch.reversed is True

    # Axis 1 is already assigned to Roll and must not be captured again.
    assert session.observe(state(-0.7, -0.8, -1.0, 0.0), now=0.3) is None

    throttle = session.observe(state(-0.7, -0.8, 1.0, 0.0), now=0.4)
    assert throttle is not None
    assert throttle.step.name == "Throttle"
    assert throttle.axis_index == 2
    assert throttle.step.mode == "unipolar"
    assert throttle.step.failsafe == 1000

    yaw = session.observe(state(-0.7, -0.8, 1.0, 0.9), now=0.5)
    assert yaw is not None
    assert yaw.step.name == "Yaw"
    assert yaw.axis_index == 3
    assert session.complete is True
    assert session.active is False


def test_auto_mapping_requires_four_axes() -> None:
    session = AutoMappingSession()
    with pytest.raises(ValueError, match="four joystick axes"):
        session.start(state(0.0, 0.0, 0.0), now=0.0)


def test_auto_mapping_arm_delay_uses_latest_resting_baseline() -> None:
    session = AutoMappingSession(threshold=0.2, arm_delay_s=0.5)
    session.start(state(0.0, 0.0, -1.0, 0.0), now=0.0)

    # Motion during the settle period updates the baseline and is not captured.
    assert session.observe(state(0.1, 0.0, -1.0, 0.0), now=0.2) is None
    assert session.observe(state(0.1, 0.0, -1.0, 0.0), now=0.5) is None

    capture = session.observe(state(0.8, 0.0, -1.0, 0.0), now=0.6)
    assert capture is not None
    assert capture.axis_index == 0
