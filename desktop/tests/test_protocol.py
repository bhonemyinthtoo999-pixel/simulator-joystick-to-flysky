from app.services.protocol_service import FrameCodec, FrameParser, MessageType


def test_protocol_roundtrip() -> None:
    raw = FrameCodec.encode(MessageType.HELLO, 42, {"client": "test"})
    frame = FrameCodec.decode(raw)
    assert frame.message_type == MessageType.HELLO
    assert frame.sequence == 42
    assert frame.payload == {"client": "test"}


def test_stream_parser_resynchronizes_after_noise() -> None:
    parser = FrameParser()
    raw = FrameCodec.encode(MessageType.STATUS, 7, {"ok": True})
    frames = parser.feed(b"boot log noise\r\n" + raw[:5])
    assert frames == []
    frames = parser.feed(raw[5:])
    assert len(frames) == 1
    assert frames[0].payload["ok"] is True
    assert parser.discarded_bytes > 0
