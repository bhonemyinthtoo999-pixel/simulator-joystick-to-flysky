from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtGui import QIcon


def asset_path(filename: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / filename
    return Path(__file__).resolve().parents[1] / "assets" / filename


def application_icon() -> QIcon:
    """Return the shared logo-safe icon used by the window and packaged EXE."""

    rendered = asset_path("SimulatorJoystickToFlySky.png")
    source = asset_path("app_icon.svg")
    icon_path = rendered if rendered.exists() else source
    return QIcon(str(icon_path))
