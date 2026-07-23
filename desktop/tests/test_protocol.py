from app.services.protocol_service import FrameCodec, FrameParser, MessageType


def test_protocol_roundtrip() -> None:
    raw = FrameCodec.encode(MessageType.HELLO, 42, {"client": "test"})
    frame = FrameCodec.decode(raw)
    assert frame.message_type == MessageType.HELLO
    assert frame.sequence == 42
    assert frame.payload == {"client": "test"}


def test_fast_channel_roundtrip_is_compact() -> None:
    channels = [1000, 1500, 2000, 1250, 1750, 1500, 1000, 2000]
    raw = FrameCodec.encode_fast_channels(77, channels)
    frame = FrameCodec.decode(raw)

    assert frame.message_type == MessageType.LIVE_CHANNELS_FAST
    assert frame.sequence == 77
    assert frame.payload["channels"] == channels
    assert frame.payload["encoding"] == "u16le-v1"
    assert len(raw) == 27

    json_frame = FrameCodec.encode(
        MessageType.LIVE_CHANNELS,
        77,
        {
            "profile_id": "example-profile-id",
            "channels": channels,
            "source": "desktop-multi-device",
            "strict_aetr_failsafe": False,
        },
    )
    assert len(raw) < len(json_frame) / 3


def test_stream_parser_resynchronizes_after_noise() -> None:
    parser = FrameParser()
    raw = FrameCodec.encode(MessageType.STATUS, 7, {"ok": True})
    frames = parser.feed(b"boot log noise\r\n" + raw[:5])
    assert frames == []
    frames = parser.feed(raw[5:])
    assert len(frames) == 1
    assert frames[0].payload["ok"] is True
    assert parser.discarded_bytes > 0
