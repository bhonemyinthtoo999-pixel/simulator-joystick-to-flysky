from __future__ import annotations

from app.services.calibration_service import AxisCalibration
from app.services.channel_mapping_service import ChannelMapper, ChannelMapping


def test_unipolar_calibration_ignores_captured_center() -> None:
    calibration = AxisCalibration(minimum=-0.92, center=-0.90, maximum=0.84)
    mapping = ChannelMapping(
        channel=3,
        name="Throttle",
        source_type="axis",
        source_index=0,
        mode="unipolar",
        minimum=1000,
        center=1500,
        maximum=2000,
        failsafe=1000,
    )
    mapper = ChannelMapper()

    assert mapper.map_channels({"axes": [-0.92]}, [mapping], [calibration]) == [1000]
    assert mapper.map_channels({"axes": [0.84]}, [mapping], [calibration]) == [2000]


def test_centered_axis_still_uses_captured_neutral() -> None:
    calibration = AxisCalibration(minimum=-0.8, center=0.1, maximum=0.9)
    mapping = ChannelMapping(
        channel=1,
        name="Roll",
        source_type="axis",
        source_index=0,
        mode="centered",
    )
    mapper = ChannelMapper()

    assert mapper.map_channels({"axes": [0.1]}, [mapping], [calibration]) == [1500]
