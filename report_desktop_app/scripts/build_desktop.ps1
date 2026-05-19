# Build desktop app with PyInstaller (one-folder output under dist/).
$ErrorActionPreference = "Stop"
$DesktopRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $DesktopRoot

Set-Location $DesktopRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..."
    python -m pip install pyinstaller
}

Write-Host "Building from $DesktopRoot (repo root: $RepoRoot)"
pyinstaller --noconfirm --clean pyinstaller.spec

$OutDir = Join-Path $DesktopRoot "dist" "SecuritiesReportDesktop"
if (Test-Path $OutDir) {
    Write-Host "Done. Run: $OutDir\SecuritiesReportDesktop.exe"
} else {
    Write-Error "Build output not found at $OutDir"
}
