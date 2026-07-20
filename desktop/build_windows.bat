@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
    py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name SimulatorJoystickToFlySky --paths . app\main.py
if errorlevel 1 exit /b 1
echo.
echo Build complete: dist\SimulatorJoystickToFlySky\SimulatorJoystickToFlySky.exe
