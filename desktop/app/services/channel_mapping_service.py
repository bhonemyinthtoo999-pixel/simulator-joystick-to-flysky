from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .calibration_service import AxisCalibration

SourceType = Literal["none", "axis", "button", "hat", "constant"]
AxisMode = Literal["centered", "unipolar"]


@dataclass
class ChannelMapping:
    """One RC output channel mapping.

    The model is intentionally device-agnostic. A mapping can read an axis,
    button, hat component, or a constant value from any SDL-compatible device.
    """

    channel: int
    name: str
    source_type: SourceType = "none"
    source_index: int = 0
    hat_component: Literal["x", "y"] = "x"
    constant_value: float = 0.0
    mode: AxisMode = "centered"
    reversed: bool = False
    minimum: int = 1000
    center: int = 1500
    maximum: int = 2000
    failsafe: int = 1500
    trim: int = 0
    expo: float = 0.0
    smoothing: float = 0.0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not 1 <= self.channel <= 16:
            errors.append("channel must be between 1 and 16")
        if self.source_type not in {"none", "axis", "button", "hat", "constant"}:
            errors.append("unsupported source_type")
        if self.mode not in {"centered", "unipolar"}:
            errors.append("unsupported mode")
        if not 800 <= self.minimum <= 2200:
            errors.append("minimum must be 800..2200 us")
        if not 800 <= self.center <= 2200:
            errors.append("center must be 800..2200 us")
        if not 800 <= self.maximum <= 2200:
            errors.append("maximum must be 800..2200 us")
        if not self.minimum <= self.center <= self.maximum:
            errors.append("minimum <= center <= maximum is required")
        if not 800 <= self.failsafe <= 2200:
            errors.append("failsafe must be 800..2200 us")
        if not -250 <= self.trim <= 250:
            errors.append("trim must be -250..250 us")
        if not 0.0 <= self.expo <= 1.0:
            errors.append("expo must be 0.0..1.0")
        if not 0.0 <= self.smoothing < 1.0:
            errors.append("smoothing must be 0.0..<1.0")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChannelMapping":
        allowed = cls.__dataclass_fields__.keys()
        values = {key: value for key, value in payload.items() if key in allowed}
        return cls(**values)


class ChannelMapper:
    """Convert a generic joystick snapshot into safe RC pulse values."""

    def __init__(self) -> None:
        self._smoothed: dict[int, float] = {}

    def reset(self) -> None:
        self._smoothed.clear()

    def map_channels(
        self,
        state: dict[str, Any] | None,
        mappings: list[ChannelMapping],
        calibrations: list[AxisCalibration] | None = None,
    ) -> list[int]:
        calibrations = calibrations or []
        return [self._map_one(state, mapping, calibrations) for mapping in mappings]

    def failsafe_channels(self, mappings: list[ChannelMapping]) -> list[int]:
        return [self._clamp_pulse(mapping.failsafe, mapping) for mapping in mappings]

    def _map_one(
        self,
        state: dict[str, Any] | None,
        mapping: ChannelMapping,
        calibrations: list[AxisCalibration],
    ) -> int:
        if state is None or mapping.source_type == "none":
            return self._clamp_pulse(mapping.failsafe, mapping)

        normalized = self._read_source(state, mapping, calibrations)
        if normalized is None:
            return self._clamp_pulse(mapping.failsafe, mapping)

        normalized = max(-1.0, min(1.0, normalized))
        if mapping.reversed:
            normalized = -normalized

        # Positive expo softens the center while preserving both end points.
        expo = max(0.0, min(1.0, float(mapping.expo)))
        normalized = ((1.0 - expo) * normalized) + (expo * normalized**3)

        smoothing = max(0.0, min(0.99, float(mapping.smoothing)))
        previous = self._smoothed.get(mapping.channel, normalized)
        normalized = (previous * smoothing) + (normalized * (1.0 - smoothing))
        self._smoothed[mapping.channel] = normalized

        if mapping.mode == "unipolar":
            unit = (normalized + 1.0) * 0.5
            pulse = mapping.minimum + unit * (mapping.maximum - mapping.minimum)
        elif normalized >= 0.0:
            pulse = mapping.center + normalized * (mapping.maximum - mapping.center)
        else:
            pulse = mapping.center + normalized * (mapping.center - mapping.minimum)

        pulse += mapping.trim
        return self._clamp_pulse(round(pulse), mapping)

    @staticmethod
    def _read_source(
        state: dict[str, Any],
        mapping: ChannelMapping,
        calibrations: list[AxisCalibration],
    ) -> float | None:
        try:
            if mapping.source_type == "axis":
                axes = state.get("axes", [])
                raw = float(axes[mapping.source_index])
                if mapping.source_index < len(calibrations):
                    return calibrations[mapping.source_index].normalize(raw)
                return raw

            if mapping.source_type == "button":
                buttons = state.get("buttons", [])
                return 1.0 if bool(buttons[mapping.source_index]) else -1.0

            if mapping.source_type == "hat":
                hats = state.get("hats", [])
                hat = hats[mapping.source_index]
                component = 0 if mapping.hat_component == "x" else 1
                return float(hat[component])

            if mapping.source_type == "constant":
                return max(-1.0, min(1.0, float(mapping.constant_value)))
        except (IndexError, KeyError, TypeError, ValueError):
            return None
        return None

    @staticmethod
    def _clamp_pulse(value: int | float, mapping: ChannelMapping) -> int:
        low = min(mapping.minimum, mapping.maximum)
        high = max(mapping.minimum, mapping.maximum)
        return int(max(low, min(high, round(value))))


def default_mappings(channel_count: int = 8) -> list[ChannelMapping]:
    names = ["Roll", "Pitch", "Throttle", "Yaw", "AUX1", "AUX2", "AUX3", "AUX4"]
    mappings: list[ChannelMapping] = []
    for index in range(channel_count):
        mapping = ChannelMapping(channel=index + 1, name=names[index] if index < len(names) else f"CH{index + 1}")
        if index < 4:
            mapping.source_type = "axis"
            mapping.source_index = index
        elif index == 4:
            mapping.source_type = "button"
            mapping.source_index = 0
        elif index == 5:
            mapping.source_type = "button"
            mapping.source_index = 1
        elif index == 6:
            mapping.source_type = "hat"
            mapping.source_index = 0
            mapping.hat_component = "x"
        elif index == 7:
            mapping.source_type = "hat"
            mapping.source_index = 0
            mapping.hat_component = "y"

        if index == 2:
            mapping.mode = "unipolar"
            mapping.failsafe = 1000
        mappings.append(mapping)
    return mappings
