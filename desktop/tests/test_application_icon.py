from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.icon_resources import application_icon, asset_path


def test_logo_safe_icon_is_available_to_qt() -> None:
    app = QApplication.instance() or QApplication([])
    path = asset_path("app_icon.svg")
    assert path.exists()
    assert path.stat().st_size > 1000
    icon = application_icon()
    assert not icon.isNull()
    assert not icon.pixmap(64, 64).isNull()
    assert app is not None
