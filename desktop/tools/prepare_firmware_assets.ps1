$ErrorActionPreference = "Stop"

$desktopRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $desktopRoot
$assetRoot = Join-Path $desktopRoot "assets/firmware"
$hexRoot = Join-Path $assetRoot "hex"
$toolRoot = Join-Path $assetRoot "tools/avrdude"
$unoOut = Join-Path $env:TEMP "simjoy-uno-build"
$megaOut = Join-Path $env:TEMP "simjoy-mega-build"

if (-not (Get-Command arduino-cli -ErrorAction SilentlyContinue)) {
    throw "arduino-cli is required to prepare the one-click firmware installer assets."
}

arduino-cli core update-index
arduino-cli core install arduino:avr

Remove-Item $unoOut, $megaOut -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $hexRoot, $toolRoot, $unoOut, $megaOut | Out-Null

arduino-cli compile --fqbn arduino:avr:uno --output-dir $unoOut (Join-Path $repoRoot "firmware/arduino-uno/simjoy_arduino_bridge")
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 --output-dir $megaOut (Join-Path $repoRoot "firmware/arduino-mega/simjoy_mega_bridge")

$unoHex = Get-ChildItem $unoOut -Filter "*.ino.hex" | Where-Object { $_.Name -notlike "*with_bootloader*" } | Select-Object -First 1
$megaHex = Get-ChildItem $megaOut -Filter "*.ino.hex" | Where-Object { $_.Name -notlike "*with_bootloader*" } | Select-Object -First 1
if (-not $unoHex) { throw "UNO firmware HEX was not generated" }
if (-not $megaHex) { throw "Mega firmware HEX was not generated" }
Copy-Item $unoHex.FullName (Join-Path $hexRoot "simjoy-uno.hex") -Force
Copy-Item $megaHex.FullName (Join-Path $hexRoot "simjoy-mega.hex") -Force

$arduinoData = Join-Path $env:LOCALAPPDATA "Arduino15/packages/arduino/tools/avrdude"
$avrdudePackage = Get-ChildItem $arduinoData -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $avrdudePackage) { throw "Arduino AVR avrdude package was not found" }
Remove-Item $toolRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $toolRoot | Out-Null
Copy-Item (Join-Path $avrdudePackage.FullName "*") $toolRoot -Recurse -Force

$required = @(
    (Join-Path $hexRoot "simjoy-uno.hex"),
    (Join-Path $hexRoot "simjoy-mega.hex"),
    (Join-Path $toolRoot "bin/avrdude.exe"),
    (Join-Path $toolRoot "etc/avrdude.conf")
)
foreach ($path in $required) {
    if (-not (Test-Path $path)) { throw "Missing firmware installer component: $path" }
}

Write-Host "Firmware installer assets prepared under $assetRoot"
