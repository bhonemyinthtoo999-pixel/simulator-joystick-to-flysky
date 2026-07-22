# Desktop Application

The desktop application combines one or more USB flight controls, calibrates each device and streams final safe RC channels to an ESP32-S3 or Arduino bridge.

## Requirements

- Windows 10 or newer
- Python 3.10–3.13, 64-bit recommended
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

The command prompt must show that the current directory ends in `simulator-joystick-to-flysky\desktop`.

## Separate stick and throttle

The application can combine independent USB devices into one AETR output:

```text
Primary Stick  → CH1 Roll, CH2 Pitch, CH4 Yaw
Throttle Unit  → CH3 Throttle
```

Recommended setup:

1. Open **Joystick Monitor** and confirm both devices appear.
2. Select the stick, open **Calibration**, move all stick axes through their full range, capture neutral and save.
3. Select the separate throttle, repeat calibration and save it under the throttle GUID.
4. Open **Channel Mapping**.
5. Bind `Primary Stick` to the stick and `Throttle Unit` to the separate throttle.
6. Leave Pedals and Auxiliary on Auto-detect unless those devices are present.
7. Run **Auto-map AETR** and follow Roll, Pitch, Throttle and Yaw prompts.
8. Verify channel direction and endpoints, then save changes.
9. Disconnect either required device and confirm strict AETR failsafe sets CH1–CH4 to safe values.

Role bindings are stored in the active profile by device GUID, while calibration is stored independently for every device GUID.

## Device roles

- **Primary Stick** — roll, pitch, twist/rudder and stick buttons
- **Throttle Unit** — separate throttle quadrant or TWCS-style controller
- **Rudder Pedals** — optional pedals
- **Auxiliary Controller** — button box, second joystick or other panel

Each channel stores both a device role and an axis/button/hat index. This allows Axis 0 on the stick and Axis 0 on the throttle to be used at the same time without conflict.

## Strict AETR failsafe

When enabled, CH1–CH4 are treated as one safety group. If any configured AETR source is missing or invalid:

- CH1 Roll → profile failsafe, normally 1500 µs
- CH2 Pitch → profile failsafe, normally 1500 µs
- CH3 Throttle → profile failsafe, normally 1000 µs
- CH4 Yaw → profile failsafe, normally 1500 µs

Auxiliary channels continue to use their own source/failsafe settings. The Arduino firmware also applies its independent 700 ms serial timeout.

## Test without hardware

1. Start the app; Demo Flight Joystick is enabled by default.
2. Open **Joystick Monitor** to see animated input.
3. Open **Calibration** and exercise the workflow.
4. Open **Channel Mapping** and test role binding, Learn Input and Auto-map AETR.
5. Open **Profiles** to create, duplicate, activate, import and export profiles.
6. Open **Adapter / Firmware** and click **Connect ESP32 simulator**.
7. Open **Diagnostics** to inspect protocol and transport statistics.

## Arduino bridges

UNO/Nano sketch:

```text
firmware/arduino-uno/simjoy_arduino_bridge/simjoy_arduino_bridge.ino
```

Mega 2560 sketch:

```text
firmware/arduino-mega/simjoy_mega_bridge/simjoy_mega_bridge.ino
```

For either board:

1. Upload the appropriate sketch with Arduino IDE.
2. Close Serial Monitor.
3. Open **Adapter / Firmware**.
4. Select the Arduino COM port and `115200` baud.
5. Click **Connect serial** and wait for the board reset/handshake.
6. Keep the desktop application running.

Arduino receives final `LIVE_CHANNELS` values. Calibration, role binding, mapping and profiles remain on the PC.

## Physical joystick support

The app uses SDL DirectInput as the primary Windows backend and WinMM as a legacy fallback. It supports many modern and older flight sticks, throttles, gamepads, wheels and RC simulator controllers that appear in Windows Game Controllers.

## Data files

User configuration is stored under:

```text
%USERPROFILE%\.simulator-joystick-to-flysky\
```

- `settings.json`
- `profiles.json`
- `calibrations.json`

## Tests

```bat
pip install -r requirements-dev.txt
python -m pytest -q
```

## Build a Windows executable

```bat
build_windows.bat
```

The executable is created under `dist\SimulatorJoystickToFlySky\`.
