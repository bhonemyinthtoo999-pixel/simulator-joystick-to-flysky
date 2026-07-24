from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class HardwareValidationStore:
    """Persist the most recent user-approved bench validation report."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (
            Path.home()
            / ".simulator-joystick-to-flysky"
            / "hardware-validation.json"
        )

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def save(self, report: dict[str, Any]) -> None:
        payload = dict(report)
        payload.setdefault("schema_version", 1)
        payload.setdefault("validated_at", utc_now())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
