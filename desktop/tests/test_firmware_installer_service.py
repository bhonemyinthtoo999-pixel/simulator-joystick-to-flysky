from __future__ import annotations

from app.services.firmware_installer_service import FirmwareInstallerService


def test_uno_flash_command_uses_expected_protocol_and_baud() -> None:
    program, arguments = FirmwareInstallerService.command_for("uno", "COM10")

    assert program.name == "avrdude.exe"
    assert arguments[arguments.index("-p") + 1] == "atmega328p"
    assert arguments[arguments.index("-c") + 1] == "arduino"
    assert arguments[arguments.index("-P") + 1] == "COM10"
    assert arguments[arguments.index("-b") + 1] == "115200"
    assert any("simjoy-uno.hex" in argument for argument in arguments)


def test_old_nano_uses_legacy_bootloader_baud() -> None:
    _program, arguments = FirmwareInstallerService.command_for("nano_old", "COM7")

    assert arguments[arguments.index("-b") + 1] == "57600"


def test_mega_uses_wiring_programmer_and_mega_hex() -> None:
    _program, arguments = FirmwareInstallerService.command_for("mega", "COM4")

    assert arguments[arguments.index("-p") + 1] == "atmega2560"
    assert arguments[arguments.index("-c") + 1] == "wiring"
    assert any("simjoy-mega.hex" in argument for argument in arguments)
