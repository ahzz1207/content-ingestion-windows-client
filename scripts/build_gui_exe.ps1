# Build the standalone GUI exe.
# Usage: pwsh scripts\build_gui_exe.ps1
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "Building demo-win GUI exe (this takes ~60s on first run)..." -ForegroundColor Cyan
python -m PyInstaller demo_win_gui.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exe = Join-Path $projectRoot "dist\demo-win-gui.exe"
if (Test-Path $exe) {
    Write-Host "Built: $exe" -ForegroundColor Green
    Write-Host "Next step: run scripts\create_gui_shortcut.ps1 to add a Desktop shortcut." -ForegroundColor Yellow
} else {
    Write-Host "Build finished but exe not found at $exe" -ForegroundColor Red
    exit 1
}
