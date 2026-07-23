from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from ..services.protocol_service import MessageType


class AdapterCommandHandlersMixin:
    """Make board commands visible and reliable during realtime streaming.

    UNO/Nano status replies are intentionally request-driven because verbose
    telemetry can disturb the low-latency control path. A short stream hold
    gives the ATmega328P time to return one status snapshot without reaching
    the 700 ms firmware failsafe timeout.
    """

    def _on_connection_changed(self, connected: bool, label: str) -> None:
        self._status_request_generation = getattr(
            self,
            "_status_request_generation",
            0,
        ) + 1
        self._status_request_pending = False
        self._status_request_retry = 0
        self._stream_paused_for_command = False
        self._identify_pending = False
        self._reboot_pending = False
        self._initial_status_scheduled = False
        super()._on_connection_changed(connected, label)

    def _record_adapter_identity(self, payload: dict[str, Any]) -> None:
        super()._record_adapter_identity(payload)
        if (
            self.serial_service.connected
            and self._adapter_kind in self._KNOWN_ADAPTER_KINDS
            and not getattr(self, "_initial_status_scheduled", False)
        ):
            self._initial_status_scheduled = True
            QTimer.singleShot(300, lambda: self._request_adapter_status(auto=True))

    def _identify_adapter(self) -> None:
        if not self.serial_service.connected:
            QMessageBox.warning(
                self,
                "Not connected",
                "Connect a COM port or the test simulator first.",
            )
            return
        self._identify_pending = True
        self.device_page.adapter_status.setText(
            "Identify request sent — waiting for the firmware handshake…"
        )
        self.device_page.show_message(
            "Identify board",
            {"state": "waiting", "request": "HELLO"},
        )
        self.serial_service.request_hello()
        QTimer.singleShot(1400, self._identify_timeout)

    def _identify_timeout(self) -> None:
        if not getattr(self, "_identify_pending", False):
            return
        self._identify_pending = False
        self.device_page.adapter_status.setText(
            "No identify response. Check that the project firmware is uploaded and the baud rate is 115200."
        )
        self.device_page.show_message(
            "Identify board",
            {"state": "no response", "request": "HELLO"},
        )

    def _request_adapter_status(self, auto: bool = False) -> None:
        if not self.serial_service.connected:
            if not auto:
                QMessageBox.warning(
                    self,
                    "Not connected",
                    "Connect an adapter before requesting firmware status.",
                )
            return
        if self._failsafe_test_active:
            return
        if getattr(self, "_status_request_pending", False):
            return

        self._status_request_generation = getattr(
            self,
            "_status_request_generation",
            0,
        ) + 1
        generation = self._status_request_generation
        self._status_request_pending = True
        self._status_request_retry = 0
        self._send_status_attempt(generation, automatic=auto)

    def _send_status_attempt(self, generation: int, *, automatic: bool) -> None:
        if (
            generation != getattr(self, "_status_request_generation", -1)
            or not getattr(self, "_status_request_pending", False)
            or not self.serial_service.connected
        ):
            return

        self._stream_paused_for_command = True
        self.device_page.health_card.value.setText("READING")
        attempt = int(getattr(self, "_status_request_retry", 0)) + 1
        self.device_page.health_card.detail.setText(
            f"Waiting for firmware snapshot • attempt {attempt}/2"
        )
        self.device_page._received_channels = []
        self.device_page._refresh_channel_rows()
        self.device_page.show_message(
            "Firmware status request",
            {
                "state": "waiting",
                "attempt": attempt,
                "automatic": automatic,
                "stream_hold_ms": 140,
            },
        )

        self.serial_service.send(MessageType.STATUS, {})
        QTimer.singleShot(
            140,
            lambda token=generation: self._resume_after_command(token),
        )
        QTimer.singleShot(
            850,
            lambda token=generation, was_auto=automatic: self._status_request_timeout(
                token,
                was_auto,
            ),
        )

    def _resume_after_command(self, generation: int) -> None:
        if generation == getattr(self, "_status_request_generation", -1):
            self._stream_paused_for_command = False

    def _status_request_timeout(self, generation: int, automatic: bool) -> None:
        if (
            generation != getattr(self, "_status_request_generation", -1)
            or not getattr(self, "_status_request_pending", False)
        ):
            return

        retry = int(getattr(self, "_status_request_retry", 0))
        if retry < 1:
            self._status_request_retry = retry + 1
            self._send_status_attempt(generation, automatic=automatic)
            return

        self._status_request_pending = False
        self._stream_paused_for_command = False
        self.device_page.health_card.value.setText("NO RESPONSE")
        self.device_page.health_card.detail.setText(
            "Firmware did not answer two STATUS requests. Reconnect COM or upload the latest UNO firmware."
        )
        self.device_page.show_message(
            "Firmware status request",
            {
                "state": "no response",
                "attempts": 2,
                "hint": "Reconnect COM and verify firmware/baud",
            },
        )
        self.diagnostics.error(
            "Adapter status",
            "No response after two firmware STATUS requests",
        )

    def _reboot_adapter(self) -> None:
        if not self.serial_service.connected:
            QMessageBox.warning(
                self,
                "Not connected",
                "Connect an adapter before rebooting it.",
            )
            return
        self._reboot_pending = True
        self._stream_paused_for_command = True
        self.device_page.adapter_status.setText(
            "Reboot command sent — waiting for the board to restart and identify itself…"
        )
        self.device_page.show_message(
            "Reboot adapter",
            {"state": "waiting", "request": "REBOOT"},
        )
        self.serial_service.send(MessageType.REBOOT, {})
        QTimer.singleShot(3200, self._reboot_timeout)

    def _reboot_timeout(self) -> None:
        if not getattr(self, "_reboot_pending", False):
            return
        self._reboot_pending = False
        self._stream_paused_for_command = False
        self.device_page.adapter_status.setText(
            "Reboot was not confirmed. Reconnect COM if the board restarted but the app did not receive its handshake."
        )
        self.device_page.show_message(
            "Reboot adapter",
            {"state": "not confirmed"},
        )

    def _on_protocol_message(
        self,
        message_type: int,
        payload: dict[str, Any],
    ) -> None:
        kind = MessageType(message_type)
        super()._on_protocol_message(message_type, payload)

        if kind == MessageType.HELLO_RESPONSE:
            if getattr(self, "_identify_pending", False):
                self._identify_pending = False
                self.device_page.show_message("Identify complete", payload)
            if getattr(self, "_reboot_pending", False):
                self._reboot_pending = False
                self._stream_paused_for_command = False
                self.device_page.show_message("Reboot complete", payload)

        elif kind == MessageType.STATUS:
            self._status_request_pending = False
            self._stream_paused_for_command = False
            self.device_page.health_card.detail.setText(
                "Firmware snapshot received • PPM and channel values are shown below"
            )

        elif kind == MessageType.ACK:
            request = str(payload.get("request", "")).upper()
            if request == "REBOOT" and getattr(self, "_reboot_pending", False):
                self.device_page.adapter_status.setText(
                    "Reboot acknowledged — waiting for startup handshake…"
                )

        elif kind == MessageType.ERROR:
            self._status_request_pending = False
            self._stream_paused_for_command = False
            self._identify_pending = False
            self.device_page.health_card.value.setText("COMMAND ERROR")
            self.device_page.health_card.detail.setText(
                str(payload.get("errors", payload))
            )
