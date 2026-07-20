from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame
from PySide6.QtCore import QObject, QTimer, Signal


@dataclass(frozen=True)
class JoystickInfo:
    """Stable metadata describing one connected joystick or game controller."""

    instance_id: int
    name: str
    guid: str
    axes: int
    buttons: int
    hats: int
    balls: int
    power_level: str


class JoystickService(QObject):
    """Detect and poll SDL-supported USB/Bluetooth joystick devices.

    SDL covers modern game controllers and many older DirectInput-compatible
    joysticks. Devices are re-enumerated periodically so connect/disconnect
    events also work for hardware that does not emit reliable hot-plug events.
    """

    devices_changed = Signal(list)
    state_changed = Signal(dict)
    backend_error = Signal(str)

    def __init__(self, poll_interval_ms: int = 20, scan_interval_ms: int = 1000) -> None:
        super().__init__()
        self._devices: dict[int, pygame.joystick.JoystickType] = {}
        self._last_signature: tuple[tuple[Any, ...], ...] = ()
        self._started = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(poll_interval_ms)
        self._poll_timer.timeout.connect(self._poll)

        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(scan_interval_ms)
        self._scan_timer.timeout.connect(self._scan_devices)

    def start(self) -> None:
        if self._started:
            return
        try:
            pygame.init()
            pygame.joystick.init()
            self._started = True
            self._scan_devices(force_emit=True)
            self._poll_timer.start()
            self._scan_timer.start()
        except pygame.error as exc:
            self.backend_error.emit(f"Joystick backend failed to start: {exc}")

    def stop(self) -> None:
        self._poll_timer.stop()
        self._scan_timer.stop()
        for joystick in self._devices.values():
            try:
                joystick.quit()
            except pygame.error:
                pass
        self._devices.clear()
        if self._started:
            pygame.joystick.quit()
            pygame.quit()
        self._started = False

    def devices(self) -> list[JoystickInfo]:
        return [self._describe(device) for device in self._devices.values()]

    def _scan_devices(self, force_emit: bool = False) -> None:
        if not self._started:
            return
        try:
            pygame.event.pump()
            found: dict[int, pygame.joystick.JoystickType] = {}
            for device_index in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(device_index)
                if not joystick.get_init():
                    joystick.init()
                found[joystick.get_instance_id()] = joystick

            removed_ids = set(self._devices) - set(found)
            for instance_id in removed_ids:
                try:
                    self._devices[instance_id].quit()
                except pygame.error:
                    pass

            self._devices = found
            signature = tuple(
                sorted(
                    (
                        info.instance_id,
                        info.name,
                        info.guid,
                        info.axes,
                        info.buttons,
                        info.hats,
                        info.balls,
                    )
                    for info in self.devices()
                )
            )
            if force_emit or signature != self._last_signature:
                self._last_signature = signature
                self.devices_changed.emit(self.devices())
        except pygame.error as exc:
            self.backend_error.emit(f"Joystick scan failed: {exc}")

    def _poll(self) -> None:
        if not self._started:
            return
        try:
            pygame.event.pump()
            snapshots: dict[int, dict[str, Any]] = {}
            for instance_id, joystick in list(self._devices.items()):
                if not joystick.get_init():
                    continue
                snapshots[instance_id] = {
                    "instance_id": instance_id,
                    "name": joystick.get_name() or "Unknown joystick",
                    "axes": [joystick.get_axis(i) for i in range(joystick.get_numaxes())],
                    "buttons": [bool(joystick.get_button(i)) for i in range(joystick.get_numbuttons())],
                    "hats": [joystick.get_hat(i) for i in range(joystick.get_numhats())],
                    "balls": [joystick.get_ball(i) for i in range(joystick.get_numballs())],
                }
            self.state_changed.emit(snapshots)
        except pygame.error as exc:
            # A device may disappear between scans. Re-enumerate immediately.
            self.backend_error.emit(f"Joystick read failed: {exc}")
            self._scan_devices(force_emit=True)

    @staticmethod
    def _describe(joystick: pygame.joystick.JoystickType) -> JoystickInfo:
        try:
            power_level = str(joystick.get_power_level())
        except (AttributeError, pygame.error):
            power_level = "unknown"
        return JoystickInfo(
            instance_id=joystick.get_instance_id(),
            name=joystick.get_name() or "Unknown joystick",
            guid=joystick.get_guid() or "unknown",
            axes=joystick.get_numaxes(),
            buttons=joystick.get_numbuttons(),
            hats=joystick.get_numhats(),
            balls=joystick.get_numballs(),
            power_level=power_level,
        )
