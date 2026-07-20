from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class DiagnosticEntry:
    timestamp: str
    level: str
    source: str
    message: str

    def format(self) -> str:
        return f"{self.timestamp} [{self.level:<7}] {self.source}: {self.message}"


class DiagnosticsService(QObject):
    entry_added = Signal(object)
    cleared = Signal()

    def __init__(self, capacity: int = 2000) -> None:
        super().__init__()
        self._entries: deque[DiagnosticEntry] = deque(maxlen=capacity)

    def log(self, level: str, source: str, message: str) -> None:
        entry = DiagnosticEntry(
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
            level=level.upper(),
            source=source,
            message=str(message),
        )
        self._entries.append(entry)
        self.entry_added.emit(entry)

    def debug(self, source: str, message: str) -> None:
        self.log("DEBUG", source, message)

    def info(self, source: str, message: str) -> None:
        self.log("INFO", source, message)

    def warning(self, source: str, message: str) -> None:
        self.log("WARNING", source, message)

    def error(self, source: str, message: str) -> None:
        self.log("ERROR", source, message)

    def clear(self) -> None:
        self._entries.clear()
        self.cleared.emit()

    def entries(self) -> list[DiagnosticEntry]:
        return list(self._entries)

    def export(self, path: Path, context: dict[str, Any] | None = None) -> None:
        lines = ["Simulator Joystick to FlySky diagnostics", "=" * 48]
        if context:
            lines.extend(f"{key}: {value}" for key, value in context.items())
            lines.append("-" * 48)
        lines.extend(entry.format() for entry in self._entries)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
