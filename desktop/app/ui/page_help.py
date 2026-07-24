from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class HelpPage(QWidget):
    navigate_requested = Signal(str)
    validation_requested = Signal()
    support_package_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._language = "en"
        self._version = ""
        self._validation_report: dict[str, object] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(28, 24, 28, 28)
        self.layout.setSpacing(16)

        self.title = QLabel()
        self.title.setStyleSheet("font-size: 28px; font-weight: 780;")
        self.subtitle = QLabel()
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: palette(mid); font-size: 12px;")
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.subtitle)

        self.quick_card = self._card()
        quick_layout = QVBoxLayout(self.quick_card)
        self.quick_heading = QLabel()
        self.quick_heading.setStyleSheet("font-size: 19px; font-weight: 720;")
        self.quick_text = QLabel()
        self.quick_text.setWordWrap(True)
        self.quick_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        quick_layout.addWidget(self.quick_heading)
        quick_layout.addWidget(self.quick_text)
        quick_buttons = QHBoxLayout()
        self.setup_button = QPushButton()
        self.controls_button = QPushButton()
        self.adapter_button = QPushButton()
        self.setup_button.clicked.connect(lambda: self.navigate_requested.emit("Setup"))
        self.controls_button.clicked.connect(
            lambda: self.navigate_requested.emit("Joystick Monitor")
        )
        self.adapter_button.clicked.connect(
            lambda: self.navigate_requested.emit("Adapter / Firmware")
        )
        quick_buttons.addWidget(self.setup_button)
        quick_buttons.addWidget(self.controls_button)
        quick_buttons.addWidget(self.adapter_button)
        quick_buttons.addStretch(1)
        quick_layout.addLayout(quick_buttons)
        self.layout.addWidget(self.quick_card)

        self.wiring_card = self._card()
        wiring_layout = QVBoxLayout(self.wiring_card)
        self.wiring_heading = QLabel()
        self.wiring_heading.setStyleSheet("font-size: 19px; font-weight: 720;")
        self.wiring_text = QLabel()
        self.wiring_text.setWordWrap(True)
        self.wiring_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.wiring_text.setStyleSheet(
            "font-family: Consolas, 'Myanmar Text', monospace; padding: 10px; "
            "border: 1px solid palette(midlight); border-radius: 8px;"
        )
        self.wiring_warning = QLabel()
        self.wiring_warning.setWordWrap(True)
        self.wiring_warning.setStyleSheet(
            "padding: 10px 12px; border: 2px solid #c68a24; border-radius: 8px; font-weight: 650;"
        )
        wiring_layout.addWidget(self.wiring_heading)
        wiring_layout.addWidget(self.wiring_text)
        wiring_layout.addWidget(self.wiring_warning)
        self.layout.addWidget(self.wiring_card)

        self.actions_grid = QGridLayout()
        self.actions_grid.setHorizontalSpacing(12)
        self.actions_grid.setVerticalSpacing(12)
        self.validation_card = self._action_card()
        validation_layout = self.validation_card.layout()
        self.validation_heading = QLabel()
        self.validation_heading.setStyleSheet("font-size: 18px; font-weight: 720;")
        self.validation_status = QLabel()
        self.validation_status.setWordWrap(True)
        self.validation_button = QPushButton()
        self.validation_button.clicked.connect(self.validation_requested.emit)
        validation_layout.addWidget(self.validation_heading)
        validation_layout.addWidget(self.validation_status)
        validation_layout.addWidget(self.validation_button)

        self.support_card = self._action_card()
        support_layout = self.support_card.layout()
        self.support_heading = QLabel()
        self.support_heading.setStyleSheet("font-size: 18px; font-weight: 720;")
        self.support_text = QLabel()
        self.support_text.setWordWrap(True)
        self.support_button = QPushButton()
        self.support_button.clicked.connect(self.support_package_requested.emit)
        self.support_result = QLabel()
        self.support_result.setWordWrap(True)
        self.support_result.setStyleSheet("font-size: 11px; color: palette(mid);")
        support_layout.addWidget(self.support_heading)
        support_layout.addWidget(self.support_text)
        support_layout.addWidget(self.support_button)
        support_layout.addWidget(self.support_result)

        self.actions_grid.addWidget(self.validation_card, 0, 0)
        self.actions_grid.addWidget(self.support_card, 0, 1)
        self.layout.addLayout(self.actions_grid)

        self.trouble_card = self._card()
        trouble_layout = QVBoxLayout(self.trouble_card)
        self.trouble_heading = QLabel()
        self.trouble_heading.setStyleSheet("font-size: 19px; font-weight: 720;")
        self.trouble_text = QLabel()
        self.trouble_text.setWordWrap(True)
        self.trouble_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        trouble_layout.addWidget(self.trouble_heading)
        trouble_layout.addWidget(self.trouble_text)
        self.layout.addWidget(self.trouble_card)

        self.about_card = self._card()
        about_layout = QVBoxLayout(self.about_card)
        self.about_heading = QLabel()
        self.about_heading.setStyleSheet("font-size: 19px; font-weight: 720;")
        self.about_text = QLabel()
        self.about_text.setWordWrap(True)
        self.about_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        about_layout.addWidget(self.about_heading)
        about_layout.addWidget(self.about_text)
        self.layout.addWidget(self.about_card)
        self.layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)
        self.set_language("en")

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame { border: 1px solid palette(midlight); border-radius: 12px; background: palette(base); }"
        )
        return card

    @classmethod
    def _action_card(cls) -> QFrame:
        card = cls._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)
        return card

    def set_version(self, version: str) -> None:
        self._version = version
        self.set_language(self._language)

    def set_validation_report(self, report: dict[str, object] | None) -> None:
        self._validation_report = dict(report or {})
        self.set_language(self._language)

    def set_support_result(self, message: str) -> None:
        self.support_result.setText(message)

    def set_language(self, language: object) -> None:
        self._language = "my" if str(language).casefold() in {"my", "မြန်မာ"} else "en"
        my = self._language == "my"
        self.title.setText("အကူအညီနှင့် Hardware စစ်ဆေးမှု" if my else "Help & Hardware Validation")
        self.subtitle.setText(
            "အခြားသူတစ်ယောက်က အကူအညီမလိုဘဲ install၊ wiring၊ validation နှင့် support report ဖန်တီးနိုင်ရန် စုစည်းထားသောနေရာ။"
            if my
            else "Everything an end user needs to install, wire, validate and report a problem without interrupting the live trainer signal."
        )
        self.quick_heading.setText("အမြန်စတင်ရန်" if my else "Quick start")
        self.quick_text.setText(
            "1. USB joystick/throttle ကို Windows နှင့်ချိတ်ပါ။\n"
            "2. Arduino ကို USB ဖြင့်ချိတ်ပြီး firmware တင်ပါ။\n"
            "3. Device တစ်ခုချင်း calibration လုပ်ပါ။\n"
            "4. Roll/Pitch/Throttle/Yaw ကို AETR mapping လုပ်ပါ။\n"
            "5. Dashboard တွင် LIVE HARDWARE ကိုစစ်ပြီး bench validation လုပ်ပါ။"
            if my
            else "1. Connect the USB stick/throttle to Windows.\n"
            "2. Connect Arduino over USB and install the bundled firmware.\n"
            "3. Calibrate each physical device.\n"
            "4. Map Roll/Pitch/Throttle/Yaw to AETR.\n"
            "5. Confirm LIVE HARDWARE on Dashboard and complete bench validation."
        )
        self.setup_button.setText("Setup Assistant" if my else "Open Setup Assistant")
        self.controls_button.setText("Joystick Monitor" if my else "Open Joystick Monitor")
        self.adapter_button.setText("Adapter / Firmware" if my else "Open Adapter / Firmware")

        self.wiring_heading.setText("FlySky trainer wiring" if my else "FlySky trainer wiring")
        self.wiring_text.setText(
            "Windows PC USB  → Arduino USB\n"
            "Arduino UNO D9   → FlySky trainer SIGNAL\n"
            "Arduino GND      → FlySky trainer GROUND\n"
            "\n"
            "Mega 2560 အသုံးပြုလျှင် PPM = D11"
            if my
            else "Windows PC USB  → Arduino USB\n"
            "Arduino UNO D9   → FlySky trainer SIGNAL\n"
            "Arduino GND      → FlySky trainer GROUND\n"
            "\n"
            "For Mega 2560 use PPM = D11"
        )
        self.wiring_warning.setText(
            "Arduino 5V ကို trainer signal pin ဆီ မချိတ်ပါနှင့်။ Propeller ဖြုတ်ပြီး aircraft/motor power ပိတ်ထားကာ bench test လုပ်ပါ။"
            if my
            else "Never connect Arduino 5V to the trainer signal pin. Remove propellers and disconnect aircraft/motor power for bench testing."
        )

        self.validation_heading.setText("Hardware စစ်ဆေးမှု" if my else "Hardware validation")
        validated_at = str(self._validation_report.get("validated_at", ""))
        board = str(self._validation_report.get("board", ""))
        firmware = str(self._validation_report.get("firmware_version", ""))
        if validated_at:
            self.validation_status.setText(
                f"နောက်ဆုံးအောင်မြင်မှု: {validated_at}\nBoard: {board or '—'}\nFirmware: {firmware or '—'}"
                if my
                else f"Last validated: {validated_at}\nBoard: {board or '—'}\nFirmware: {firmware or '—'}"
            )
        else:
            self.validation_status.setText(
                "Hardware validation report မရှိသေးပါ။ Physical trainer path ကို bench ပေါ်တွင် အတည်ပြုပါ။"
                if my
                else "No hardware validation report has been saved yet. Verify the physical trainer path on the bench."
            )
        self.validation_button.setText("Validation စတင်ရန်" if my else "Start validation")

        self.support_heading.setText("Support package" if my else "Create support package")
        self.support_text.setText(
            "App version၊ controller/adapter အကျဉ်းချုပ်၊ mapping၊ validation နှင့် diagnostic log များကို ZIP တစ်ခုအဖြစ် သိမ်းမည်။ Password၊ ကိုယ်ရေးဖိုင်နှင့် joystick လှုပ်ရှားမှုမှတ်တမ်း မပါဝင်ပါ။"
            if my
            else "Save app version, controller/adapter summary, mapping, validation and diagnostic logs in one ZIP. Passwords, personal files and joystick movement history are excluded."
        )
        self.support_button.setText("Support ZIP ဖန်တီးရန်" if my else "Create Support ZIP")

        self.trouble_heading.setText("အများဆုံးတွေ့ရသော ပြဿနာများ" if my else "Common problems")
        self.trouble_text.setText(
            "• FlySky trainer မလှုပ်ပါ — COM connection၊ D9/GND wiring နှင့် LIVE HARDWARE status ကိုစစ်ပါ။\n"
            "• Stick direction ပြောင်းပြန် — Channel Mapping တွင် Reverse direction ကိုပြင်ပါ။\n"
            "• Throttle idle မြင့်နေသည် — Calibration နှင့် CH3 minimum/failsafe ကိုစစ်ပါ။\n"
            "• Arduino မတွေ့ပါ — Arduino Serial Monitor/IDE ကိုပိတ်ပြီး COM port ပြန်စစ်ပါ။\n"
            "• Offline simulator ကို physical hardware ချိတ်ထားချိန် မသုံးပါနှင့်။"
            if my
            else "• FlySky trainer does not move — check COM connection, D9/GND wiring and LIVE HARDWARE status.\n"
            "• Stick direction is reversed — enable Reverse direction in Channel Mapping.\n"
            "• Throttle idle is too high — check calibration and CH3 minimum/failsafe.\n"
            "• Arduino is not detected — close Arduino Serial Monitor/IDE and rescan COM ports.\n"
            "• Do not use Offline simulator while physical hardware is connected."
        )

        self.about_heading.setText("App အကြောင်း" if my else "About")
        self.about_text.setText(
            f"Simulator Joystick to FlySky v{self._version or '—'}\n"
            "Windows USB flight controls → desktop AETR mapping → Arduino PPM bridge → FlySky trainer port\n"
            "Account မလိုပါ။ Profile၊ calibration နှင့် settings များကို local computer တွင်သာသိမ်းထားသည်။"
            if my
            else f"Simulator Joystick to FlySky v{self._version or '—'}\n"
            "Windows USB flight controls → desktop AETR mapping → Arduino PPM bridge → FlySky trainer port\n"
            "No account is required. Profiles, calibration and settings remain on the local computer."
        )
        self._apply_responsive_layout()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        columns = 1 if width < 900 else 2
        self.actions_grid.removeWidget(self.validation_card)
        self.actions_grid.removeWidget(self.support_card)
        self.actions_grid.addWidget(self.validation_card, 0, 0)
        self.actions_grid.addWidget(
            self.support_card,
            1 if columns == 1 else 0,
            0 if columns == 1 else 1,
        )
        margin = 14 if width < 760 else 20 if width < 1050 else 28
        self.layout.setContentsMargins(margin, 20, margin, 24)
