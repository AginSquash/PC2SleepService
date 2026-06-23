#Requires -Version 5.1
$ErrorActionPreference = "Stop"

Write-Host "Building PCSleepService.exe ..."

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found in PATH"
}

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install pyinstaller

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m PyInstaller `
    --onefile `
    --windowed `
    --name PCSleepService `
    --hidden-import comtypes `
    --collect-submodules comtypes `
    src/pc2sleep/__main__.py

Write-Host ""
Write-Host "Done. Executable: $root\dist\PCSleepService.exe"
