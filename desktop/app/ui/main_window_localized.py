from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
)

from ..services.hardware_validation_service import HardwareValidationStore
from ..services.localization_service import apply_widget_language
from ..services.protocol_service import MessageType
from ..services.support_package_service import SupportPackageService
from .main_window_product import MainWindow as _ProductMainWindow
from .page_help import HelpPage
from .validation_wizard import HardwareValidationWizard


class MainWindow(_ProductMainWindow):
    """Final product shell with bilingual help, validation and support tools."""

    NAVIGATION_KEYS = _ProductMainWindow.NAVIGATION_KEYS + ("Help & Validation",)

    def __init__(self) -> None:
        self._last_adapter_status_payload: dict[str, Any] = {}
        self._last_adapter_identity_payload: dict[str, Any] = {}
        self._validation_report: dict[str, Any] = {}
        super().__init__()

        self._wizard_firmware_row = self._find_layout_with_widgets(
            self.setup_wizard,
            self.setup_wizard.board_combo,
            self.setup_wizard.port_combo,
        )
        self._wizard_flash_row = self._find_layout_with_widgets(
            self.setup_wizard,
            self.setup_wizard.flash_button,
            self.setup_wizard.cancel_flash_button,
        )
        self._localization_timer = QTimer(self)
        self._localization_timer.setInterval(500)
        self._localization_timer.timeout.connect(self._refresh_visible_language)
        self._localization_timer.start()
        self._apply_wizard_responsive()
        self._refresh_validation_snapshot()

    def _install_product_navigation(self) -> None:
        """Add the end-user help page before the product sidebar is assembled."""

        if not hasattr(self, "help_page"):
            self.validation_store = HardwareValidationStore()
            self._validation_report = self.validation_store.load()
            self.support_package_service = SupportPackageService()
            self.help_page = HelpPage()
            self.validation_wizard = HardwareValidationWizard(self)
            self.pages.addWidget(self.help_page)
            QListWidgetItem("Help & Validation", self.navigation)

            self.help_page.navigate_requested.connect(
                self._navigate_to_product_page
            )
            self.help_page.validation_requested.connect(
                self._open_hardware_validation
            )
            self.help_page.support_package_requested.connect(
                self._create_support_package
            )
            self.validation_wizard.navigate_requested.connect(
                self._navigate_to_product_page
            )
            self.validation_wizard.status_requested.connect(
                self._request_validation_status
            )
            self.validation_wizard.completed.connect(
                self._save_hardware_validation
            )
            app = QApplication.instance()
            version = app.applicationVersion() if app is not None else ""
            self.help_page.set_version(version or "0.8.3")
            self.help_page.set_validation_report(self._validation_report)

        super()._install_product_navigation()

    def _apply_language(self) -> None:
        super()._apply_language()
        if not hasattr(self, "help_page"):
            return
        self.help_page.set_language(self._language)
        self.validation_wizard.set_language(self._language)
        self.help_page.set_validation_report(self._validation_report)
        item = self.navigation.item(self.navigation.count() - 1)
        if item is not None:
            item.setText(
                "အကူအညီနှင့် Hardware စစ်ဆေးမှု"
                if self._language == "my"
                else "Help & Validation"
            )
            item.setData(Qt.ItemDataRole.UserRole, "Help & Validation")

    def _refresh_visible_language(self) -> None:
        if self._language == "my":
            current = self.pages.currentWidget()
            if current is not None and current is not self.help_page:
                apply_widget_language(current, self._language)
            if self.setup_wizard.isVisible():
                apply_widget_language(self.setup_wizard, self._language)
        if self.pages.currentWidget() is self.help_page:
            self.help_page.set_language(self._language)
        if self.validation_wizard.isVisible():
            self.validation_wizard.set_language(self._language)
        self._refresh_validation_snapshot()

    def _record_adapter_identity(self, payload: dict[str, Any]) -> None:
        self._last_adapter_identity_payload = dict(payload)
        super()._record_adapter_identity(payload)
        self._refresh_validation_snapshot()

    def _on_protocol_message(
        self,
        message_type: int,
        payload: dict[str, Any],
    ) -> None:
        try:
            kind = MessageType(message_type)
        except ValueError:
            kind = None
        if kind == MessageType.STATUS:
            self._last_adapter_status_payload = dict(payload)
        super()._on_protocol_message(message_type, payload)
        self._refresh_validation_snapshot()

    def _on_connection_changed(self, connected: bool, label: str) -> None:
        if not connected:
            self._last_adapter_status_payload = {}
            self._last_adapter_identity_payload = {}
        super()._on_connection_changed(connected, label)
        self._refresh_validation_snapshot()

    def _validation_snapshot(self) -> dict[str, Any]:
        physical_devices = [
            info
            for info in self._device_infos.values()
            if not info.is_virtual
        ]
        controls_ready = bool(physical_devices)
        physical_kinds = {
            "arduino_uno",
            "arduino_mega",
            "arduino",
            "esp32",
        }
        adapter_ready = (
            self.serial_service.connected
            and self._adapter_kind in physical_kinds
        )
        command_paused = bool(
            getattr(self, "_stream_paused_for_command", False)
        )
        streaming = (
            adapter_ready
            and not self._stream_paused_for_test
            and not command_paused
            and not self.channel_mapper.last_strict_failsafe
        )
        active = self._active_profile()
        first_four = active.mappings[:4]
        mapping_ready = (
            len(first_four) == 4
            and not active.validate()
            and not self.channel_mapper.last_strict_failsafe
            and all(mapping.source_type != "none" for mapping in first_four)
        )
        status = self._last_adapter_status_payload
        ppm_active = bool(status.get("ppm_active", False))
        identity = self._last_adapter_identity_payload
        board = str(
            identity.get("board")
            or status.get("board")
            or self._adapter_kind
        )
        firmware = str(
            identity.get("firmware_version")
            or status.get("firmware_version")
            or ""
        )
        ppm_pin = identity.get("ppm_gpio", status.get("ppm_gpio"))
        if ppm_pin is None:
            if self._adapter_kind == "arduino_uno":
                ppm_pin = 9
            elif self._adapter_kind == "arduino_mega":
                ppm_pin = 11

        my = self._language == "my"
        device_names = ", ".join(info.name for info in physical_devices[:4])
        controls_detail = (
            f"တွေ့ရှိသည်: {device_names}"
            if my and controls_ready
            else f"Detected: {device_names}"
            if controls_ready
            else "Physical USB flight control မတွေ့ပါ"
            if my
            else "No physical USB flight control detected"
        )
        adapter_detail = (
            f"{board} • {self._adapter_connection_label or 'connected'}"
            if adapter_ready
            else "Physical Arduino/ESP32 adapter မချိတ်ထားပါ"
            if my
            else "No physical Arduino/ESP32 adapter identified"
        )
        stream_detail = (
            f"CH1–CH4: {list(self._current_channels[:4])}"
            if streaming
            else "Live output ရပ်ထားသည် သို့မဟုတ် failsafe active ဖြစ်နေသည်"
            if my
            else "Live output is paused or strict failsafe is active"
        )
        mapping_detail = (
            "AETR channel ၄ ခုနှင့် strict failsafe အခြေအနေကောင်းသည်"
            if my and mapping_ready
            else "First four AETR channels and strict failsafe are healthy"
            if mapping_ready
            else "AETR mapping သို့မဟုတ် calibration ကိုပြင်ရန်လိုသည်"
            if my
            else "AETR mapping or calibration requires attention"
        )
        ppm_detail = (
            f"PPM active • pin D{ppm_pin}" if ppm_active and ppm_pin is not None
            else "PPM active" if ppm_active
            else "Adapter STATUS ကိုတောင်းပြီး PPM active ကိုစစ်ပါ"
            if my
            else "Request adapter STATUS to verify PPM active"
        )
        return {
            "controls_ready": controls_ready,
            "controls_detail": controls_detail,
            "adapter_ready": adapter_ready,
            "adapter_detail": adapter_detail,
            "streaming": streaming,
            "stream_detail": stream_detail,
            "mapping_ready": mapping_ready,
            "mapping_detail": mapping_detail,
            "ppm_active": ppm_active,
            "ppm_detail": ppm_detail,
            "board": board,
            "firmware_version": firmware,
            "connection": self._adapter_connection_label,
            "ppm_pin": ppm_pin,
            "channels": list(self._current_channels),
        }

    def _refresh_validation_snapshot(self) -> None:
        if not hasattr(self, "validation_wizard"):
            return
        self.validation_wizard.set_snapshot(self._validation_snapshot())
        self.help_page.set_validation_report(self._validation_report)

    def _open_hardware_validation(self) -> None:
        self.validation_wizard.set_language(self._language)
        self._refresh_validation_snapshot()
        self.validation_wizard.show_validation()
        self._request_validation_status()

    def _request_validation_status(self) -> None:
        if (
            self.serial_service.connected
            and self._adapter_kind
            in {"arduino_uno", "arduino_mega", "arduino", "esp32"}
        ):
            self.serial_service.send(MessageType.STATUS, {})
            self.diagnostics.info(
                "Hardware validation",
                "Requested non-disruptive adapter STATUS snapshot",
            )
        else:
            self._refresh_validation_snapshot()

    def _save_hardware_validation(self, report: object) -> None:
        if not isinstance(report, dict):
            return
        try:
            self.validation_store.save(report)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Validation save failed",
                str(exc),
            )
            return
        self._validation_report = dict(report)
        self.help_page.set_validation_report(self._validation_report)
        self.diagnostics.info(
            "Hardware validation",
            f"Validation report saved for {report.get('board', 'adapter')}",
        )
        QMessageBox.information(
            self,
            "Hardware validated",
            (
                "Hardware validation report ကို local computer တွင် သိမ်းပြီးပြီ။"
                if self._language == "my"
                else "The hardware validation report was saved on this computer."
            ),
        )

    def _support_context(self) -> dict[str, Any]:
        app = QApplication.instance()
        active = self._active_profile()
        devices = []
        for info in self._device_infos.values():
            devices.append(
                {
                    "name": info.name,
                    "backend": info.backend,
                    "axes": info.axes,
                    "buttons": info.buttons,
                    "hats": info.hats,
                    "virtual": info.is_virtual,
                    "guid_suffix": info.guid[-8:] if info.guid else "",
                }
            )
        calibration_summary = []
        for guid, axes in self.calibrations.items():
            match = next(
                (
                    info.name
                    for info in self._device_infos.values()
                    if info.guid == guid
                ),
                "Previously saved device",
            )
            calibration_summary.append(
                {
                    "device": match,
                    "saved_axes": len(axes),
                    "guid_suffix": guid[-8:] if guid else "",
                }
            )
        readiness = getattr(self, "_readiness_report", None)
        readiness_context = {}
        if readiness is not None:
            readiness_context = {
                "ready": bool(readiness.ready),
                "headline": readiness.headline,
                "next_action": readiness.next_action,
                "items": [
                    {
                        "key": item.key,
                        "passed": item.passed,
                        "title": item.title,
                        "detail": item.detail,
                    }
                    for item in readiness.items
                ],
            }
        bindings = {
            role: (
                "automatic"
                if value in {"", "*", "__AUTO__"}
                else "bound"
            )
            for role, value in active.device_bindings.items()
        }
        return {
            "application": {
                "name": "Simulator Joystick to FlySky",
                "version": app.applicationVersion() if app is not None else "",
                "language": self._language,
                "low_latency_mode": self.settings.low_latency_mode,
                "realtime_rate_hz": self.settings.realtime_rate_hz,
            },
            "adapter": {
                "kind": self._adapter_kind,
                "connection": self._adapter_connection_label,
                "capabilities": sorted(self._adapter_capabilities),
                "identity": self._last_adapter_identity_payload,
                "status": self._last_adapter_status_payload,
            },
            "flight_controls": devices,
            "calibration_summary": calibration_summary,
            "profile": {
                "name": active.name,
                "channel_count": active.channel_count,
                "strict_aetr_failsafe": active.strict_aetr_failsafe,
                "device_roles": bindings,
                "ppm_frame_us": active.ppm_frame_us,
                "ppm_pulse_us": active.ppm_pulse_us,
                "failsafe_timeout_ms": active.failsafe_timeout_ms,
                "mappings": [mapping.to_dict() for mapping in active.mappings],
            },
            "current_channels": list(self._current_channels),
            "readiness": readiness_context,
        }

    def _create_support_package(self) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        default_name = f"SimulatorJoystickToFlySky-Support-{stamp}.zip"
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Create Support Package",
            str(Path.home() / default_name),
            "ZIP archives (*.zip)",
        )
        if not filename:
            return
        try:
            path = self.support_package_service.create(
                Path(filename),
                context=self._support_context(),
                diagnostics=self.diagnostics.entries(),
                validation_report=self._validation_report,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Support package failed",
                str(exc),
            )
            return
        message = (
            f"Support ZIP သိမ်းပြီးပြီ: {path}"
            if self._language == "my"
            else f"Support ZIP saved: {path}"
        )
        self.help_page.set_support_result(message)
        self.diagnostics.info("Support", f"Support package created: {path.name}")
        QMessageBox.information(self, "Support package", message)

    def _apply_wizard_responsive(self) -> None:
        super()._apply_wizard_responsive()
        if not hasattr(self, "_wizard_firmware_row"):
            return
        narrow = self.setup_wizard.width() < 760
        direction = (
            QBoxLayout.Direction.TopToBottom
            if narrow
            else QBoxLayout.Direction.LeftToRight
        )
        if self._wizard_firmware_row is not None:
            self._wizard_firmware_row.setDirection(direction)
        if self._wizard_flash_row is not None:
            self._wizard_flash_row.setDirection(direction)
