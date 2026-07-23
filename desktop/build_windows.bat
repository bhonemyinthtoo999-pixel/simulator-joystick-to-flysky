@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set QT_QPA_PLATFORM=offscreen

if not exist .venv (
    py -3 -m venv .venv
    if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate
if errorlevel 1 exit /b 1

python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

python tools\build_icon.py
if errorlevel 1 exit /b 1

where arduino-cli >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: arduino-cli was not found.
    echo Install Arduino CLI and add it to PATH to build the one-click firmware installer.
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File tools\prepare_firmware_assets.ps1
if errorlevel 1 exit /b 1

python -m pytest -q --tb=short
if errorlevel 1 exit /b 1

python -m PyInstaller --noconfirm --clean SimulatorJoystickToFlySky.spec
if errorlevel 1 exit /b 1

"dist\SimulatorJoystickToFlySky\SimulatorJoystickToFlySky.exe" --packaging-smoke-test
if errorlevel 1 exit /b 1

if not exist "dist\SimulatorJoystickToFlySky\_internal\assets\firmware\hex\simjoy-uno.hex" exit /b 1
if not exist "dist\SimulatorJoystickToFlySky\_internal\assets\firmware\hex\simjoy-mega.hex" exit /b 1
if not exist "dist\SimulatorJoystickToFlySky\_internal\assets\firmware\tools\avrdude\bin\avrdude.exe" exit /b 1

echo.
echo Build complete.
echo Application: dist\SimulatorJoystickToFlySky\SimulatorJoystickToFlySky.exe
echo Icon: assets\SimulatorJoystickToFlySky.ico
echo One-click Arduino firmware installer: included
echo Keep the complete SimulatorJoystickToFlySky folder together when copying it.
endlocal
