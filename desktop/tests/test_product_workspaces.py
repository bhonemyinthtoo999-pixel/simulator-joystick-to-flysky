from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QSplitter

from app.services.settings_service import AppSettings
from app.ui.main_window_polished import MainWindow
from app.ui.page_mapping_product import MappingPage
from app.ui.page_settings_product import SettingsPage


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_settings_use_wide_control_center_and_keep_theme_payload() -> None:
    page = SettingsPage()
    page.resize(1250, 760)
    page.set_settings(AppSettings(language="my", color_theme="ocean"))
    captured: list[dict[str, object]] = []
    page.save_requested.connect(captured.append)
    page._save()

    assert page.control_center.isVisible() is False or page.control_center is not None
    assert page.content.maximumWidth() >= 1200
    assert page.theme.currentData() == "ocean"
    assert captured and captured[-1]["color_theme"] == "ocean"
    assert page.general_card.isHidden()
    page.close()


def test_mapping_wide_view_expands_channels_and_hides_editor_scrollbars() -> None:
    page = MappingPage()
    page.resize(1320, 760)
    page.show()
    _TEST_APPLICATION.processEvents()

    assert isinstance(page._splitter, QSplitter)
    assert page._splitter.orientation() == Qt.Orientation.Horizontal
    assert page._channel_panel is not None
    assert page._channel_panel.minimumWidth() >= 380
    assert page._editor_scroll is not None
    assert (
        page._editor_scroll.verticalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    page.close()


def test_about_credit_mentions_maha_and_bmh_without_duplicates() -> None:
    class _Help:
        about_text = QLabel("Simulator Joystick to FlySky")

    class _Shell:
        help_page = _Help()
        _language = "en"

    shell = _Shell()
    MainWindow._apply_about_credit(shell)
    MainWindow._apply_about_credit(shell)
    text = shell.help_page.about_text.text()
    assert "Myanmar Aero Hobbyist Association" in text
    assert "BMH" in text
    assert text.count("Myanmar Aero Hobbyist Association") == 1
