from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class AppSettings:
    demo_joystick_enabled: bool = True
    channel_rate_hz: int = 50
    serial_baud: int = 115200
    auto_connect: bool = False
    last_port: str = ""
    log_level: str = "INFO"

    def validate(self) -> None:
        self.channel_rate_hz = max(10, min(100, int(self.channel_rate_hz)))
        if self.serial_baud not in {9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600}:
            self.serial_baud = 115200
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            self.log_level = "INFO"


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".simulator-joystick-to-flysky" / "settings.json")

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            settings = AppSettings(**{key: value for key, value in payload.items() if key in AppSettings.__dataclass_fields__})
            settings.validate()
            return settings
        except (OSError, ValueError, TypeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        settings.validate()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        temporary.replace(self.path)
