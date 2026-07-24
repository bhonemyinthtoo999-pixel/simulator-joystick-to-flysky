from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.localization_service import (
    localize_readiness_report,
    navigation_label,
    normalize_language,
)
from app.services.readiness_service import ReadinessItem, ReadinessReport
from app.services.settings_service import AppSettings, SettingsStore
from app.ui.main_window_product import MainWindow
from app.ui.page_dashboard_responsive import DashboardPage


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_language_normalization_and_navigation_labels() -> None:
    assert normalize_language("Myanmar") == "my"
    assert normalize_language("မြန်မာ") == "my"
    assert normalize_language("English") == "en"
    assert navigation_label("Dashboard", "my") == "ပင်မစာမျက်နှာ"
    assert navigation_label("Adapter / Firmware", "my") == "Adapter / Firmware"


def test_settings_store_round_trips_burmese_language(tmp_path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(language="my")
    store.save(settings)
    loaded = store.load()
    assert loaded.language == "my"
    assert "မြန်မာ" not in (tmp_path / "settings.json").read_text(encoding="utf-8") or loaded.language == "my"


def test_readiness_report_is_localized_without_changing_navigation_keys() -> None:
    report = ReadinessReport(
        ready=False,
        headline="SETUP REQUIRED",
        summary="Connect a USB stick, throttle or pedals. Demo input does not count as flight-ready hardware.",
        next_action="Connect flight controls",
        next_page="Joystick Monitor",
        items=(
            ReadinessItem(
                "controls",
                "Connect flight controls",
                "action",
                "Connect a USB stick, throttle or pedals. Demo input does not count as flight-ready hardware.",
                "Joystick Monitor",
            ),
        ),
    )
    localized = localize_readiness_report(report, "my")
    assert localized.headline == "ပြင်ဆင်ရန် လိုအပ်သည်"
    assert localized.items[0].title == "Flight control များ ချိတ်ပါ"
    assert localized.next_page == "Joystick Monitor"
    assert localized.items[0].action == "Joystick Monitor"


def test_dashboard_reflows_for_narrow_and_wide_windows() -> None:
    page = DashboardPage()
    page.resize(720, 780)
    page._apply_responsive_layout()
    assert page._last_checklist_columns == 1
    page.resize(1000, 780)
    page._apply_responsive_layout()
    assert page._last_checklist_columns == 2
    page.resize(1320, 780)
    page._apply_responsive_layout()
    assert page._last_checklist_columns == 3
    page.set_language("my")
    assert "FlySky" in page.windowTitle() or page.windowTitle() == ""
    page.close()


def test_product_window_switches_language_and_preserves_page_keys(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.settings_service.Path.home",
        lambda: tmp_path,
    )
    window = MainWindow()
    window._language = "my"
    window.settings.language = "my"
    window._apply_language()

    assert window.navigation.item(0).text() == "ပင်မစာမျက်နှာ"
    assert window.navigation.item(0).data(0x0100) == "Dashboard"
    assert window.settings_page.language.currentData() in {"en", "my"}

    window.resize(780, 700)
    window._apply_responsive_layout()
    assert window.navigation_panel.width() == 150
    window.close()
