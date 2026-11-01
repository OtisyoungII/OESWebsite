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
