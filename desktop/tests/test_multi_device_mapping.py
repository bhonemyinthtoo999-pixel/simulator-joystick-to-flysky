from __future__ import annotations

from app.services.channel_mapping_service import ChannelMapper, ChannelMapping


def test_separate_stick_and_throttle_combine_into_aetr() -> None:
    mappings = [
        ChannelMapping(1, "Roll", source_role="primary_stick", source_type="axis", source_index=0),
        ChannelMapping(2, "Pitch", source_role="primary_stick", source_type="axis", source_index=1),
        ChannelMapping(
            3,
            "Throttle",
            source_role="throttle",
            source_type="axis",
            source_index=0,
            mode="unipolar",
            failsafe=1000,
        ),
        ChannelMapping(4, "Yaw", source_role="primary_stick", source_type="axis", source_index=2),
    ]
    states = {
        "primary_stick": {"axes": [0.5, -0.5, 0.25]},
        "throttle": {"axes": [-1.0]},
    }
    mapper = ChannelMapper()

    assert mapper.map_channels_multi(states, mappings) == [1750, 1250, 1000, 1625]
    assert mapper.last_strict_failsafe is False


def test_strict_aetr_failsafe_groups_all_primary_channels() -> None:
    mappings = [
        ChannelMapping(1, "Roll", source_role="primary_stick", source_type="axis", source_index=0, failsafe=1500),
        ChannelMapping(2, "Pitch", source_role="primary_stick", source_type="axis", source_index=1, failsafe=1500),
        ChannelMapping(
            3,
            "Throttle",
            source_role="throttle",
            source_type="axis",
            source_index=0,
            mode="unipolar",
            failsafe=1000,
        ),
        ChannelMapping(4, "Yaw", source_role="primary_stick", source_type="axis", source_index=2, failsafe=1500),
    ]
    mapper = ChannelMapper()
    channels = mapper.map_channels_multi(
        {"primary_stick": {"axes": [0.8, -0.7, 0.2]}, "throttle": None},
        mappings,
        strict_aetr_failsafe=True,
    )

    assert channels == [1500, 1500, 1000, 1500]
    assert mapper.last_strict_failsafe is True
    assert mapper.last_missing_aetr_roles == ["throttle"]


def test_non_strict_mode_only_fails_missing_channel() -> None:
    mappings = [
        ChannelMapping(1, "Roll", source_role="primary_stick", source_type="axis", source_index=0),
        ChannelMapping(2, "Pitch", source_role="primary_stick", source_type="axis", source_index=1),
        ChannelMapping(3, "Throttle", source_role="throttle", source_type="axis", source_index=0, mode="unipolar", failsafe=1000),
        ChannelMapping(4, "Yaw", source_role="primary_stick", source_type="axis", source_index=2),
    ]
    mapper = ChannelMapper()
    channels = mapper.map_channels_multi(
        {"primary_stick": {"axes": [0.4, -0.4, 0.2]}, "throttle": None},
        mappings,
        strict_aetr_failsafe=False,
    )

    assert channels == [1700, 1300, 1000, 1600]
    assert mapper.last_strict_failsafe is False
