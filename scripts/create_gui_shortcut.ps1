# Create a Desktop shortcut for demo-win-gui.exe.
# Usage: pwsh scripts\create_gui_shortcut.ps1
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $projectRoot "dist\demo-win-gui.exe"
if (-not (Test-Path $exe)) {
    Write-Host "exe not found: $exe. Run build_gui_exe.ps1 first." -ForegroundColor Red
    exit 1
}

$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Demo Win GUI.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "Demo Win GUI — content ingestion workstation"
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath" -ForegroundColor Green
Write-Host "Target: $exe" -ForegroundColor Gray
Write-Host "Working dir: $projectRoot" -ForegroundColor Gray
