from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QWidget

from ..services.calibration_service import CalibrationSession, CalibrationStore
from ..services.channel_mapping_service import ChannelMapper
from ..services.device_role_service import DeviceRoleResolver, ResolvedDeviceRoles
from ..services.diagnostics_service import DiagnosticsService
from ..services.joystick_service import JoystickInfo, JoystickService
from ..services.profile_service import ControllerProfile, ProfileCollection, ProfileStore
from ..services.protocol_service import MessageType
from ..services.serial_service import SerialService
from ..services.settings_service import SettingsStore
from .device_handlers import DeviceHandlersMixin
from .input_handlers import InputHandlersMixin
from .profile_handlers import ProfileHandlersMixin
from .pages import CalibrationPage, DashboardPage, DevicePage, DiagnosticsPage, JoystickPage, MappingPage, ProfilesPage, SettingsPage


class MainWindow(InputHandlersMixin, ProfileHandlersMixin, DeviceHandlersMixin, QMainWindow):
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
        self.joystick_service = JoystickService(demo_enabled=self.settings.demo_joystick_enabled)

        self._device_infos: dict[int, JoystickInfo] = {}
        self._selected_instance_id: int | None = None
        self._latest_states: dict[int, dict[str, Any]] = {}
        self._calibration_session: CalibrationSession | None = None
        self._current_channels: list[int] = []
        self._auto_connect_attempted = False
        self._selected_profile_id: str | None = self.profile_collection.active_profile_id
        self._adapter_kind = "disconnected"
        self._adapter_capabilities: set[str] = set()
        self._stream_paused_for_test = False
        self._failsafe_test_active = False
        self._failsafe_test_generation = 0
        self._failsafe_verify_after = 0.0

        self.dashboard_page = DashboardPage()
        self.joystick_page = JoystickPage()
        self.mapping_page = MappingPage()
        self.calibration_page = CalibrationPage()
        self.profiles_page = ProfilesPage()
        self.device_page = DevicePage()
        self.diagnostics_page = DiagnosticsPage()
        self.settings_page = SettingsPage()
        self.settings_page.set_settings(self.settings)

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

        self.channel_timer = QTimer(self)
        self.channel_timer.timeout.connect(self._channel_tick)
        self._apply_channel_rate()
        self.channel_timer.start()

        self.serial_service.start()
        self.joystick_service.start()
        self.diagnostics.info("Application", "Desktop application started")
        self.diagnostics.info("Demo", f"Demo joystick {'enabled' if self.settings.demo_joystick_enabled else 'disabled'}")

    def _wire_signals(self) -> None:
        self.joystick_service.devices_changed.connect(self._on_devices_changed)
        self.joystick_service.state_changed.connect(self._on_state_changed)
        self.joystick_service.backend_error.connect(lambda message: self._transport_error("Joystick", message))
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
        self.profiles_page.activate_requested.connect(self._activate_selected_profile)
        self.profiles_page.save_details_requested.connect(self._save_profile_details)
        self.profiles_page.import_requested.connect(self._import_profile)
        self.profiles_page.export_requested.connect(self._export_profile)

        self.device_page.refresh_requested.connect(self.serial_service.scan_ports)
        self.device_page.connect_requested.connect(self._connect_serial)
        self.device_page.simulator_requested.connect(self.serial_service.connect_simulator)
        self.device_page.disconnect_requested.connect(self.serial_service.disconnect)
        self.device_page.hello_requested.connect(self.serial_service.request_hello)
        self.device_page.status_requested.connect(lambda: self.serial_service.send(MessageType.STATUS, {}))
        self.device_page.upload_requested.connect(self._upload_active_profile)
        self.device_page.reboot_requested.connect(lambda: self.serial_service.send(MessageType.REBOOT, {}))
        self.device_page.bootloader_requested.connect(lambda: self.serial_service.send(MessageType.BOOTLOADER, {}))
        self.device_page.failsafe_test_requested.connect(self._start_failsafe_test)
        self.device_page.failsafe_abort_requested.connect(self._abort_failsafe_test)

        self.serial_service.ports_changed.connect(self._on_ports_changed)
        self.serial_service.connection_changed.connect(self._on_connection_changed)
        self.serial_service.message_received.connect(self._on_protocol_message)
        self.serial_service.transport_error.connect(lambda message: self._transport_error("Serial", message))
        self.serial_service.stats_changed.connect(self.diagnostics_page.set_stats)

        self.diagnostics.entry_added.connect(self.diagnostics_page.add_entry)
        self.diagnostics.cleared.connect(self.diagnostics_page.clear)
        self.diagnostics_page.clear_requested.connect(self.diagnostics.clear)
        self.diagnostics_page.export_requested.connect(self._export_diagnostics)
        self.settings_page.save_requested.connect(self._save_settings)

    def closeEvent(self, event: Any) -> None:
        self._stream_paused_for_test = False
        self._failsafe_test_active = False
        self.channel_timer.stop()
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
        return self.profile_store.find(self.profile_collection, self._selected_profile_id)

    def _selected_info(self) -> JoystickInfo | None:
        return self._device_infos.get(self._selected_instance_id)

    def _resolved_inputs(self, profile: ControllerProfile | None = None) -> ResolvedDeviceRoles:
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
            self._current_channels = [mapping.failsafe for mapping in active.mappings]
            self.dashboard_page.set_channels(self._current_channels)

    def _refresh_mapping_page(self) -> None:
        active = self._active_profile()
        self.mapping_preview_mapper.reset()
        self.mapping_page.set_profile(
            active,
            list(self._device_infos.values()),
            self._selected_instance_id,
        )
