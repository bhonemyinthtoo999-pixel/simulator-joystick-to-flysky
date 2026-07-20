# Hardware

This directory will contain:

- Wiring diagrams
- USB Host power design
- FlySky trainer connector pinout
- Schematic and PCB files
- Bill of materials
- Enclosure design
- Hardware test records

## Initial power concept

A regulated ready-made 5 V power bank supplies both the ESP32-S3 board and the joystick USB VBUS through separate branches with a common ground. The joystick must not be powered from the ESP32-S3 3.3 V regulator or a GPIO pin.

The final design should include appropriate current limiting or resettable protection, local decoupling, and verification that the chosen ESP32-S3 board exposes the required native USB Host/OTG data path.
