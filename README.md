# Simulator Joystick to FlySky

Open-source hardware and software for using a USB simulator joystick as a student/trainer control source for a FlySky transmitter.

## Target architecture

```text
USB simulator joystick
        │ USB HID
        ▼
ESP32-S3 USB Host adapter ── PPM ──► FlySky trainer/student port
        ▲
        │ optional UART configuration and diagnostics
        ▼
Windows desktop application
```

The FlySky transmitter remains the radio link and retains its trainer switch, mixes, model settings and safety behavior.

## Current MVP

### Desktop application

- Generic SDL/DirectInput joystick discovery and hot-plug monitoring
- Built-in Demo Flight Joystick for testing with no hardware
- Live axes, buttons and hat-switch monitor
- Calibration capture and persistent per-GUID calibration
- 4–16 channel mapping with endpoints, reverse, trim, expo, smoothing and failsafe
- Profile create, duplicate, import, export, activate and persistence
- Versioned CRC-protected desktop/device protocol
- Real serial connection and built-in ESP32-S3 simulator
- Diagnostics export and Windows executable build script

### ESP32-S3 firmware

- ESP-IDF USB Host HID driver integration
- Generic HID report descriptor parser for axes, buttons and hats
- Standalone channel mapping and NVS profile storage
- RMT-based configurable PPM output
- UART desktop protocol for profile upload, status, diagnostics and bounded live-channel testing
- Input timeout and per-channel failsafe behavior

## Test now without a joystick

```bat
cd desktop
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main
```

Demo Controller is enabled by default. Open **ESP32-S3 / Firmware** and choose **Connect built-in simulator** to test the full desktop workflow without physical hardware.

## Firmware build

```bash
cd firmware/esp32-s3
idf.py set-target esp32s3
idf.py build
idf.py -p COM_PORT flash monitor
```

Firmware compilation and desktop tests can be performed now. Real USB-host compatibility, PPM polarity, trainer-port wiring and flight behavior must be validated with the actual ESP32-S3 board, joystick and FlySky transmitter before use on an aircraft.

## Safety

- Test first with no propeller or motor power.
- Confirm channel order, endpoints, direction and throttle failsafe.
- Do not connect an unknown trainer-port voltage directly to ESP32-S3 GPIO.
- Use a common ground and an appropriate signal-conditioning circuit.
- The adapter does not replace the transmitter or receiver failsafe configuration.

See [desktop/README.md](desktop/README.md), [firmware/esp32-s3/README.md](firmware/esp32-s3/README.md), [hardware/README.md](hardware/README.md) and [docs/protocol.md](docs/protocol.md).
