# Arduino Mega 2560 Bridge Firmware

This firmware is the higher-capacity AVR bridge for the project:

```text
USB flight stick ─┐
                  ├─ Windows desktop app ─ USB Serial ─ Arduino Mega 2560 ─ PPM ─ FlySky trainer port
USB throttle ─────┘
```

The desktop application performs multi-device detection, role binding, per-device calibration, cross-device AETR mapping and strict AETR failsafe. The Mega receives final RC pulse values only; it does not act as a USB joystick host.

## Sketch

```text
simjoy_mega_bridge/simjoy_mega_bridge.ino
```

Arduino IDE settings:

- Board: **Arduino Mega or Mega 2560**
- Processor: **ATmega2560**
- Serial baud: **115200**
- No third-party libraries required

## Default configuration

| Setting | Default |
|---|---:|
| PPM output | D11 |
| Default channels | 8 |
| Maximum channels | 12 |
| 4–8 channel frame | 22.5 ms |
| 9–12 channel frame | 30 ms |
| Separator pulse | 400 µs |
| Idle level | HIGH |
| Active separator | LOW |
| Desktop timeout | 700 ms |

The firmware increases the frame length for more than eight channels. The exact FlySky transmitter may accept fewer channels, so begin with the normal 8-channel AETR/AUX profile.

## Wiring

```text
Mega D11 ── 1 kΩ series resistor ── FlySky trainer signal
Mega GND ────────────────────────── FlySky trainer ground
```

A 1 kΩ resistor limits fault current but is not a complete voltage-level protection circuit. Confirm the trainer signal pin, ground, polarity and voltage before connection. Do not connect an unknown trainer-port power pin.

## Failsafe

When valid desktop channel packets stop for more than 700 ms:

- CH3 returns to `1000 µs`.
- Other active channels return to `1500 µs`.
- PPM generation continues with deterministic timing.
- The AVR watchdog resets the board if the main loop stalls.

The desktop app also provides strict grouped AETR failsafe. If the separate stick or throttle disappears, CH1–CH4 are set to the profile's safe values before the packet reaches the Mega.

## Bench-test order

1. Upload with the transmitter disconnected.
2. Confirm D11 PPM timing with a logic analyzer or oscilloscope.
3. Bind `Primary Stick` and `Throttle Unit` in Channel Mapping.
4. Calibrate each USB device separately.
5. Run cross-device Auto-map AETR and verify all directions.
6. Stop the desktop app and confirm CH3 returns to 1000 µs within 700 ms.
7. Connect trainer signal and ground only, with aircraft power off and propeller removed.
