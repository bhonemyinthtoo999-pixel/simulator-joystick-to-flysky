from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import time
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ..services.protocol_service import MessageType


class DeviceHandlersMixin:
    _KNOWN_ADAPTER_KINDS = {
        "arduino_uno",
        "arduino_mega",
        "arduino",
        "esp32",
        "simulator",
    }

    def _connect_serial(self, port: str, baud: int) -> None:
        self._cancel_adapter_probe()
        self.settings.last_port = port
        self.settings.serial_baud = baud
        try:
            self.settings_store.save(self.settings)
        except OSError:
            pass
        self.serial_service.set_baud(baud)
        self.serial_service.connect_port(port, baud)

    def _connect_simulator(self) -> None:
        self._cancel_adapter_probe()
        self.serial_service.connect_simulator()

    def _disconnect_serial(self) -> None:
        self._cancel_adapter_probe()
        self.serial_service.disconnect()

    def _cancel_adapter_probe(self) -> None:
        self._adapter_probe_generation = getattr(
            self,
            "_adapter_probe_generation",
            0,
        ) + 1
        self._adapter_probe_active = False
        self._adapter_probe_ports = []
        self._adapter_probe_current = ""

    def _on_ports_changed(self, ports: list[dict[str, Any]]) -> None:
        self.device_page.set_ports(ports, self.settings.last_port)
        signature = tuple(str(item.get("device", "")) for item in ports)

        if self.serial_service.connected or getattr(
            self,
            "_adapter_probe_active",
            False,
        ):
            return

        if self.settings.auto_detect_adapter:
            previous = getattr(self, "_adapter_probe_signature", None)
            if signature == previous:
                return
            self._adapter_probe_signature = signature
            candidates = self._adapter_port_candidates(ports)
            if not candidates:
                self.dashboard_page.set_adapter_state("disconnected")
                return
            self._adapter_probe_generation = getattr(
                self,
                "_adapter_probe_generation",
                0,
            ) + 1
            generation = self._adapter_probe_generation
            self._adapter_probe_ports = candidates
            self._adapter_probe_active = True
            self._probe_next_adapter(generation)
            return

        if (
            self.settings.auto_connect
            and not self._auto_connect_attempted
            and self.settings.last_port
            and any(
                port.get("device") == self.settings.last_port
                for port in ports
            )
        ):
            self._auto_connect_attempted = True
            self.serial_service.connect_port(
                self.settings.last_port,
                self.settings.serial_baud,
            )

    def _adapter_port_candidates(
        self,
        ports: list[dict[str, Any]],
    ) -> list[str]:
        scored: list[tuple[int, str]] = []
        last_port = self.settings.last_port

        for item in ports:
            device = str(item.get("device", "")).strip()
            if not device:
                continue
            description = str(item.get("description", ""))
            hwid = str(item.get("hwid", ""))
            text = f"{description} {hwid}".casefold()
            score = 0

            if self.settings.auto_connect and device == last_port:
                score += 1000
            elif device == last_port:
                score += 120

            strong_hints = (
                "arduino",
                "esp32",
                "atmega",
                "usb serial device",
                "usb-serial",
                "ch340",
                "ch341",
                "cp210",
                "silicon labs",
                "wch.cn",
                "ftdi",
            )
            for hint in strong_hints:
                if hint in text:
                    score += 80

            if item.get("vid") is not None and item.get("pid") is not None:
                score += 10

            if score > 0:
                scored.append((score, device))

        if not scored and len(ports) == 1:
            only_device = str(ports[0].get("device", "")).strip()
            if only_device:
                scored.append((1, only_device))

        scored.sort(key=lambda value: (-value[0], value[1]))
        return [device for _score, device in scored]

    def _probe_next_adapter(self, generation: int) -> None:
        if (
            generation != getattr(self, "_adapter_probe_generation", -1)
            or not getattr(self, "_adapter_probe_active", False)
        ):
            return

        ports = getattr(self, "_adapter_probe_ports", [])
        if not ports:
            self._adapter_probe_active = False
            self._adapter_probe_current = ""
            self.dashboard_page.set_adapter_state("probe_failed")
            self.diagnostics.info(
                "Adapter auto-detect",
                "No candidate serial port returned a compatible firmware handshake",
            )
            return

        port = ports.pop(0)
        self._adapter_probe_current = port
        self.dashboard_page.set_adapter_state(
            "serial_unknown",
            connection=f"Auto-detect probing {port} @ {self.settings.serial_baud}",
        )
        self.diagnostics.info(
            "Adapter auto-detect",
            f"Probing {port} for an Arduino or ESP32 firmware handshake",
        )
        self.serial_service.connect_port(port, self.settings.serial_baud)
        QTimer.singleShot(
            1800,
            lambda token=generation, candidate=port: self._adapter_probe_timeout(
                token,
                candidate,
            ),
        )

    def _adapter_probe_timeout(self, generation: int, port: str) -> None:
        if (
            generation != getattr(self, "_adapter_probe_generation", -1)
            or not getattr(self, "_adapter_probe_active", False)
            or port != getattr(self, "_adapter_probe_current", "")
        ):
            return
        if self._adapter_kind in self._KNOWN_ADAPTER_KINDS:
            return

        self.diagnostics.info(
            "Adapter auto-detect",
            f"No compatible handshake from {port}; trying the next candidate",
        )
        self.serial_service.disconnect()
        QTimer.singleShot(
            120,
            lambda token=generation: self._probe_next_adapter(token),
        )

    def _on_connection_changed(self, connected: bool, label: str) -> None:
        self._failsafe_test_generation = getattr(
            self,
            "_failsafe_test_generation",
            0,
        ) + 1
        self._stream_paused_for_test = False
        self._failsafe_test_active = False
        self._failsafe_verify_after = 0.0
        self._adapter_connection_label = label if connected else ""

        if not connected:
            self._adapter_kind = "disconnected"
            self._adapter_capabilities = set()
            if not getattr(self, "_adapter_probe_active", False):
                self.dashboard_page.set_adapter_state("disconnected")
        elif "simulator" in label.casefold():
            self._adapter_kind = "simulator"
            self._adapter_capabilities = {
                "profiles",
                "desktop_stream",
                "diagnostics",
                "failsafe",
            }
            self.dashboard_page.set_adapter_state(
                "simulator",
                board="Built-in ESP32-S3 simulator",
                connection=label,
            )
        else:
            self._adapter_kind = "serial_unknown"
            self._adapter_capabilities = set()
            self.dashboard_page.set_adapter_state(
                "serial_unknown",
                connection=label,
            )

        self.device_page.set_connection(connected, label)
        self.diagnostics.info(
            "Serial",
            f"{'Connected to' if connected else 'Disconnected from'} {label}",
        )

    @staticmethod
    def _classify_adapter(
        payload: dict[str, Any],
        current: str = "serial_unknown",
    ) -> str:
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
        if (
            "arduino uno" in board
            or "arduino nano" in board
            or "atmega328" in board
        ):
            return "arduino_uno"
        if (
            "arduino mega" in board
            or "mega 2560" in board
            or "atmega2560" in board
        ):
            return "arduino_mega"
        if (
            "arduino" in board
            or "stream_only" in capabilities
            or "desktop_bridge" in mode
        ):
            return "arduino"
        if (
            "esp32" in board
            or "usb_hid_host" in capabilities
            or "profiles" in capabilities
        ):
            return "esp32"
        return current if current != "disconnected" else "serial_unknown"

    def _record_adapter_identity(self, payload: dict[str, Any]) -> None:
        raw_capabilities = payload.get("capabilities", [])
        if isinstance(raw_capabilities, (list, tuple, set)):
            self._adapter_capabilities.update(
                str(value).casefold()
                for value in raw_capabilities
            )
        self._adapter_kind = self._classify_adapter(
            payload,
            self._adapter_kind,
        )
        self.device_page.set_adapter_identity(self._adapter_kind, payload)
        self.dashboard_page.set_adapter_state(
            self._adapter_kind,
            board=str(payload.get("board", "")),
            connection=getattr(self, "_adapter_connection_label", ""),
        )

        if (
            getattr(self, "_adapter_probe_active", False)
            and self._adapter_kind in self._KNOWN_ADAPTER_KINDS
        ):
            detected_port = getattr(self, "_adapter_probe_current", "")
            self._adapter_probe_active = False
            self._adapter_probe_ports = []
            if detected_port:
                self.settings.last_port = detected_port
                try:
                    self.settings_store.save(self.settings)
                except OSError:
                    pass
            self.diagnostics.info(
                "Adapter auto-detect",
                f"Detected {payload.get('board', self._adapter_kind)} on {detected_port}",
            )

    def _on_protocol_message(
        self,
        message_type: int,
        payload: dict[str, Any],
    ) -> None:
        kind = MessageType(message_type)
        self.diagnostics.debug("Protocol", f"RX {kind.name}: {payload}")
        if kind == MessageType.HELLO_RESPONSE:
            self._record_adapter_identity(payload)
            self.device_page.show_message("Handshake complete", payload)
            self.serial_service.send(MessageType.DEVICE_INFO, {})
        elif kind == MessageType.DEVICE_INFO:
            self._record_adapter_identity(payload)
            self.device_page.show_message("Device information", payload)
        elif kind == MessageType.STATUS:
            self.device_page.update_adapter_status(payload)
            self.device_page.show_message("Live device status", payload)
            if (
                self._failsafe_test_active
                and time.monotonic()
                >= getattr(self, "_failsafe_verify_after", 0.0)
            ):
                self._finish_failsafe_test(payload)
        elif kind == MessageType.ACK:
            self.device_page.show_message("Command acknowledged", payload)
        elif kind == MessageType.ERROR:
            self.device_page.show_message("Device error", payload)
            self.diagnostics.error("Device", str(payload))
        elif kind == MessageType.LOG:
            self.diagnostics.info(
                "Firmware",
                str(payload.get("message", payload)),
            )

    def _start_failsafe_test(self) -> None:
        supported = {
            "arduino_uno",
            "arduino_mega",
            "arduino",
            "simulator",
        }
        if self._adapter_kind not in supported:
            QMessageBox.information(
                self,
                "Compatible adapter required",
                "Connect and identify an Arduino UNO/Nano or Mega bridge, or use the built-in simulator.",
            )
            return
        if not self.serial_service.connected:
            QMessageBox.warning(
                self,
                "Not connected",
                "Connect the serial adapter first.",
            )
            return
        if self._failsafe_test_active:
            return

        self._failsafe_test_generation = getattr(
            self,
            "_failsafe_test_generation",
            0,
        ) + 1
        generation = self._failsafe_test_generation
        self._failsafe_test_active = True
        self._stream_paused_for_test = True
        self._failsafe_verify_after = time.monotonic() + 0.82
        expected = [1500, 1500, 1000, 1500]
        self.device_page.set_failsafe_test_state(
            "waiting",
            "Desktop channel streaming is paused. Waiting beyond the firmware 700 ms communication timeout…",
            38,
            expected,
        )
        self.diagnostics.info(
            "Failsafe test",
            "LIVE_CHANNELS paused for firmware timeout verification",
        )
        QTimer.singleShot(
            900,
            lambda token=generation: self._request_failsafe_status(token),
        )
        QTimer.singleShot(
            2500,
            lambda token=generation: self._failsafe_test_timeout(token),
        )

    def _request_failsafe_status(self, generation: int) -> None:
        if (
            not self._failsafe_test_active
            or generation != self._failsafe_test_generation
        ):
            return
        self.device_page.set_failsafe_test_state(
            "verifying",
            "Communication timeout elapsed. Reading firmware channels and checking the safe AETR values…",
            76,
            [1500, 1500, 1000, 1500],
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

        explicit_failsafe = payload.get("failsafe_active")
        stream_active = bool(
            payload.get(
                "stream_active",
                payload.get("joystick_connected", False),
            )
        )
        safe_values_match = len(received) == 4 and all(
            abs(received[index] - expected[index]) <= 5
            for index in range(4)
        )
        state_agrees = explicit_failsafe is not False and not stream_active
        passed = safe_values_match and state_agrees

        self._failsafe_test_active = False
        self._stream_paused_for_test = False
        self._failsafe_verify_after = 0.0
        if passed:
            self.device_page.set_failsafe_test_state(
                "pass",
                "PASS — firmware communication failsafe verified. Normal live channel streaming has resumed.",
                100,
                expected,
                received,
            )
            self.diagnostics.info(
                "Failsafe test",
                f"PASS: firmware returned {received}",
            )
        else:
            reason = (
                f"expected {expected}, received "
                f"{received or 'no valid channel array'}, "
                f"stream_active={stream_active}, "
                f"failsafe_active={explicit_failsafe}"
            )
            self.device_page.set_failsafe_test_state(
                "fail",
                f"FAIL — {reason}. Normal live channel streaming has resumed.",
                100,
                expected,
                received,
            )
            self.diagnostics.error("Failsafe test", reason)

        QTimer.singleShot(
            300,
            lambda: self.serial_service.send(MessageType.STATUS, {}),
        )

    def _abort_failsafe_test(self) -> None:
        if not self._failsafe_test_active and not self._stream_paused_for_test:
            return
        self._failsafe_test_generation = getattr(
            self,
            "_failsafe_test_generation",
            0,
        ) + 1
        self._failsafe_test_active = False
        self._stream_paused_for_test = False
        self._failsafe_verify_after = 0.0
        self.device_page.set_failsafe_test_state(
            "aborted",
            "Test aborted. Normal live channel streaming has been restored.",
            0,
            [1500, 1500, 1000, 1500],
        )
        self.diagnostics.info(
            "Failsafe test",
            "Test aborted and LIVE_CHANNELS restored",
        )

    def _failsafe_test_timeout(self, generation: int) -> None:
        if (
            not self._failsafe_test_active
            or generation != self._failsafe_test_generation
        ):
            return
        self._failsafe_test_active = False
        self._stream_paused_for_test = False
        self._failsafe_verify_after = 0.0
        self.device_page.set_failsafe_test_state(
            "fail",
            "FAIL — no firmware status response was received. Normal live channel streaming has resumed.",
            100,
            [1500, 1500, 1000, 1500],
        )
        self.diagnostics.error(
            "Failsafe test",
            "No status response before timeout",
        )

    def _upload_active_profile(self) -> None:
        if not self.serial_service.connected:
            QMessageBox.warning(
                self,
                "Not connected",
                "Connect an adapter or the test simulator first.",
            )
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
            QMessageBox.warning(
                self,
                "Invalid profile",
                "\n".join(errors[:12]),
            )
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
        self.serial_service.send(
            MessageType.PROFILE_ACTIVATE,
            {"profile_id": active.profile_id},
        )
        self.diagnostics.info(
            "Firmware",
            f"ESP32 profile upload requested for {active.name}",
        )

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
        self.joystick_service.set_demo_enabled(
            self.settings.demo_joystick_enabled
        )
        self.serial_service.set_baud(self.settings.serial_baud)
        self._apply_channel_rate()
        self.settings_page.set_settings(self.settings)
        self.diagnostics.info("Settings", "Settings saved")

    def _apply_channel_rate(self) -> None:
        interval = max(
            10,
            round(1000 / max(1, self.settings.channel_rate_hz)),
        )
        if hasattr(self, "channel_timer"):
            self.channel_timer.setInterval(interval)

    def _export_diagnostics(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export diagnostics",
            "simjoy-diagnostics.txt",
            "Text files (*.txt)",
        )
        if not filename:
            return
        context = {
            "active_profile": self._active_profile().name,
            "selected_joystick": (
                self._selected_info().name
                if self._selected_info()
                else "None"
            ),
            "serial_connected": self.serial_service.connected,
            "adapter_kind": self._adapter_kind,
            "demo_enabled": self.settings.demo_joystick_enabled,
            "failsafe_test_active": self._failsafe_test_active,
        }
        try:
            self.diagnostics.export(Path(filename), context)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _transport_error(self, source: str, message: str) -> None:
        self.diagnostics.error(source, message)
        if source == "Joystick":
            self.joystick_page.backend_status.setText(message)
