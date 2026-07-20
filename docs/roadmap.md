# Development Roadmap

## Phase 1 — Foundation

- Define architecture and safety boundaries.
- Record validated FlySky trainer waveform assumptions.
- Establish repository structure and coding rules.
- Define profile format and desktop-device protocol.

## Phase 2 — Desktop MVP

- Build PySide6 application shell.
- Detect local simulator joysticks.
- Display axes, buttons, and hats live.
- Implement calibration wizard.
- Implement channel mapping and profile persistence.
- Add virtual RC channel monitor.

## Phase 3 — ESP32-S3 Firmware MVP

- Bring up USB Host.
- Enumerate PXN 2119 Pro.
- Parse required axes and buttons.
- Generate deterministic six-channel PPM.
- Store and load one validated profile.
- Add status LED and serial diagnostics.

## Phase 4 — Integration

- Implement versioned desktop-device protocol.
- Read device, firmware, joystick, and fault status.
- Upload, validate, activate, and export profiles.
- Add joystick-disconnect and watchdog failsafe tests.
- Measure end-to-end latency and PPM timing.

## Phase 5 — Hardware

- Design protected 5 V USB Host power path.
- Add current limiting or resettable fuse.
- Finalize trainer connector wiring.
- Produce schematic, PCB, BOM, and enclosure.
- Add convenient power switch, LED, and optional buzzer.

## Phase 6 — Release validation

- Automated desktop tests.
- Firmware unit and hardware-in-loop tests where practical.
- Oscilloscope verification of every PPM timing parameter.
- Propeller-off bench test with transmitter and receiver.
- Repeated power-loss, reset, disconnect, and invalid-profile tests.
- Controlled first field test only after documented sign-off.

## Initial MVP definition

The first useful release must:

1. Read the PXN 2119 Pro through ESP32-S3 USB Host.
2. Map four primary axes to roll, pitch, throttle, and yaw.
3. Output six-channel FlySky-compatible trainer PPM.
4. Store calibration and mapping in flash.
5. Enter a documented safe state on joystick disconnect or firmware fault.
6. Be configured through a Windows desktop application.
