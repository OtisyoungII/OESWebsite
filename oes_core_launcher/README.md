# OES Core Windows Launcher

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

Normal startup never asks for or displays the secret. Stop sends a private stdin
control message to the launcher-owned worker and waits before using bounded process
termination as a fallback. Ollama is probed every ten seconds; no inference is used
for health checks and the model may unload normally.

The shortcuts contain only the Python executable path, module name, working directory,
description, and icon path. They contain no worker credential or other secret. Re-running
the installer updates the same two `OES Core.lnk` files without launching OES Core.
