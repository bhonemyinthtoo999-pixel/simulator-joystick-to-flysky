from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .joystick_service import JoystickInfo

AUTO_DEVICE_GUID = "*"
ROLE_ORDER = ("primary_stick", "throttle", "pedals", "auxiliary")
ROLE_LABELS = {
    "primary_stick": "Primary Stick",
    "throttle": "Throttle Unit",
    "pedals": "Rudder Pedals",
    "auxiliary": "Auxiliary Controller",
}


def default_device_bindings() -> dict[str, str]:
    return {role: AUTO_DEVICE_GUID for role in ROLE_ORDER}


@dataclass(frozen=True)
class ResolvedDeviceRoles:
    infos: dict[str, JoystickInfo | None]
    states: dict[str, dict[str, Any] | None]
    guids: dict[str, str]

    def missing(self, roles: set[str] | None = None) -> list[str]:
        wanted = roles or set(ROLE_ORDER)
        return [role for role in ROLE_ORDER if role in wanted and self.states.get(role) is None]


class DeviceRoleResolver:
    """Bind stable profile roles to currently connected joystick devices.

    Exact GUID bindings always win. An automatic binding uses device names and
    unused-device preference so a traditional stick plus a separate throttle is
    combined without relying on USB enumeration order.
    """

    THROTTLE_WORDS = ("throttle", "twcs", "quadrant", "lever")
    PEDAL_WORDS = ("pedal", "rudder")
    STICK_WORDS = ("stick", "joystick", "hotas", "flight")

    @classmethod
    def resolve(
        cls,
        bindings: dict[str, str] | None,
        devices: list[JoystickInfo],
        snapshots: dict[int, dict[str, Any]] | None = None,
        selected_instance_id: int | None = None,
    ) -> ResolvedDeviceRoles:
        normalized = default_device_bindings()
        normalized.update({key: value for key, value in (bindings or {}).items() if key in ROLE_ORDER})
        snapshots = snapshots or {}
        usable = [device for device in devices if device.instance_id in snapshots or not snapshots]
        physical = [device for device in usable if not device.is_virtual]
        candidates = physical or usable

        selected = next(
            (device for device in candidates if device.instance_id == selected_instance_id),
            None,
        )
        infos: dict[str, JoystickInfo | None] = {}
        claimed: set[int] = set()

        # Resolve explicit GUID bindings before automatic roles.
        for role in ROLE_ORDER:
            guid = normalized.get(role, AUTO_DEVICE_GUID)
            if guid == AUTO_DEVICE_GUID:
                continue
            info = next((device for device in usable if device.guid == guid), None)
            infos[role] = info
            if info is not None:
                claimed.add(info.instance_id)

        for role in ROLE_ORDER:
            if role in infos:
                continue
            info = cls._auto_pick(role, candidates, claimed, selected)
            infos[role] = info
            if info is not None and role != "throttle":
                claimed.add(info.instance_id)

        role_states: dict[str, dict[str, Any] | None] = {}
        guids: dict[str, str] = {}
        for role in ROLE_ORDER:
            info = infos.get(role)
            role_states[role] = snapshots.get(info.instance_id) if info is not None else None
            guids[role] = info.guid if info is not None else ""
        return ResolvedDeviceRoles(infos=infos, states=role_states, guids=guids)

    @classmethod
    def _auto_pick(
        cls,
        role: str,
        devices: list[JoystickInfo],
        claimed: set[int],
        selected: JoystickInfo | None,
    ) -> JoystickInfo | None:
        if not devices:
            return None

        if role == "primary_stick":
            if selected is not None and selected.axes >= 2:
                return selected
            named = cls._find_named(devices, cls.STICK_WORDS, claimed)
            return named or next((device for device in devices if device.axes >= 2), devices[0])

        if role == "throttle":
            named = cls._find_named(devices, cls.THROTTLE_WORDS, claimed)
            if named is not None:
                return named
            unused = next((device for device in devices if device.instance_id not in claimed and device.axes), None)
            # A combined HOTAS or single flight stick may provide throttle on the
            # same USB device, so falling back to the primary stick is intentional.
            return unused or selected or next((device for device in devices if device.axes), None)

        if role == "pedals":
            return cls._find_named(devices, cls.PEDAL_WORDS, claimed)

        return next((device for device in devices if device.instance_id not in claimed), None)

    @staticmethod
    def _find_named(
        devices: list[JoystickInfo],
        words: tuple[str, ...],
        claimed: set[int],
    ) -> JoystickInfo | None:
        for device in devices:
            lowered = device.name.casefold()
            if device.instance_id not in claimed and any(word in lowered for word in words):
                return device
        return None
