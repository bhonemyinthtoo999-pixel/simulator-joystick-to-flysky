from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..services.localization_service import SUPPORTED_LANGUAGES, normalize_language
from ..services.settings_service import AppSettings
from .toggle_switch import ToggleSwitch


class SettingsPage(QWidget):
    save_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._language = "en"
        self._last_card_columns = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        viewport = QWidget()
        viewport_layout = QHBoxLayout(viewport)
        viewport_layout.setContentsMargins(20, 22, 20, 28)
        viewport_layout.addStretch(1)

        self.content = QWidget()
        self.content.setMaximumWidth(980)
        self.content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.title = QLabel()
        self.title.setStyleSheet("font-size: 30px; font-weight: 800;")
        self.intro = QLabel()
        self.intro.setWordWrap(True)
        self.intro.setStyleSheet("font-size: 12px; color: palette(mid);")
        layout.addWidget(self.title)
        layout.addWidget(self.intro)

        self.cards_grid = QGridLayout()
        self.cards_grid.setHorizontalSpacing(16)
        self.cards_grid.setVerticalSpacing(16)

        self.general_card, general = self._make_card()
        self.general_heading = QLabel()
        self.general_heading.setStyleSheet("font-size: 19px; font-weight: 750;")
        self.general_subtitle = self._subtitle_label()
        general.addWidget(self.general_heading)
        general.addWidget(self.general_subtitle)

        self.language = QComboBox()
        self.language.setMinimumWidth(180)
        for code, label in SUPPORTED_LANGUAGES:
            self.language.addItem(label, code)
        self.language_label = QLabel()
        general.addWidget(self._field_row(self.language_label, self.language))

        self.demo = ToggleSwitch()
        (
            self.demo_row,
            self.demo_title,
            self.demo_detail,
        ) = self._toggle_row(self.demo)
        general.addWidget(self.demo_row)
        general.addStretch(1)

        self.performance_card, performance = self._make_card()
        self.performance_heading = QLabel()
        self.performance_heading.setStyleSheet("font-size: 19px; font-weight: 750;")
        self.performance_subtitle = self._subtitle_label()
        performance.addWidget(self.performance_heading)
        performance.addWidget(self.performance_subtitle)

        self.low_latency = ToggleSwitch()
        (
            self.low_latency_row,
            self.low_latency_title,
            self.low_latency_detail,
        ) = self._toggle_row(self.low_latency)
        performance.addWidget(self.low_latency_row)

        self.realtime_rate = QSpinBox()
        self.realtime_rate.setRange(50, 200)
        self.realtime_rate.setSingleStep(10)
        self.realtime_rate.setSuffix(" Hz")
        self.realtime_rate.setMinimumWidth(130)
        self.realtime_label = QLabel()
        performance.addWidget(self._field_row(self.realtime_label, self.realtime_rate))

        self.rate = QSpinBox()
        self.rate.setRange(10, 60)
        self.rate.setSuffix(" Hz")
        self.rate.setMinimumWidth(130)
        self.rate_label = QLabel()
        performance.addWidget(self._field_row(self.rate_label, self.rate))
        performance.addStretch(1)

        self.adapter_card, adapter = self._make_card()
        self.adapter_heading = QLabel()
        self.adapter_heading.setStyleSheet("font-size: 19px; font-weight: 750;")
        self.adapter_subtitle = self._subtitle_label()
        adapter.addWidget(self.adapter_heading)
        adapter.addWidget(self.adapter_subtitle)

        self.auto_detect_adapter = ToggleSwitch()
        (
            self.auto_detect_row,
            self.auto_detect_title,
            self.auto_detect_detail,
        ) = self._toggle_row(self.auto_detect_adapter)
        adapter.addWidget(self.auto_detect_row)

        self.auto_connect = ToggleSwitch()
        (
            self.auto_connect_row,
            self.auto_connect_title,
            self.auto_connect_detail,
        ) = self._toggle_row(self.auto_connect)
        adapter.addWidget(self.auto_connect_row)

        fields = QWidget()
        fields_layout = QGridLayout(fields)
        fields_layout.setContentsMargins(0, 4, 0, 0)
        fields_layout.setHorizontalSpacing(20)
        fields_layout.setVerticalSpacing(12)
        fields_layout.setColumnStretch(0, 1)
        fields_layout.setColumnStretch(2, 1)

        self.baud = QComboBox()
        for value in (
            9600,
            19200,
            38400,
            57600,
            115200,
            230400,
            460800,
            921600,
        ):
            self.baud.addItem(str(value), value)
        self.baud.setMinimumWidth(150)
        self.baud_label = QLabel()

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setMinimumWidth(150)
        self.log_label = QLabel()

        fields_layout.addWidget(self.baud_label, 0, 0)
        fields_layout.addWidget(self.baud, 0, 1)
        fields_layout.addWidget(self.log_label, 0, 2)
        fields_layout.addWidget(self.log_level, 0, 3)
        adapter.addWidget(fields)

        self.cards_grid.addWidget(self.general_card, 0, 0)
        self.cards_grid.addWidget(self.performance_card, 0, 1)
        self.cards_grid.addWidget(self.adapter_card, 1, 0, 1, 2)
        layout.addLayout(self.cards_grid)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.save_button = QPushButton()
        self.save_button.setProperty("buttonRole", "success")
        self.save_button.setMinimumHeight(42)
        self.save_button.setMinimumWidth(190)
        self.save_button.setMaximumWidth(240)
        self.save_button.clicked.connect(self._save)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setStyleSheet(
            "font-size: 11px; color: palette(mid); padding: 10px 12px; "
            "border: 1px solid palette(midlight); border-radius: 9px;"
        )
        layout.addWidget(self.note)
        layout.addStretch(1)

        viewport_layout.addWidget(self.content, 1)
        viewport_layout.addStretch(1)
        scroll.setWidget(viewport)
        outer.addWidget(scroll)

        self.set_language("en")
        self._apply_responsive_layout()

    @staticmethod
    def _make_card() -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setProperty("uiCard", True)
        body = QVBoxLayout(card)
        body.setContentsMargins(20, 18, 20, 18)
        body.setSpacing(12)
        return card, body

    @staticmethod
    def _subtitle_label() -> QLabel:
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 11px; color: palette(mid);")
        return label

    @staticmethod
    def _field_row(label: QLabel, control: QWidget) -> QWidget:
        row = QWidget()
        row.setObjectName("settingFieldRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 5, 0, 5)
        row_layout.setSpacing(14)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        control.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(label, 1)
        row_layout.addWidget(control, 0)
        return row

    @staticmethod
    def _toggle_row(toggle: ToggleSwitch) -> tuple[QFrame, QLabel, QLabel]:
        row = QFrame()
        row.setObjectName("settingToggleRow")
        row.setStyleSheet(
            "QFrame#settingToggleRow { padding: 3px; border: 1px solid palette(midlight); "
            "border-radius: 11px; background: palette(alternate-base); }"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(13, 10, 13, 10)
        row_layout.setSpacing(14)
        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        title = QLabel()
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 12px; font-weight: 700;")
        detail = QLabel()
        detail.setWordWrap(True)
        detail.setStyleSheet("font-size: 10px; color: palette(mid);")
        text_box.addWidget(title)
        text_box.addWidget(detail)
        row_layout.addLayout(text_box, 1)
        row_layout.addWidget(toggle, 0)
        return row, title, detail

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        columns = 1 if self.width() < 930 else 2
        if columns == self._last_card_columns:
            return
        for card in (self.general_card, self.performance_card, self.adapter_card):
            self.cards_grid.removeWidget(card)
        if columns == 1:
            self.cards_grid.addWidget(self.general_card, 0, 0)
            self.cards_grid.addWidget(self.performance_card, 1, 0)
            self.cards_grid.addWidget(self.adapter_card, 2, 0)
        else:
            self.cards_grid.addWidget(self.general_card, 0, 0)
            self.cards_grid.addWidget(self.performance_card, 0, 1)
            self.cards_grid.addWidget(self.adapter_card, 1, 0, 1, 2)
        self.cards_grid.setColumnStretch(0, 1)
        self.cards_grid.setColumnStretch(1, 1 if columns == 2 else 0)
        self._last_card_columns = columns

    def set_language(self, language: object) -> None:
        self._language = normalize_language(language)
        my = self._language == "my"

        self.title.setText("ဆက်တင်များ" if my else "Settings")
        self.intro.setText(
            "ဘာသာစကား၊ realtime output နှင့် adapter ချိတ်ဆက်မှုဆိုင်ရာ ဆက်တင်များကို ရှင်းလင်းစွာပြင်ဆင်နိုင်သည်။ သိမ်းပြီးသည်နှင့် ဘာသာစကားချက်ချင်းပြောင်းမည်။"
            if my
            else "Choose the app language and tune realtime output, adapter discovery and diagnostics in one place. Language changes apply immediately after saving."
        )

        self.general_heading.setText("အထွေထွေ" if my else "General")
        self.general_subtitle.setText(
            "ဘာသာစကားနှင့် စမ်းသပ်အသုံးပြုရန် demo input"
            if my
            else "Language and safe demo input"
        )
        self.language_label.setText("ဘာသာစကား" if my else "Language")
        self.demo_title.setText(
            "Built-in Demo Flight Joystick"
            if my
            else "Built-in Demo Flight Joystick"
        )
        self.demo_detail.setText(
            "Hardware မချိတ်ထားချိန် UI စမ်းသပ်ရန်သာ။ Flight-ready hardware အဖြစ်မတွက်ပါ။"
            if my
            else "Use only to explore the UI without hardware. It never counts as flight-ready input."
        )
        self.demo.setAccessibleName(self.demo_title.text())

        self.performance_heading.setText("စွမ်းဆောင်ရည်" if my else "Performance")
        self.performance_subtitle.setText(
            "Joystick → Arduino realtime path နှင့် UI refresh"
            if my
            else "Realtime joystick-to-Arduino output and UI refresh"
        )
        self.low_latency_title.setText(
            "Low-latency flight output"
            if my
            else "Low-latency flight output"
        )
        self.low_latency_detail.setText(
            "FlySky trainer control အတွက် အကြံပြုသည်။ Compact binary channel frame ကိုအသုံးပြုမည်။"
            if my
            else "Recommended for FlySky trainer control. Uses the compact binary channel stream when supported."
        )
        self.low_latency.setAccessibleName(self.low_latency_title.text())
        self.realtime_label.setText(
            "Realtime output အမြန်နှုန်း" if my else "Realtime output limit"
        )
        self.rate_label.setText("UI refresh အမြန်နှုန်း" if my else "UI refresh rate")

        self.adapter_heading.setText(
            "Adapter နှင့် Diagnostics" if my else "Adapter & Diagnostics"
        )
        self.adapter_subtitle.setText(
            "USB serial board ရှာဖွေမှုနှင့် support log အဆင့်"
            if my
            else "USB serial board discovery and support logging"
        )
        self.auto_detect_title.setText(
            "Arduino / ESP32 adapter ကို အလိုအလျောက်ရှာရန်"
            if my
            else "Automatically detect Arduino / ESP32 adapter"
        )
        self.auto_detect_detail.setText(
            "Firmware handshake မှန်ကန်မှသာ physical adapter အဖြစ်လက်ခံမည်။"
            if my
            else "A serial port is accepted only after a valid firmware handshake."
        )
        self.auto_detect_adapter.setAccessibleName(self.auto_detect_title.text())
        self.auto_connect_title.setText(
            "နောက်ဆုံးအောင်မြင်ခဲ့သော COM port ကို ဦးစားပေးရန်"
            if my
            else "Prefer the last successful COM port"
        )
        self.auto_connect_detail.setText(
            "App ပြန်ဖွင့်ချိန် မကြာခဏသုံးသော adapter ကိုအရင်စမ်းမည်။"
            if my
            else "Try the previously working adapter first when the app starts."
        )
        self.auto_connect.setAccessibleName(self.auto_connect_title.text())
        self.baud_label.setText("မူလ serial baud" if my else "Default serial baud")
        self.log_label.setText("Diagnostics အဆင့်" if my else "Diagnostics level")

        self.save_button.setText("ဆက်တင်များ သိမ်းရန်" if my else "Save settings")
        self.note.setText(
            "Low-latency mode သည် realtime joystick-to-Arduino output ကို dashboard နှင့် mapping UI update များမှ ခွဲထားသည်။ တိုက်ရိုက် stick response အတွက် mapping smoothing ကို 0 ထားပါ။"
            if my
            else "Low-latency mode keeps realtime joystick-to-Arduino output separate from heavier dashboard and mapping updates. Set mapping smoothing to 0 for the most direct stick response."
        )

    def set_settings(self, settings: AppSettings) -> None:
        self.demo.setChecked(settings.demo_joystick_enabled)
        self.low_latency.setChecked(settings.low_latency_mode)
        self.realtime_rate.setValue(settings.realtime_rate_hz)
        self.rate.setValue(settings.channel_rate_hz)
        index = self.baud.findData(settings.serial_baud)
        if index >= 0:
            self.baud.setCurrentIndex(index)
        self.auto_detect_adapter.setChecked(settings.auto_detect_adapter)
        self.auto_connect.setChecked(settings.auto_connect)
        self.log_level.setCurrentText(settings.log_level)
        language_index = self.language.findData(normalize_language(settings.language))
        if language_index >= 0:
            self.language.setCurrentIndex(language_index)
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
        }
        self.save_requested.emit(payload)
