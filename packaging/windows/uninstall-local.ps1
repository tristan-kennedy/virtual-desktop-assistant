$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $env:LOCALAPPDATA "DipsyDolphin"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Dipsy Dolphin.lnk"

Remove-Item -Recurse -Force $InstallRoot -ErrorAction SilentlyContinue
Remove-Item -Force $ShortcutPath -ErrorAction SilentlyContinue

Write-Host "Removed local Dipsy Dolphin install from $InstallRoot"
