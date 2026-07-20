# Hardware Notes

## Core parts

- ESP32-S3 board with USB-OTG host capability
- USB host connector or OTG adapter with correct VBUS power arrangement
- Stable 5 V supply or power bank
- FlySky trainer-port cable
- 3.3 V-safe signal-conditioning stage
- Optional CH340/USB-to-TTL adapter for desktop configuration

## Signal path

```text
Joystick USB D+/D− → ESP32-S3 USB-OTG host
ESP32-S3 PPM GPIO  → protection/level stage → FlySky trainer signal
ESP32-S3 GND       ─────────────────────────→ FlySky trainer ground
```

Do not connect the FlySky trainer-port power/VCC line to the ESP32-S3 unless its voltage, direction and purpose have been measured and documented.

## Recommended bring-up order

1. Power the ESP32-S3 only and confirm firmware starts.
2. Measure the PPM GPIO with an oscilloscope or logic analyzer.
3. Confirm frame period, pulse width, polarity and `1000/1500/2000 µs` channel values.
4. Connect the joystick and inspect USB/HID diagnostics.
5. Connect only PPM signal and ground to the transmitter through the protection stage.
6. Verify trainer switch behavior with no aircraft power.
7. Verify receiver outputs with motor/propeller made safe.

## Electrical note

A simple series resistor may limit fault current but does not guarantee voltage compatibility or protect against an incorrectly identified trainer pin. Prefer a verified transistor, open-drain/open-collector or buffer circuit selected after measuring the transmitter port.
