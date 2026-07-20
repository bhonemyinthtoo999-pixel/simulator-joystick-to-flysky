# System Architecture

## Product boundary

The product has two cooperating parts:

1. **Standalone adapter** — ESP32-S3 reads the USB joystick and generates the FlySky trainer signal.
2. **Desktop application** — configures profiles, calibrates controls, displays diagnostics, and updates firmware.

The adapter must continue operating after the desktop application is disconnected.

## Runtime data path

```text
USB HID Device
    ↓
USB Host and HID Parser
    ↓
Raw Input State
    ↓
Calibration and Normalization
    ↓
Axis/Button Mapping
    ↓
Dead Zone, Reverse, Trim, Expo, Dual Rate
    ↓
Safety and Failsafe
    ↓
RC Channel Values
    ↓
PPM Scheduler
    ↓
FlySky Trainer/Student Input
```

## Firmware modules

- `usb_host`: device enumeration, reconnect, and power-state reporting.
- `hid`: generic HID parsing plus device-specific descriptors when required.
- `input`: stable raw axis and button state.
- `calibration`: raw minimum, center, maximum, and noise limits.
- `mapping`: joystick controls to RC channels and actions.
- `processing`: dead zone, curves, trim, rates, and endpoint conversion.
- `safety`: startup checks, arming policy, range checks, disconnect failsafe, and watchdog.
- `profiles`: validated persistent configuration.
- `ppm`: deterministic FlySky-compatible output generation.
- `device_protocol`: communication with the desktop application.
- `diagnostics`: status, counters, timing, and fault reporting.

## Desktop modules

- Device discovery and connection
- Dashboard and diagnostics
- Live joystick monitor
- RC channel monitor
- Calibration wizard
- Channel mapping editor
- Profile manager
- Firmware updater
- Log export and troubleshooting

## Ownership rules

- FlySky remains the master transmitter.
- The adapter behaves as the student input.
- Firmware owns real-time joystick processing and PPM generation.
- Desktop software owns user interaction and configuration authoring.
- A disconnected desktop must not interrupt valid standalone operation.

## Initial technology choices

- Firmware target: ESP32-S3 with native USB Host/OTG support.
- Desktop MVP: Python 3 with PySide6.
- Configuration transport: versioned command/response protocol over USB serial initially.
- Persistent storage: validated profile data in ESP32 non-volatile storage.

All technology choices remain subject to prototype testing, but architecture and safety boundaries should remain stable.
