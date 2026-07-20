# Desktop–Device Protocol v1.0

## Transport

The initial hardware transport is a 3.3 V UART exposed to Windows through a USB-to-TTL adapter for ESP32-S3, or the onboard USB serial interface of an Arduino UNO/Nano. Default settings are `115200 8N1`.

## Frame format

All integer fields are little-endian.

| Offset | Size | Field |
|---:|---:|---|
| 0 | 2 | Magic bytes `S`, `J` |
| 2 | 1 | Protocol major version |
| 3 | 1 | Message type |
| 4 | 2 | Sequence number |
| 6 | 2 | UTF-8 JSON payload length |
| 8 | N | JSON object payload |
| 8+N | 2 | CRC16-CCITT over bytes from major version through payload |

CRC parameters:

- Polynomial: `0x1021`
- Initial value: `0xFFFF`
- No reflection
- No final XOR

Maximum desktop/ESP32 payload: 8192 bytes.

The Arduino UNO/Nano bridge intentionally limits received payloads to 384 bytes because the ATmega328P has 2 KB SRAM. Normal `HELLO`, `DEVICE_INFO`, `STATUS` and `LIVE_CHANNELS` frames fit within this limit. Persistent profile data remains on the desktop in Arduino bridge mode.

## Message types

| ID | Name | Direction |
|---:|---|---|
| 1 | `HELLO` | Desktop → device |
| 2 | `HELLO_RESPONSE` | Device → desktop |
| 3 | `DEVICE_INFO` | Both |
| 4 | `STATUS` | Both |
| 5 | `LIVE_INPUT` | Device → desktop, reserved |
| 6 | `LIVE_CHANNELS` | Desktop → device |
| 7 | `PROFILE_LIST` | Reserved |
| 8 | `PROFILE_READ` | Reserved |
| 9 | `PROFILE_VALIDATE` | Desktop → device |
| 10 | `PROFILE_WRITE` | Desktop → device |
| 11 | `PROFILE_ACTIVATE` | Desktop → device |
| 12 | `CALIBRATION` | Reserved |
| 13 | `REBOOT` | Desktop → device |
| 14 | `BOOTLOADER` | Desktop → device; may return unsupported |
| 15 | `ACK` | Device → desktop |
| 16 | `ERROR` | Device → desktop |
| 17 | `LOG` | Device → desktop |

## Device capability modes

An ESP32-S3 standalone adapter reports capabilities such as `usb_hid_host`, `profiles`, `ppm` and `desktop_stream`.

An Arduino UNO/Nano bridge reports `stream_only`. In this mode:

- the desktop application owns calibration, mapping and profiles;
- `LIVE_CHANNELS` contains the final pulse values sent to the PPM engine;
- the desktop must remain connected;
- large persistent-profile payloads are not required;
- the firmware still provides CRC checking, status, timeout failsafe and watchdog protection.

## Safety rules

- Invalid magic, length, version, JSON or CRC is discarded.
- Profile data is validated before ESP32-S3 NVS replacement.
- All channel values are clamped to `800–2200 µs`.
- ESP32-S3 `LIVE_CHANNELS` expires after 500 ms; it then returns to standalone HID mapping or failsafe.
- Arduino `LIVE_CHANNELS` expires after 700 ms; it then outputs CH3 at 1000 µs and other active channels at 1500 µs.
- Joystick input expires according to `failsafe_timeout_ms` in an ESP32-S3 active profile.
- Profile validation does not modify the active profile.
- Firmware PPM timing remains bounded even when desktop data is malformed.

## Compatibility

A protocol-major mismatch blocks normal command processing. Minor-version additions should preserve existing field meanings and make new JSON fields optional where practical.
