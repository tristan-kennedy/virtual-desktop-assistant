$ErrorActionPreference = "Stop"

$PackagingRoot = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $PackagingRoot
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue

if (-not $UvCommand) {
    throw "uv is required to build Dipsy Dolphin. Install it with 'winget install --id=astral-sh.uv -e' and rerun packaging\windows\build-app.ps1."
}

& $UvCommand.Source run --project $RepoRoot python -m scripts.windows_build app @args

if ($LASTEXITCODE -ne 0) {
    throw "Windows app build failed."
}
