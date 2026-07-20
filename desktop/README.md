# Desktop Application

The desktop application will configure and diagnose the standalone adapter.

## Planned stack

- Python 3
- PySide6 / Qt
- `hidapi` or an equivalent joystick discovery layer
- `pyserial` for the initial ESP32-S3 configuration transport
- `pytest` for tests
- PyInstaller for the first Windows package

## MVP screens

- Dashboard
- Joystick monitor
- RC channel monitor
- Calibration wizard
- Channel mapping
- Profiles
- Firmware and diagnostics

The desktop application must never be required for normal standalone joystick-to-FlySky operation after a valid profile has been saved to the adapter.
