from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..services.firmware_installer_service import FIRMWARE_TARGETS
from ..services.readiness_service import ReadinessReport


class SetupWizard(QDialog):
    """A guided setup center that hides engineering details from first-time users."""

    action_requested = Signal(str)
    finish_requested = Signal()
    firmware_install_requested = Signal(str, str)
    firmware_cancel_requested = Signal()
    ports_refresh_requested = Signal()

    PAGE_TITLES = (
        "Welcome",
        "Flight controls",
        "Adapter firmware",
        "Calibration & mapping",
        "Ready check",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set up Simulator Joystick to FlySky")
        self.resize(940, 650)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._report: ReadinessReport | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(
            "QFrame { border-bottom: 1px solid palette(midlight); background: palette(base); }"
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 16)
        title = QLabel("Get ready to fly")
        title.setStyleSheet("font-size: 25px; font-weight: 750;")
        subtitle = QLabel(
            "Connect your controls and adapter, install firmware, calibrate, map AETR and verify safety."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: palette(mid);")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(18, 18, 18, 12)
        body.setSpacing(18)
        self.steps = QListWidget()
        self.steps.setFixedWidth(210)
        self.steps.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for number, title_text in enumerate(self.PAGE_TITLES, start=1):
            QListWidgetItem(f"{number}.  {title_text}", self.steps)
        self.steps.currentRowChanged.connect(self._set_page)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._welcome_page())
        self.stack.addWidget(self._controls_page())
        self.stack.addWidget(self._firmware_page())
        self.stack.addWidget(self._mapping_page())
        self.stack.addWidget(self._ready_page())
        body.addWidget(self.steps)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        footer = QFrame()
        footer.setStyleSheet("QFrame { border-top: 1px solid palette(midlight); }")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 12, 18, 12)
        self.status = QLabel("Setup progress is saved automatically.")
        self.status.setStyleSheet("color: palette(mid);")
        self.back_button = QPushButton("Back")
        self.next_button = QPushButton("Next")
        self.later_button = QPushButton("Finish later")
        self.finish_button = QPushButton("Finish setup")
        self.finish_button.setEnabled(False)
        self.back_button.clicked.connect(self._back)
        self.next_button.clicked.connect(self._next)
        self.later_button.clicked.connect(self.hide)
        self.finish_button.clicked.connect(self.finish_requested.emit)
        footer_layout.addWidget(self.status, 1)
        footer_layout.addWidget(self.later_button)
        footer_layout.addWidget(self.back_button)
        footer_layout.addWidget(self.next_button)
        footer_layout.addWidget(self.finish_button)
        root.addWidget(footer)

        self.steps.setCurrentRow(0)

    @staticmethod
    def _page(title: str, intro: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 2, 8, 8)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 22px; font-weight: 700;")
        description = QLabel(intro)
        description.setWordWrap(True)
        description.setStyleSheet("font-size: 12px; color: palette(mid);")
        layout.addWidget(heading)
        layout.addWidget(description)
        return page, layout

    def _welcome_page(self) -> QWidget:
        page, layout = self._page(
            "Welcome",
            "This assistant turns the engineering setup into a short guided flow. You can leave and return without losing profiles or calibration.",
        )
        hero = QFrame()
        hero.setFrameShape(QFrame.Shape.StyledPanel)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        label = QLabel("What you will complete")
        label.setStyleSheet("font-size: 17px; font-weight: 650;")
        details = QLabel(
            "1. Detect the USB stick and separate throttle\n"
            "2. Detect the Arduino or ESP32 adapter\n"
            "3. Install or update the Arduino bridge firmware\n"
            "4. Calibrate every required device\n"
            "5. Map AETR and verify strict failsafe"
        )
        details.setStyleSheet("font-size: 13px; line-height: 1.5;")
        hero_layout.addWidget(label)
        hero_layout.addWidget(details)
        layout.addWidget(hero)
        privacy = QLabel(
            "No account is required. Joystick data, profiles and calibration stay on this computer."
        )
        privacy.setWordWrap(True)
        privacy.setStyleSheet(
            "padding: 10px 12px; border: 1px solid palette(midlight); border-radius: 8px;"
        )
        layout.addWidget(privacy)
        layout.addStretch(1)
        return page

    def _controls_page(self) -> QWidget:
        page, layout = self._page(
            "Connect flight controls",
            "Connect the stick, throttle and optional pedals directly to Windows. The app combines them into one AETR output.",
        )
        self.controls_state = QLabel("Scanning USB controls…")
        self.controls_state.setWordWrap(True)
        self.controls_state.setStyleSheet(
            "font-size: 16px; font-weight: 650; padding: 14px; border: 1px solid palette(midlight); border-radius: 8px;"
        )
        monitor = QPushButton("Open Joystick Monitor")
        monitor.clicked.connect(lambda: self._open_action("Joystick Monitor"))
        layout.addWidget(self.controls_state)
        layout.addWidget(monitor)
        layout.addStretch(1)
        return page

    def _firmware_page(self) -> QWidget:
        page, layout = self._page(
            "Install adapter firmware",
            "For Arduino bridges the application can install the tested PPM firmware without Arduino IDE. Select the exact board and COM port before continuing.",
        )
        self.adapter_state = QLabel("No physical adapter identified yet.")
        self.adapter_state.setWordWrap(True)
        self.adapter_state.setStyleSheet(
            "font-size: 14px; padding: 12px; border: 1px solid palette(midlight); border-radius: 8px;"
        )
        self.board_combo = QComboBox()
        for target in FIRMWARE_TARGETS:
            self.board_combo.addItem(f"{target.label} • PPM {target.ppm_pin}", target.target_id)
        self.port_combo = QComboBox()
        refresh = QPushButton("Refresh COM ports")
        refresh.clicked.connect(self.ports_refresh_requested.emit)
        self.flash_confirmation = QCheckBox(
            "I confirmed the selected board and removed aircraft/motor power."
        )
        self.flash_button = QPushButton("Install firmware")
        self.flash_button.setMinimumHeight(38)
        self.flash_button.clicked.connect(self._request_firmware_install)
        self.cancel_flash_button = QPushButton("Cancel installation")
        self.cancel_flash_button.setEnabled(False)
        self.cancel_flash_button.clicked.connect(self.firmware_cancel_requested.emit)
        self.firmware_progress = QProgressBar()
        self.firmware_progress.setRange(0, 100)
        self.firmware_progress.setValue(0)
        self.firmware_log = QPlainTextEdit()
        self.firmware_log.setReadOnly(True)
        self.firmware_log.setMaximumBlockCount(300)
        self.firmware_log.setPlaceholderText("Firmware installation messages will appear here.")

        row = QHBoxLayout()
        row.addWidget(self.board_combo, 2)
        row.addWidget(self.port_combo, 1)
        row.addWidget(refresh)
        buttons = QHBoxLayout()
        buttons.addWidget(self.flash_button)
        buttons.addWidget(self.cancel_flash_button)
        buttons.addStretch(1)
        layout.addWidget(self.adapter_state)
        layout.addLayout(row)
        layout.addWidget(self.flash_confirmation)
        layout.addLayout(buttons)
        layout.addWidget(self.firmware_progress)
        layout.addWidget(self.firmware_log, 1)
        open_hardware = QPushButton("Open Adapter / Firmware page")
        open_hardware.clicked.connect(lambda: self._open_action("Adapter / Firmware"))
        layout.addWidget(open_hardware)
        return page

    def _mapping_page(self) -> QWidget:
        page, layout = self._page(
            "Calibrate and map AETR",
            "Calibrate each physical device separately, then assign Roll, Pitch, Throttle and Yaw. The setup assistant will update automatically.",
        )
        self.calibration_state = QLabel("Calibration status is being checked.")
        self.mapping_state = QLabel("Mapping status is being checked.")
        for label in (self.calibration_state, self.mapping_state):
            label.setWordWrap(True)
            label.setStyleSheet(
                "font-size: 14px; padding: 12px; border: 1px solid palette(midlight); border-radius: 8px;"
            )
        calibration = QPushButton("Open Calibration")
        calibration.clicked.connect(lambda: self._open_action("Calibration"))
        mapping = QPushButton("Open Channel Mapping")
        mapping.clicked.connect(lambda: self._open_action("Channel Mapping"))
        layout.addWidget(self.calibration_state)
        layout.addWidget(calibration)
        layout.addWidget(self.mapping_state)
        layout.addWidget(mapping)
        layout.addStretch(1)
        return page

    def _ready_page(self) -> QWidget:
        page, layout = self._page(
            "Ready check",
            "All required items must be ready before the setup can be marked complete. Hardware testing should still be done without propellers or motor power.",
        )
        self.ready_title = QLabel("SETUP REQUIRED")
        self.ready_title.setStyleSheet("font-size: 28px; font-weight: 800;")
        self.ready_summary = QLabel("Complete the checklist below.")
        self.ready_summary.setWordWrap(True)
        self.ready_items = QVBoxLayout()
        layout.addWidget(self.ready_title)
        layout.addWidget(self.ready_summary)
        layout.addLayout(self.ready_items)
        hardware = QPushButton("Open final hardware test")
        hardware.clicked.connect(lambda: self._open_action("Adapter / Firmware"))
        layout.addWidget(hardware)
        layout.addStretch(1)
        return page

    def _set_page(self, index: int) -> None:
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        self.back_button.setEnabled(index > 0)
        self.next_button.setVisible(index < self.stack.count() - 1)
        self.finish_button.setVisible(index == self.stack.count() - 1)

    def _back(self) -> None:
        self.steps.setCurrentRow(max(0, self.steps.currentRow() - 1))

    def _next(self) -> None:
        self.steps.setCurrentRow(min(self.stack.count() - 1, self.steps.currentRow() + 1))

    def _open_action(self, page: str) -> None:
        self.action_requested.emit(page)
        self.hide()

    def _request_firmware_install(self) -> None:
        if not self.flash_confirmation.isChecked():
            self.status.setText("Confirm the board and safety checkbox before installing firmware.")
            return
        target = str(self.board_combo.currentData() or "")
        port = str(self.port_combo.currentData() or "")
        self.firmware_install_requested.emit(target, port)

    def set_ports(self, ports: list[dict[str, Any]], preferred: str = "") -> None:
        current = self.port_combo.currentData() or preferred
        self.port_combo.clear()
        for item in ports:
            device = str(item.get("device", ""))
            description = str(item.get("description", "Serial device"))
            if device:
                self.port_combo.addItem(f"{device} — {description}", device)
        wanted = preferred or current
        for index in range(self.port_combo.count()):
            if self.port_combo.itemData(index) == wanted:
                self.port_combo.setCurrentIndex(index)
                break

    def set_adapter_summary(self, text: str, target_hint: str = "") -> None:
        self.adapter_state.setText(text)
        if target_hint:
            index = self.board_combo.findData(target_hint)
            if index >= 0:
                self.board_combo.setCurrentIndex(index)

    def set_firmware_install_available(self, available: bool, detail: str = "") -> None:
        self.flash_button.setEnabled(available and not self.cancel_flash_button.isEnabled())
        if detail:
            self.firmware_log.setPlainText(detail)

    def set_firmware_running(self, running: bool) -> None:
        self.board_combo.setEnabled(not running)
        self.port_combo.setEnabled(not running)
        self.flash_button.setEnabled(not running)
        self.cancel_flash_button.setEnabled(running)
        self.flash_confirmation.setEnabled(not running)
        if running:
            self.firmware_progress.setRange(0, 0)
            self.status.setText("Installing firmware. Do not disconnect USB.")
        else:
            self.firmware_progress.setRange(0, 100)

    def append_firmware_message(self, text: str) -> None:
        self.firmware_log.appendPlainText(text)

    def firmware_finished(self, success: bool, message: str) -> None:
        self.set_firmware_running(False)
        self.firmware_progress.setValue(100 if success else 0)
        self.status.setText(message)
        self.firmware_log.appendPlainText(message)
        if success:
            self.flash_confirmation.setChecked(False)

    def set_report(self, report: ReadinessReport) -> None:
        self._report = report
        by_key = {item.key: item for item in report.items}
        controls = by_key.get("controls")
        roles = by_key.get("roles")
        calibration = by_key.get("calibration")
        mapping = by_key.get("mapping")
        adapter = by_key.get("adapter")
        if controls:
            self.controls_state.setText(f"{controls.title}\n{controls.detail}")
        if adapter:
            self.adapter_state.setText(f"{adapter.title}\n{adapter.detail}")
        if calibration:
            self.calibration_state.setText(
                f"{calibration.title}\n{calibration.detail}"
            )
        if mapping and roles:
            self.mapping_state.setText(
                f"{roles.title}\n{roles.detail}\n\n{mapping.title}\n{mapping.detail}"
            )

        self.ready_title.setText(report.headline)
        self.ready_summary.setText(report.summary)
        while self.ready_items.count():
            item = self.ready_items.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for entry in report.items:
            label = QLabel(
                ("✓  " if entry.passed else "○  ")
                + entry.title
                + " — "
                + entry.detail
            )
            label.setWordWrap(True)
            label.setStyleSheet(
                "padding: 8px 10px; border: 1px solid palette(midlight); border-radius: 7px;"
            )
            self.ready_items.addWidget(label)
        self.finish_button.setEnabled(report.ready)
        self.status.setText(
            "Everything is ready. Finish setup to use the dashboard."
            if report.ready
            else f"Next: {report.next_action}"
        )

    def show_page(self, index: int = 0) -> None:
        self.steps.setCurrentRow(max(0, min(index, self.stack.count() - 1)))
        self.show()
        self.raise_()
        self.activateWindow()
