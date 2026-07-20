# Simulator Joystick to FlySky

Universal USB simulator joystick adapter for the FlySky FS-i6/FS-i6X trainer port.

> Project status: early development. Hardware and firmware are not yet flight-tested as a complete standalone system.

## Goal

Build a plug-and-play adapter that lets a compatible USB simulator joystick control a FlySky transmitter through its trainer/student input.

```text
USB Simulator Joystick
        ↓
ESP32-S3 USB Host
        ↓
Calibration + Channel Mapping + Safety
        ↓
FlySky-compatible PPM
        ↓
FlySky Trainer/Student Port
```

The planned desktop application will configure, calibrate, diagnose, and update the adapter. The final adapter itself is intended to work without a PC after configuration.

## Planned features

- USB HID joystick detection
- PXN 2119 Pro support as the first tested device
- Configurable axis and button mapping
- Per-channel minimum, center, maximum, reverse, trim, expo, and dual rate
- Multiple aircraft profiles
- Live joystick and RC channel monitor
- Safe startup, disconnect failsafe, watchdog, and emergency disarm
- FlySky-compatible six-channel negative-polarity PPM output
- ESP32-S3 firmware update from the desktop application
- Windows desktop application first, with Linux and macOS considered later

## Repository structure

```text
.
├── desktop/              Desktop configuration application
├── firmware/esp32-s3/    Standalone ESP32-S3 firmware
├── hardware/             Wiring, schematic, PCB, and enclosure files
├── docs/                 Architecture, protocol, roadmap, and safety notes
├── examples/             Test data and reference examples
├── assets/               Images and project artwork
├── AGENTS.md             Development rules for AI coding agents
└── README.md
```

## Current validated information

The earlier Arduino/Python prototype confirmed the target FlySky trainer signal characteristics used by this project:

- Student-input trainer architecture
- Negative-polarity PPM
- Idle HIGH
- Approximately 400 µs LOW separator pulse
- Approximately 21 ms frame
- Six channels

These values must be verified again with the ESP32-S3 standalone hardware before any flight test.

## Development phases

1. **Foundation** — documentation, protocol, repository structure, and safety rules.
2. **Desktop MVP** — device discovery, joystick monitor, channel monitor, calibration, and profiles.
3. **ESP32-S3 MVP** — USB Host, HID parsing, configuration storage, and PPM generation.
4. **Integration** — desktop-to-device protocol, diagnostics, firmware update, and failsafe testing.
5. **Hardware** — protected USB power path, trainer connector, PCB, and enclosure.
6. **Flight validation** — bench test first, propeller removed, then controlled ground and flight tests.

## Safety warning

This project can command a real RC aircraft. Incorrect mapping, polarity, timing, power wiring, or failsafe behavior can cause injury or property damage.

- Never perform initial tests with a propeller installed.
- Keep the FlySky transmitter as the master controller.
- Verify every channel direction and endpoint before enabling trainer mode.
- Test joystick disconnect, ESP32 reset, power loss, and invalid configuration behavior.
- Do not fly until the complete signal path has passed repeatable bench tests.

## License

This project is released under the MIT License. See `LICENSE`.
