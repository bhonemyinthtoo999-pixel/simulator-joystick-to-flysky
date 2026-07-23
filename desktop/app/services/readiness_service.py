from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .device_role_service import ROLE_LABELS, ResolvedDeviceRoles
from .joystick_service import JoystickInfo
from .profile_service import ControllerProfile


@dataclass(frozen=True)
class ReadinessItem:
    key: str
    title: str
    state: str
    detail: str
    action: str = ""

    @property
    def passed(self) -> bool:
        return self.state == "ready"


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    headline: str
    summary: str
    next_action: str
    next_page: str
    items: tuple[ReadinessItem, ...]


class ReadinessService:
    """Turn technical runtime state into an end-user setup checklist."""

    PHYSICAL_ADAPTERS = {"arduino_uno", "arduino_mega", "arduino", "esp32"}

    @classmethod
    def assess(
        cls,
        *,
        profile: ControllerProfile,
        devices: Sequence[JoystickInfo],
        resolved: ResolvedDeviceRoles,
        calibrations: Mapping[str, object],
        adapter_kind: str,
        serial_connected: bool,
        strict_failsafe_active: bool,
        adapter_capabilities: set[str] | None = None,
    ) -> ReadinessReport:
        capabilities = adapter_capabilities or set()
        physical = [device for device in devices if not device.is_virtual]
        required_roles = {
            mapping.source_role
            for mapping in profile.mappings[:4]
            if mapping.source_type not in {"none", "constant"}
        }

        items: list[ReadinessItem] = []

        if physical:
            names = ", ".join(device.name for device in physical[:3])
            if len(physical) > 3:
                names += f" +{len(physical) - 3} more"
            controls_item = ReadinessItem(
                "controls",
                "Flight controls detected",
                "ready",
                names,
            )
        else:
            controls_item = ReadinessItem(
                "controls",
                "Connect flight controls",
                "action",
                "Connect a USB stick, throttle or pedals. Demo input does not count as flight-ready hardware.",
                "Joystick Monitor",
            )
        items.append(controls_item)

        missing_roles = [role for role in required_roles if resolved.infos.get(role) is None]
        if not missing_roles and required_roles:
            role_text = ", ".join(
                f"{ROLE_LABELS.get(role, role)} → {resolved.infos[role].name}"
                for role in sorted(required_roles)
                if resolved.infos.get(role) is not None
            )
            role_item = ReadinessItem(
                "roles",
                "AETR device roles assigned",
                "ready",
                role_text,
            )
        else:
            missing_text = ", ".join(ROLE_LABELS.get(role, role) for role in missing_roles) or "AETR inputs"
            role_item = ReadinessItem(
                "roles",
                "Assign AETR controls",
                "action",
                f"Missing or unavailable: {missing_text}.",
                "Channel Mapping",
            )
        items.append(role_item)

        calibration_missing: list[str] = []
        for role in sorted(required_roles):
            info = resolved.infos.get(role)
            if info is None:
                continue
            if not calibrations.get(info.guid):
                calibration_missing.append(ROLE_LABELS.get(role, role))
        if not calibration_missing and required_roles:
            calibration_item = ReadinessItem(
                "calibration",
                "Controls calibrated",
                "ready",
                "Every required AETR device has saved per-device calibration.",
            )
        else:
            calibration_item = ReadinessItem(
                "calibration",
                "Calibrate controls",
                "action",
                "Calibration required for " + (", ".join(calibration_missing) or "the connected AETR controls") + ".",
                "Calibration",
            )
        items.append(calibration_item)

        mapping_errors = profile.validate()
        aetr_unmapped = [
            mapping.channel
            for mapping in profile.mappings[:4]
            if mapping.source_type == "none"
        ]
        if not mapping_errors and not aetr_unmapped:
            mapping_item = ReadinessItem(
                "mapping",
                "AETR mapping is valid",
                "ready",
                f"Profile “{profile.name}” has safe endpoints and failsafe values.",
            )
        else:
            detail = (
                f"Unmapped channels: {', '.join(f'CH{channel}' for channel in aetr_unmapped)}."
                if aetr_unmapped
                else mapping_errors[0] if mapping_errors else "Review the active profile."
            )
            mapping_item = ReadinessItem(
                "mapping",
                "Complete channel mapping",
                "action",
                detail,
                "Channel Mapping",
            )
        items.append(mapping_item)

        if serial_connected and adapter_kind in cls.PHYSICAL_ADAPTERS:
            encoding = "low-latency binary streaming" if "fast_channels_v1" in capabilities else "compatible channel streaming"
            adapter_item = ReadinessItem(
                "adapter",
                "Hardware adapter connected",
                "ready",
                encoding,
            )
        elif adapter_kind == "simulator":
            adapter_item = ReadinessItem(
                "adapter",
                "Connect a physical adapter",
                "action",
                "The test simulator has no physical PPM output. Connect an Arduino or ESP32 adapter.",
                "Adapter / Firmware",
            )
        else:
            adapter_item = ReadinessItem(
                "adapter",
                "Connect the trainer adapter",
                "action",
                "Connect and identify an Arduino UNO/Nano, Mega 2560 or ESP32-S3 adapter.",
                "Adapter / Firmware",
            )
        items.append(adapter_item)

        if strict_failsafe_active:
            safety_item = ReadinessItem(
                "safety",
                "Failsafe is active",
                "blocked",
                "One or more required AETR sources are missing or invalid. Output is using safe values.",
                "Channel Mapping",
            )
        elif profile.strict_aetr_failsafe:
            safety_item = ReadinessItem(
                "safety",
                "Strict AETR failsafe armed",
                "ready",
                "Roll, pitch, throttle and yaw will move to their configured safe values if a required source disappears.",
            )
        else:
            safety_item = ReadinessItem(
                "safety",
                "Enable strict AETR failsafe",
                "action",
                "Strict grouped failsafe is recommended before connecting an aircraft.",
                "Channel Mapping",
            )
        items.append(safety_item)

        ready = all(item.passed for item in items)
        if ready:
            return ReadinessReport(
                ready=True,
                headline="READY TO USE",
                summary="Flight controls, mapping, calibration, adapter and failsafe are ready.",
                next_action="Open hardware test",
                next_page="Adapter / Firmware",
                items=tuple(items),
            )

        next_item = next(item for item in items if not item.passed)
        return ReadinessReport(
            ready=False,
            headline="SETUP REQUIRED",
            summary=next_item.detail,
            next_action=next_item.title,
            next_page=next_item.action or "Setup",
            items=tuple(items),
        )
