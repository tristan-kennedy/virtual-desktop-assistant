param(
    [string]$AppVersion = "0.1.0",
    [string]$OutputBaseName = "DipsyDolphin-Setup",
    [switch]$Clean,
    [switch]$SkipAppBuild
)

$ErrorActionPreference = "Stop"

$PackagingRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PackagingRoot)
$ArtifactsRoot = Join-Path $RepoRoot ".artifacts\windows"
$DistDir = Join-Path $ArtifactsRoot "pyinstaller\dist\DipsyDolphin"
$InstallerOutDir = Join-Path $ArtifactsRoot "installer"
$BuildAppScript = Join-Path $PackagingRoot "build-app.ps1"
$InstallerScript = Join-Path $PackagingRoot "dipsy-dolphin.iss"

if (-not $SkipAppBuild) {
    if ($Clean) {
        & $BuildAppScript -Clean -AppVersion $AppVersion
    }
    else {
        & $BuildAppScript -AppVersion $AppVersion
    }
}

if (-not (Test-Path $DistDir)) {
    throw "App bundle not found at $DistDir"
}

if ($Clean) {
    Remove-Item -Recurse -Force $InstallerOutDir -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $InstallerOutDir | Out-Null

$PossibleIsccPaths = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)

$IsccCommand = Get-Command iscc -ErrorAction SilentlyContinue
$IsccPath = if ($IsccCommand) { $IsccCommand.Source } else { $PossibleIsccPaths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1 }

if (-not $IsccPath) {
    throw "Inno Setup 6 was not found. Install it, for example with 'winget install JRSoftware.InnoSetup', then rerun packaging\windows\build-installer.ps1."
}

& $IsccPath "/DSourceDir=$DistDir" "/DOutputDir=$InstallerOutDir" "/DAppVersion=$AppVersion" "/DOutputBaseName=$OutputBaseName" $InstallerScript

$SetupExe = Join-Path $InstallerOutDir "$OutputBaseName.exe"
Write-Host "Built Windows installer into $SetupExe"
