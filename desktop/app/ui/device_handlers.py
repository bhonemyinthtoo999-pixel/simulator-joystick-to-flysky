from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..services.protocol_service import MessageType


class DeviceHandlersMixin:
    def _connect_serial(self, port: str, baud: int) -> None:
        self.settings.last_port = port
        self.settings.serial_baud = baud
        try:
            self.settings_store.save(self.settings)
        except OSError:
            pass
        self.serial_service.set_baud(baud)
        self.serial_service.connect_port(port, baud)

    def _on_ports_changed(self, ports: list[dict[str, Any]]) -> None:
        self.device_page.set_ports(ports, self.settings.last_port)
        if (
            self.settings.auto_connect
            and not self._auto_connect_attempted
            and not self.serial_service.connected
            and self.settings.last_port
            and any(port["device"] == self.settings.last_port for port in ports)
        ):
            self._auto_connect_attempted = True
            self.serial_service.connect_port(self.settings.last_port, self.settings.serial_baud)

    def _on_connection_changed(self, connected: bool, label: str) -> None:
        self._stream_paused_for_test = False
        self._failsafe_test_active = False
        if not connected:
            self._adapter_kind = "disconnected"
            self._adapter_capabilities = set()
        elif "simulator" in label.casefold():
            self._adapter_kind = "simulator"
            self._adapter_capabilities = {"profiles", "desktop_stream", "diagnostics"}
        else:
            self._adapter_kind = "serial_unknown"
            self._adapter_capabilities = set()

        self.device_page.set_connection(connected, label)
        self.dashboard_page.device_value.setText(label if connected else "Disconnected")
        self.diagnostics.info("Serial", f"{'Connected to' if connected else 'Disconnected from'} {label}")

    @staticmethod
    def _classify_adapter(payload: dict[str, Any], current: str = "serial_unknown") -> str:
        board = str(payload.get("board", "")).casefold()
        mode = str(payload.get("mode", "")).casefold()
        raw_capabilities = payload.get("capabilities", [])
        capabilities = {
            str(value).casefold()
            for value in raw_capabilities
            if isinstance(raw_capabilities, (list, tuple, set))
        }

        if "simulat" in board or current == "simulator":
            return "simulator"
        if "arduino uno" in board or "arduino nano" in board or "atmega328" in board:
            return "arduino_uno"
        if "arduino mega" in board or "mega 2560" in board or "atmega2560" in board:
            return "arduino_mega"
        if "arduino" in board or "stream_only" in capabilities or "desktop_bridge" in mode:
            return "arduino"
        if "esp32" in board or "usb_hid_host" in capabilities or "profiles" in capabilities:
            return "esp32"
        return current if current != "disconnected" else "serial_unknown"

    def _record_adapter_identity(self, payload: dict[str, Any]) -> None:
        raw_capabilities = payload.get("capabilities", [])
        if isinstance(raw_capabilities, (list, tuple, set)):
            self._adapter_capabilities.update(str(value).casefold() for value in raw_capabilities)
        self._adapter_kind = self._classify_adapter(payload, self._adapter_kind)
        self.device_page.set_adapter_identity(self._adapter_kind, payload)

    def _on_protocol_message(self, message_type: int, payload: dict[str, Any]) -> None:
        kind = MessageType(message_type)
        self.diagnostics.debug("Protocol", f"RX {kind.name}: {payload}")
        if kind == MessageType.HELLO_RESPONSE:
            self._record_adapter_identity(payload)
            self.device_page.show_message("Handshake complete", payload)
            self.dashboard_page.device_value.setText(str(payload.get("board", "Unknown adapter")))
            self.serial_service.send(MessageType.DEVICE_INFO, {})
        elif kind == MessageType.DEVICE_INFO:
            self._record_adapter_identity(payload)
            self.device_page.show_message("Device information", payload)
        elif kind == MessageType.STATUS:
            self.device_page.update_adapter_status(payload)
            self.device_page.show_message("Live device status", payload)
            if self._failsafe_test_active:
                self._finish_failsafe_test(payload)
        elif kind == MessageType.ACK:
            self.device_page.show_message("Command acknowledged", payload)
        elif kind == MessageType.ERROR:
            self.device_page.show_message("Device error", payload)
            self.diagnostics.error("Device", str(payload))
        elif kind == MessageType.LOG:
            self.diagnostics.info("Firmware", str(payload.get("message", payload)))

    def _start_failsafe_test(self) -> None:
        if self._adapter_kind not in {"arduino_uno", "arduino_mega", "arduino"}:
            QMessageBox.information(
                self,
                "Arduino required",
                "Connect and identify an Arduino UNO/Nano or Mega bridge before running this test.",
            )
            return
        if not self.serial_service.connected:
            QMessageBox.warning(self, "Not connected", "Connect the Arduino serial port first.")
            return
        answer = QMessageBox.warning(
            self,
            "Safety confirmation",
            "Remove propellers and disconnect motor power before continuing.\n\n"
            "The desktop will pause channel streaming for about one second so the Arduino communication failsafe activates.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Ok:
            return

        self._failsafe_test_active = True
        self._stream_paused_for_test = True
        self.device_page.set_failsafe_test_state(
            "waiting",
            "Stream paused. Waiting longer than the Arduino 700 ms communication timeout…",
            35,
        )
        self.diagnostics.info("Failsafe test", "LIVE_CHANNELS paused for Arduino timeout verification")
        QTimer.singleShot(850, self._request_failsafe_status)
        QTimer.singleShot(2200, self._failsafe_test_timeout)

    def _request_failsafe_status(self) -> None:
        if not self._failsafe_test_active:
            return
        self.device_page.set_failsafe_test_state(
            "verifying",
            "Timeout elapsed. Reading Arduino channels and comparing the safe AETR values…",
            72,
        )
        self.serial_service.send(MessageType.STATUS, {})

    def _finish_failsafe_test(self, payload: dict[str, Any]) -> None:
        channels = payload.get("channels", [])
        expected = [1500, 1500, 1000, 1500]
        received: list[int] = []
        if isinstance(channels, list):
            try:
                received = [int(value) for value in channels[:4]]
            except (TypeError, ValueError):
                received = []

        self._failsafe_test_active = False
        self._stream_paused_for_test = False
        passed = len(received) == 4 and all(abs(received[i] - expected[i]) <= 5 for i in range(4))
        if passed:
            self.device_page.set_failsafe_test_state(
                "pass",
                "PASS — Arduino communication failsafe verified. Normal live streaming has resumed.",
                100,
            )
            self.diagnostics.info("Failsafe test", f"PASS: Arduino returned {received}")
        else:
            self.device_page.set_failsafe_test_state(
                "fail",
                f"FAIL — expected {expected}, received {received or 'no valid channel array'}. Normal streaming has resumed.",
                100,
            )
            self.diagnostics.error("Failsafe test", f"FAIL: expected {expected}, received {received}")

    def _failsafe_test_timeout(self) -> None:
        if not self._failsafe_test_active:
            return
        self._failsafe_test_active = False
        self._stream_paused_for_test = False
        self.device_page.set_failsafe_test_state(
            "fail",
            "FAIL — no Arduino status response was received. Normal live streaming has resumed.",
            100,
        )
        self.diagnostics.error("Failsafe test", "No status response before timeout")

    def _upload_active_profile(self) -> None:
        if not self.serial_service.connected:
            QMessageBox.warning(self, "Not connected", "Connect an adapter or the test simulator first.")
            return
        if self._adapter_kind not in {"esp32", "simulator"}:
            QMessageBox.information(
                self,
                "Arduino stream bridge",
                "Arduino UNO/Nano and Mega bridges do not store profiles. The active desktop profile, "
                "multi-device AETR mapping and calibration remain on the PC, and final live channels are "
                "already streamed to the Arduino automatically.",
            )
            return

        active = self._active_profile()
        errors = active.validate()
        if errors:
            QMessageBox.warning(self, "Invalid profile", "\n".join(errors[:12]))
            return
        info = self._selected_info()
        calibration = self.calibrations.get(info.guid, []) if info else []
        payload = {
            "profile": active.to_dict(),
            "calibration_guid": info.guid if info else "",
            "calibration": [asdict(axis) for axis in calibration],
        }
        self.serial_service.send(MessageType.PROFILE_VALIDATE, payload)
        self.serial_service.send(MessageType.PROFILE_WRITE, payload)
        self.serial_service.send(MessageType.PROFILE_ACTIVATE, {"profile_id": active.profile_id})
        self.diagnostics.info("Firmware", f"ESP32 profile upload requested for {active.name}")

    def _save_settings(self, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.settings.validate()
        try:
            self.settings_store.save(self.settings)
        except OSError as exc:
            QMessageBox.critical(self, "Settings save failed", str(exc))
            return
        self.joystick_service.set_demo_enabled(self.settings.demo_joystick_enabled)
        self.serial_service.set_baud(self.settings.serial_baud)
        self._apply_channel_rate()
        self.settings_page.set_settings(self.settings)
        self.diagnostics.info("Settings", "Settings saved")

    def _apply_channel_rate(self) -> None:
        interval = max(10, round(1000 / max(1, self.settings.channel_rate_hz)))
        if hasattr(self, "channel_timer"):
            self.channel_timer.setInterval(interval)

    def _export_diagnostics(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Export diagnostics", "simjoy-diagnostics.txt", "Text files (*.txt)")
        if not filename:
            return
        context = {
            "active_profile": self._active_profile().name,
            "selected_joystick": self._selected_info().name if self._selected_info() else "None",
            "serial_connected": self.serial_service.connected,
            "adapter_kind": self._adapter_kind,
            "demo_enabled": self.settings.demo_joystick_enabled,
        }
        try:
            self.diagnostics.export(Path(filename), context)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _transport_error(self, source: str, message: str) -> None:
        self.diagnostics.error(source, message)
        if source == "Joystick":
            self.joystick_page.backend_status.setText(message)
