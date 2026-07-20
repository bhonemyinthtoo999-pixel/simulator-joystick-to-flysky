# ESP32-S3 Firmware

ESP-IDF firmware for the standalone adapter:

```text
USB joystick → ESP32-S3 USB Host → PPM → FlySky trainer port
```

## Implemented modules

- `usb_joystick.c`: USB Host and HID interface lifecycle
- `hid_report_parser.c`: generic HID report-descriptor parsing and raw report decoding
- `profile_store.c`: profile validation, NVS persistence, mapping, expo, smoothing and failsafe
- `ppm_output.c`: RMT-generated PPM frames
- `protocol.c`: CRC16 framed UART configuration protocol
- `main.c`: safety-oriented runtime coordinator

## Toolchain

Use ESP-IDF 5.3 or newer. The managed component dependency is declared in `main/idf_component.yml`:

```yaml
espressif/usb_host_hid: "^1.2.0"
```

## Build and flash

```bash
idf.py set-target esp32s3
idf.py build
idf.py -p COM_PORT flash monitor
```

Configuration is available through:

```bash
idf.py menuconfig
```

Open **Simulator Joystick to FlySky** to configure:

- PPM output GPIO, default GPIO 4
- Desktop protocol UART, default UART1
- Protocol TX/RX pins, default GPIO17/GPIO18
- Protocol baud rate, default 115200
- USB task core

## UART desktop connection

The firmware intentionally uses a configurable UART rather than the USB-OTG port, because the USB-OTG peripheral is operating as the joystick host.

Typical USB-to-TTL wiring:

```text
USB-TTL TX  → ESP32-S3 protocol RX (default GPIO18)
USB-TTL RX  → ESP32-S3 protocol TX (default GPIO17)
USB-TTL GND → ESP32-S3 GND
```

Use 3.3 V UART logic. Do not connect the USB-to-TTL 5 V/VCC pin unless the board's power design explicitly requires it.

## USB host power

The joystick requires a stable 5 V VBUS supply. Many ESP32-S3 boards do not automatically provide sufficient USB-host current. Use a board with an OTG host power switch or an externally powered USB-host connection with a common ground. Do not feed external 5 V back into the computer or board USB connector.

## PPM safety

Default profile:

- 8 channels
- 22.5 ms frame
- 300 µs pulse
- Positive polarity
- CH3 throttle failsafe at 1000 µs
- Other channels centered at 1500 µs

PPM polarity and trainer-port electrical interface must be confirmed on the exact FlySky model. Start testing with the aircraft unpowered and propeller removed.

## Current validation status

The source is an implementation-ready MVP, but it has not yet been validated on the user's physical ESP32-S3, joystick or FlySky trainer port. HID report layouts vary across manufacturers; the parser intentionally supports standard axes/buttons/hats and treats other variable multi-bit controls as ordered axes, but unusual proprietary devices may need device-specific handling.
