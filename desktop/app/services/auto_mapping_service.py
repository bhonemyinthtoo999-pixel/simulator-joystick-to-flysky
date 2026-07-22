from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


@dataclass(frozen=True)
class AutoMapStep:
    channel_index: int
    name: str
    prompt: str
    mode: str
    failsafe: int


@dataclass(frozen=True)
class AutoMapCapture:
    step: AutoMapStep
    axis_index: int
    reversed: bool
    change: float


class AutoMappingSession:
    """Identify the primary flight-control axes from deliberate user motion.

    Each step captures the strongest unused axis. The requested movement is
    considered the positive RC direction, so a negative raw delta automatically
    enables channel reversal.
    """

    DEFAULT_STEPS = (
        AutoMapStep(0, "Roll", "Move the roll control fully RIGHT", "centered", 1500),
        AutoMapStep(1, "Pitch", "Pull the pitch control fully BACK", "centered", 1500),
        AutoMapStep(2, "Throttle", "Move the throttle to FULL / HIGH", "unipolar", 1000),
        AutoMapStep(3, "Yaw", "Move the rudder or twist control fully RIGHT", "centered", 1500),
    )

    def __init__(self, threshold: float = 0.25, arm_delay_s: float = 0.35) -> None:
        self.threshold = max(0.05, float(threshold))
        self.arm_delay_s = max(0.0, float(arm_delay_s))
        self.steps = self.DEFAULT_STEPS
        self.step_index = 0
        self.used_axes: set[int] = set()
        self.baseline: list[float] = []
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

    def start(self, state: dict[str, Any], now: float | None = None) -> None:
        axes = self._axes(state)
        if len(axes) < len(self.steps):
            raise ValueError("At least four joystick axes are required for automatic flight-control mapping.")
        self.step_index = 0
        self.used_axes.clear()
        self.active = True
        self._arm(axes, now)

    def cancel(self) -> None:
        self.active = False
        self.baseline = []
        self.used_axes.clear()

    def observe(self, state: dict[str, Any], now: float | None = None) -> AutoMapCapture | None:
        if not self.active or self.complete:
            return None
        axes = self._axes(state)
        if len(axes) != len(self.baseline):
            self._arm(axes, now)
            return None

        timestamp = time.monotonic() if now is None else float(now)
        if timestamp < self.armed_at:
            # Track the resting position while the user releases the previous control.
            self.baseline = axes
            return None

        strongest_axis = -1
        strongest_delta = 0.0
        for index, (before, current) in enumerate(zip(self.baseline, axes)):
            if index in self.used_axes:
                continue
            delta = current - before
            if abs(delta) > abs(strongest_delta):
                strongest_axis = index
                strongest_delta = delta

        if strongest_axis < 0 or abs(strongest_delta) < self.threshold:
            return None

        step = self.steps[self.step_index]
        capture = AutoMapCapture(
            step=step,
            axis_index=strongest_axis,
            reversed=strongest_delta < 0.0,
            change=strongest_delta,
        )
        self.used_axes.add(strongest_axis)
        self.step_index += 1
        if self.complete:
            self.active = False
            self.baseline = []
        else:
            self._arm(axes, timestamp)
        return capture

    def _arm(self, axes: list[float], now: float | None) -> None:
        timestamp = time.monotonic() if now is None else float(now)
        self.baseline = list(axes)
        self.armed_at = timestamp + self.arm_delay_s

    @staticmethod
    def _axes(state: dict[str, Any]) -> list[float]:
        try:
            return [float(value) for value in state.get("axes", [])]
        except (TypeError, ValueError):
            return []
