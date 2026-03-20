param(
    [switch]$Clean,
    [string]$AppVersion = "0.1.0"
)

$ErrorActionPreference = "Stop"

$PackagingRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $PackagingRoot
$ArtifactsRoot = Join-Path $RepoRoot ".artifacts\windows"
$BuildVenv = Join-Path $ArtifactsRoot ".venv-build"
$PyInstallerRoot = Join-Path $ArtifactsRoot "pyinstaller"
$WorkPath = Join-Path $PyInstallerRoot "build"
$DistPath = Join-Path $PyInstallerRoot "dist"
$SpecPath = Join-Path $PyInstallerRoot "spec"
$PythonExe = Join-Path $BuildVenv "Scripts\python.exe"
$PyLauncher = Get-Command py -ErrorAction SilentlyContinue
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($Clean) {
    Remove-Item -Recurse -Force $PyInstallerRoot -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $ArtifactsRoot | Out-Null
New-Item -ItemType Directory -Force -Path $WorkPath | Out-Null
New-Item -ItemType Directory -Force -Path $DistPath | Out-Null
New-Item -ItemType Directory -Force -Path $SpecPath | Out-Null

if (-not (Test-Path $PythonExe)) {
    if ($PythonCommand) {
        & $PythonCommand.Source -m venv $BuildVenv
    }
    elseif ($PyLauncher) {
        & $PyLauncher.Source -3 -m venv $BuildVenv
    }
    else {
        throw "Python 3 is required to build Dipsy Dolphin."
    }

    if (-not (Test-Path $PythonExe)) {
        throw "Virtual environment creation failed. Expected $PythonExe to exist."
    }
}

& $PythonExe -m pip install --upgrade pip pyinstaller
& $PythonExe -m PyInstaller --noconfirm --clean --windowed --onedir --name DipsyDolphin --paths $RepoRoot --specpath $SpecPath --distpath $DistPath --workpath $WorkPath (Join-Path $RepoRoot "main.py")

$OutputDir = Join-Path $DistPath "DipsyDolphin"
Write-Host "Built Dipsy Dolphin app bundle $AppVersion into $OutputDir"
