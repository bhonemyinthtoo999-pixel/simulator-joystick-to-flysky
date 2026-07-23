from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from ..services.calibration_service import CalibrationSession, CalibrationStore
from ..services.channel_mapping_service import ChannelMapper
from ..services.device_role_service import DeviceRoleResolver, ResolvedDeviceRoles
from ..services.diagnostics_service import DiagnosticsService
from ..services.firmware_installer_service import FirmwareInstallerService
from ..services.joystick_service import JoystickInfo, JoystickService
from ..services.profile_service import (
    ControllerProfile,
    ProfileCollection,
    ProfileStore,
)
from ..services.protocol_service import MessageType
from ..services.serial_service import SerialService
from ..services.settings_service import SettingsStore
from .adapter_command_handlers import AdapterCommandHandlersMixin
from .device_handlers import DeviceHandlersMixin
from .input_handlers import InputHandlersMixin
from .product_setup_handlers import ProductSetupHandlersMixin
from .profile_handlers import ProfileHandlersMixin
from .pages import (
    CalibrationPage,
    DashboardPage,
    DevicePage,
    DiagnosticsPage,
    JoystickPage,
    MappingPage,
    ProfilesPage,
    SettingsPage,
)
from .setup_wizard import SetupWizard


class MainWindow(
    InputHandlersMixin,
    ProfileHandlersMixin,
    ProductSetupHandlersMixin,
    AdapterCommandHandlersMixin,
    DeviceHandlersMixin,
    QMainWindow,
):
    """Main application coordinator with service-backed UI pages."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulator Joystick to FlySky")
        self.resize(1380, 880)

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.calibration_store = CalibrationStore()
        self.calibrations = self.calibration_store.load()
        self.profile_store = ProfileStore()
        self.profile_collection: ProfileCollection = self.profile_store.load()
        self.channel_mapper = ChannelMapper()
        self.mapping_preview_mapper = ChannelMapper()
        self.device_role_resolver = DeviceRoleResolver()
        self.diagnostics = DiagnosticsService()
        self.serial_service = SerialService(self.settings.serial_baud)
        self.joystick_service = JoystickService(
            poll_interval_ms=5 if self.settings.low_latency_mode else 20,
            demo_enabled=self.settings.demo_joystick_enabled,
        )
        self.firmware_installer = FirmwareInstallerService()

        self._device_infos: dict[int, JoystickInfo] = {}
        self._selected_instance_id: int | None = None
        self._latest_states: dict[int, dict[str, Any]] = {}
        self._calibration_session: CalibrationSession | None = None
        self._current_channels: list[int] = []
        self._last_sent_channels: list[int] = []
        self._last_realtime_send_at = 0.0
        self._last_input_ui_at = 0.0
        self._auto_connect_attempted = False
        self._selected_profile_id: str | None = (
            self.profile_collection.active_profile_id
        )
        self._adapter_kind = "disconnected"
        self._adapter_capabilities: set[str] = set()
        self._adapter_connection_label = ""
        self._adapter_probe_active = False
        self._adapter_probe_generation = 0
        self._adapter_probe_ports: list[str] = []
        self._adapter_probe_current = ""
        self._adapter_probe_signature: tuple[str, ...] | None = None
        self._stream_paused_for_test = False
        self._stream_paused_for_command = False
        self._failsafe_test_active = False
        self._failsafe_test_generation = 0
        self._failsafe_verify_after = 0.0
        self._status_request_generation = 0
        self._status_request_pending = False
        self._status_request_retry = 0
        self._identify_pending = False
        self._reboot_pending = False
        self._initial_status_scheduled = False
        self._serial_ports: list[dict[str, Any]] = []
        self._readiness_report = None
        self._firmware_install_port = ""
        self._firmware_install_target = ""

        self.dashboard_page = DashboardPage()
        self.joystick_page = JoystickPage()
        self.mapping_page = MappingPage()
        self.calibration_page = CalibrationPage()
        self.profiles_page = ProfilesPage()
        self.device_page = DevicePage()
        self.diagnostics_page = DiagnosticsPage()
        self.settings_page = SettingsPage()
        self.settings_page.set_settings(self.settings)
        self.setup_wizard = SetupWizard(self)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(230)
        for title in (
            "Dashboard",
            "Joystick Monitor",
            "Channel Mapping",
            "Calibration",
            "Profiles",
            "Adapter / Firmware",
            "Diagnostics",
            "Settings",
        ):
            QListWidgetItem(title, self.navigation)
        self.pages = QStackedWidget()
        for page in (
            self.dashboard_page,
            self.joystick_page,
            self.mapping_page,
            self.calibration_page,
            self.profiles_page,
            self.device_page,
            self.diagnostics_page,
            self.settings_page,
        ):
            self.pages.addWidget(page)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        root_layout.addWidget(self.navigation)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

        self._wire_signals()
        self._refresh_profiles()

        # This timer is intentionally UI-only. Realtime mapping and serial output
        # are driven by fresh joystick snapshots in InputHandlersMixin.
        self.channel_timer = QTimer(self)
        self.channel_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.channel_timer.timeout.connect(self._channel_tick)
        self._apply_channel_rate()
        self.channel_timer.start()

        self.readiness_timer = QTimer(self)
        self.readiness_timer.setInterval(500)
        self.readiness_timer.timeout.connect(self._refresh_readiness)
        self.readiness_timer.start()

        self.serial_service.start()
        self.joystick_service.start()
        self.diagnostics.info("Application", "Desktop application started")
        self.diagnostics.info(
            "Realtime",
            (
                f"Low-latency mode active: {self.settings.realtime_rate_hz} Hz output limit"
                if self.settings.low_latency_mode
                else f"Standard output mode: {self.settings.realtime_rate_hz} Hz limit"
            ),
        )
        self.diagnostics.info(
            "Demo",
            "Demo joystick "
            f"{'enabled' if self.settings.demo_joystick_enabled else 'disabled'}",
        )
        QTimer.singleShot(250, self._refresh_readiness)
        if (
            not self.settings.setup_completed
            or self.settings.setup_revision < self.SETUP_REVISION
        ):
            QTimer.singleShot(900, self._open_setup_wizard)

    def _wire_signals(self) -> None:
        self.joystick_service.devices_changed.connect(self._on_devices_changed)
        self.joystick_service.state_changed.connect(self._on_state_changed)
        self.joystick_service.backend_error.connect(
            lambda message: self._transport_error("Joystick", message)
        )
        self.joystick_page.device_selected.connect(self._select_device)

        self.calibration_page.start_requested.connect(self._start_calibration)
        self.calibration_page.center_requested.connect(self._capture_center)
        self.calibration_page.save_requested.connect(self._save_calibration)
        self.calibration_page.reset_requested.connect(self._reset_calibration)

        self.mapping_page.apply_requested.connect(self._save_mappings)
        self.mapping_page.reset_requested.connect(self._reset_mappings)

        self.profiles_page.profile_selected.connect(self._profile_selected)
        self.profiles_page.create_requested.connect(self._create_profile)
        self.profiles_page.duplicate_requested.connect(self._duplicate_profile)
        self.profiles_page.delete_requested.connect(self._delete_profile)
        self.profiles_page.activate_requested.connect(
            self._activate_selected_profile
        )
        self.profiles_page.save_details_requested.connect(
            self._save_profile_details
        )
        self.profiles_page.import_requested.connect(self._import_profile)
        self.profiles_page.export_requested.connect(self._export_profile)

        self.device_page.refresh_requested.connect(self._refresh_adapter_ports)
        self.device_page.connect_requested.connect(self._connect_serial)
        self.device_page.simulator_requested.connect(self._connect_simulator)
        self.device_page.disconnect_requested.connect(self._disconnect_and_rescan)
        self.device_page.hello_requested.connect(self._identify_adapter)
        self.device_page.status_requested.connect(self._request_adapter_status)
        self.device_page.upload_requested.connect(self._upload_active_profile)
        self.device_page.reboot_requested.connect(self._reboot_adapter)
        self.device_page.bootloader_requested.connect(
            lambda: self.serial_service.send(MessageType.BOOTLOADER, {})
        )
        self.device_page.failsafe_test_requested.connect(
            self._start_failsafe_test
        )
        self.device_page.failsafe_abort_requested.connect(
            self._abort_failsafe_test
        )

        self.serial_service.ports_changed.connect(self._on_ports_changed)
        self.serial_service.connection_changed.connect(
            self._on_connection_changed
        )
        self.serial_service.message_received.connect(self._on_protocol_message)
        self.serial_service.transport_error.connect(
            lambda message: self._transport_error("Serial", message)
        )
        self.serial_service.stats_changed.connect(
            self.diagnostics_page.set_stats
        )

        self.dashboard_page.setup_requested.connect(self._open_setup_wizard)
        self.dashboard_page.action_requested.connect(
            self._navigate_to_product_page
        )
        self.setup_wizard.action_requested.connect(
            self._navigate_to_product_page
        )
        self.setup_wizard.finish_requested.connect(self._finish_product_setup)
        self.setup_wizard.firmware_install_requested.connect(
            self._install_bundled_firmware
        )
        self.setup_wizard.firmware_cancel_requested.connect(
            self.firmware_installer.cancel
        )
        self.setup_wizard.ports_refresh_requested.connect(
            self.serial_service.force_scan_ports
        )
        self.firmware_installer.progress.connect(self._firmware_progress)
        self.firmware_installer.completed.connect(
            self._firmware_install_completed
        )
        self.firmware_installer.failed.connect(self._firmware_install_failed)
        self.firmware_installer.running_changed.connect(
            self._firmware_running_changed
        )

        self.diagnostics.entry_added.connect(
            self.diagnostics_page.add_entry
        )
        self.diagnostics.cleared.connect(self.diagnostics_page.clear)
        self.diagnostics_page.clear_requested.connect(
            self.diagnostics.clear
        )
        self.diagnostics_page.export_requested.connect(
            self._export_diagnostics
        )
        self.settings_page.save_requested.connect(self._save_settings)

    def _connect_simulator(self) -> None:
        """Allow simulator testing, but give physical hardware priority."""

        super()._connect_simulator()
        if self.settings.auto_detect_adapter:
            QTimer.singleShot(250, self.serial_service.force_scan_ports)

    def _on_ports_changed(self, ports: list[dict[str, Any]]) -> None:
        """Replace a simulator session when a physical adapter is available."""

        self._serial_ports = list(ports)
        self.setup_wizard.set_ports(ports, self.settings.last_port)

        if self.serial_service.simulated and self.settings.auto_detect_adapter:
            candidates = self._adapter_port_candidates(ports)
            if candidates:
                self._adapter_probe_signature = tuple(
                    str(item.get("device", "")) for item in ports
                )
                self._adapter_probe_generation += 1
                generation = self._adapter_probe_generation
                self._adapter_probe_ports = candidates
                self._adapter_probe_current = ""
                self._adapter_probe_active = True
                self.dashboard_page.set_adapter_state(
                    "serial_unknown",
                    connection="Physical adapter found; leaving test simulator",
                )
                self.diagnostics.info(
                    "Adapter auto-detect",
                    "Physical serial adapter detected while the simulator was active; switching to hardware",
                )
                self.serial_service.disconnect()
                QTimer.singleShot(
                    120,
                    lambda token=generation: self._probe_next_adapter(token),
                )
                return

        super()._on_ports_changed(ports)

    def _refresh_adapter_ports(self) -> None:
        self._adapter_probe_signature = None
        self.serial_service.force_scan_ports()

    def _disconnect_and_rescan(self) -> None:
        self._disconnect_serial()
        self._adapter_probe_signature = None
        if self.settings.auto_detect_adapter:
            QTimer.singleShot(120, self.serial_service.force_scan_ports)

    def closeEvent(self, event: Any) -> None:
        self._cancel_adapter_probe()
        self._stream_paused_for_test = False
        self._stream_paused_for_command = False
        self._failsafe_test_active = False
        self._status_request_pending = False
        if self.firmware_installer.running:
            self.firmware_installer.cancel()
        self.channel_timer.stop()
        self.readiness_timer.stop()
        self.joystick_service.stop()
        self.serial_service.stop()
        try:
            self.profile_store.save(self.profile_collection)
            self.settings_store.save(self.settings)
        except OSError:
            pass
        super().closeEvent(event)

    def _active_profile(self) -> ControllerProfile:
        return self.profile_store.active(self.profile_collection)

    def _selected_profile(self) -> ControllerProfile | None:
        return self.profile_store.find(
            self.profile_collection,
            self._selected_profile_id,
        )

    def _selected_info(self) -> JoystickInfo | None:
        return self._device_infos.get(self._selected_instance_id)

    def _resolved_inputs(
        self,
        profile: ControllerProfile | None = None,
    ) -> ResolvedDeviceRoles:
        active = profile or self._active_profile()
        return self.device_role_resolver.resolve(
            active.device_bindings,
            list(self._device_infos.values()),
            self._latest_states,
            self._selected_instance_id,
        )

    def _refresh_profiles(self) -> None:
        active = self._active_profile()
        self.dashboard_page.profile_value.setText(active.name)
        self.profiles_page.set_profiles(
            self.profile_collection.profiles,
            self.profile_collection.active_profile_id,
            self._selected_profile_id,
        )
        self._refresh_mapping_page()
        if len(self._current_channels) != active.channel_count:
            self._current_channels = [
                mapping.failsafe
                for mapping in active.mappings
            ]
            self.dashboard_page.set_channels(self._current_channels)
        if hasattr(self, "setup_wizard"):
            QTimer.singleShot(0, self._refresh_readiness)

    def _refresh_mapping_page(self) -> None:
        active = self._active_profile()
        self.mapping_preview_mapper.reset()
        self.mapping_page.set_profile(
            active,
            list(self._device_infos.values()),
            self._selected_instance_id,
        )
