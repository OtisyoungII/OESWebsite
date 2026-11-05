# OES Core Windows Launcher

The **Eyeball** tab includes **Open 3D Eyeball**, **Open 3D Tuner**, and
**Close Eyeball** controls. OES Core resolves only
`build/oes-core-renderer/Release/oes-eyeball-renderer.exe` beneath its own
repository checkout; it never searches PATH or another checkout for an older binary. If the
renderer has not been built, the launcher displays the exact local CMake build command.

The launcher controls the existing `python -m worker` process. It does not implement
inference, relay communication, or public chat policy.

## Development setup

1. Install `launcher-requirements.txt` into the repository virtual environment.
2. Copy `config.example.json` to `%LOCALAPPDATA%\OES\Core\config.json` and replace
   the model digest. This file contains non-secret configuration only.
3. Run `.venv\Scripts\python.exe -m oes_core_launcher.provision` once. Enter the
   rotated shared key in the masked provisioning window. It is stored as a Generic Credential
   named `OES Core/Outbound Worker` in Windows Credential Manager.
4. Run `.venv\Scripts\python.exe -m oes_core_launcher.install_shortcut` once.
   This installs or updates both the desktop shortcut and the per-user Windows
   Startup shortcut named **OES Core**.
5. OES Core launches automatically at Windows sign-in. Double-click **OES Core**
   on the desktop to start it manually. For direct development startup, run
   `.venv\Scripts\pythonw.exe -m oes_core_launcher`.

The checked-in Eyeball icon and launch PNGs preserve the website artwork from
`static/images/oes-logo.svg`; only the icon container, baseball bat, and impact accent are
composed around it. Rebuild every Windows icon size and both launch states with
`.venv\Scripts\python.exe tools\build_oes_core_icon.py`.

Normal startup never asks for or displays the secret. Stop sends a private stdin
control message to the launcher-owned worker and waits before using bounded process
termination as a fallback. Ollama is probed every ten seconds; no inference is used
for health checks and the model may unload normally.

The shortcuts contain only the Python executable path, module name, working directory,
description, and icon path. They contain no worker credential or other secret. Re-running
the installer updates the same two `OES Core.lnk` files without launching OES Core.

## Operations console telemetry

OES Core stores content-free operational events in
`%LOCALAPPDATA%\OES\Core\telemetry.db`. The Overview, Eyeball, Activity, Health and
Audit tabs read that local database only while the window is visible. Prompts, responses,
public lookup queries/evidence, URLs, network addresses, credentials and protocol secrets
are excluded by the shared event schema.

The authenticated worker receives bounded at-least-once event batches in its existing
connect, heartbeat and idle-poll responses. It acknowledges event IDs only after a local
SQLite transaction succeeds. Telemetry failures do not stop worker polling, heartbeats or
inference. Detailed events expire after 30 days; small daily aggregate rows remain for
long-term totals. All-time means since the telemetry start date displayed in the console.
Visitor sessions, conversations and new/returning visitors are intentionally not measured.
