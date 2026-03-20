# Windows Install

## Overview

Dipsy Dolphin supports both a quick local install flow and a real Inno Setup installer flow.

- Inno Setup installs app files to `%LOCALAPPDATA%\Programs\Dipsy Dolphin` by default
- The quick local install script copies app files to `%LOCALAPPDATA%\DipsyDolphin\app`
- Profile data is stored in `%LOCALAPPDATA%\DipsyDolphin\data\profile.json`
- The Inno Setup flow registers a normal Windows uninstaller for the current user

## Local build

Build the Windows app bundle with:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build-app.ps1
```

That script creates an isolated build virtual environment in `.artifacts\windows\.venv-build` and writes the packaged app bundle to `.artifacts\windows\pyinstaller\dist\DipsyDolphin`.

## Installer build

Build the Windows setup wizard with:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build-installer.ps1
```

Notes:

- The script first builds the app bundle unless `-SkipAppBuild` is supplied
- Inno Setup 6 must be installed so `ISCC.exe` is available
- The finished installer is written to `.artifacts\windows\installer\DipsyDolphin-Setup.exe`
- You can override the installer version with `-AppVersion` and the output file name with `-OutputBaseName`

If Inno Setup is not installed yet, one option is:

```powershell
winget install JRSoftware.InnoSetup
```

## Local install

For quick local testing without the wizard, install the packaged app for the current user with:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\install-local.ps1 -Build -DesktopShortcut
```

Notes:

- `-Build` rebuilds the app before copying it into the install directory
- `-DesktopShortcut` creates `Dipsy Dolphin.lnk` on the current user's desktop

## Uninstall

Remove the quick local install with:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\uninstall-local.ps1
```

That removes the quick local install, the stored profile data, and the desktop shortcut created by the local install script.

## GitHub Actions automation

Two workflows live in `.github/workflows/`:

- `main-prerelease.yml` builds on every push to `main`, uploads the installer as a workflow artifact, and updates the rolling prerelease tagged `main-latest`
- `release-installer.yml` builds on version tags matching `v*`, uploads the installer as a workflow artifact, and publishes a normal GitHub Release

Release versioning rules:

- A git tag like `v0.3.0` becomes installer version `0.3.0`
- The tagged release asset is named `DipsyDolphin-Setup-0.3.0.exe`
- Main prerelease assets are named like `DipsyDolphin-Setup-main-1a2b3c4.exe`
