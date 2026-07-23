# Windows portable application

The GitHub Actions workflow **Build Windows application** produces a Windows 10/11 x64 package named:

```text
SimulatorJoystickToFlySky-Windows-x64-v0.7.0.zip
```

## Run the application

1. Extract the complete ZIP file to a normal folder.
2. Keep every file in the extracted folder together.
3. Double-click `SimulatorJoystickToFlySky.exe`.
4. Python is not required on the destination computer.

The executable is currently unsigned. Windows SmartScreen may show an **Unknown publisher** warning. Check that the ZIP came from this repository's successful GitHub Actions build before choosing **More info → Run anyway**.

## Included firmware

The portable package also contains:

```text
firmware/arduino-uno/
firmware/arduino-mega/
```

- Arduino UNO/Nano PPM output: D9
- Arduino Mega 2560 PPM output: D11

## User data

Profiles, calibrations and settings remain outside the application folder under:

```text
%USERPROFILE%\.simulator-joystick-to-flysky\
```

This lets a newer portable application reuse the existing configuration.

## Build locally

From the repository's `desktop` directory, double-click or run:

```bat
build_windows.bat
```

The tested application folder is created at:

```text
dist\SimulatorJoystickToFlySky\
```

Do not copy only the EXE from this folder. The adjacent Qt, pygame and Python runtime files are required.
