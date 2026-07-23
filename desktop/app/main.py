from __future__ import annotations

import os
import sys
import traceback


def _configure_windows_joystick_backend() -> str:
    """Configure SDL before pygame is imported by the UI services."""

    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    default_mode = "directinput" if sys.platform == "win32" else "auto"
    mode = os.environ.get(
        "SIMJOY_INPUT_BACKEND",
        default_mode,
    ).strip().casefold()
    if sys.platform == "win32" and mode == "directinput":
        os.environ["SDL_JOYSTICK_HIDAPI"] = "0"
        os.environ["SDL_JOYSTICK_WGI"] = "0"
        os.environ["SDL_JOYSTICK_RAWINPUT"] = "0"
    return mode


INPUT_BACKEND_MODE = _configure_windows_joystick_backend()

from PySide6.QtWidgets import QApplication, QMessageBox

from .ui.main_window import MainWindow

APP_VERSION = "0.6.0"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Simulator Joystick to FlySky")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Simulator Joystick to FlySky")
    app.setProperty("simjoyInputBackend", INPUT_BACKEND_MODE)
    app.setProperty(
        "simjoyFeatureSet",
        "low-latency-realtime-output-fast-binary-uno-d9",
    )

    def show_unhandled_exception(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: object,
    ) -> None:
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        QMessageBox.critical(None, "Unexpected error", details)

    sys.excepthook = show_unhandled_exception
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
