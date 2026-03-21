$ErrorActionPreference = "Stop"

$PackagingRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PackagingRoot)
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue

if (-not $UvCommand) {
    throw "uv is required to build the Dipsy Dolphin installer. Install it with 'winget install --id=astral-sh.uv -e' and rerun packaging\windows\build-installer.ps1."
}

& $UvCommand.Source run --project $RepoRoot python -m scripts.windows_build installer @args

if ($LASTEXITCODE -ne 0) {
    throw "Windows installer build failed."
}
