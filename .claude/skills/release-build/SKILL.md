---
name: release-build
description: Build a new QuoteTrip release (.exe and installer). Use when the user asks to build a release, cut a new version, build the installer, or ship an update.
disable-model-invocation: true
---

Walk through the release workflow for QuoteTrip (repo folder still named `voy_cotizador`). This is a Windows desktop packaging flow (PyInstaller + Inno Setup) — there is no CI, so every check below is manual.

## 1. Confirm the target version

Ask the user what version this release is (e.g. `1.2.0`) if not already stated.

## 2. Ask: patch or full release?

Two release types (see `README Actualizaciones.md`):
- **Patch** (`tipo: "parche"`) — only `app.py`/`quotetrip/`/`assets/` changed (features, fixes, PDF/UI tweaks). Ships a small `.zip`, applied in-app without reinstalling.
- **Full** (`tipo: "completo"`) — dependencies changed, `VoyCotizador.spec` itself changed (new/updated package, new hidden import, etc.), **or `desktop.py` changed**. Needs the full `Setup.exe`.

`desktop.py` is compiled into the `.exe` (PyInstaller `Analysis` entry point), not shipped as a loose file like `app.py` — a patch can never update it. **Any diff touching `desktop.py` forces a full release**, no exceptions. This also means the release that *first* ships this patch mechanism had to be full (existing installs need the new `desktop.py` before they can apply any patch at all) — already handled at runtime by `self_update.desktop_soporta_parches()`, which falls back to the full installer if the running `desktop.py` predates it, but don't rely on that as a substitute for getting this call right.

If unclear from the diff, ask the user rather than guessing — shipping a patch when a dependency (or `desktop.py`) changed leaves the runtime stale.

## 3. Check version sync BEFORE building

These must all show the same version:
- `quotetrip/config.py` — `APP_VERSION = "X.Y.Z"`
- `installer.iss` — `#define MyAppVersion "X.Y.Z"` (around line 12, full releases only, but keep it in sync regardless)
- `version.json` — `"version": "X.Y.Z"` at repo root

Grep all three and compare. If any are out of sync, update them to match the target version before building. Also sanity-check `version.json`'s `url` points at the real GitHub Releases asset for this repo (`TheProgramerBone/voy_cotizador`) — if it still has a placeholder or a stale filename, flag it to the user, or the in-app update check will send people to the wrong place.

## 4a. Patch release

Run `build_patch.bat` (zips `app.py` + `quotetrip/` + `assets/` from the repo root — no PyInstaller build needed). Output: `Output\QuoteTrip-Patch.zip` + `Output\QuoteTrip-Patch.sha256.txt`. Use that sha256 when updating `version.json` (`"tipo": "parche"`, `"sha256": "..."`, `"url"` pointing at the `.zip` release asset).

## 4b. Full release

Run `build_exe.bat` (`pyinstaller --noconfirm --clean VoyCotizador.spec` — the `.spec` filename itself wasn't renamed, only what it builds). Report any PyInstaller errors — do not proceed to the installer step if this fails.

Then `build_installer.bat` (re-runs `build_exe.bat`, then invokes Inno Setup's `ISCC.exe installer.iss`). Requires Inno Setup 6 installed locally (not pip-installable — from jrsoftware.org). If `ISCC.exe` isn't found, tell the user to install Inno Setup rather than trying to work around it.

Output: `Output\QuoteTrip-Setup.exe`. Use `"tipo": "completo"` in `version.json` (no `sha256` needed — the installer path doesn't check one).

## 5. After building

Remind the user:
- Full installer only: it's unsigned, so Windows SmartScreen will warn on first run (expected, documented in `README Instalador.md`). The patch `.zip` isn't an installer, so it skips SmartScreen entirely.
- Per `README Actualizaciones.md`, the build artifact (`.zip` or `Setup.exe`) + updated `version.json` need to be published to GitHub Releases on `TheProgramerBone/voy_cotizador` (remote already configured) for the in-app update notice (`UPDATE_URL` in `quotetrip/config.py`, pointed at this repo's `version.json` on `master`) to reach anyone.
- Patch releases apply on the *next* app restart (staged to `%LOCALAPPDATA%\QuoteTrip\update_staging\`, applied by `desktop.py` before the server starts) — not instantly on download.
- This release adds the account/login gate (`quotetrip/auth.py`) — a fresh install now starts with account registration instead of going straight into the app; worth a quick manual click-through after installing, not just trusting the build succeeded.
