from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QLabel

from ..services.settings_service import AppSettings
from .page_settings import SettingsPage as _BaseSettingsPage
from .theme_presets import THEME_CHOICES, normalize_theme


class SettingsPage(_BaseSettingsPage):
    """Polished settings page with a persistent whole-app color theme selector."""

    def __init__(self) -> None:
        super().__init__()
        self.theme_label = QLabel()
        self.theme = QComboBox()
        self.theme.setMinimumWidth(180)
        for code, label in THEME_CHOICES:
            self.theme.addItem(label, code)
        self.theme_row = self._field_row(self.theme_label, self.theme)
        general_layout = self.general_card.layout()
        if general_layout is not None:
            general_layout.insertWidget(3, self.theme_row)
        self.set_language(self._language)

    def set_language(self, language: object) -> None:
        super().set_language(language)
        if not hasattr(self, "theme_label"):
            return
        my = self._language == "my"
        self.theme_label.setText("App အရောင် theme" if my else "Application color theme")
        labels = {
            "aurora": "Aurora Purple" if not my else "Aurora ခရမ်း",
            "ocean": "Ocean Blue" if not my else "Ocean အပြာ",
            "emerald": "Emerald Green" if not my else "Emerald အစိမ်း",
            "sunset": "Sunset Orange" if not my else "Sunset လိမ္မော်",
            "rose": "Rose Pink" if not my else "Rose ပန်းရောင်",
        }
        for index in range(self.theme.count()):
            code = str(self.theme.itemData(index))
            self.theme.setItemText(index, labels.get(code, code))
        self.theme.setToolTip(
            "Sidebar၊ buttons၊ cards၊ progress bars နှင့် transmitter monitor အရောင်အားလုံးကို ပြောင်းမည်။"
            if my
            else "Changes the sidebar, buttons, cards, progress bars and transmitter monitor accents."
        )

    def set_settings(self, settings: AppSettings) -> None:
        super().set_settings(settings)
        index = self.theme.findData(normalize_theme(settings.color_theme))
        if index >= 0:
            self.theme.setCurrentIndex(index)
        self.set_language(settings.language)

    def _save(self) -> None:
        payload: dict[str, Any] = {
            "demo_joystick_enabled": self.demo.isChecked(),
            "low_latency_mode": self.low_latency.isChecked(),
            "realtime_rate_hz": self.realtime_rate.value(),
            "channel_rate_hz": self.rate.value(),
            "serial_baud": int(self.baud.currentData()),
            "auto_detect_adapter": self.auto_detect_adapter.isChecked(),
            "auto_connect": self.auto_connect.isChecked(),
            "log_level": self.log_level.currentText(),
            "language": str(self.language.currentData() or "en"),
            "color_theme": normalize_theme(self.theme.currentData()),
        }
        self.save_requested.emit(payload)
