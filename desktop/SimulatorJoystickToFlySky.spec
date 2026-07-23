# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


pygame_binaries = collect_dynamic_libs("pygame")
pygame_data = collect_data_files("pygame", include_py_files=False)
pygame_hiddenimports = collect_submodules("pygame")
application_data = [
    ("assets/app_icon.svg", "assets"),
    ("assets/SimulatorJoystickToFlySky.png", "assets"),
]

analysis = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=pygame_binaries,
    datas=pygame_data + application_data,
    hiddenimports=pygame_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="SimulatorJoystickToFlySky",
    icon="assets/SimulatorJoystickToFlySky.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SimulatorJoystickToFlySky",
)
