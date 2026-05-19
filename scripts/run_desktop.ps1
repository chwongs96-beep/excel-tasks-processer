# Launch the PySide6 desktop reporting app.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Desktop = Join-Path $Root "report_desktop_app"
Set-Location $Desktop
python main.py
