# Desktop Application

The desktop application is the configuration, calibration and diagnostics tool for Simulator Joystick to FlySky. It also provides a complete no-hardware demo mode.

## Requirements

- Windows 10 or newer
- Python 3.10–3.13 (64-bit recommended)
- A physical joystick is optional

## Install and run

From the repository's `desktop` directory:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main
```

The command prompt must show that the current directory ends in `simulator-joystick-to-flysky\desktop` before running the commands.

## Test without hardware

1. Start the app. **Demo Flight Joystick** is enabled by default.
2. Open **Joystick Monitor** to see animated axes, buttons and hat input.
3. Open **Calibration** and exercise the full calibration workflow.
4. Open **Channel Mapping** to edit RC channels and see live `1000–2000 µs` output.
5. Open **Profiles** to create, duplicate, activate, import and export profiles.
6. Open **ESP32-S3 / Firmware** and click **Connect built-in simulator**.
7. Click **Handshake**, then **Upload active profile**.
8. Open **Diagnostics** to inspect protocol and transport statistics.

## Physical joystick support

The app uses pygame/SDL. It can enumerate many modern and older Windows joystick devices, including DirectInput-compatible flight sticks, gamepads, wheels and RC simulator controllers. A device must appear to Windows as a joystick/game controller. Proprietary devices that require a vendor-only protocol may need a future adapter backend.

## Data files

User configuration is stored under:

```text
%USERPROFILE%\.simulator-joystick-to-flysky\
```

Files include:

- `settings.json`
- `profiles.json`
- `calibrations.json`

## Tests

```bat
pip install -r requirements-dev.txt
pytest -q
```

## Build a Windows executable

```bat
build_windows.bat
```

The executable is created under `dist\SimulatorJoystickToFlySky\`.
