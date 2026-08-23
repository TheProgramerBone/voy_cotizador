---
name: release-build
description: Build a new VoyCotizador release (.exe and installer). Use when the user asks to build a release, cut a new version, build the installer, or ship an update.
disable-model-invocation: true
---

Walk through the release workflow for voy_cotizador. This is a Windows desktop packaging flow (PyInstaller + Inno Setup) — there is no CI, so every check below is manual.

## 1. Confirm the target version

Ask the user what version this release is (e.g. `1.2.0`) if not already stated.

## 2. Check version sync BEFORE building

Three places must all show the same version:
- `app.py` — `APP_VERSION = "X.Y.Z"` (around line 79)
- `installer.iss` — `#define MyAppVersion "X.Y.Z"` (around line 12)
- `version.json` — `"version": "X.Y.Z"` at repo root

Grep all three and compare. If any are out of sync, update them to match the target version before building. If `version.json`'s `url` still has the `USUARIO/REPO` placeholder, flag it to the user — that must point at the real GitHub repo before this file is published, or the in-app update check will fail.

## 3. Build the .exe

Run `build_exe.bat` (this runs `pyinstaller --noconfirm --clean VoyCotizador.spec`). Report any PyInstaller errors — do not proceed to the installer step if this fails.

## 4. Build the installer

Run `build_installer.bat` (this re-runs `build_exe.bat`, then invokes Inno Setup's `ISCC.exe installer.iss`). This requires Inno Setup 6 installed locally (not pip-installable — from jrsoftware.org). If `ISCC.exe` isn't found, tell the user to install Inno Setup rather than trying to work around it.

Output lands at `Output\VoyCotizador-Setup.exe`.

## 5. After building

Remind the user:
- The installer is unsigned, so Windows SmartScreen will warn on first run (expected, documented in `README Instalador.md`).
- Per `README Actualizaciones.md`, the installer/`version.json` are meant to be published to GitHub Releases — this repo currently has no git remote configured, so that step is manual/external until one is set up.
- `UPDATE_URL` in `app.py` is empty by default (update-check disabled); it must point at the hosted `version.json` for the in-app update notice to work.
