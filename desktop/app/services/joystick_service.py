from __future__ import annotations

from dataclasses import dataclass
import math
import os
import time
from typing import Any

# The desktop UI is owned by Qt, not SDL. Without this hint some Windows
# DirectInput devices (including older Thrustmaster sticks) are enumerated by
# SDL but stop reporting axis changes because SDL never owns the focused window.
os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")

import pygame
from PySide6.QtCore import QObject, QTimer, Signal

DEMO_INSTANCE_ID = -1
DEMO_GUID = "SIMJOY-DEMO-CONTROLLER-V1"


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
    is_virtual: bool = False
    backend: str = "SDL"


class JoystickService(QObject):
    """Detect and poll SDL-supported USB/Bluetooth joystick devices.

    A hidden SDL window is created only to keep SDL's Windows event pump alive.
    The visible application window remains the PySide6/Qt window.
    """

    devices_changed = Signal(list)
    state_changed = Signal(dict)
    backend_error = Signal(str)

    def __init__(
        self,
        poll_interval_ms: int = 20,
        scan_interval_ms: int = 1000,
        demo_enabled: bool = True,
    ) -> None:
        super().__init__()
        self._devices: dict[int, pygame.joystick.JoystickType] = {}
        self._last_signature: tuple[tuple[Any, ...], ...] = ()
        self._started = False
        self._pygame_available = False
        self._hidden_display_created = False
        self._demo_enabled = bool(demo_enabled)
        self._demo_started_at = time.monotonic()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(poll_interval_ms)
        self._poll_timer.timeout.connect(self._poll)

        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(scan_interval_ms)
        self._scan_timer.timeout.connect(self._scan_devices)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        try:
            pygame.display.init()
            if pygame.display.get_surface() is None:
                hidden_flag = getattr(pygame, "HIDDEN", 0)
                pygame.display.set_mode((1, 1), hidden_flag)
                self._hidden_display_created = True
            pygame.joystick.init()
            pygame.event.clear()
            self._pygame_available = True
        except (pygame.error, OSError) as exc:
            self._pygame_available = False
            self.backend_error.emit(
                f"Physical joystick backend failed; demo mode remains available: {exc}"
            )
        self._scan_devices(force_emit=True)
        self._poll_timer.start()
        self._scan_timer.start()

    def stop(self) -> None:
        self._poll_timer.stop()
        self._scan_timer.stop()
        for joystick in self._devices.values():
            try:
                joystick.quit()
            except pygame.error:
                pass
        self._devices.clear()
        if self._pygame_available:
            pygame.joystick.quit()
            if self._hidden_display_created:
                pygame.display.quit()
            pygame.quit()
        self._pygame_available = False
        self._hidden_display_created = False
        self._started = False

    def set_demo_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._demo_enabled:
            return
        self._demo_enabled = enabled
        self._demo_started_at = time.monotonic()
        self._scan_devices(force_emit=True)

    def devices(self) -> list[JoystickInfo]:
        devices = [self._describe(device) for device in self._devices.values()]
        if self._demo_enabled:
            devices.append(self._demo_info())
        return devices

    def _drain_events(self) -> bool:
        """Drain SDL's bounded event queue and report hot-plug changes.

        Calling only event.pump() lets continuous JOYAXISMOTION events fill the
        SDL queue. Once full, some DirectInput devices appear frozen even though
        they remain connected. Draining the queue every poll prevents that.
        """

        if not self._pygame_available:
            return False
        needs_rescan = False
        added = getattr(pygame, "JOYDEVICEADDED", None)
        removed = getattr(pygame, "JOYDEVICEREMOVED", None)
        for event in pygame.event.get():
            if event.type == added or event.type == removed:
                needs_rescan = True
        return needs_rescan

    def _scan_devices(self, force_emit: bool = False) -> None:
        if not self._started:
            return
        try:
            found: dict[int, pygame.joystick.JoystickType] = {}
            if self._pygame_available:
                pygame.event.pump()
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
            self._emit_devices_if_changed(force_emit)
        except pygame.error as exc:
            self.backend_error.emit(f"Joystick scan failed: {exc}")

    def _emit_devices_if_changed(self, force_emit: bool = False) -> None:
        infos = self.devices()
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
                    info.is_virtual,
                    info.backend,
                )
                for info in infos
            )
        )
        if force_emit or signature != self._last_signature:
            self._last_signature = signature
            self.devices_changed.emit(infos)

    def _poll(self) -> None:
        if not self._started:
            return
        try:
            if self._drain_events():
                self._scan_devices(force_emit=True)

            snapshots: dict[int, dict[str, Any]] = {}
            if self._pygame_available:
                # Pump once more immediately before synchronous state reads.
                pygame.event.pump()
                for instance_id, joystick in list(self._devices.items()):
                    if not joystick.get_init():
                        continue
                    snapshots[instance_id] = {
                        "instance_id": instance_id,
                        "name": joystick.get_name() or "Unknown joystick",
                        "guid": joystick.get_guid() or "unknown",
                        "axes": [
                            float(joystick.get_axis(i))
                            for i in range(joystick.get_numaxes())
                        ],
                        "buttons": [
                            bool(joystick.get_button(i))
                            for i in range(joystick.get_numbuttons())
                        ],
                        "hats": [
                            joystick.get_hat(i)
                            for i in range(joystick.get_numhats())
                        ],
                        "balls": [
                            joystick.get_ball(i)
                            for i in range(joystick.get_numballs())
                        ],
                        "is_virtual": False,
                        "backend": "SDL",
                        "timestamp": time.monotonic(),
                    }
            if self._demo_enabled:
                snapshots[DEMO_INSTANCE_ID] = self._demo_state()
            self.state_changed.emit(snapshots)
        except pygame.error as exc:
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
            is_virtual=False,
            backend="SDL",
        )

    @staticmethod
    def _demo_info() -> JoystickInfo:
        return JoystickInfo(
            instance_id=DEMO_INSTANCE_ID,
            name="Demo Flight Joystick (No hardware required)",
            guid=DEMO_GUID,
            axes=6,
            buttons=12,
            hats=1,
            balls=0,
            power_level="wired",
            is_virtual=True,
            backend="Demo",
        )

    def _demo_state(self) -> dict[str, Any]:
        t = time.monotonic() - self._demo_started_at
        throttle = ((t % 8.0) / 4.0) - 1.0
        if throttle > 1.0:
            throttle = 3.0 - throttle
        buttons = [False] * 12
        buttons[int(t // 1.5) % len(buttons)] = True
        direction = int(t // 1.0) % 5
        hats = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)]
        return {
            "instance_id": DEMO_INSTANCE_ID,
            "name": "Demo Flight Joystick (No hardware required)",
            "guid": DEMO_GUID,
            "axes": [
                math.sin(t * 0.8) * 0.85,
                math.cos(t * 0.65) * 0.75,
                throttle,
                math.sin(t * 0.42),
                math.sin(t * 1.3) * 0.5,
                math.cos(t * 1.1) * 0.5,
            ],
            "buttons": buttons,
            "hats": [hats[direction]],
            "balls": [],
            "is_virtual": True,
            "backend": "Demo",
            "timestamp": time.monotonic(),
        }
