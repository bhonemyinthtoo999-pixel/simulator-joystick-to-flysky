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

python -m pytest -q --tb=short
if errorlevel 1 exit /b 1

python -m PyInstaller --noconfirm --clean SimulatorJoystickToFlySky.spec
if errorlevel 1 exit /b 1

"dist\SimulatorJoystickToFlySky\SimulatorJoystickToFlySky.exe" --packaging-smoke-test
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo Application: dist\SimulatorJoystickToFlySky\SimulatorJoystickToFlySky.exe
echo Keep the complete SimulatorJoystickToFlySky folder together when copying it.
endlocal
