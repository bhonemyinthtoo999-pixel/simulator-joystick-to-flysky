# ESP32-S3 Firmware

Standalone firmware responsibilities:

- Act as a USB Host for compatible simulator joysticks.
- Parse HID input, beginning with the PXN 2119 Pro.
- Apply calibration, mapping, curves, limits, and safety rules.
- Generate deterministic FlySky-compatible six-channel PPM.
- Store validated profiles in non-volatile memory.
- Expose a versioned configuration and diagnostics protocol.
- Handle boot, reset, joystick disconnect, invalid profile, and watchdog faults safely.

The initial implementation framework will be selected after USB Host and timing prototypes are compared. Real-time PPM timing must not depend on desktop communication or UI activity.
