from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def main() -> int:
    """Desktop app ကို စတင်ရန် main entry point ဖြစ်သည်။"""
    app = QApplication(sys.argv)
    app.setApplicationName("Simulator Joystick to FlySky")
    app.setOrganizationName("Simulator Joystick to FlySky")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
