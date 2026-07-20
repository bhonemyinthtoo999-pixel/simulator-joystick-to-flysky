# Desktop–Device Protocol v1.0

## Transport

The initial hardware transport is a 3.3 V UART exposed to Windows through a USB-to-TTL adapter. Default settings are `115200 8N1`.

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

Maximum payload: 8192 bytes.

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

## Safety rules

- Invalid magic, length, version, JSON or CRC is discarded.
- Profile data is validated before NVS replacement.
- All channel values are clamped to `800–2200 µs`.
- `LIVE_CHANNELS` expires after 500 ms; the firmware then returns to standalone HID mapping or failsafe.
- Joystick input expires according to `failsafe_timeout_ms` in the active profile.
- Profile validation does not modify the active profile.
- Firmware profile mapping and PPM timing remain bounded even when desktop data is malformed.

## Compatibility

A protocol-major mismatch blocks normal command processing. Minor-version additions should preserve existing field meanings and make new JSON fields optional where practical.
