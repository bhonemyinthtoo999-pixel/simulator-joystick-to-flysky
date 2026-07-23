from __future__ import annotations

from collections import deque
import time
from typing import Any

import serial
from serial.tools import list_ports
from PySide6.QtCore import QObject, QTimer, Signal

from .protocol_service import (
    FrameCodec,
    FrameParser,
    MessageType,
    PROTOCOL_MAJOR,
    PROTOCOL_MINOR,
    ProtocolFrame,
)


class SerialService(QObject):
    # These values contain nested Python containers and optional None values.
    # Signal(object) avoids Shiboken QVariant copy-conversion failures.
    ports_changed = Signal(object)
    connection_changed = Signal(bool, str)
    message_received = Signal(int, object)
    transport_error = Signal(str)
    stats_changed = Signal(object)

    def __init__(self, baud: int = 115200) -> None:
        super().__init__()
        self._baud = baud
        self._serial: serial.Serial | None = None
        self._parser = FrameParser()
        self._sequence = 0
        self._connected_label = "Disconnected"
        self._simulated = False
        self._simulated_profile: dict[str, Any] | None = None
        self._simulated_channels = [
            1500,
            1500,
            1000,
            1500,
            1500,
            1500,
            1500,
            1500,
        ]
        self._simulated_pending: deque[
            tuple[MessageType, int, dict[str, Any]]
        ] = deque()
        self._simulated_last_channels_at = 0.0
        self._simulated_stream_active = False
        self._simulated_timeout_s = 0.7
        self._tx_frames = 0
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._last_ports: tuple[tuple[str, str], ...] = ()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(10)
        self._poll_timer.timeout.connect(self._poll)
        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(1000)
        self._scan_timer.timeout.connect(self.scan_ports)
        self._sim_status_timer = QTimer(self)
        self._sim_status_timer.setInterval(500)
        self._sim_status_timer.timeout.connect(self._emit_simulated_status)

    @property
    def connected(self) -> bool:
        return self._simulated or bool(
            self._serial and self._serial.is_open
        )

    @property
    def simulated(self) -> bool:
        return self._simulated

    def start(self) -> None:
        self.force_scan_ports()
        self._poll_timer.start()
        self._scan_timer.start()

    def stop(self) -> None:
        self._poll_timer.stop()
        self._scan_timer.stop()
        self._sim_status_timer.stop()
        self.disconnect()

    def set_baud(self, baud: int) -> None:
        self._baud = int(baud)

    def scan_ports(self, force: bool = False) -> None:
        ports = [
            {
                "device": port.device,
                "description": port.description or "Serial port",
                "hwid": port.hwid or "",
                "vid": port.vid,
                "pid": port.pid,
            }
            for port in list_ports.comports()
        ]
        signature = tuple(
            (item["device"], item["description"])
            for item in ports
        )
        if force or signature != self._last_ports:
            self._last_ports = signature
            self.ports_changed.emit(ports)

    def force_scan_ports(self) -> None:
        self.scan_ports(force=True)

    def connect_port(self, port: str, baud: int | None = None) -> None:
        self.disconnect()
        if not port:
            self.transport_error.emit("Select a serial port first.")
            return
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=int(baud or self._baud),
                timeout=0,
                write_timeout=0.2,
            )
            self._simulated = False
            self._parser = FrameParser()
            self._connected_label = (
                f"{port} @ {int(baud or self._baud)}"
            )
            self.connection_changed.emit(True, self._connected_label)
            self.request_hello()
        except (serial.SerialException, OSError) as exc:
            self._serial = None
            self.transport_error.emit(f"Could not open {port}: {exc}")
            self.connection_changed.emit(False, "Disconnected")

    def connect_simulator(self) -> None:
        self.disconnect()
        self._simulated = True
        self._simulated_channels = [
            1500,
            1500,
            1000,
            1500,
            1500,
            1500,
            1500,
            1500,
        ]
        self._simulated_last_channels_at = 0.0
        self._simulated_stream_active = False
        self._connected_label = "Built-in ESP32-S3 simulator"
        self.connection_changed.emit(True, self._connected_label)
        self._sim_status_timer.start()
        self.request_hello()

    def disconnect(self) -> None:
        self._sim_status_timer.stop()
        self._simulated = False
        self._simulated_stream_active = False
        self._simulated_last_channels_at = 0.0
        self._simulated_pending.clear()
        if self._serial is not None:
            try:
                self._serial.close()
            except (serial.SerialException, OSError):
                pass
        self._serial = None
        if self._connected_label != "Disconnected":
            self._connected_label = "Disconnected"
            self.connection_changed.emit(False, "Disconnected")

    def request_hello(self) -> int:
        return self.send(
            MessageType.HELLO,
            {
                "client": "simulator-joystick-to-flysky-desktop",
                "protocol_major": PROTOCOL_MAJOR,
                "protocol_minor": PROTOCOL_MINOR,
            },
        )

    def send(
        self,
        message_type: MessageType | int,
        payload: dict[str, Any] | None = None,
    ) -> int:
        self._sequence = (self._sequence + 1) & 0xFFFF
        kind = MessageType(message_type)
        frame = FrameCodec.encode(
            kind,
            self._sequence,
            payload or {},
        )
        if self._simulated:
            self._tx_frames += 1
            self._tx_bytes += len(frame)
            self._simulate_request(
                kind,
                self._sequence,
                payload or {},
            )
            self._emit_stats()
            return self._sequence
        if not self._serial or not self._serial.is_open:
            return self._sequence
        try:
            written = self._serial.write(frame)
            self._tx_frames += 1
            self._tx_bytes += written
            self._emit_stats()
        except (serial.SerialException, OSError) as exc:
            self.transport_error.emit(f"Serial write failed: {exc}")
            self.disconnect()
        return self._sequence

    def _poll(self) -> None:
        if self._simulated:
            if self._simulated_pending:
                kind, sequence, payload = (
                    self._simulated_pending.popleft()
                )
                self._deliver_simulated(kind, sequence, payload)
            return
        if not self._serial or not self._serial.is_open:
            return
        try:
            waiting = self._serial.in_waiting
            if waiting <= 0:
                return
            data = self._serial.read(min(waiting, 4096))
            self._rx_bytes += len(data)
            for frame in self._parser.feed(data):
                self._deliver(frame)
            self._emit_stats()
        except (serial.SerialException, OSError) as exc:
            self.transport_error.emit(f"Serial read failed: {exc}")
            self.disconnect()

    def _deliver(self, frame: ProtocolFrame) -> None:
        self.message_received.emit(
            int(frame.message_type),
            frame.payload,
        )

    def _simulate_request(
        self,
        kind: MessageType,
        sequence: int,
        payload: dict[str, Any],
    ) -> None:
        response_kind = MessageType.ACK
        response: dict[str, Any] = {
            "ok": True,
            "request": kind.name,
            "sequence": sequence,
        }
        if kind == MessageType.HELLO:
            response_kind = MessageType.HELLO_RESPONSE
            response = {
                "protocol_major": PROTOCOL_MAJOR,
                "protocol_minor": PROTOCOL_MINOR,
                "firmware_version": "0.2.0-simulator",
                "board": "ESP32-S3 N16R8 (simulated)",
                "hardware_revision": "SIM-2",
                "capabilities": [
                    "usb_hid_host",
                    "ppm",
                    "profiles",
                    "desktop_stream",
                    "diagnostics",
                    "failsafe",
                ],
            }
        elif kind == MessageType.DEVICE_INFO:
            response_kind = MessageType.DEVICE_INFO
            response = {
                "board": "ESP32-S3 N16R8 (simulated)",
                "firmware_version": "0.2.0-simulator",
                "ppm_gpio": 4,
                "mode": "desktop_stream_simulator",
                "active_profile": (
                    self._simulated_profile or {}
                ).get("name", "Default"),
            }
        elif kind == MessageType.STATUS:
            response_kind = MessageType.STATUS
            response = self._simulated_status_payload()
        elif kind == MessageType.PROFILE_VALIDATE:
            profile = payload.get("profile", {})
            errors = self._validate_simulated_profile(profile)
            response = {
                "ok": not errors,
                "request": kind.name,
                "errors": errors,
            }
            response_kind = (
                MessageType.ACK
                if not errors
                else MessageType.ERROR
            )
        elif kind == MessageType.PROFILE_WRITE:
            profile = payload.get("profile", {})
            errors = self._validate_simulated_profile(profile)
            if errors:
                response_kind = MessageType.ERROR
                response = {
                    "ok": False,
                    "request": kind.name,
                    "errors": errors,
                }
            else:
                self._simulated_profile = profile
                response = {
                    "ok": True,
                    "request": kind.name,
                    "profile_id": profile.get("profile_id"),
                }
        elif kind == MessageType.PROFILE_ACTIVATE:
            response = {
                "ok": self._simulated_profile is not None,
                "request": kind.name,
            }
        elif kind == MessageType.LIVE_CHANNELS:
            channels = payload.get("channels", [])
            if isinstance(channels, list) and channels:
                self._simulated_channels = [
                    max(800, min(2200, int(value)))
                    for value in channels[:16]
                ]
                self._simulated_last_channels_at = time.monotonic()
                self._simulated_stream_active = True
            return
        elif kind == MessageType.REBOOT:
            self._simulated_stream_active = False
            self._simulated_last_channels_at = 0.0
            response = {
                "ok": True,
                "request": kind.name,
                "message": "Simulator rebooted",
            }
        elif kind == MessageType.BOOTLOADER:
            response = {
                "ok": True,
                "request": kind.name,
                "message": "Simulator entered bootloader mode",
            }
        self._simulated_pending.append(
            (response_kind, sequence, response)
        )

    @staticmethod
    def _validate_simulated_profile(profile: Any) -> list[str]:
        errors: list[str] = []
        if not isinstance(profile, dict):
            return ["profile must be an object"]
        channel_count = profile.get("channel_count", 0)
        mappings = profile.get("mappings", [])
        if (
            not isinstance(channel_count, int)
            or not 4 <= channel_count <= 16
        ):
            errors.append("channel_count must be 4..16")
        if (
            not isinstance(mappings, list)
            or len(mappings) != channel_count
        ):
            errors.append("mapping count must match channel_count")
        return errors

    def _simulated_status_payload(self) -> dict[str, Any]:
        now = time.monotonic()
        age_s = (
            now - self._simulated_last_channels_at
            if self._simulated_last_channels_at
            else 0.0
        )
        if (
            self._simulated_stream_active
            and age_s > self._simulated_timeout_s
        ):
            count = max(4, len(self._simulated_channels))
            self._simulated_channels = [
                1000 if index == 2 else 1500
                for index in range(count)
            ]
            self._simulated_stream_active = False
        failsafe_active = not self._simulated_stream_active
        return {
            "uptime_ms": int(now * 1000),
            "joystick_connected": self._simulated_stream_active,
            "stream_active": self._simulated_stream_active,
            "failsafe_active": failsafe_active,
            "stream_age_ms": int(age_s * 1000),
            "ppm_active": True,
            "channels": list(self._simulated_channels),
            "active_profile": (
                self._simulated_profile or {}
            ).get("name", "Default"),
            "faults": (
                ["desktop_stream_timeout"]
                if failsafe_active
                else []
            ),
        }

    def _deliver_simulated(
        self,
        kind: MessageType,
        sequence: int,
        payload: dict[str, Any],
    ) -> None:
        encoded = FrameCodec.encode(kind, sequence, payload)
        self._rx_bytes += len(encoded)
        for frame in self._parser.feed(encoded):
            self._deliver(frame)
        self._emit_stats()

    def _emit_simulated_status(self) -> None:
        if not self._simulated:
            return
        self._deliver_simulated(
            MessageType.STATUS,
            0,
            self._simulated_status_payload(),
        )

    def _emit_stats(self) -> None:
        stats = self._parser.stats()
        stats.update(
            {
                "tx_frames": self._tx_frames,
                "tx_bytes": self._tx_bytes,
                "rx_bytes": self._rx_bytes,
                "connected": self.connected,
                "simulated": self._simulated,
            }
        )
        self.stats_changed.emit(stats)
