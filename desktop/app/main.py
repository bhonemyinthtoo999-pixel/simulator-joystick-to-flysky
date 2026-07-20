from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from .ui.main_window import MainWindow

APP_VERSION = "0.2.0"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Simulator Joystick to FlySky")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Simulator Joystick to FlySky")

    def show_unhandled_exception(exc_type: type[BaseException], exc: BaseException, tb: object) -> None:
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        QMessageBox.critical(None, "Unexpected error", details)

    sys.excepthook = show_unhandled_exception
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
