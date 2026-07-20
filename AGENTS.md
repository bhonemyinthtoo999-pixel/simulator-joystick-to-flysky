# AGENTS.md

## Project mission

Develop a safe, open-source adapter that converts compatible USB simulator joystick input into a FlySky trainer/student signal.

## Fixed architecture

```text
USB Simulator Joystick → ESP32-S3 USB Host → Input Processing → Safety Layer → FlySky PPM → Trainer Port
```

The desktop application configures and diagnoses the standalone adapter. The desktop application must not be required during normal use.

## Non-negotiable technical facts

Until new oscilloscope measurements prove otherwise, preserve these validated FlySky trainer assumptions:

- Student-input architecture
- Six channels
- Negative-polarity PPM
- Idle HIGH
- Approximately 400 µs LOW separator pulse
- Approximately 21 ms frame

Do not silently change PPM polarity, pulse timing, channel count, trainer role, or signal ownership.

## Safety requirements

- Default to a disarmed/safe state after boot, reset, malformed configuration, USB disconnect, or communication timeout.
- Throttle must never jump to an active value during startup or profile loading.
- Clamp every channel to configured safe bounds.
- Validate configuration before saving or applying it.
- Implement watchdog and joystick-disconnect handling before any flight release.
- Never describe untested code or hardware as flight-ready.
- Bench tests must be performed without a propeller.

## Code organization

- `desktop/`: desktop configuration application.
- `firmware/esp32-s3/`: standalone embedded firmware.
- `hardware/`: schematics, PCB, wiring, BOM, and enclosure.
- `docs/`: architecture, protocol, roadmap, and safety documentation.
- `examples/`: test captures, sample profiles, and reference data.

Keep hardware-specific code behind clear interfaces. Keep joystick parsing, normalization, channel mapping, safety, transport, and PPM output as separate modules.

## Coding style

- Prefer explicit types, clear names, and small testable functions.
- Add error handling for device, file, serial, USB, and configuration failures.
- Do not hard-code joystick axis mappings outside profiles or device descriptors.
- Use English identifiers and documentation. Burmese comments may be added where they improve accessibility, but they must not replace precise technical names.
- Add tests for normalization, reversal, dead zones, endpoint mapping, failsafe, and protocol parsing.

## Change discipline

Before changing signal timing, power design, channel behavior, failsafe behavior, or protocol fields:

1. Document the reason.
2. Add or update tests.
3. State whether the change is bench-tested, hardware-tested, or untested.
4. Update the relevant file in `docs/`.

Do not redesign the project around Arduino UNO or a permanently connected PC unless the repository owner explicitly changes the architecture.
