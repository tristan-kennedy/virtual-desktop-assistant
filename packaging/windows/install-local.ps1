param(
    [switch]$Build,
    [switch]$DesktopShortcut
)

$ErrorActionPreference = "Stop"

$PackagingRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PackagingRoot)
$BuildScript = Join-Path $PackagingRoot "build-app.ps1"
$DistDir = Join-Path $RepoRoot ".artifacts\windows\pyinstaller\dist\DipsyDolphin"
$BuiltExe = Join-Path $DistDir "DipsyDolphin.exe"
$InstallRoot = Join-Path $env:LOCALAPPDATA "DipsyDolphin"
$InstallAppDir = Join-Path $InstallRoot "app"
$LauncherPath = Join-Path $InstallAppDir "DipsyDolphin.exe"

if ($Build -or -not (Test-Path $BuiltExe)) {
    & $BuildScript
}

New-Item -ItemType Directory -Force -Path $InstallAppDir | Out-Null
Copy-Item -Path (Join-Path $DistDir "*") -Destination $InstallAppDir -Recurse -Force

if ($DesktopShortcut) {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "Dipsy Dolphin.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $LauncherPath
    $Shortcut.WorkingDirectory = $InstallAppDir
    $Shortcut.IconLocation = "$LauncherPath,0"
    $Shortcut.Save()
}

Write-Host "Installed Dipsy Dolphin locally to $InstallAppDir"
Write-Host "User data will be stored in $InstallRoot\data"
