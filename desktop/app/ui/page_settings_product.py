from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .page_settings_themed import SettingsPage as _ThemedSettingsPage
from .toggle_switch import ToggleSwitch


class SettingsPage(_ThemedSettingsPage):
    """Wide, low-scroll settings control center for desktop-sized windows."""

    def __init__(self) -> None:
        super().__init__()
        self._settings_columns = 0

        # Replace the previous small floating cards with one wide control surface.
        self.general_card.hide()
        self.performance_card.hide()
        self.adapter_card.hide()
        self.content.setMaximumWidth(1240)

        self.control_center = QFrame()
        self.control_center.setFrameShape(QFrame.Shape.StyledPanel)
        self.control_center.setProperty("uiCard", True)
        center_layout = QVBoxLayout(self.control_center)
        center_layout.setContentsMargins(22, 20, 22, 20)
        center_layout.setSpacing(15)

        self.appearance_section = self._section()
        appearance_layout = QVBoxLayout(self.appearance_section)
        appearance_layout.setContentsMargins(18, 15, 18, 15)
        appearance_layout.setSpacing(10)
        self.appearance_heading = self._heading()
        self.appearance_detail = self._detail()
        appearance_layout.addWidget(self.appearance_heading)
        appearance_layout.addWidget(self.appearance_detail)
        self.appearance_fields = QGridLayout()
        self.appearance_fields.setHorizontalSpacing(28)
        self.appearance_fields.setVerticalSpacing(8)
        self.language_product_label = QLabel()
        self.theme_product_label = QLabel()
        self.language_product_label.setStyleSheet("font-weight: 700;")
        self.theme_product_label.setStyleSheet("font-weight: 700;")
        self.language.setMinimumWidth(220)
        self.theme.setMinimumWidth(220)
        self.appearance_fields.addWidget(self.language_product_label, 0, 0)
        self.appearance_fields.addWidget(self.language, 1, 0)
        self.appearance_fields.addWidget(self.theme_product_label, 0, 1)
        self.appearance_fields.addWidget(self.theme, 1, 1)
        self.appearance_fields.setColumnStretch(0, 1)
        self.appearance_fields.setColumnStretch(1, 1)
        appearance_layout.addLayout(self.appearance_fields)
        center_layout.addWidget(self.appearance_section)

        self.lower_grid = QGridLayout()
        self.lower_grid.setHorizontalSpacing(16)
        self.lower_grid.setVerticalSpacing(16)

        self.performance_section = self._section()
        performance_layout = QVBoxLayout(self.performance_section)
        performance_layout.setContentsMargins(18, 15, 18, 15)
        performance_layout.setSpacing(10)
        self.performance_product_heading = self._heading()
        self.performance_product_detail = self._detail()
        performance_layout.addWidget(self.performance_product_heading)
        performance_layout.addWidget(self.performance_product_detail)
        self.low_latency_product_title = QLabel()
        self.low_latency_product_detail = QLabel()
        performance_layout.addWidget(
            self._switch_row(
                self.low_latency,
                self.low_latency_product_title,
                self.low_latency_product_detail,
            )
        )
        performance_fields = QGridLayout()
        performance_fields.setHorizontalSpacing(20)
        performance_fields.setVerticalSpacing(8)
        self.realtime_product_label = QLabel()
        self.ui_rate_product_label = QLabel()
        self.realtime_product_label.setStyleSheet("font-weight: 700;")
        self.ui_rate_product_label.setStyleSheet("font-weight: 700;")
        performance_fields.addWidget(self.realtime_product_label, 0, 0)
        performance_fields.addWidget(self.ui_rate_product_label, 0, 1)
        performance_fields.addWidget(self.realtime_rate, 1, 0)
        performance_fields.addWidget(self.rate, 1, 1)
        performance_fields.setColumnStretch(0, 1)
        performance_fields.setColumnStretch(1, 1)
        performance_layout.addLayout(performance_fields)
        performance_layout.addStretch(1)

        self.hardware_section = self._section()
        hardware_layout = QVBoxLayout(self.hardware_section)
        hardware_layout.setContentsMargins(18, 15, 18, 15)
        hardware_layout.setSpacing(10)
        self.hardware_product_heading = self._heading()
        self.hardware_product_detail = self._detail()
        hardware_layout.addWidget(self.hardware_product_heading)
        hardware_layout.addWidget(self.hardware_product_detail)

        self.demo_product_title = QLabel()
        self.demo_product_detail = QLabel()
        self.detect_product_title = QLabel()
        self.detect_product_detail = QLabel()
        self.connect_product_title = QLabel()
        self.connect_product_detail = QLabel()
        hardware_layout.addWidget(
            self._switch_row(self.demo, self.demo_product_title, self.demo_product_detail)
        )
        hardware_layout.addWidget(
            self._switch_row(
                self.auto_detect_adapter,
                self.detect_product_title,
                self.detect_product_detail,
            )
        )
        hardware_layout.addWidget(
            self._switch_row(
                self.auto_connect,
                self.connect_product_title,
                self.connect_product_detail,
            )
        )
        hardware_fields = QGridLayout()
        hardware_fields.setHorizontalSpacing(20)
        hardware_fields.setVerticalSpacing(8)
        self.baud_product_label = QLabel()
        self.log_product_label = QLabel()
        self.baud_product_label.setStyleSheet("font-weight: 700;")
        self.log_product_label.setStyleSheet("font-weight: 700;")
        hardware_fields.addWidget(self.baud_product_label, 0, 0)
        hardware_fields.addWidget(self.log_product_label, 0, 1)
        hardware_fields.addWidget(self.baud, 1, 0)
        hardware_fields.addWidget(self.log_level, 1, 1)
        hardware_fields.setColumnStretch(0, 1)
        hardware_fields.setColumnStretch(1, 1)
        hardware_layout.addLayout(hardware_fields)

        self.lower_grid.addWidget(self.performance_section, 0, 0)
        self.lower_grid.addWidget(self.hardware_section, 0, 1)
        center_layout.addLayout(self.lower_grid)

        content_layout = self.content.layout()
        if isinstance(content_layout, QVBoxLayout):
            content_layout.insertWidget(2, self.control_center)

        self.save_button.setMinimumWidth(210)
        self.save_button.setMaximumWidth(280)
        self.note.setMaximumWidth(1240)
        self.set_language(self._language)
        self._apply_product_layout()

    @staticmethod
    def _section() -> QFrame:
        frame = QFrame()
        frame.setObjectName("settingsProductSection")
        frame.setStyleSheet(
            "QFrame#settingsProductSection { border: 1px solid palette(midlight); "
            "border-radius: 13px; background: palette(alternate-base); }"
        )
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return frame

    @staticmethod
    def _heading() -> QLabel:
        label = QLabel()
        label.setStyleSheet("font-size: 18px; font-weight: 800;")
        return label

    @staticmethod
    def _detail() -> QLabel:
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 11px; color: palette(mid);")
        return label

    @staticmethod
    def _switch_row(toggle: ToggleSwitch, title: QLabel, detail: QLabel) -> QFrame:
        row = QFrame()
        row.setObjectName("settingsProductSwitch")
        row.setStyleSheet(
            "QFrame#settingsProductSwitch { border: 0; border-bottom: 1px solid palette(midlight); }"
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 8, 2, 9)
        layout.setSpacing(14)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 12px; font-weight: 750;")
        detail.setWordWrap(True)
        detail.setStyleSheet("font-size: 10px; color: palette(mid);")
        text_layout.addWidget(title)
        text_layout.addWidget(detail)
        layout.addLayout(text_layout, 1)
        layout.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_product_layout()

    def _apply_product_layout(self) -> None:
        columns = 1 if self.width() < 1040 else 2
        if columns == self._settings_columns:
            return
        self.lower_grid.removeWidget(self.performance_section)
        self.lower_grid.removeWidget(self.hardware_section)
        self.lower_grid.addWidget(self.performance_section, 0, 0)
        self.lower_grid.addWidget(
            self.hardware_section,
            1 if columns == 1 else 0,
            0 if columns == 1 else 1,
        )
        self.lower_grid.setColumnStretch(0, 1)
        self.lower_grid.setColumnStretch(1, 1 if columns == 2 else 0)
        self._settings_columns = columns

    def set_language(self, language: object) -> None:
        super().set_language(language)
        if not hasattr(self, "appearance_heading"):
            return
        my = self._language == "my"
        self.title.setText("ဆက်တင်များ" if my else "Settings")
        self.intro.setText(
            "App အပြင်အဆင်၊ realtime control performance နှင့် hardware ချိတ်ဆက်မှုများကို စာမျက်နှာတစ်ခုတည်းတွင် ပြင်ဆင်နိုင်သည်။"
            if my
            else "Configure appearance, realtime control performance and hardware behavior from one wide control center."
        )
        self.appearance_heading.setText("အပြင်အဆင်" if my else "Appearance")
        self.appearance_detail.setText(
            "ဘာသာစကားနှင့် app တစ်ခုလုံး၏ အရောင် theme"
            if my
            else "Language and the color theme used throughout the application"
        )
        self.language_product_label.setText("ဘာသာစကား" if my else "Language")
        self.theme_product_label.setText("App အရောင် theme" if my else "Application color theme")

        self.performance_product_heading.setText("Realtime စွမ်းဆောင်ရည်" if my else "Realtime performance")
        self.performance_product_detail.setText(
            "Joystick → Arduino output path ကို UI animation များမှ သီးခြားထိန်းချုပ်သည်။"
            if my
            else "Keep the joystick-to-Arduino path independent from heavier interface updates."
        )
        self.low_latency_product_title.setText("Low-latency flight output")
        self.low_latency_product_detail.setText(
            "FlySky trainer control အတွက် အကြံပြုထားသော compact channel stream"
            if my
            else "Recommended compact channel stream for FlySky trainer control"
        )
        self.realtime_product_label.setText("Realtime output အမြန်နှုန်း" if my else "Realtime output limit")
        self.ui_rate_product_label.setText("UI refresh အမြန်နှုန်း" if my else "UI refresh rate")

        self.hardware_product_heading.setText("Hardware နှင့် Diagnostics" if my else "Hardware & diagnostics")
        self.hardware_product_detail.setText(
            "Demo input၊ adapter auto-detection၊ COM preference နှင့် support log"
            if my
            else "Demo input, adapter discovery, COM preference and support logging"
        )
        self.demo_product_title.setText("Built-in Demo Flight Joystick")
        self.demo_product_detail.setText(
            "Hardware မရှိချိန် UI စမ်းသပ်ရန်သာ" if my else "UI exploration only when physical hardware is unavailable"
        )
        self.detect_product_title.setText(
            "Arduino / ESP32 adapter ကို အလိုအလျောက်ရှာရန်"
            if my
            else "Automatically detect Arduino / ESP32 adapter"
        )
        self.detect_product_detail.setText(
            "မှန်ကန်သော firmware handshake ရရှိမှသာ လက်ခံမည်"
            if my
            else "Accept a serial port only after a valid firmware handshake"
        )
        self.connect_product_title.setText(
            "နောက်ဆုံးအောင်မြင်ခဲ့သော COM port ကို ဦးစားပေးရန်"
            if my
            else "Prefer the last successful COM port"
        )
        self.connect_product_detail.setText(
            "App စတင်ချိန်တွင် ယခင် adapter ကိုအရင်စမ်းမည်"
            if my
            else "Try the previously working adapter first at startup"
        )
        self.baud_product_label.setText("မူလ serial baud" if my else "Default serial baud")
        self.log_product_label.setText("Diagnostics အဆင့်" if my else "Diagnostics level")
        self.save_button.setText("ဆက်တင်များ သိမ်းရန်" if my else "Save settings")
