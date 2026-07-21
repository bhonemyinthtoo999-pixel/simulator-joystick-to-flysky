from __future__ import annotations

from dataclasses import dataclass
import re
import sys
from typing import Any

LEGACY_INSTANCE_BASE = 100_000


@dataclass(frozen=True)
class LegacyJoystickInfo:
    instance_id: int
    device_id: int
    name: str
    guid: str
    axes: int
    buttons: int
    hats: int
    vendor_id: int
    product_id: int


class WindowsLegacyJoystickBackend:
    """Read older Windows joysticks through the WinMM joystick API.

    SDL normally provides the best device support. WinMM is kept as a fallback for
    older DirectInput-era flight sticks that appear in Windows Game Controllers but
    are not exposed correctly by the SDL build used by pygame.
    """

    def __init__(self) -> None:
        self.available = False
        self.last_error = ""
        self._winmm: Any = None
        self._caps_type: Any = None
        self._info_type: Any = None
        self._devices: dict[int, tuple[LegacyJoystickInfo, Any]] = {}

        if sys.platform != "win32":
            return

        try:
            import ctypes
            from ctypes import wintypes

            class JOYCAPSW(ctypes.Structure):
                _fields_ = [
                    ("wMid", wintypes.WORD),
                    ("wPid", wintypes.WORD),
                    ("szPname", wintypes.WCHAR * 32),
                    ("wXmin", wintypes.UINT),
                    ("wXmax", wintypes.UINT),
                    ("wYmin", wintypes.UINT),
                    ("wYmax", wintypes.UINT),
                    ("wZmin", wintypes.UINT),
                    ("wZmax", wintypes.UINT),
                    ("wNumButtons", wintypes.UINT),
                    ("wPeriodMin", wintypes.UINT),
                    ("wPeriodMax", wintypes.UINT),
                    ("wRmin", wintypes.UINT),
                    ("wRmax", wintypes.UINT),
                    ("wUmin", wintypes.UINT),
                    ("wUmax", wintypes.UINT),
                    ("wVmin", wintypes.UINT),
                    ("wVmax", wintypes.UINT),
                    ("wCaps", wintypes.UINT),
                    ("wMaxAxes", wintypes.UINT),
                    ("wNumAxes", wintypes.UINT),
                    ("wMaxButtons", wintypes.UINT),
                    ("szRegKey", wintypes.WCHAR * 32),
                    ("szOEMVxD", wintypes.WCHAR * 260),
                ]

            class JOYINFOEX(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("dwXpos", wintypes.DWORD),
                    ("dwYpos", wintypes.DWORD),
                    ("dwZpos", wintypes.DWORD),
                    ("dwRpos", wintypes.DWORD),
                    ("dwUpos", wintypes.DWORD),
                    ("dwVpos", wintypes.DWORD),
                    ("dwButtons", wintypes.DWORD),
                    ("dwButtonNumber", wintypes.DWORD),
                    ("dwPOV", wintypes.DWORD),
                    ("dwReserved1", wintypes.DWORD),
                    ("dwReserved2", wintypes.DWORD),
                ]

            winmm = ctypes.WinDLL("winmm")
            winmm.joyGetNumDevs.restype = wintypes.UINT
            winmm.joyGetDevCapsW.argtypes = [wintypes.UINT_PTR, ctypes.POINTER(JOYCAPSW), wintypes.UINT]
            winmm.joyGetDevCapsW.restype = wintypes.UINT
            winmm.joyGetPosEx.argtypes = [wintypes.UINT, ctypes.POINTER(JOYINFOEX)]
            winmm.joyGetPosEx.restype = wintypes.UINT

            self._ctypes = ctypes
            self._winmm = winmm
            self._caps_type = JOYCAPSW
            self._info_type = JOYINFOEX
            self.available = True
        except (AttributeError, OSError) as exc:
            self.last_error = f"WinMM joystick backend unavailable: {exc}"

    @staticmethod
    def normalize_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", name.casefold())

    def scan(self) -> list[LegacyJoystickInfo]:
        if not self.available:
            self._devices.clear()
            return []

        found: dict[int, tuple[LegacyJoystickInfo, Any]] = {}
        try:
            device_slots = min(int(self._winmm.joyGetNumDevs()), 64)
            for device_id in range(device_slots):
                caps = self._caps_type()
                if self._winmm.joyGetDevCapsW(device_id, self._ctypes.byref(caps), self._ctypes.sizeof(caps)) != 0:
                    continue
                state = self._new_state()
                if self._winmm.joyGetPosEx(device_id, self._ctypes.byref(state)) != 0:
                    continue

                name = str(caps.szPname).strip() or f"Legacy joystick {device_id}"
                vendor_id = int(caps.wMid)
                product_id = int(caps.wPid)
                stable_name = self.normalize_name(name) or "joystick"
                info = LegacyJoystickInfo(
                    instance_id=LEGACY_INSTANCE_BASE + device_id,
                    device_id=device_id,
                    name=name,
                    guid=f"WINMM-{vendor_id:04X}-{product_id:04X}-{stable_name}",
                    axes=max(2, min(6, int(caps.wNumAxes))),
                    buttons=min(32, int(caps.wNumButtons)),
                    hats=1 if int(caps.wCaps) & 0x10 else 0,
                    vendor_id=vendor_id,
                    product_id=product_id,
                )
                found[info.instance_id] = (info, caps)
            self._devices = found
            self.last_error = ""
        except (AttributeError, OSError, ValueError) as exc:
            self._devices.clear()
            self.last_error = f"WinMM joystick scan failed: {exc}"
        return [pair[0] for pair in self._devices.values()]

    def poll(self) -> dict[int, dict[str, Any]]:
        if not self.available:
            return {}

        snapshots: dict[int, dict[str, Any]] = {}
        disconnected: list[int] = []
        for instance_id, (device, caps) in list(self._devices.items()):
            state = self._new_state()
            result = self._winmm.joyGetPosEx(device.device_id, self._ctypes.byref(state))
            if result != 0:
                disconnected.append(instance_id)
                continue

            axis_values = [
                self._normalize_axis(state.dwXpos, caps.wXmin, caps.wXmax),
                self._normalize_axis(state.dwYpos, caps.wYmin, caps.wYmax),
                self._normalize_axis(state.dwZpos, caps.wZmin, caps.wZmax),
                self._normalize_axis(state.dwRpos, caps.wRmin, caps.wRmax),
                self._normalize_axis(state.dwUpos, caps.wUmin, caps.wUmax),
                self._normalize_axis(state.dwVpos, caps.wVmin, caps.wVmax),
            ][: device.axes]
            buttons = [bool(int(state.dwButtons) & (1 << index)) for index in range(device.buttons)]
            hats = [self._pov_to_hat(int(state.dwPOV))] if device.hats else []
            snapshots[instance_id] = {
                "instance_id": instance_id,
                "name": device.name,
                "axes": axis_values,
                "buttons": buttons,
                "hats": hats,
                "balls": [],
                "is_virtual": False,
                "backend": "Windows WinMM fallback",
                "vendor_id": device.vendor_id,
                "product_id": device.product_id,
            }

        for instance_id in disconnected:
            self._devices.pop(instance_id, None)
        return snapshots

    def _new_state(self) -> Any:
        state = self._info_type()
        state.dwSize = self._ctypes.sizeof(self._info_type)
        state.dwFlags = 0x000000FF
        return state

    @staticmethod
    def _normalize_axis(value: int, minimum: int, maximum: int) -> float:
        if maximum <= minimum:
            return 0.0
        normalized = ((float(value) - float(minimum)) / float(maximum - minimum)) * 2.0 - 1.0
        return max(-1.0, min(1.0, normalized))

    @staticmethod
    def _pov_to_hat(pov: int) -> tuple[int, int]:
        if pov == 0xFFFF or pov > 35999:
            return (0, 0)
        sector = int((pov + 2250) // 4500) % 8
        return (
            (0, 1),
            (1, 1),
            (1, 0),
            (1, -1),
            (0, -1),
            (-1, -1),
            (-1, 0),
            (-1, 1),
        )[sector]
