from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from ..services.firmware_installer_service import FirmwareInstallerService
from ..services.readiness_service import ReadinessService


class ProductSetupHandlersMixin:
    SETUP_REVISION = 1

    def _refresh_readiness(self) -> None:
        active = self._active_profile()
        resolved = self._resolved_inputs(active)
        report = ReadinessService.assess(
            profile=active,
            devices=list(self._device_infos.values()),
            resolved=resolved,
            calibrations=self.calibrations,
            adapter_kind=self._adapter_kind,
            serial_connected=self.serial_service.connected,
            strict_failsafe_active=self.channel_mapper.last_strict_failsafe,
            adapter_capabilities=set(self._adapter_capabilities),
        )
        self._readiness_report = report
        self.dashboard_page.set_readiness(report)
        self.setup_wizard.set_report(report)

        target_hint = ""
        if self._adapter_kind == "arduino_uno":
            target_hint = "uno"
        elif self._adapter_kind == "arduino_mega":
            target_hint = "mega"
        board = self.dashboard_page.device_value.text()
        connection = getattr(self, "_adapter_connection_label", "")
        self.setup_wizard.set_adapter_summary(
            f"{board}\n{connection}".strip(),
            target_hint,
        )

        installer_available = any(
            FirmwareInstallerService.installer_available(target.target_id)
            for target in FirmwareInstallerService.targets()
        )
        if installer_available:
            self.setup_wizard.set_firmware_install_available(True)
        else:
            self.setup_wizard.set_firmware_install_available(
                False,
                "Firmware installer files are not included in this development run. Use the packaged Windows build or Arduino IDE.",
            )

    def _open_setup_wizard(self, page: int = 0) -> None:
        self.setup_wizard.set_ports(
            getattr(self, "_serial_ports", []),
            self.settings.last_port,
        )
        self._refresh_readiness()
        self.setup_wizard.show_page(page)

    def _navigate_to_product_page(self, page_name: str) -> None:
        for index in range(self.navigation.count()):
            item = self.navigation.item(index)
            if item and item.text() == page_name:
                self.navigation.setCurrentRow(index)
                self.showNormal()
                self.raise_()
                self.activateWindow()
                return
        if page_name == "Setup":
            self._open_setup_wizard()

    def _finish_product_setup(self) -> None:
        report = getattr(self, "_readiness_report", None)
        if report is None or not report.ready:
            QMessageBox.information(
                self,
                "Setup is not complete",
                "Complete the remaining setup checklist before marking the application ready.",
            )
            self._refresh_readiness()
            return
        self.settings.setup_completed = True
        self.settings.setup_revision = self.SETUP_REVISION
        try:
            self.settings_store.save(self.settings)
        except OSError as exc:
            QMessageBox.critical(self, "Could not save setup", str(exc))
            return
        self.setup_wizard.hide()
        self.navigation.setCurrentRow(0)
        self.diagnostics.info("Setup", "First-run setup completed")

    def _install_bundled_firmware(self, target_id: str, port: str) -> None:
        target = FirmwareInstallerService.target(target_id)
        if target is None:
            QMessageBox.warning(self, "Invalid board", "Select a supported Arduino board.")
            return
        if not port:
            QMessageBox.warning(self, "COM port required", "Select the Arduino COM port.")
            return
        answer = QMessageBox.question(
            self,
            "Install Arduino firmware",
            f"Install the tested bridge firmware on:\n\n{target.label}\nPort: {port}\nPPM output: {target.ppm_pin}\n\n"
            "This replaces the sketch currently stored on that board. Continue only if the selected board and port are correct.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._firmware_install_port = port
        self._firmware_install_target = target_id
        self._stream_paused_for_command = True
        self._cancel_adapter_probe()
        if self.serial_service.connected:
            self.serial_service.disconnect()
        self.setup_wizard.set_firmware_running(True)
        self.setup_wizard.append_firmware_message(
            f"Releasing {port} and preparing the bundled firmware installer…"
        )
        QTimer.singleShot(
            350,
            lambda: self.firmware_installer.install(target_id, port),
        )

    def _firmware_progress(self, message: str) -> None:
        self.setup_wizard.append_firmware_message(message)
        self.diagnostics.info("Firmware installer", message)

    def _firmware_install_completed(self, message: str) -> None:
        self._stream_paused_for_command = False
        self.setup_wizard.firmware_finished(True, message)
        self.settings.last_port = getattr(self, "_firmware_install_port", "")
        try:
            self.settings_store.save(self.settings)
        except OSError:
            pass
        self.diagnostics.info("Firmware installer", message)
        self._adapter_probe_signature = None
        QTimer.singleShot(1400, self.serial_service.force_scan_ports)
        QTimer.singleShot(2400, self._refresh_readiness)

    def _firmware_install_failed(self, message: str) -> None:
        self._stream_paused_for_command = False
        self.setup_wizard.firmware_finished(False, message)
        self.diagnostics.error("Firmware installer", message)
        self._adapter_probe_signature = None
        QTimer.singleShot(400, self.serial_service.force_scan_ports)

    def _firmware_running_changed(self, running: bool) -> None:
        self.setup_wizard.set_firmware_running(running)
