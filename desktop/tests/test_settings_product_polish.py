from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.settings_service import AppSettings
from app.ui.page_settings import SettingsPage
from app.ui.toggle_switch import ToggleSwitch


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def _grid_position(page: SettingsPage, widget) -> tuple[int, int, int, int]:
    index = page.cards_grid.indexOf(widget)
    assert index >= 0
    return page.cards_grid.getItemPosition(index)


def test_settings_uses_accessible_toggle_controls() -> None:
    page = SettingsPage()
    assert isinstance(page.demo, ToggleSwitch)
    assert isinstance(page.low_latency, ToggleSwitch)
    assert isinstance(page.auto_detect_adapter, ToggleSwitch)
    assert isinstance(page.auto_connect, ToggleSwitch)

    page.demo.setChecked(False)
    page.demo.click()
    assert page.demo.isChecked()
    assert page.demo.accessibleName()
    page.close()


def test_settings_cards_reflow_for_window_width() -> None:
    page = SettingsPage()
    page.resize(760, 760)
    page._apply_responsive_layout()
    assert _grid_position(page, page.general_card)[:2] == (0, 0)
    assert _grid_position(page, page.performance_card)[:2] == (1, 0)
    assert _grid_position(page, page.adapter_card)[:2] == (2, 0)

    page.resize(1200, 760)
    page._apply_responsive_layout()
    assert _grid_position(page, page.general_card)[:2] == (0, 0)
    assert _grid_position(page, page.performance_card)[:2] == (0, 1)
    assert _grid_position(page, page.adapter_card) == (1, 0, 1, 2)
    page.close()


def test_settings_burmese_copy_and_payload_are_preserved() -> None:
    page = SettingsPage()
    page.set_settings(
        AppSettings(
            language="my",
            demo_joystick_enabled=False,
            low_latency_mode=True,
            realtime_rate_hz=120,
            channel_rate_hz=40,
            serial_baud=115200,
            auto_detect_adapter=True,
            auto_connect=True,
            log_level="INFO",
        )
    )
    assert page.title.text() == "ဆက်တင်များ"
    assert "Joystick" in page.demo_title.text()
    assert page.content.maximumWidth() == 980
    assert page.save_button.maximumWidth() == 240

    payloads: list[dict[str, object]] = []
    page.save_requested.connect(payloads.append)
    page._save()
    assert payloads[-1]["language"] == "my"
    assert payloads[-1]["realtime_rate_hz"] == 120
    assert payloads[-1]["auto_connect"] is True
    page.close()
