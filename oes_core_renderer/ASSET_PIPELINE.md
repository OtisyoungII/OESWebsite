# OES Eyeball character asset pipeline

The default Phase 1 character is procedural because Blender is not installed on the
validated Windows node. No `.blend` or exported glTF asset is claimed in this phase.

## Intended Blender to glTF 2.0 workflow

1. Model at real scale with the eye looking down Blender `-Z`, `+Y` up.
2. Apply object scale and rotation before export; retain named child objects for `body`,
   `iris`, `pupil`, `lens`, and `aperture_blade_00` through `aperture_blade_07`.
3. Use Principled BSDF materials with metallic, roughness, base color, emissive, and alpha
   only. Pack image textures beside the asset; do not use network or data URIs.
4. Export **glTF Separate (`.gltf` + `.bin`)**, selected objects only, with:
   - `+Y Up`
   - normals and UVs
   - materials and hierarchy
   - animation disabled unless an approved clip is intentionally authored
   - no Draco compression during the initial compatibility milestone
5. Run `python -m oes_core_renderer.gltf_pipeline path\to\character.gltf` after a CLI
   entry point is added with the runtime-loader milestone. The current validator is used
   programmatically by tests and rejects missing movable parts, remote buffers, traversal,
   and non-2.0 assets.

## Runtime-loader decision

The D3D11 renderer needs indexed positions, normals, UVs, node transforms, PBR material
factors, and separately addressable aperture meshes. The recommended next step is a pinned,
license-preserved lightweight glTF 2.0 parser such as `cgltf`, followed by a narrow D3D upload
adapter. The current ad-hoc tuning JSON reader is deliberately **not** expanded into a glTF
parser. Image decoding can continue through Windows Imaging Component.

Until Blender and the approved parser are available, the validated procedural character is
the runtime default and theme manifests must not refer to an external production model.
