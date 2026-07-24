from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class HardwareValidationWizard(QDialog):
    """Bench-validation flow that never pauses or reroutes live channel streaming."""

    navigate_requested = Signal(str)
    status_requested = Signal()
    completed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.resize(900, 720)
        self._language = "en"
        self._snapshot: dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            "QFrame { border-bottom: 1px solid palette(midlight); background: palette(base); }"
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 16)
        self.title = QLabel()
        self.title.setStyleSheet("font-size: 25px; font-weight: 760;")
        self.subtitle = QLabel()
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: palette(mid);")
        header_layout.addWidget(self.title)
        header_layout.addWidget(self.subtitle)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        self.safety_notice = QLabel()
        self.safety_notice.setWordWrap(True)
        self.safety_notice.setStyleSheet(
            "padding: 12px 14px; border: 2px solid #c68a24; border-radius: 10px; font-weight: 650;"
        )
        layout.addWidget(self.safety_notice)

        self.auto_heading = QLabel()
        self.auto_heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(self.auto_heading)

        self.auto_grid = QGridLayout()
        self.auto_grid.setHorizontalSpacing(12)
        self.auto_grid.setVerticalSpacing(12)
        self.auto_labels: dict[str, tuple[QLabel, QLabel, QFrame]] = {}
        for index, key in enumerate(("controls", "adapter", "stream", "mapping", "ppm")):
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(13, 11, 13, 11)
            heading = QLabel()
            heading.setStyleSheet("font-size: 11px; font-weight: 750; color: palette(mid);")
            state = QLabel("CHECKING")
            state.setStyleSheet("font-size: 17px; font-weight: 750;")
            detail = QLabel()
            detail.setWordWrap(True)
            detail.setStyleSheet("font-size: 11px; color: palette(mid);")
            card_layout.addWidget(heading)
            card_layout.addWidget(state)
            card_layout.addWidget(detail)
            self.auto_grid.addWidget(card, index // 2, index % 2)
            self.auto_labels[key] = (state, detail, heading)
        layout.addLayout(self.auto_grid)

        action_row = QHBoxLayout()
        self.open_controls = QPushButton()
        self.open_adapter = QPushButton()
        self.refresh_status = QPushButton()
        self.open_controls.clicked.connect(
            lambda: self.navigate_requested.emit("Joystick Monitor")
        )
        self.open_adapter.clicked.connect(
            lambda: self.navigate_requested.emit("Adapter / Firmware")
        )
        self.refresh_status.clicked.connect(self.status_requested.emit)
        action_row.addWidget(self.open_controls)
        action_row.addWidget(self.open_adapter)
        action_row.addWidget(self.refresh_status)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.manual_heading = QLabel()
        self.manual_heading.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(self.manual_heading)

        self.manual_checks: dict[str, QCheckBox] = {}
        for key in (
            "bench_safe",
            "trainer_moves",
            "directions",
            "throttle_idle",
            "failsafe_bench",
        ):
            box = QCheckBox()
            box.setWordWrap(True)
            box.toggled.connect(self._update_finish_state)
            layout.addWidget(box)
            self.manual_checks[key] = box

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "padding: 12px 14px; border: 1px solid palette(midlight); border-radius: 9px;"
        )
        layout.addWidget(self.summary)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QFrame()
        footer.setStyleSheet("QFrame { border-top: 1px solid palette(midlight); }")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 12, 18, 12)
        self.close_button = QPushButton()
        self.complete_button = QPushButton()
        self.complete_button.setMinimumHeight(40)
        self.complete_button.clicked.connect(self._complete)
        self.close_button.clicked.connect(self.hide)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.close_button)
        footer_layout.addWidget(self.complete_button)
        root.addWidget(footer)

        self.set_language("en")
        self.set_snapshot({})

    def set_language(self, language: object) -> None:
        self._language = "my" if str(language).casefold() in {"my", "မြန်မာ"} else "en"
        my = self._language == "my"
        self.setWindowTitle("Hardware စစ်ဆေးမှု" if my else "Hardware Validation")
        self.title.setText("Hardware စစ်ဆေးမှု" if my else "Hardware Validation")
        self.subtitle.setText(
            "လက်ရှိ Arduino/FlySky output ကို မရပ်ဘဲ bench test များကို အဆင့်လိုက်အတည်ပြုပါ။"
            if my
            else "Confirm the real Arduino/FlySky signal path step by step without pausing or rerouting live output."
        )
        self.safety_notice.setText(
            "လုံခြုံရေး — Propeller ဖြုတ်ထားပြီး motor/aircraft power ပိတ်ထားသည့် bench setup ပေါ်တွင်သာ စစ်ဆေးပါ။ Validation wizard က channel streaming ကိုမရပ်ပါ။"
            if my
            else "SAFETY — Validate only on a bench with propellers removed and aircraft/motor power disconnected. This wizard never pauses channel streaming."
        )
        self.auto_heading.setText("အလိုအလျောက် စစ်ဆေးချက်များ" if my else "Automatic live checks")
        self.manual_heading.setText("အသုံးပြုသူ အတည်ပြုရမည့် စစ်ဆေးချက်များ" if my else "Manual bench confirmations")
        headings = {
            "controls": "PHYSICAL CONTROLS",
            "adapter": "PHYSICAL ADAPTER",
            "stream": "LIVE STREAM",
            "mapping": "AETR SAFETY",
            "ppm": "PPM ENGINE",
        }
        my_headings = {
            "controls": "PHYSICAL CONTROL",
            "adapter": "PHYSICAL ADAPTER",
            "stream": "LIVE STREAM",
            "mapping": "AETR လုံခြုံရေး",
            "ppm": "PPM ENGINE",
        }
        for key, (_state, _detail, heading) in self.auto_labels.items():
            heading.setText((my_headings if my else headings)[key])
        manual = {
            "bench_safe": (
                "Propeller ဖြုတ်ထားပြီး aircraft/motor power ပိတ်ထားကြောင်း အတည်ပြုသည်။"
                if my
                else "Propellers are removed and aircraft/motor power is disconnected."
            ),
            "trainer_moves": (
                "Dashboard transmitter animation နှင့် FlySky trainer input တူညီစွာ လှုပ်ကြောင်း စစ်ပြီးပြီ။"
                if my
                else "The Dashboard transmitter animation and FlySky trainer input move together."
            ),
            "directions": (
                "Roll၊ Pitch နှင့် Yaw direction များ မှန်ကြောင်း bench ပေါ်တွင် စစ်ပြီးပြီ။"
                if my
                else "Roll, pitch and yaw directions were checked on the bench."
            ),
            "throttle_idle": (
                "Throttle idle တွင် CH3 သည် သတ်မှတ်ထားသော safe low value ဖြစ်ကြောင်း စစ်ပြီးပြီ။"
                if my
                else "Throttle idle produces the configured safe low CH3 value."
            ),
            "failsafe_bench": (
                "USB disconnect / communication failsafe ကို motor power မရှိဘဲ စစ်ပြီးပြီ။"
                if my
                else "USB disconnect / communication failsafe was tested without motor power."
            ),
        }
        for key, box in self.manual_checks.items():
            box.setText(manual[key])
        self.open_controls.setText("Joystick Monitor ဖွင့်ရန်" if my else "Open Joystick Monitor")
        self.open_adapter.setText("Adapter / Firmware ဖွင့်ရန်" if my else "Open Adapter / Firmware")
        self.refresh_status.setText("Status ပြန်စစ်ရန်" if my else "Refresh adapter status")
        self.close_button.setText("ပိတ်ရန်" if my else "Close")
        self.complete_button.setText("Validation report သိမ်းရန်" if my else "Save validation report")
        self.set_snapshot(self._snapshot)

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = dict(snapshot)
        checks = {
            "controls": bool(snapshot.get("controls_ready")),
            "adapter": bool(snapshot.get("adapter_ready")),
            "stream": bool(snapshot.get("streaming")),
            "mapping": bool(snapshot.get("mapping_ready")),
            "ppm": bool(snapshot.get("ppm_active")),
        }
        my = self._language == "my"
        details = {
            "controls": str(snapshot.get("controls_detail") or ("Physical control မတွေ့ပါ" if my else "No physical flight control detected")),
            "adapter": str(snapshot.get("adapter_detail") or ("Physical adapter မချိတ်ထားပါ" if my else "No physical adapter identified")),
            "stream": str(snapshot.get("stream_detail") or ("Live channel stream မရှိသေးပါ" if my else "No active live channel stream")),
            "mapping": str(snapshot.get("mapping_detail") or ("AETR mapping ကို စစ်ဆေးရန်လိုသည်" if my else "AETR mapping requires attention")),
            "ppm": str(snapshot.get("ppm_detail") or ("Adapter STATUS ကို ပြန်တောင်းပါ" if my else "Request adapter STATUS to verify PPM")),
        }
        for key, passed in checks.items():
            state, detail, _heading = self.auto_labels[key]
            state.setText(("အောင်မြင်" if my else "PASS") if passed else ("မပြည့်စုံ" if my else "NOT READY"))
            state.setStyleSheet(
                "font-size: 17px; font-weight: 750; color: "
                + ("#238453;" if passed else "#a66b10;")
            )
            detail.setText(details[key])
        self._update_finish_state()

    def _all_ready(self) -> bool:
        auto_ready = all(
            bool(self._snapshot.get(key))
            for key in (
                "controls_ready",
                "adapter_ready",
                "streaming",
                "mapping_ready",
                "ppm_active",
            )
        )
        manual_ready = all(box.isChecked() for box in self.manual_checks.values())
        return auto_ready and manual_ready

    def _update_finish_state(self) -> None:
        ready = self._all_ready()
        self.complete_button.setEnabled(ready)
        if self._language == "my":
            self.summary.setText(
                "စစ်ဆေးချက်အားလုံး ပြည့်စုံပြီ။ Validation report ကို သိမ်းနိုင်ပါပြီ။"
                if ready
                else "Automatic check အားလုံး PASS ဖြစ်ပြီး manual checkbox အားလုံးကို bench ပေါ်တွင်အတည်ပြုပြီးမှ report သိမ်းနိုင်မည်။"
            )
        else:
            self.summary.setText(
                "All checks are complete. The validation report can be saved."
                if ready
                else "All automatic checks must pass and every manual bench confirmation must be checked before saving."
            )

    def _complete(self) -> None:
        if not self._all_ready():
            QMessageBox.warning(
                self,
                "Validation incomplete",
                "Complete every automatic and manual check first.",
            )
            return
        report = {
            "schema_version": 1,
            "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "board": self._snapshot.get("board", ""),
            "firmware_version": self._snapshot.get("firmware_version", ""),
            "connection": self._snapshot.get("connection", ""),
            "ppm_pin": self._snapshot.get("ppm_pin"),
            "channels": list(self._snapshot.get("channels", [])),
            "automatic_checks": {
                "physical_controls": True,
                "physical_adapter": True,
                "live_stream": True,
                "aetr_mapping": True,
                "ppm_active": True,
            },
            "manual_confirmations": {key: True for key in self.manual_checks},
            "safety_note": "User confirmed a propeller-free, motor-power-disconnected bench test.",
        }
        self.completed.emit(report)
        self.hide()

    def show_validation(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
