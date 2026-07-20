# Desktop–Device Protocol

## Status

Draft for the initial USB serial implementation. No field layout is frozen yet.

## Design goals

- Versioned and backward-compatible where practical.
- Easy to inspect during development.
- Strict length and value validation.
- Explicit request, response, acknowledgement, and error messages.
- Safe handling of interrupted profile uploads.
- No command may bypass firmware safety checks.

## Initial transport

The first implementation will use USB CDC serial between the desktop application and ESP32-S3. HID joystick input and FlySky PPM output remain independent of this configuration link.

## Planned message groups

- `HELLO`: protocol and firmware version negotiation.
- `DEVICE_INFO`: board, firmware, hardware revision, and capabilities.
- `STATUS`: joystick, PPM, profile, power, and fault status.
- `LIVE_INPUT`: raw and normalized joystick state.
- `LIVE_CHANNELS`: final RC channel values.
- `PROFILE_LIST`: stored profiles and active profile.
- `PROFILE_READ`: retrieve one profile.
- `PROFILE_VALIDATE`: validate without saving.
- `PROFILE_WRITE`: staged profile upload.
- `PROFILE_ACTIVATE`: atomically activate a validated profile.
- `CALIBRATION`: start, sample, complete, or cancel calibration.
- `REBOOT`: controlled reboot with acknowledgement.
- `BOOTLOADER`: enter supported firmware-update mode.
- `ERROR`: structured error code and diagnostic message.

## Safety behavior

- Invalid, incomplete, oversized, or unsupported messages are rejected.
- Profile writes are staged and verified before replacing the active profile.
- Loss of desktop communication does not disable valid standalone operation.
- Desktop commands cannot directly set unrestricted live PPM values in a release build.
- Firmware applies channel clamps and failsafe policy after all configuration input.

## Versioning

Every session must negotiate a protocol major and minor version. A major-version mismatch blocks configuration writes but may still allow basic device identification.
