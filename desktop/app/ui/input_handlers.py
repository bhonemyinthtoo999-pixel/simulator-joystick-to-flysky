from __future__ import annotations

import time
from typing import Any

from PySide6.QtWidgets import QMessageBox

from ..services.calibration_service import CalibrationSession
from ..services.channel_mapping_service import default_mappings
from ..services.joystick_service import JoystickInfo


class InputHandlersMixin:
    def _on_devices_changed(self, devices: list[JoystickInfo]) -> None:
        self._device_infos = {device.instance_id: device for device in devices}
        selected = self.joystick_page.set_devices(devices, self._selected_instance_id)
        self._select_device(selected)
        physical = [device for device in devices if not device.is_virtual]
        if physical:
            self.dashboard_page.joystick_value.setText(
                physical[0].name
                if len(physical) == 1
                else f"{len(physical)} physical devices"
            )
        elif devices:
            self.dashboard_page.joystick_value.setText("Demo Controller")
        else:
            self.dashboard_page.joystick_value.setText("Not detected")
        self.diagnostics.info(
            "Joystick",
            f"Device list changed: {len(physical)} physical, {len(devices) - len(physical)} demo",
        )

    def _select_device(self, instance_id: int | None) -> None:
        self._selected_instance_id = instance_id
        self._calibration_session = None
        self.channel_mapper.reset()
        self.mapping_preview_mapper.reset()
        info = self._selected_info()
        saved = self.calibrations.get(info.guid, []) if info else []
        self.joystick_page.set_selected_device(info)
        self.calibration_page.set_device(info, saved)
        self.calibration_page.set_buttons(info is not None, False, bool(saved))
        self._refresh_mapping_page()
        if info:
            self.diagnostics.info("Joystick", f"Selected {info.name} ({info.guid})")

    def _on_state_changed(self, snapshots: dict[int, dict[str, Any]]) -> None:
        self._latest_states = snapshots

        # The flight-output path runs immediately from the freshest multi-device
        # snapshot. It no longer waits for the dashboard/UI refresh timer.
        self._update_realtime_output()

        if self._selected_instance_id is None:
            return
        state = snapshots.get(self._selected_instance_id)
        if state is None:
            return

        axes = [float(value) for value in state.get("axes", [])]
        if self._calibration_session is not None:
            # Capture every sample even though visual calibration updates are
            # throttled below.
            self._calibration_session.observe(axes)

        now = time.monotonic()
        if now - getattr(self, "_last_input_ui_at", 0.0) < (1.0 / 30.0):
            return
        self._last_input_ui_at = now

        self.joystick_page.update_state(state)
        if self._calibration_session is not None:
            self.calibration_page.update_values(
                axes,
                self._calibration_session.minimum,
                self._calibration_session.center,
                self._calibration_session.maximum,
            )
        else:
            self.calibration_page.update_values(axes)

    def _map_active_channels(self) -> list[int]:
        active = self._active_profile()
        resolved = self._resolved_inputs(active)
        channels = self.channel_mapper.map_channels_multi(
            resolved.states,
            active.mappings,
            self.calibrations,
            resolved.guids,
            active.strict_aetr_failsafe,
        )
        self._current_channels = channels
        return channels

    def _update_realtime_output(self) -> None:
        channels = self._map_active_channels()
        self._maybe_stream_channels(channels)

    def _maybe_stream_channels(
        self,
        channels: list[int],
        *,
        keepalive_only: bool = False,
    ) -> None:
        if not self.serial_service.connected or self._stream_paused_for_test:
            return

        now = time.monotonic()
        last_sent_at = getattr(self, "_last_realtime_send_at", 0.0)
        elapsed = now - last_sent_at
        rate_hz = (
            self.settings.realtime_rate_hz
            if self.settings.low_latency_mode
            else max(10, self.settings.channel_rate_hz)
        )
        minimum_interval = 1.0 / max(1, rate_hz)
        changed = channels != getattr(self, "_last_sent_channels", [])
        keepalive_due = elapsed >= 0.10

        should_send = keepalive_due if keepalive_only else (
            (changed and elapsed >= minimum_interval) or keepalive_due
        )
        if not should_send:
            return

        fast_supported = "fast_channels_v1" in self._adapter_capabilities
        self.serial_service.send_live_channels(
            channels,
            fast=fast_supported,
        )
        self._last_sent_channels = list(channels)
        self._last_realtime_send_at = now

    def _channel_tick(self) -> None:
        # UI work is intentionally decoupled from realtime streaming.
        channels = self._current_channels
        if not channels:
            channels = self._map_active_channels()

        self.dashboard_page.update_channels(channels)
        if self.channel_mapper.last_strict_failsafe:
            missing = ", ".join(self.channel_mapper.last_missing_aetr_roles)
            self.dashboard_page.safety_value.setText(
                f"STRICT AETR FAILSAFE ACTIVE — missing or invalid source: {missing}. "
                "CH1–CH4 are using safe values."
            )
        else:
            protocol = (
                "compact binary"
                if "fast_channels_v1" in self._adapter_capabilities
                else "compatible JSON"
            )
            self.dashboard_page.safety_value.setText(
                f"AETR sources healthy. Realtime output uses {protocol} streaming."
            )

        # Mapping preview is one of the heaviest UI operations, so only run it
        # while the user is actually viewing the mapping page.
        if self.pages.currentWidget() is self.mapping_page:
            active = self._active_profile()
            draft_mappings = self.mapping_page.mappings()
            draft_bindings = self.mapping_page.device_bindings()
            draft_resolved = self.device_role_resolver.resolve(
                draft_bindings,
                list(self._device_infos.values()),
                self._latest_states,
                self._selected_instance_id,
            )
            self.mapping_page.update_input_states(draft_resolved.states)
            preview_channels = self.mapping_preview_mapper.map_channels_multi(
                draft_resolved.states,
                draft_mappings if draft_mappings else active.mappings,
                self.calibrations,
                draft_resolved.guids,
                self.mapping_page.strict_aetr_failsafe(),
            )
            self.mapping_page.update_preview(preview_channels)

        streaming = self.serial_service.connected and not self._stream_paused_for_test
        if self.pages.currentWidget() is self.device_page:
            self.device_page.update_desktop_channels(channels, streaming)

        # Keep the Arduino watchdog fed even when all controls remain stationary.
        self._maybe_stream_channels(channels, keepalive_only=True)

    def _start_calibration(self) -> None:
        info = self._selected_info()
        if info is None:
            return
        self._calibration_session = CalibrationSession(info.axes)
        self.calibration_page.status.setText(
            "Recording limits: move every axis slowly through its complete physical range. "
            "The captured range should approach 2.000 for a full -1 to +1 axis."
        )
        self.calibration_page.set_buttons(True, True, info.guid in self.calibrations)
        self.calibration_page._set_step(2)
        self.diagnostics.info("Calibration", f"Started for {info.name}")

    def _capture_center(self) -> None:
        if self._calibration_session is None or self._selected_instance_id is None:
            return
        state = self._latest_states.get(self._selected_instance_id)
        if state is None:
            return
        self._calibration_session.capture_center(state.get("axes", []))
        self.calibration_page.status.setText(
            "Neutral position captured. Check that centered controls are released and throttle remains at its normal idle position, then save."
        )
        self.calibration_page._set_step(3)
        self.diagnostics.info("Calibration", "Center captured")

    def _save_calibration(self) -> None:
        info = self._selected_info()
        session = self._calibration_session
        if info is None or session is None:
            return
        if session.samples < 5:
            QMessageBox.warning(
                self,
                "Not enough samples",
                "Move the joystick through its complete range before saving calibration.",
            )
            return
        self.calibrations[info.guid] = session.result()
        try:
            self.calibration_store.save(self.calibrations)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self._calibration_session = None
        self.calibration_page.set_device(info, self.calibrations[info.guid])
        self.calibration_page.status.setText("Calibration saved for this joystick GUID.")
        self.calibration_page._set_step(4)
        self.diagnostics.info(
            "Calibration",
            f"Saved {len(self.calibrations[info.guid])} axes",
        )

    def _reset_calibration(self) -> None:
        info = self._selected_info()
        if info is None:
            return
        self.calibrations.pop(info.guid, None)
        try:
            self.calibration_store.save(self.calibrations)
        except OSError as exc:
            QMessageBox.critical(self, "Reset failed", str(exc))
            return
        self._calibration_session = None
        self.calibration_page.set_device(info, [])
        self.calibration_page.status.setText(
            "Saved calibration removed. Default -1 to +1 range is active."
        )
        self.calibration_page._set_step(1)
        self.diagnostics.info("Calibration", f"Reset calibration for {info.name}")

    def _save_mappings(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            QMessageBox.warning(
                self,
                "Invalid mapping",
                "Mapping editor returned an invalid payload.",
            )
            return
        mappings = payload.get("mappings", [])
        bindings = payload.get("device_bindings", {})
        active = self._active_profile()
        active.mappings = mappings
        active.channel_count = len(mappings)
        active.device_bindings = dict(bindings)
        active.strict_aetr_failsafe = bool(
            payload.get("strict_aetr_failsafe", True)
        )
        active.touch()
        errors = active.validate()
        if errors:
            QMessageBox.warning(self, "Invalid mapping", "\n".join(errors[:12]))
            return
        self._save_profiles_to_disk()
        self.channel_mapper.reset()
        self.mapping_preview_mapper.reset()
        self._last_sent_channels = []
        self._refresh_profiles()
        self.diagnostics.info(
            "Mapping",
            f"Saved {len(mappings)} channels with multi-device role bindings to {active.name}",
        )

    def _reset_mappings(self) -> None:
        active = self._active_profile()
        active.mappings = default_mappings(active.channel_count)
        active.touch()
        self._save_profiles_to_disk()
        self.channel_mapper.reset()
        self.mapping_preview_mapper.reset()
        self._last_sent_channels = []
        self._refresh_profiles()
        self.diagnostics.info("Mapping", f"Reset {active.name} to AETR defaults")
