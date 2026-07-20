from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable


@dataclass
class AxisCalibration:
    minimum: float = -1.0
    center: float = 0.0
    maximum: float = 1.0
    deadzone: float = 0.03
    inverted: bool = False

    def normalize(self, raw: float) -> float:
        raw = max(self.minimum, min(self.maximum, float(raw)))
        if raw >= self.center:
            span = max(1e-6, self.maximum - self.center)
            value = (raw - self.center) / span
        else:
            span = max(1e-6, self.center - self.minimum)
            value = (raw - self.center) / span
        if abs(value) < self.deadzone:
            value = 0.0
        if self.inverted:
            value = -value
        return max(-1.0, min(1.0, value))

    def to_rc(self, raw: float, rc_min: int = 1000, rc_center: int = 1500, rc_max: int = 2000) -> int:
        value = self.normalize(raw)
        if value >= 0:
            pulse = rc_center + value * (rc_max - rc_center)
        else:
            pulse = rc_center + value * (rc_center - rc_min)
        return int(round(pulse))


class CalibrationSession:
    """Collect minimum, center and maximum values for an arbitrary joystick."""

    def __init__(self, axis_count: int) -> None:
        self.axis_count = axis_count
        self.minimum = [float("inf")] * axis_count
        self.maximum = [float("-inf")] * axis_count
        self.center = [0.0] * axis_count
        self.samples = 0

    def observe(self, axes: Iterable[float]) -> None:
        values = list(axes)
        for index in range(min(self.axis_count, len(values))):
            value = float(values[index])
            self.minimum[index] = min(self.minimum[index], value)
            self.maximum[index] = max(self.maximum[index], value)
        self.samples += 1

    def capture_center(self, axes: Iterable[float]) -> None:
        values = list(axes)
        for index in range(min(self.axis_count, len(values))):
            self.center[index] = float(values[index])

    def result(self) -> list[AxisCalibration]:
        result: list[AxisCalibration] = []
        for index in range(self.axis_count):
            minimum = self.minimum[index]
            maximum = self.maximum[index]
            if minimum == float("inf"):
                minimum = -1.0
            if maximum == float("-inf"):
                maximum = 1.0
            if maximum - minimum < 0.05:
                minimum, maximum = -1.0, 1.0
            center = max(minimum, min(maximum, self.center[index]))
            result.append(AxisCalibration(minimum=minimum, center=center, maximum=maximum))
        return result


class CalibrationStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".simulator-joystick-to-flysky" / "calibrations.json")

    def load(self) -> dict[str, list[AxisCalibration]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return {
                guid: [AxisCalibration(**axis) for axis in axes]
                for guid, axes in payload.items()
                if isinstance(axes, list)
            }
        except (OSError, ValueError, TypeError):
            return {}

    def save(self, data: dict[str, list[AxisCalibration]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {guid: [asdict(axis) for axis in axes] for guid, axes in data.items()}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)
