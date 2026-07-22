# Arduino UNO/Nano D9 Bridge Firmware

This firmware is the ATmega328P desktop bridge for the multi-device AETR system:

```text
Thrustmaster stick USB ─┐
                        ├─ Windows desktop app ─ USB serial ─ Arduino UNO/Nano ─ D9 PPM ─ FlySky trainer port
Separate throttle USB ──┘
```

The desktop application detects both USB devices, binds their roles, calibrates each GUID, combines them into AETR channels and applies strict AETR failsafe. The UNO receives only final RC pulse values and generates the PPM signal on digital pin 9.

The UNO/Nano is not a USB host. The Windows desktop application must remain running.

## Supported boards

- Arduino UNO R3, ATmega328P
- Arduino Nano, ATmega328P

Sketch path:

```text
firmware/arduino-uno/simjoy_arduino_bridge/simjoy_arduino_bridge.ino
```

No third-party Arduino library is required.

## D9 configuration

The firmware source contains:

```cpp
constexpr uint8_t PPM_OUTPUT_PIN = 9;
constexpr uint8_t MAX_CHANNELS = 8;
constexpr uint8_t DEFAULT_CHANNEL_COUNT = 8;
constexpr uint16_t PPM_FRAME_US = 22500;
constexpr uint16_t PPM_PULSE_US = 400;
constexpr bool PPM_IDLE_HIGH = true;
constexpr uint32_t FAILSAFE_TIMEOUT_MS = 700;
```

Default behavior:

| Setting | Value |
|---|---:|
| PPM output | Arduino D9 |
| Maximum channels | 8 |
| PPM frame | 22.5 ms |
| Separator pulse | 400 µs |
| Idle level | HIGH |
| Active separator | LOW |
| USB serial | 115200 baud |
| Serial timeout | 700 ms |

The polarity is the current FlySky prototype assumption. Confirm the exact trainer-port polarity and voltage before connecting a powered model.

## Multi-device AETR setup

Recommended channel order:

```text
CH1 Aileron / Roll    ← Primary Stick
CH2 Elevator / Pitch  ← Primary Stick
CH3 Throttle          ← Throttle Unit
CH4 Rudder / Yaw      ← Primary Stick or Rudder Pedals
```

Desktop setup:

1. Connect the Thrustmaster stick and separate throttle to the PC.
2. Confirm both appear in **Joystick Monitor**.
3. Select the stick and save its calibration.
4. Select the throttle and save its calibration separately.
5. Open **Channel Mapping**.
6. Bind `Primary Stick` to the stick GUID.
7. Bind `Throttle Unit` to the throttle GUID.
8. Run **Auto-map AETR**.
9. Verify direction, endpoints and failsafe values.
10. Save the profile.

The app sends the resulting channel array to the UNO. Axis numbers can overlap between USB devices because the desktop mapping also stores the device role.

## Strict AETR failsafe

The desktop application treats CH1–CH4 as one safety group. If a required stick or throttle source disappears, it sends safe AETR values:

```text
CH1 Roll      1500 µs
CH2 Pitch     1500 µs
CH3 Throttle  1000 µs
CH4 Yaw       1500 µs
```

The UNO also has an independent serial failsafe. At startup, or when no valid channel packet is received for more than 700 ms:

- CH3 returns to `1000 µs`.
- All other active channels return to `1500 µs`.
- PPM generation continues with deterministic timing.
- The AVR watchdog resets the board if the main loop stalls.

The FlySky transmitter and receiver failsafe must still be configured and tested independently.

## Arduino IDE upload

1. Install Arduino IDE 2.x.
2. Open `simjoy_arduino_bridge.ino`.
3. Select **Arduino Uno** for an UNO R3.
4. For a Nano select **Arduino Nano** and the correct processor/bootloader.
5. Select the board COM port.
6. Click **Upload**.
7. Close Serial Monitor before the desktop app connects.

## Desktop connection

1. Start the desktop application.
2. Open **Adapter / Firmware**.
3. Select the UNO COM port.
4. Select `115200` baud.
5. Click **Connect serial**.
6. Wait about two seconds because opening the serial port normally resets the UNO.
7. Click **Handshake** if board information does not appear automatically.
8. Keep the desktop application running while controlling the model.

The UNO advertises stream-only operation. Profiles, role bindings and calibration remain on the PC; profile upload is not required for UNO operation.

## Wiring

```text
Arduino UNO D9  ── 1 kΩ series resistor ── FlySky trainer signal
Arduino UNO GND ────────────────────────── FlySky trainer ground
```

A 1 kΩ resistor limits fault current but is not a complete level-shifting or protection circuit. Identify signal, ground, polarity and voltage before connection. Do not connect an unknown trainer-port power pin to the Arduino.

## Bench-test order

1. Upload the sketch with the transmitter disconnected.
2. Run the desktop app and connect the UNO at 115200 baud.
3. Verify CH1–CH4 change correctly in the app.
4. Measure D9 with an oscilloscope or logic analyzer.
5. Confirm approximately 400 µs separator pulses and a 22.5 ms frame.
6. Disconnect the throttle USB and confirm strict AETR failsafe in the app.
7. Stop the desktop app and confirm UNO serial failsafe within 700 ms.
8. Connect trainer signal and ground only through the protection resistor/stage.
9. Test with aircraft power off and propeller removed.
10. Verify every channel direction and endpoint before flight.

## Protocol subset

The firmware uses the project's framed `SJ` protocol with CRC16 and supports:

- `HELLO` / `HELLO_RESPONSE`
- `DEVICE_INFO`
- `STATUS`
- `LIVE_CHANNELS`
- stream-only acknowledgements for profile commands
- `REBOOT`
- `ACK` and `ERROR`

The receive payload buffer is limited to 384 bytes to protect the UNO/Nano's 2 KB SRAM. The desktop sends final live channels rather than large persistent profiles.
