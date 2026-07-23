# Desktop Application

The desktop application combines one or more USB flight controls, calibrates each device and streams final safe RC channels to an ESP32-S3 or Arduino bridge.

## Ready-to-use first run

Version 0.8 introduces a product-facing setup assistant. A new user can follow this flow without editing Python files or manually constructing serial commands:

```text
Connect flight controls
→ Detect the adapter
→ Install Arduino firmware
→ Calibrate each device
→ Map AETR
→ Verify strict failsafe
→ READY TO USE
```

The Dashboard always shows one clear state:

- **READY TO USE** — physical controls, calibration, AETR mapping, adapter and strict failsafe are ready.
- **SETUP REQUIRED** — the next required action is shown with a button that opens the correct page.

The setup assistant can be reopened from the Dashboard at any time.

## Windows packaged application

The packaged Windows x64 build includes:

- the complete PySide6 desktop application and Python runtime
- the application icon and Qt/pygame dependencies
- precompiled Arduino UNO/Nano and Mega bridge firmware
- a bundled firmware flashing tool used by the setup assistant
- the original Arduino sketches for advanced/manual installation

Python and Arduino IDE are not required for normal end-user setup. The user must still select the correct board and COM port before flashing. The application asks for confirmation because firmware installation replaces the sketch currently stored on the selected board.

## Requirements

- Windows 10 or newer
- A USB flight stick, throttle, pedals or other Windows game controller
- Arduino UNO/Nano, Mega 2560 or a supported ESP32-S3 adapter for physical trainer output
- A FlySky transmitter with a compatible trainer input

Python 3.10–3.13 is needed only when running from source.

## Install and run from source

From the repository's `desktop` directory:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main
```

The command prompt must show that the current directory ends in `simulator-joystick-to-flysky\desktop`.

A source/development run may not include the bundled `avrdude` and precompiled HEX files. In that case the setup assistant explains that the packaged Windows build or Arduino IDE is required for firmware installation.

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

## One-click Arduino firmware installation

The setup assistant supports these targets:

```text
Arduino UNO / compatible ATmega328P        115200 baud, PPM D9
Arduino Nano — new bootloader              115200 baud, PPM D9
Arduino Nano — old bootloader               57600 baud, PPM D9
Arduino Mega 2560 / compatible ATmega2560  115200 baud, PPM D11
```

The Windows release compiles the firmware from the repository source during GitHub Actions, then bundles the generated HEX files and the Arduino AVR `avrdude` package. The app invokes the tool directly without a command shell and never guesses a blank board model silently.

Before flashing:

1. Remove aircraft and motor power.
2. Close Arduino Serial Monitor and any program using the COM port.
3. Select the exact board/bootloader and COM port.
4. Keep the USB cable connected until the installation finishes.
5. Wait for the app to reconnect and identify the board.

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

## Test without hardware

1. Enable the Demo Flight Joystick under **Settings**.
2. Open **Joystick Monitor** to see animated input.
3. Open **Calibration** and exercise the workflow.
4. Open **Channel Mapping** and test role binding, Device/Input selection, Learn Input and Auto-map AETR.
5. Open **Profiles** to create, duplicate, activate, import and export profiles.
6. Open **Adapter / Firmware** and click **Test simulator**.
7. Run the guided failsafe test with aircraft power disconnected.
8. Open **Diagnostics** to inspect protocol and transport statistics.

The readiness Dashboard intentionally does not treat the demo joystick or software simulator as physical flight-ready hardware.

## Arduino bridge source

UNO/Nano sketch:

```text
firmware/arduino-uno/simjoy_arduino_bridge/simjoy_arduino_bridge.ino
```

Mega 2560 sketch:

```text
firmware/arduino-mega/simjoy_mega_bridge/simjoy_mega_bridge.ino
```

Arduino receives final channel values. Calibration, role binding, mapping and profiles remain on the PC.

## Physical joystick support

The app uses SDL DirectInput as the primary Windows backend and WinMM as a legacy fallback. It supports many modern and older flight sticks, throttles, gamepads, wheels and RC simulator controllers that appear in Windows Game Controllers.

## Data and privacy

No account is required. Joystick input, profiles, calibration and settings remain local under:

```text
%USERPROFILE%\.simulator-joystick-to-flysky\
```

Files:

- `settings.json`
- `profiles.json`
- `calibrations.json`

The application does not upload joystick values or profiles. Diagnostics are exported only when the user explicitly chooses to create a report.

## Tests

```bat
pip install -r requirements-dev.txt
python -m pytest -q
```

GitHub Actions runs the desktop test suite on Python 3.10 and 3.12. The suite includes UI smoke tests, readiness decisions, firmware command generation, device-axis mapping, protocol framing, multi-device channel mapping and simulated communication failsafe behavior.

## Build a Windows application

```bat
build_windows.bat
```

The executable is created under:

```text
dist\SimulatorJoystickToFlySky\
```

Keep the complete folder together. The one-click firmware feature is included in official GitHub Windows builds; local builds also require Arduino CLI and the Arduino AVR core/tool package to prepare firmware installer assets.
