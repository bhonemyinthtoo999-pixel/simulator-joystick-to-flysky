from app.services.calibration_service import AxisCalibration
from app.services.channel_mapping_service import ChannelMapper, ChannelMapping


def test_centered_axis_mapping() -> None:
    mapper = ChannelMapper()
    mapping = ChannelMapping(channel=1, name="Roll", source_type="axis", source_index=0)
    assert mapper.map_channels({"axes": [-1.0]}, [mapping]) == [1000]
    mapper.reset()
    assert mapper.map_channels({"axes": [0.0]}, [mapping]) == [1500]
    mapper.reset()
    assert mapper.map_channels({"axes": [1.0]}, [mapping]) == [2000]


def test_calibration_and_reverse() -> None:
    mapper = ChannelMapper()
    mapping = ChannelMapping(channel=1, name="Pitch", source_type="axis", source_index=0, reversed=True)
    calibration = AxisCalibration(minimum=-0.5, center=0.0, maximum=0.5)
    assert mapper.map_channels({"axes": [0.5]}, [mapping], [calibration]) == [1000]


def test_missing_source_uses_failsafe() -> None:
    mapper = ChannelMapper()
    mapping = ChannelMapping(channel=3, name="Throttle", source_type="axis", source_index=9, failsafe=1000)
    assert mapper.map_channels({"axes": [0.0]}, [mapping]) == [1000]
