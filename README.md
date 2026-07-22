# Simulator Joystick to FlySky

Open-source hardware and software for combining USB simulator controls and using them as a student/trainer control source for a FlySky transmitter.

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

### Arduino desktop bridges

```text
USB flight stick ─┐
                  ├─ Windows desktop application ─ USB serial ─ Arduino ─ PPM ─► FlySky trainer port
USB throttle ─────┘
```

Supported bridge boards:

- Arduino UNO/Nano: 8 channels, PPM on D9
- Arduino Mega 2560: up to 12 channels, PPM on D11

The Arduino paths require the desktop application to remain running. The PC performs multi-device detection, role binding, calibration and channel mapping; the Arduino receives final safe RC pulse values.

## Current MVP

### Desktop application

- Generic SDL DirectInput and Windows legacy joystick discovery
- Multiple simultaneously connected USB controllers
- Logical device roles: Primary Stick, Throttle Unit, Rudder Pedals and Auxiliary Controller
- Exact GUID binding or automatic role detection
- Per-device, per-GUID calibration
- Cross-device Learn Input and AETR auto-mapping
- Strict grouped AETR failsafe when any primary control source disappears
- 4–16 channel mapping with endpoints, reverse, trim, expo and smoothing
- Profile create, duplicate, import, export, activate and persistence
- Versioned CRC-protected desktop/device protocol
- Real serial connection and built-in ESP32-S3 simulator
- Diagnostics export and Windows executable build script

### ESP32-S3 firmware

- ESP-IDF USB Host HID driver integration
- Generic HID report descriptor parser for axes, buttons and hats
- Standalone channel mapping and NVS profile storage
- RMT-based configurable PPM output
- UART desktop protocol for profile upload, status and diagnostics
- Input timeout and per-channel failsafe behavior

### Arduino UNO/Nano firmware

- Timer1-generated PPM on D9
- Up to 8 streamed channels
- Shared `SJ` CRC16 protocol at 115200 baud
- 700 ms communication timeout, CH3 low-throttle failsafe and AVR watchdog

### Arduino Mega 2560 firmware

- Timer1-generated PPM on D11
- Up to 12 streamed channels
- 22.5 ms frame for up to 8 channels and 30 ms frame for 9–12 channels
- Larger AVR serial payload and status buffers
- Shared timeout, failsafe and watchdog behavior

## Desktop run

```bat
cd desktop
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main
```

For a separate Thrustmaster stick and throttle:

1. Open **Calibration**, select each USB device and calibrate it separately.
2. Open **Channel Mapping**.
3. Bind `Primary Stick` to the stick and `Throttle Unit` to the throttle.
4. Run **Auto-map AETR**.
5. Verify CH1 Roll, CH2 Pitch, CH3 Throttle and CH4 Yaw.
6. Save changes and confirm strict AETR failsafe before connecting the trainer port.

## Firmware upload

UNO/Nano sketch:

```text
firmware/arduino-uno/simjoy_arduino_bridge/simjoy_arduino_bridge.ino
```

Mega 2560 sketch:

```text
firmware/arduino-mega/simjoy_mega_bridge/simjoy_mega_bridge.ino
```

Select the Arduino COM port in the desktop application, use 115200 baud, and keep the application running while using an Arduino bridge.

## Safety

- Test first with no propeller or motor power.
- Confirm AETR order, endpoints, direction and throttle failsafe.
- Disconnect either the stick or throttle and verify grouped CH1–CH4 failsafe.
- Do not connect an unknown trainer-port voltage directly to a microcontroller GPIO.
- Use a common ground and an appropriate signal-conditioning or protection circuit.
- The adapter does not replace transmitter or receiver failsafe configuration.

See [desktop/README.md](desktop/README.md), [firmware/esp32-s3/README.md](firmware/esp32-s3/README.md), [firmware/arduino-uno/README.md](firmware/arduino-uno/README.md), [firmware/arduino-mega/README.md](firmware/arduino-mega/README.md), [hardware/README.md](hardware/README.md) and [docs/protocol.md](docs/protocol.md).
