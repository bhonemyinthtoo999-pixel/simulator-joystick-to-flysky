# Roadmap

## v0.2 MVP — implemented in source

- Full desktop workflow with no-hardware demo
- Generic desktop joystick monitor and calibration
- Channel mapping and profiles
- Serial protocol and simulated ESP32-S3
- ESP32-S3 USB HID host foundation
- Generic HID descriptor parser
- RMT PPM output
- NVS profile persistence and failsafe
- Unit tests for protocol, profiles, calibration and mapping

## Hardware validation milestone

- Compile with selected ESP-IDF release
- Verify board USB host VBUS hardware
- Capture reports from PXN 2119 Pro and representative legacy joystick
- Confirm firmware field order against desktop/Windows field order
- Measure PPM timing and polarity
- Validate FS-i6/FS-i6X trainer behavior
- Test disconnect, brownout and malformed-profile failsafe paths

## Later enhancements

- Visual firmware-side HID field inspector
- Calibration upload and standalone calibration wizard
- Per-device HID quirk/plugin database
- Signed firmware releases and Windows installer
- Automated ESP-IDF CI build
- Hardware revision and enclosure design
