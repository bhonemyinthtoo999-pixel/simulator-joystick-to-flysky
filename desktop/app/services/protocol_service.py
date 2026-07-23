from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import json
import struct
from typing import Any, Iterable

MAGIC = b"SJ"
PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 0
MAX_PAYLOAD = 8192
_HEADER = struct.Struct("<2sBBHH")
_CRC = struct.Struct("<H")


class MessageType(IntEnum):
    HELLO = 1
    HELLO_RESPONSE = 2
    DEVICE_INFO = 3
    STATUS = 4
    LIVE_INPUT = 5
    LIVE_CHANNELS = 6
    PROFILE_LIST = 7
    PROFILE_READ = 8
    PROFILE_VALIDATE = 9
    PROFILE_WRITE = 10
    PROFILE_ACTIVATE = 11
    CALIBRATION = 12
    REBOOT = 13
    BOOTLOADER = 14
    ACK = 15
    ERROR = 16
    LOG = 17
    LIVE_CHANNELS_FAST = 18


@dataclass(frozen=True)
class ProtocolFrame:
    major: int
    message_type: MessageType
    sequence: int
    payload: dict[str, Any]


class ProtocolError(ValueError):
    pass


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (
                ((crc << 1) ^ 0x1021) & 0xFFFF
                if crc & 0x8000
                else (crc << 1) & 0xFFFF
            )
    return crc


class FrameCodec:
    @staticmethod
    def _encode_payload(
        message_type: MessageType | int,
        sequence: int,
        payload: bytes,
    ) -> bytes:
        if len(payload) > MAX_PAYLOAD:
            raise ProtocolError(f"payload exceeds {MAX_PAYLOAD} bytes")
        header = _HEADER.pack(
            MAGIC,
            PROTOCOL_MAJOR,
            int(message_type),
            sequence & 0xFFFF,
            len(payload),
        )
        crc = crc16_ccitt(header[2:] + payload)
        return header + payload + _CRC.pack(crc)

    @staticmethod
    def encode(
        message_type: MessageType | int,
        sequence: int,
        payload: dict[str, Any] | None = None,
    ) -> bytes:
        encoded = json.dumps(
            payload or {},
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return FrameCodec._encode_payload(message_type, sequence, encoded)

    @staticmethod
    def encode_fast_channels(
        sequence: int,
        channels: Iterable[int],
    ) -> bytes:
        values = [max(800, min(2200, int(value))) for value in channels]
        if not 4 <= len(values) <= 16:
            raise ProtocolError("fast channel packet requires 4..16 channels")
        payload = bytes([len(values)]) + struct.pack(
            f"<{len(values)}H",
            *values,
        )
        return FrameCodec._encode_payload(
            MessageType.LIVE_CHANNELS_FAST,
            sequence,
            payload,
        )

    @staticmethod
    def decode(frame: bytes) -> ProtocolFrame:
        if len(frame) < _HEADER.size + _CRC.size:
            raise ProtocolError("frame is too short")
        magic, major, message_type, sequence, payload_length = _HEADER.unpack_from(frame)
        expected_length = _HEADER.size + payload_length + _CRC.size
        if magic != MAGIC:
            raise ProtocolError("bad frame magic")
        if payload_length > MAX_PAYLOAD:
            raise ProtocolError("payload is too large")
        if len(frame) != expected_length:
            raise ProtocolError("frame length mismatch")
        payload_bytes = frame[_HEADER.size : _HEADER.size + payload_length]
        expected_crc = _CRC.unpack_from(frame, _HEADER.size + payload_length)[0]
        actual_crc = crc16_ccitt(frame[2 : _HEADER.size] + payload_bytes)
        if expected_crc != actual_crc:
            raise ProtocolError("CRC mismatch")
        try:
            kind = MessageType(message_type)
        except ValueError as exc:
            raise ProtocolError(f"unknown message type {message_type}") from exc

        if kind == MessageType.LIVE_CHANNELS_FAST:
            if not payload_bytes:
                raise ProtocolError("fast channel payload is empty")
            count = payload_bytes[0]
            if not 4 <= count <= 16:
                raise ProtocolError("fast channel count must be 4..16")
            expected_payload_length = 1 + (count * 2)
            if len(payload_bytes) != expected_payload_length:
                raise ProtocolError("fast channel payload length mismatch")
            channels = list(struct.unpack(f"<{count}H", payload_bytes[1:]))
            payload: dict[str, Any] = {
                "channels": channels,
                "encoding": "u16le-v1",
            }
        else:
            try:
                decoded = json.loads(payload_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProtocolError(f"invalid JSON payload: {exc}") from exc
            if not isinstance(decoded, dict):
                raise ProtocolError("payload root must be an object")
            payload = decoded

        return ProtocolFrame(
            major=major,
            message_type=kind,
            sequence=sequence,
            payload=payload,
        )


class FrameParser:
    """Incremental, resynchronizing parser for noisy serial streams."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.frames_received = 0
        self.crc_errors = 0
        self.format_errors = 0
        self.discarded_bytes = 0

    def feed(self, data: bytes) -> list[ProtocolFrame]:
        self._buffer.extend(data)
        frames: list[ProtocolFrame] = []
        while True:
            start = self._buffer.find(MAGIC)
            if start < 0:
                keep = 1 if self._buffer.endswith(MAGIC[:1]) else 0
                discarded = len(self._buffer) - keep
                if discarded > 0:
                    del self._buffer[:discarded]
                    self.discarded_bytes += discarded
                break
            if start > 0:
                del self._buffer[:start]
                self.discarded_bytes += start
            if len(self._buffer) < _HEADER.size:
                break
            _, _, _, _, payload_length = _HEADER.unpack_from(self._buffer)
            if payload_length > MAX_PAYLOAD:
                del self._buffer[0]
                self.format_errors += 1
                continue
            total = _HEADER.size + payload_length + _CRC.size
            if len(self._buffer) < total:
                break
            candidate = bytes(self._buffer[:total])
            try:
                frame = FrameCodec.decode(candidate)
            except ProtocolError as exc:
                if "CRC" in str(exc):
                    self.crc_errors += 1
                else:
                    self.format_errors += 1
                del self._buffer[0]
                continue
            del self._buffer[:total]
            self.frames_received += 1
            frames.append(frame)
        return frames

    def stats(self) -> dict[str, int]:
        return {
            "frames_received": self.frames_received,
            "crc_errors": self.crc_errors,
            "format_errors": self.format_errors,
            "discarded_bytes": self.discarded_bytes,
            "buffered_bytes": len(self._buffer),
        }
