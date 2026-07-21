from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
if sys.platform == "win32":
    os.environ["SDL_JOYSTICK_HIDAPI"] = "0"
    os.environ["SDL_JOYSTICK_WGI"] = "0"
    os.environ["SDL_JOYSTICK_RAWINPUT"] = "0"

import pygame


def main() -> int:
    pygame.display.init()
    pygame.display.set_mode((1, 1), getattr(pygame, "HIDDEN", 0))
    pygame.joystick.init()
    pygame.event.clear()

    count = pygame.joystick.get_count()
    print(
        f"pygame={pygame.version.ver} SDL={pygame.version.SDL} devices={count} "
        f"HIDAPI={os.environ.get('SDL_JOYSTICK_HIDAPI', 'auto')} "
        f"WGI={os.environ.get('SDL_JOYSTICK_WGI', 'auto')} "
        f"RAWINPUT={os.environ.get('SDL_JOYSTICK_RAWINPUT', 'auto')}"
    )
    if count == 0:
        print("No joystick detected by SDL DirectInput.")
        return 1

    devices: list[pygame.joystick.JoystickType] = []
    for index in range(count):
        joystick = pygame.joystick.Joystick(index)
        joystick.init()
        devices.append(joystick)
        print(
            f"[{index}] name={joystick.get_name()!r} "
            f"guid={joystick.get_guid()} instance={joystick.get_instance_id()} "
            f"axes={joystick.get_numaxes()} buttons={joystick.get_numbuttons()} "
            f"hats={joystick.get_numhats()}"
        )

    print("Move every axis. Press Ctrl+C to stop.")
    last_lines: dict[int, str] = {}
    try:
        while True:
            pygame.event.get()
            pygame.event.pump()
            for index, joystick in enumerate(devices):
                axes = [
                    round(float(joystick.get_axis(axis)), 4)
                    for axis in range(joystick.get_numaxes())
                ]
                buttons = [
                    button
                    for button in range(joystick.get_numbuttons())
                    if joystick.get_button(button)
                ]
                hats = [
                    joystick.get_hat(hat)
                    for hat in range(joystick.get_numhats())
                ]
                line = f"[{index}] axes={axes} pressed={buttons} hats={hats}"
                if line != last_lines.get(index):
                    print(line, flush=True)
                    last_lines[index] = line
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        for joystick in devices:
            joystick.quit()
        pygame.joystick.quit()
        pygame.display.quit()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
