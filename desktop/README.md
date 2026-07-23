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
6. Select each RC channel and choose its **Device** and **Input** explicitly, or use **Learn Input**.
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

## Adapter & Hardware Test center

The **Adapter / Firmware** page is the final software-side check before connecting the FlySky trainer port.

It shows:

- detected board and firmware version
- COM transport and connection state
- Arduino UNO D9, Mega D11 or ESP32 PPM output information
- Desktop target values beside firmware-received values
- MATCH or pulse difference for CH1–CH8
- adapter status age and stream/failsafe state
- raw handshake, status, ACK and error payloads

### Guided communication failsafe test

1. Remove the propeller and disconnect motor/aircraft power.
2. Connect and identify the Arduino bridge, or use the built-in simulator first.
3. Confirm that normal Desktop and Adapter values match.
4. Tick the safety confirmation checkbox.
5. Click **Run failsafe test**.
6. The app pauses `LIVE_CHANNELS` beyond the firmware 700 ms timeout.
7. It requests firmware status and verifies:

```text
CH1 = 1500 µs
CH2 = 1500 µs
CH3 = 1000 µs
CH4 = 1500 µs
```

8. The normal live stream resumes automatically after PASS, FAIL, timeout or manual Abort.

A periodic status packet that arrives before the 700 ms deadline is ignored by the test state machine, preventing false results.

## Test without hardware

1. Start the app; Demo Flight Joystick is enabled by default.
2. Open **Joystick Monitor** to see animated input.
3. Open **Calibration** and exercise the workflow.
4. Open **Channel Mapping** and test role binding, explicit Device/Input selection, Learn Input and Auto-map AETR.
5. Open **Profiles** to create, duplicate, activate, import and export profiles.
6. Open **Adapter / Firmware** and click **Test simulator**.
7. Tick the safety confirmation and run the guided failsafe test. The simulator models the same 700 ms desktop-stream timeout.
8. Open **Diagnostics** to inspect protocol and transport statistics.

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
5. Click **Connect COM** and wait for the board reset/handshake.
6. Confirm Desktop and Adapter channel values match.
7. Run the guided communication failsafe test.
8. Keep the desktop application running while using an Arduino bridge.

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

GitHub Actions runs the desktop test suite on Python 3.10 and 3.12. The suite includes UI smoke tests, device-axis mapping, protocol framing, multi-device channel mapping and simulated communication failsafe behavior.

## Build a Windows executable

```bat
build_windows.bat
```

The executable is created under `dist\SimulatorJoystickToFlySky\`.
