# Architecture

## Desktop layers

- **UI pages:** status, monitor, calibration, mapping, profiles, device, diagnostics and settings
- **Joystick service:** SDL discovery, polling, hot-plug and virtual demo controller
- **Calibration service:** per-axis min/center/max/deadzone normalization
- **Channel mapper:** generic source mapping and safe RC pulse generation
- **Profile service:** persistent configuration and import/export
- **Serial/protocol services:** real UART and deterministic device simulator
- **Diagnostics service:** bounded event history and export

## Firmware layers

- **USB Host/HID:** interface discovery, raw input report acquisition and generic descriptor decoding
- **Input model:** normalized axes, buttons and hats independent of joystick model
- **Profile runtime:** source mapping, reverse, trim, expo, smoothing and failsafe
- **PPM engine:** RMT waveform generation independent of USB timing
- **Protocol:** profile configuration, status and bounded desktop test stream
- **NVS:** atomic active-profile persistence

## Runtime priority

PPM waveform generation and control processing are independent of the desktop application. Loss of desktop communication does not stop standalone operation. Loss of valid joystick input produces configured failsafe values.
