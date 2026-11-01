# OES Eyeball native renderer proof of concept

This subtree is intentionally limited to proving that the canonical OES Eyeball can be
presented by a native Windows Direct3D 11 renderer. It is not the final animation system.

The source of truth remains `static/images/oes-logo.svg`. The build verifies that file's
SHA-256 and copies both it and the existing lossless 220x220 RGBA raster derivative into
the renderer output. Direct3D samples that verified derivative without changing its aspect
ratio. No generated or redrawn Eyeball is used.

## Build on the Windows OES machine

Use a Visual Studio x64 Developer PowerShell:

```powershell
cmake -S oes_core_renderer -B build/oes-core-renderer -A x64
cmake --build build/oes-core-renderer --config Release
```

Run the inventory first, then launch the proof:

```powershell
powershell -ExecutionPolicy Bypass -File oes_core_renderer/tools/windows_gpu_inventory.ps1
build/oes-core-renderer/Release/oes-eyeball-renderer.exe
```

The renderer writes `oes-eyeball-renderer-diagnostics.json` beside its executable. The
record includes the selected adapter, PCI vendor/device IDs, D3D feature level, hardware
versus WARP device type, initialization time, first-frame time, and working set.

Use `--force-warp` to prove the software fallback independently. A renderer failure exits
only this process. It cannot terminate the Python launcher, worker, Ollama, telemetry, or
tray, and the launcher's existing static canonical Eyeball remains its fallback.

The renderer uses a transparent DirectComposition swap chain and a minimal HLSL textured
quad. It intentionally has no animation, bat, particles, expression system, or glass shader.

## Developer tuning panel

The optional visual tuner is a separate standard-library Python process. It publishes a
versioned, bounded JSON parameter snapshot atomically under
`%LOCALAPPDATA%\OES\Core\Renderer\renderer-tuning.json`. The renderer polls that local file;
it does not open a socket or require the panel to be present. Renderer diagnostics flow in
the other direction through `renderer-diagnostics.json` in the same directory.

While both processes are running, the tuner finds the renderer by its fixed private window
class and temporarily uses the Win32 `SetParent` boundary to host that **actual D3D11 HWND**
inside its Live Native Preview frame. No Python or tkinter approximation of the Eyeball is
drawn. Closing the tuner restores the renderer's original top-level style, parent, position,
and dimensions, so standalone renderer operation remains unchanged.

After building the renderer, launch it normally and then launch the panel from the repository:

```powershell
build\oes-core-renderer\Release\oes-eyeball-renderer.exe
python -m oes_core_renderer.tuning_panel
```

The accepted baseline is encoded as `CANONICAL_PARAMETERS` in `tuning.py`. **Reset to
Canonical** republishes those exact values. **Hold Canonical** temporarily shows those values
and restores the current tuning on release. Save/Load Preset operates only on parameter JSON;
neither operation modifies `static/images/oes-logo.svg` or its verified raster derivative.
The renderer remains independently launchable and uses canonical defaults when no valid
control file exists. `--control` and `--diagnostics` may select alternate local files for
development/testing.

The current verified raster is 220x220, so enlargement can soften it. A future fidelity pass
can replace the WIC raster upload in `Renderer::create_texture` with a resolution-independent
SVG/vector render target (or a separately approved higher-resolution canonical derivative)
without changing identity ownership, the tuning schema, or a future animation/expression
layer. That work is intentionally not part of this panel pass.
