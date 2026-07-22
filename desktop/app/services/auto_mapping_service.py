from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .device_role_service import ROLE_ORDER


@dataclass(frozen=True)
class AutoMapStep:
    channel_index: int
    name: str
    prompt: str
    mode: str
    failsafe: int
    preferred_role: str


@dataclass(frozen=True)
class AutoMapCapture:
    step: AutoMapStep
    source_role: str
    axis_index: int
    reversed: bool
    change: float


class AutoMappingSession:
    """Identify AETR axes across one or more role-bound USB devices."""

    DEFAULT_STEPS = (
        AutoMapStep(0, "Roll", "Move the roll control fully RIGHT", "centered", 1500, "primary_stick"),
        AutoMapStep(1, "Pitch", "Pull the pitch control fully BACK", "centered", 1500, "primary_stick"),
        AutoMapStep(2, "Throttle", "Move the throttle to FULL / HIGH", "unipolar", 1000, "throttle"),
        AutoMapStep(3, "Yaw", "Move the rudder, pedals or twist control fully RIGHT", "centered", 1500, "primary_stick"),
    )

    def __init__(self, threshold: float = 0.25, arm_delay_s: float = 0.35) -> None:
        self.threshold = max(0.05, float(threshold))
        self.arm_delay_s = max(0.0, float(arm_delay_s))
        self.steps = self.DEFAULT_STEPS
        self.step_index = 0
        # Keys use the physical device identity when available, preventing one
        # axis from being assigned twice when two roles resolve to one HOTAS.
        self.used_axes: set[tuple[str, int]] = set()
        self.baseline: dict[str, list[float]] = {}
        self.armed_at = 0.0
        self.active = False

    @property
    def current_step(self) -> AutoMapStep | None:
        if not self.active or self.step_index >= len(self.steps):
            return None
        return self.steps[self.step_index]

    @property
    def progress_text(self) -> str:
        if not self.active:
            return "Auto mapping is not active."
        return f"Step {self.step_index + 1} of {len(self.steps)}"

    @property
    def complete(self) -> bool:
        return self.step_index >= len(self.steps)

    def start(self, states: dict[str, Any], now: float | None = None) -> None:
        role_states = self._coerce_role_states(states)
        axes = self._all_axes(role_states)
        unique_axes = {
            self._axis_key(role, role_states.get(role), index)
            for role, values in axes.items()
            for index in range(len(values))
        }
        if len(unique_axes) < len(self.steps):
            raise ValueError("At least four joystick axes across the bound devices are required for automatic AETR mapping.")
        self.step_index = 0
        self.used_axes.clear()
        self.active = True
        self._arm(axes, now)

    def cancel(self) -> None:
        self.active = False
        self.baseline = {}
        self.used_axes.clear()

    def observe(self, states: dict[str, Any], now: float | None = None) -> AutoMapCapture | None:
        if not self.active or self.complete:
            return None
        role_states = self._coerce_role_states(states)
        axes_by_role = self._all_axes(role_states)
        timestamp = time.monotonic() if now is None else float(now)
        if timestamp < self.armed_at:
            self.baseline = {role: list(values) for role, values in axes_by_role.items()}
            return None

        step = self.steps[self.step_index]
        role_order = [step.preferred_role] + [role for role in ROLE_ORDER if role != step.preferred_role]
        strongest_role = ""
        strongest_axis = -1
        strongest_delta = 0.0
        strongest_preferred = False

        for role in role_order:
            before = self.baseline.get(role, [])
            current = axes_by_role.get(role, [])
            state = role_states.get(role)
            for index in range(min(len(before), len(current))):
                key = self._axis_key(role, state, index)
                if key in self.used_axes:
                    continue
                delta = current[index] - before[index]
                preferred = role == step.preferred_role
                # Prefer the expected role when its motion is deliberate. This
                # makes a separate throttle win the Throttle step even when a
                # combined HOTAS exposes the same physical device under roles.
                if abs(delta) >= self.threshold and preferred and not strongest_preferred:
                    strongest_role = role
                    strongest_axis = index
                    strongest_delta = delta
                    strongest_preferred = True
                elif preferred == strongest_preferred and abs(delta) > abs(strongest_delta):
                    strongest_role = role
                    strongest_axis = index
                    strongest_delta = delta

        if strongest_axis < 0 or abs(strongest_delta) < self.threshold:
            return None

        capture = AutoMapCapture(
            step=step,
            source_role=strongest_role,
            axis_index=strongest_axis,
            reversed=strongest_delta < 0.0,
            change=strongest_delta,
        )
        self.used_axes.add(self._axis_key(strongest_role, role_states.get(strongest_role), strongest_axis))
        self.step_index += 1
        if self.complete:
            self.active = False
            self.baseline = {}
        else:
            self._arm(axes_by_role, timestamp)
        return capture

    def _arm(self, axes: dict[str, list[float]], now: float | None) -> None:
        timestamp = time.monotonic() if now is None else float(now)
        self.baseline = {role: list(values) for role, values in axes.items()}
        self.armed_at = timestamp + self.arm_delay_s

    @staticmethod
    def _coerce_role_states(states: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
        if "axes" in states or "buttons" in states or "hats" in states:
            return {"primary_stick": states}
        return {
            role: value if isinstance(value, dict) else None
            for role, value in states.items()
            if role in ROLE_ORDER
        }

    @staticmethod
    def _all_axes(role_states: dict[str, dict[str, Any] | None]) -> dict[str, list[float]]:
        result: dict[str, list[float]] = {}
        for role in ROLE_ORDER:
            state = role_states.get(role)
            if not state:
                continue
            try:
                result[role] = [float(value) for value in state.get("axes", [])]
            except (TypeError, ValueError):
                result[role] = []
        return result

    @staticmethod
    def _axis_key(role: str, state: dict[str, Any] | None, axis_index: int) -> tuple[str, int]:
        state = state or {}
        identity = state.get("guid") or state.get("instance_id") or role
        return (str(identity), axis_index)
