# Arduino UNO/Nano Bridge Firmware

This firmware provides a lower-cost compatibility path for the project:

```text
USB simulator joystick
        ↓
Windows desktop application
        ↓ USB serial, 115200 baud
Arduino UNO/Nano
        ↓ PPM
FlySky trainer/student port
```

Unlike the ESP32-S3 firmware, an Arduino UNO or Nano cannot connect directly to a normal USB joystick without extra USB-host hardware. The desktop application must remain running and performs joystick detection, calibration, channel mapping, expo, trim and endpoint processing.

## Supported boards

- Arduino UNO R3 with ATmega328P
- Arduino Nano with ATmega328P

The sketch is located at:

```text
simjoy_arduino_bridge/simjoy_arduino_bridge.ino
```

## Arduino IDE upload

1. Install Arduino IDE 2.x.
2. Open `simjoy_arduino_bridge.ino`.
3. Select **Arduino Uno** or **Arduino Nano**.
4. For a clone Nano, try **ATmega328P (Old Bootloader)** when normal upload fails.
5. Select the correct COM port.
6. Click **Upload**.
7. Close Arduino Serial Monitor before connecting from the desktop application.

No third-party Arduino library is required.

## Desktop connection

1. Start the desktop app.
2. Select the Arduino COM port under **Adapter / Firmware**.
3. Use `115200` baud and click **Connect serial**.
4. Wait about two seconds after connecting because opening the serial port resets an UNO/Nano.
5. Click **Handshake** when needed.
6. Leave the desktop application running while controlling the model.

The Arduino advertises `stream_only` capability. Profile files remain on the PC; the firmware receives only the final channel pulse values. The ESP32 profile-upload function is therefore not required for Arduino bridge operation.

## Default PPM configuration

| Setting | Default |
|---|---:|
| Output pin | D9 |
| Maximum channels | 8 |
| Frame period | 22.5 ms |
| Separator pulse | 400 µs |
| Idle level | HIGH |
| Active separator | LOW |
| Serial baud | 115200 |
| Desktop timeout | 700 ms |

The polarity matches the earlier FlySky Arduino prototype assumptions: idle HIGH with LOW separator pulses. Confirm it on the exact transmitter before connecting a powered aircraft. To change it, edit:

```cpp
constexpr bool PPM_IDLE_HIGH = true;
```

## Failsafe

At startup and whenever no valid channel packet is received for 700 ms:

- CH3 is set to `1000 µs` for low throttle.
- All other active channels are set to `1500 µs`.
- PPM generation continues, so the trainer input receives a deterministic safe frame rather than random timing.
- The AVR watchdog resets the firmware if the main loop stops responding.

The transmitter and receiver failsafe must still be configured and tested independently.

## Basic wiring

```text
Arduino D9  ── 1 kΩ series resistor ── FlySky trainer signal
Arduino GND ─────────────────────────── FlySky trainer ground
```

A 1 kΩ series resistor is useful for limiting fault current during bench testing, but it does not prove voltage compatibility and is not a complete protection circuit. Identify signal and ground with measurements or verified documentation. Do not connect an unknown trainer-port power pin to the Arduino.

## Bench-test order

1. Upload the sketch with no transmitter connected.
2. Use an oscilloscope or logic analyzer on D9 and confirm the expected idle level, pulse width and frame timing.
3. Connect the desktop Demo Flight Joystick and verify changing channel values.
4. Stop the desktop application and confirm CH3 returns to 1000 µs within 700 ms.
5. Connect only trainer signal and ground through the protection resistor/stage.
6. Test the FlySky trainer switch with no aircraft power and no propeller.
7. Verify every direction, endpoint and disconnect behavior before flight.

## Protocol subset

The firmware uses the same `SJ` framed CRC16 protocol as the ESP32-S3 version and supports:

- `HELLO` / `HELLO_RESPONSE`
- `DEVICE_INFO`
- `STATUS`
- `LIVE_CHANNELS`
- profile commands as stream-only acknowledgements when the payload fits AVR memory
- `REBOOT`
- `ACK` and `ERROR`

The UNO/Nano receive payload buffer is intentionally limited to 384 bytes to protect its 2 KB SRAM. Large persistent-profile payloads are not used by this bridge firmware.
