# Simulator Joystick to FlySky

Open-source hardware and software for using a USB simulator joystick as a student/trainer control source for a FlySky transmitter.

## Hardware paths

### Standalone ESP32-S3 adapter

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

After a valid profile is saved, the ESP32-S3 path can operate without a PC.

### Arduino UNO/Nano desktop bridge

```text
USB simulator joystick
        ▼
Windows desktop application
        │ USB serial
        ▼
Arduino UNO/Nano ── PPM ──► FlySky trainer/student port
```

The Arduino path is a lower-cost bridge. The desktop application must remain running because an UNO/Nano is not acting as the USB joystick host.

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

### Arduino UNO/Nano bridge firmware

- No third-party Arduino libraries required
- Timer1-generated PPM on D9
- Up to 8 streamed channels
- Shared `SJ` CRC16 serial protocol at 115200 baud
- Startup and 700 ms communication-timeout failsafe
- CH3 low-throttle failsafe at 1000 µs and other channels at 1500 µs
- AVR watchdog protection
- Arduino CLI GitHub Actions compile check

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

## ESP32-S3 firmware build

```bash
cd firmware/esp32-s3
idf.py set-target esp32s3
idf.py build
idf.py -p COM_PORT flash monitor
```

## Arduino firmware upload

Open this sketch in Arduino IDE 2.x and upload it to an Arduino UNO or Nano:

```text
firmware/arduino-uno/simjoy_arduino_bridge/simjoy_arduino_bridge.ino
```

Then select the Arduino COM port in the desktop application, use 115200 baud, and keep the application running while using the controller.

Firmware compilation and desktop tests can be performed now. Real USB-host compatibility, PPM polarity, trainer-port wiring and flight behavior must be validated with the actual board, joystick and FlySky transmitter before use on an aircraft.

## Safety

- Test first with no propeller or motor power.
- Confirm channel order, endpoints, direction and throttle failsafe.
- Do not connect an unknown trainer-port voltage directly to a microcontroller GPIO.
- Use a common ground and an appropriate signal-conditioning or protection circuit.
- The adapter does not replace the transmitter or receiver failsafe configuration.

See [desktop/README.md](desktop/README.md), [firmware/esp32-s3/README.md](firmware/esp32-s3/README.md), [firmware/arduino-uno/README.md](firmware/arduino-uno/README.md), [hardware/README.md](hardware/README.md) and [docs/protocol.md](docs/protocol.md).
