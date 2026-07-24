from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from app.services.joystick_service import JoystickInfo
from app.services.settings_service import AppSettings
from app.ui.page_joystick_polished import JoystickPage
from app.ui.page_settings_themed import SettingsPage
from app.ui.theme_presets import DynamicProductThemeController, normalize_theme
from app.ui.transmitter_monitor import TransmitterCanvas


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_color_theme_is_validated_and_saved_in_settings_payload() -> None:
    settings = AppSettings(color_theme="sunset")
    settings.validate()
    assert settings.color_theme == "sunset"

    page = SettingsPage()
    page.set_settings(settings)
    assert page.theme.currentData() == "sunset"

    emitted: list[dict[str, object]] = []
    page.save_requested.connect(lambda payload: emitted.append(dict(payload)))
    page._save()
    assert emitted[-1]["color_theme"] == "sunset"
    page.close()


def test_unknown_color_theme_falls_back_to_aurora() -> None:
    settings = AppSettings(color_theme="not-a-theme")
    settings.validate()
    assert settings.color_theme == "aurora"
    assert normalize_theme("Ocean Blue") == "ocean"


def test_dynamic_theme_updates_application_palette_property() -> None:
    root = QWidget()
    controller = DynamicProductThemeController(_TEST_APPLICATION, root, "ocean")
    assert controller.theme_name == "ocean"
    assert _TEST_APPLICATION.property("simjoyColorTheme") == "ocean"

    controller.apply_theme("emerald")
    palette = _TEST_APPLICATION.property("simjoyThemePalette")
    assert controller.theme_name == "emerald"
    assert isinstance(palette, dict)
    assert palette["primary"] == "#059669"
    root.close()


def test_pressed_joystick_button_has_green_on_style() -> None:
    page = JoystickPage()
    page.set_selected_device(
        JoystickInfo(
            instance_id=1,
            name="Test Flight Stick",
            guid="TEST-GUID",
            axes=2,
            buttons=2,
            hats=0,
            balls=0,
            power_level="wired",
            is_virtual=False,
            backend="SDL DirectInput",
        )
    )
    page.update_state({"axes": [0.0, 0.0], "buttons": [1, 0], "hats": []})

    assert page._button_labels[0].text() == "B0: ON"
    assert "#d1fae5" in page._button_labels[0].styleSheet()
    assert "#34d399" in page._button_labels[0].styleSheet()
    assert page._button_labels[1].text() == "B1: OFF"
    page.close()


def test_transmitter_canvas_renders_with_selected_theme() -> None:
    _TEST_APPLICATION.setProperty(
        "simjoyThemePalette",
        {
            "primary": "#0284c7",
            "primary_light": "#38bdf8",
            "primary_dark": "#075985",
            "secondary": "#06b6d4",
            "accent": "#2563eb",
            "success": "#10b981",
        },
    )
    canvas = TransmitterCanvas()
    canvas.resize(960, 390)
    canvas.set_channels([1750, 1250, 1000, 1600])
    canvas.set_link_state("live")
    image = QPixmap(canvas.size())
    image.fill()
    canvas.render(image)
    assert not image.isNull()
    canvas.close()
