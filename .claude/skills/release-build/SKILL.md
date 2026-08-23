---
name: release-build
description: Build a new QuoteTrip release (.exe and installer). Use when the user asks to build a release, cut a new version, build the installer, or ship an update.
disable-model-invocation: true
---

Walk through the release workflow for QuoteTrip (repo folder still named `voy_cotizador`). This is a Windows desktop packaging flow (PyInstaller + Inno Setup) — there is no CI, so every check below is manual.

## 1. Confirm the target version

Ask the user what version this release is (e.g. `1.2.0`) if not already stated.

## 2. Check version sync BEFORE building

Three places must all show the same version:
- `quotetrip/config.py` — `APP_VERSION = "X.Y.Z"`
- `installer.iss` — `#define MyAppVersion "X.Y.Z"` (around line 12)
- `version.json` — `"version": "X.Y.Z"` at repo root

Grep all three and compare. If any are out of sync, update them to match the target version before building. Also sanity-check `version.json`'s `url` points at the real GitHub Releases asset for this repo (`TheProgramerBone/voy_cotizador`) — if it still has a placeholder or a stale filename, flag it to the user, or the in-app update check will send people to the wrong place.

## 3. Build the .exe

Run `build_exe.bat` (this runs `pyinstaller --noconfirm --clean VoyCotizador.spec` — the `.spec` filename itself wasn't renamed, only what it builds). Report any PyInstaller errors — do not proceed to the installer step if this fails.

## 4. Build the installer

Run `build_installer.bat` (this re-runs `build_exe.bat`, then invokes Inno Setup's `ISCC.exe installer.iss`). This requires Inno Setup 6 installed locally (not pip-installable — from jrsoftware.org). If `ISCC.exe` isn't found, tell the user to install Inno Setup rather than trying to work around it.

Output lands at `Output\QuoteTrip-Setup.exe`.

## 5. After building

Remind the user:
- The installer is unsigned, so Windows SmartScreen will warn on first run (expected, documented in `README Instalador.md`).
- Per `README Actualizaciones.md`, the installer/`version.json` need to be published to GitHub Releases on `TheProgramerBone/voy_cotizador` (the remote is already configured) for the in-app update notice (`UPDATE_URL` in `quotetrip/config.py`, already pointed at this repo's `version.json` on `master`) to actually reach anyone.
- This release adds the account/login gate (`quotetrip/auth.py`) — a fresh install now starts with account registration instead of going straight into the app; worth a quick manual click-through after installing, not just trusting the build succeeded.
