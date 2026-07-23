from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from ..icon_resources import asset_path


@dataclass(frozen=True)
class FirmwareTarget:
    target_id: str
    label: str
    board_family: str
    mcu: str
    programmer: str
    baud: int
    hex_filename: str
    ppm_pin: str


FIRMWARE_TARGETS: tuple[FirmwareTarget, ...] = (
    FirmwareTarget(
        "uno",
        "Arduino UNO / compatible ATmega328P",
        "Arduino UNO/Nano",
        "atmega328p",
        "arduino",
        115200,
        "simjoy-uno.hex",
        "D9",
    ),
    FirmwareTarget(
        "nano_new",
        "Arduino Nano ATmega328P — new bootloader",
        "Arduino UNO/Nano",
        "atmega328p",
        "arduino",
        115200,
        "simjoy-uno.hex",
        "D9",
    ),
    FirmwareTarget(
        "nano_old",
        "Arduino Nano ATmega328P — old bootloader",
        "Arduino UNO/Nano",
        "atmega328p",
        "arduino",
        57600,
        "simjoy-uno.hex",
        "D9",
    ),
    FirmwareTarget(
        "mega",
        "Arduino Mega 2560 / compatible ATmega2560",
        "Arduino Mega 2560",
        "atmega2560",
        "wiring",
        115200,
        "simjoy-mega.hex",
        "D11",
    ),
)


class FirmwareInstallerService(QObject):
    """Flash bundled, precompiled bridge firmware without requiring Arduino IDE."""

    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)
    running_changed = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._process: QProcess | None = None
        self._target: FirmwareTarget | None = None

    @staticmethod
    def targets() -> tuple[FirmwareTarget, ...]:
        return FIRMWARE_TARGETS

    @staticmethod
    def target(target_id: str) -> FirmwareTarget | None:
        return next((item for item in FIRMWARE_TARGETS if item.target_id == target_id), None)

    @staticmethod
    def _tool_paths() -> tuple[Path, Path]:
        root = asset_path("firmware/tools/avrdude")
        return root / "bin" / "avrdude.exe", root / "etc" / "avrdude.conf"

    @staticmethod
    def _hex_path(target: FirmwareTarget) -> Path:
        return asset_path(f"firmware/hex/{target.hex_filename}")

    @classmethod
    def installer_available(cls, target_id: str = "uno") -> bool:
        target = cls.target(target_id)
        if target is None:
            return False
        avrdude, config = cls._tool_paths()
        return avrdude.exists() and config.exists() and cls._hex_path(target).exists()

    @classmethod
    def missing_components(cls, target_id: str) -> list[str]:
        target = cls.target(target_id)
        if target is None:
            return ["unknown firmware target"]
        avrdude, config = cls._tool_paths()
        components = {
            "avrdude.exe": avrdude,
            "avrdude.conf": config,
            target.hex_filename: cls._hex_path(target),
        }
        return [name for name, path in components.items() if not path.exists()]

    @classmethod
    def command_for(cls, target_id: str, port: str) -> tuple[Path, list[str]]:
        target = cls.target(target_id)
        if target is None:
            raise ValueError(f"Unsupported firmware target: {target_id}")
        clean_port = port.strip()
        if not clean_port:
            raise ValueError("A serial port is required")
        avrdude, config = cls._tool_paths()
        hex_path = cls._hex_path(target)
        arguments = [
            "-C",
            str(config),
            "-p",
            target.mcu,
            "-c",
            target.programmer,
            "-P",
            clean_port,
            "-b",
            str(target.baud),
            "-D",
            "-U",
            f"flash:w:{hex_path}:i",
        ]
        return avrdude, arguments

    @property
    def running(self) -> bool:
        return self._process is not None

    def install(self, target_id: str, port: str) -> None:
        if self.running:
            self.failed.emit("Another firmware installation is already running.")
            return
        target = self.target(target_id)
        if target is None:
            self.failed.emit("Unsupported Arduino board selection.")
            return
        missing = self.missing_components(target_id)
        if missing:
            self.failed.emit(
                "This application build does not include the firmware installer components: "
                + ", ".join(missing)
            )
            return
        try:
            program, arguments = self.command_for(target_id, port)
        except ValueError as exc:
            self.failed.emit(str(exc))
            return

        process = QProcess(self)
        process.setProgram(str(program))
        process.setArguments(arguments)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read_output)
        process.errorOccurred.connect(self._process_error)
        process.finished.connect(self._process_finished)
        self._process = process
        self._target = target
        self.running_changed.emit(True)
        self.progress.emit(
            f"Preparing {target.label} firmware for {port}. Keep the USB cable connected."
        )
        process.start()

    def cancel(self) -> None:
        process = self._process
        if process is None:
            return
        process.kill()
        process.waitForFinished(1500)
        self._finish_cleanup()
        self.failed.emit("Firmware installation was cancelled.")

    def _read_output(self) -> None:
        process = self._process
        if process is None:
            return
        text = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in text.splitlines():
            clean = line.strip()
            if clean:
                self.progress.emit(clean)

    def _process_error(self, _error: QProcess.ProcessError) -> None:
        process = self._process
        if process is None:
            return
        if process.state() == QProcess.ProcessState.NotRunning:
            message = process.errorString() or "The firmware flashing process could not start."
            self._finish_cleanup()
            self.failed.emit(message)

    def _process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        target = self._target
        process = self._process
        if process is None:
            return
        remaining = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in remaining.splitlines():
            clean = line.strip()
            if clean:
                self.progress.emit(clean)
        label = target.label if target is not None else "Arduino"
        self._finish_cleanup()
        if exit_code == 0:
            self.completed.emit(
                f"Firmware installed successfully on {label}. The board will restart automatically."
            )
        else:
            self.failed.emit(
                f"Firmware installation failed with exit code {exit_code}. Check the selected board, COM port and USB cable."
            )

    def _finish_cleanup(self) -> None:
        process = self._process
        self._process = None
        self._target = None
        if process is not None:
            process.deleteLater()
        self.running_changed.emit(False)
