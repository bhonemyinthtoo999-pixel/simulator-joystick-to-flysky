from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from ..services.calibration_service import CalibrationSession
from ..services.channel_mapping_service import default_mappings
from ..services.joystick_service import JoystickInfo
from ..services.protocol_service import MessageType


class InputHandlersMixin:
    def _on_devices_changed(self, devices: list[JoystickInfo]) -> None:
        self._device_infos = {device.instance_id: device for device in devices}
        selected = self.joystick_page.set_devices(devices, self._selected_instance_id)
        self._select_device(selected)
        physical = [device for device in devices if not device.is_virtual]
        if physical:
            self.dashboard_page.joystick_value.setText(physical[0].name if len(physical) == 1 else f"{len(physical)} physical devices")
        elif devices:
            self.dashboard_page.joystick_value.setText("Demo Controller")
        else:
            self.dashboard_page.joystick_value.setText("Not detected")
        self.diagnostics.info("Joystick", f"Device list changed: {len(physical)} physical, {len(devices) - len(physical)} demo")

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
        if self._selected_instance_id is None:
            return
        state = snapshots.get(self._selected_instance_id)
        if state is None:
            return
        self.joystick_page.update_state(state)
        self.mapping_page.update_input_state(state)
        axes = [float(value) for value in state.get("axes", [])]
        if self._calibration_session is not None:
            self._calibration_session.observe(axes)
            self.calibration_page.update_values(
                axes,
                self._calibration_session.minimum,
                self._calibration_session.center,
                self._calibration_session.maximum,
            )
        else:
            self.calibration_page.update_values(axes)

    def _channel_tick(self) -> None:
        active = self._active_profile()
        info = self._selected_info()
        state = self._latest_states.get(self._selected_instance_id) if self._selected_instance_id is not None else None
        calibrations = self.calibrations.get(info.guid, []) if info else []

        # Saved mappings drive the dashboard and any connected hardware.
        channels = self.channel_mapper.map_channels(state, active.mappings, calibrations)
        self._current_channels = channels
        self.dashboard_page.update_channels(channels)

        # Draft editor values are calculated separately for immediate feedback.
        # They are never streamed to Arduino/ESP32 until the user saves them.
        draft_mappings = self.mapping_page.mappings()
        preview_channels = self.mapping_preview_mapper.map_channels(
            state,
            draft_mappings if draft_mappings else active.mappings,
            calibrations,
        )
        self.mapping_page.update_preview(preview_channels)

        if self.serial_service.connected:
            self.serial_service.send(
                MessageType.LIVE_CHANNELS,
                {
                    "profile_id": active.profile_id,
                    "channels": channels,
                    "source": "desktop",
                },
            )

    def _start_calibration(self) -> None:
        info = self._selected_info()
        if info is None:
            return
        self._calibration_session = CalibrationSession(info.axes)
        self.calibration_page.status.setText("Recording limits: move every control through its complete range.")
        self.calibration_page.set_buttons(True, True, info.guid in self.calibrations)
        self.diagnostics.info("Calibration", f"Started for {info.name}")

    def _capture_center(self) -> None:
        if self._calibration_session is None or self._selected_instance_id is None:
            return
        state = self._latest_states.get(self._selected_instance_id)
        if state is None:
            return
        self._calibration_session.capture_center(state.get("axes", []))
        self.calibration_page.status.setText("Center captured. Save when the min/max values look correct.")
        self.diagnostics.info("Calibration", "Center captured")

    def _save_calibration(self) -> None:
        info = self._selected_info()
        session = self._calibration_session
        if info is None or session is None:
            return
        if session.samples < 5:
            QMessageBox.warning(self, "Not enough samples", "Move the joystick before saving calibration.")
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
        self.diagnostics.info("Calibration", f"Saved {len(self.calibrations[info.guid])} axes")

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
        self.calibration_page.status.setText("Saved calibration removed. Default range is active.")
        self.diagnostics.info("Calibration", f"Reset calibration for {info.name}")

    def _save_mappings(self, mappings: list[Any]) -> None:
        active = self._active_profile()
        active.mappings = mappings
        active.channel_count = len(mappings)
        active.touch()
        errors = active.validate()
        if errors:
            QMessageBox.warning(self, "Invalid mapping", "\n".join(errors[:12]))
            return
        self._save_profiles_to_disk()
        self.channel_mapper.reset()
        self.mapping_preview_mapper.reset()
        self._refresh_profiles()
        self.diagnostics.info("Mapping", f"Saved {len(mappings)} channels to {active.name}")

    def _reset_mappings(self) -> None:
        active = self._active_profile()
        active.mappings = default_mappings(active.channel_count)
        active.touch()
        self._save_profiles_to_disk()
        self.channel_mapper.reset()
        self.mapping_preview_mapper.reset()
        self._refresh_profiles()
        self.diagnostics.info("Mapping", f"Reset {active.name} to defaults")
