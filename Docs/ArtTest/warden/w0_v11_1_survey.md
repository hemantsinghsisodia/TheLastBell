# W0: survey of the owner's Warden V11.1 (2026-11-11)

Read-only. Unreal was closed and no Unreal process was started. The blend was opened in Blender 5.2.2 headless and never saved. The owner's folder was only read. All numbers are in `w0_v11_1_survey.json`; the scripts are `Tools/blender/warden/w0_survey_blend.py`, `w0_survey_fbx.py` and `w0_render_mask.py`.

**Headline findings (details below)**
1. Skeleton: compatible. 110 bones, same names, order and hierarchy, rest positions identical (0.000 cm). Only 19 bones differ in rest *roll* by 0.10-0.18 deg.
2. Mesh: 8 material slots, not 6. Slots 0-5 are unchanged in name and order; `M_Warden_DimEyes` (6) and `M_Warden_Keratin` (7) are new. Height 289.99 cm. Triangles are down 5.5 % (LOD0 94,515), but the engine vertex count is up 9-20 %. The FBX exports need the same +90 deg rotation as P13.
3. Clips: not identical. Legs, spine, head and upper arms are unchanged; lower arms, hands, fingers and the chains differ by up to 19.5 cm.
4. Mask: all of slot 1 is the mask, 100 % on `head`. Under it is a black hood interior, with no face. A `HoodVoid` is not needed.
5. Materials: the mask slot has no `Fade` and no `TellGlow` and is opaque (so the plan's `M_LB_Invisible` fallback applies). Our current `M_Warden_BellMetal` has `TellGlow` but no `Fade`.
6. **A problem the task did not ask about:** V11.1 does not contain the P13-4c reweight. Its robe skin weights are back at V5.5's level (section 8).
7. `SM_LB_Warden_Apparition` is a baked copy of V5.5 and goes stale (section 7).

## 1. Copy into the repo

| Item | Result |
|---|---|
| `SourceArt/Warden/V11_1/` | `Warden_Rigged.blend`, `exports/` (3 mesh LOD + 3 clip FBX), `previews/` (with `previews/unreal`), `reports/`, `scripts/`, `README.md` (the owner's `Unreal-README.md`). Blend and the six FBX copied byte-identical (SHA-256 checked against the source). |
| LFS | `.gitattributes` puts `*.blend`, `*.fbx`, `*.png`, `*.jpg` on LFS. `V5_5w2` is stored the same way (`git lfs ls-files` lists its blend, `exports` and `ue_lod`). So V11_1 follows it; nothing is a plain blob. |
| Zip | Not copied. Its SHA-256 `8ee91d13...779a` matches the owner's `.sha256` file. |
| Extraction | `Content/WardenArtV11_1/` (35 files) and `Verification/` (7 JSON) went to `ExternalAssets/Incoming/warden_v11_1/`. `git check-ignore -v` confirms the ignore rule (`.gitignore` line 21). All 42 files match the zip's `SHA256.json`. |
| Size | About 360 MB of new LFS objects (blend 329 MiB, FBX 11 MB, previews 19 MB). The repo already tracks about 6.9 GB in LFS, so check the GitHub LFS quota before the owner pushes. |

## 2. Skeleton compatibility (V11.1 blend vs `SourceArt/Warden/V5_5w2` blend)

| Check | Result |
|---|---|
| Armature | `Warden_Rig`, 110 bones in both |
| Names, order, parents | identical; 0 parent differences |
| Rest head positions | max difference 0.000 cm; **0 bones above 0.1 cm** |
| Rest tail positions | max difference 0.000 cm; 0 bones above 0.1 cm |
| Rest orientation (roll) | 19 bones differ by 0.10-0.18 deg: `middle_03_l/r` 0.175, `index_03_l/r` 0.149, `spine_02` 0.148, `thumb_03_l/r` 0.147, `robe_04_01` 0.140, `ring_03_l/r` 0.132, `robe_01_01` 0.130, `robe_03_02` 0.129, `robe_06_01` 0.128, `robe_05_02` 0.121, `hand_l/r` 0.118, `head` 0.104, `ring_01_l/r` 0.102. At finger length that is about 0.01 cm. |
| Head bone | head at (0, -30.62, 239.37) cm, same as before. Rest axes: bone Y = world up, bone Z = the Warden's forward (world -Y), bone X = world +X |
| `mask` socket | The project's `SK_Warden` has a mesh socket `mask` on `head` at zero offset (`p13_reimport_pre.json`). **The native V11.1 `SK_Warden.uasset` has no socket** (no `SkeletalMeshSocket`, no `mask` name). |
| Owner's own check | `import-v11_1.json`: the mesh imported onto `/Game/WardenArtV5/Meshes/SK_Warden_Skeleton` and passed |

The UE `SK_Warden_Skeleton` was not read (Unreal closed), so the comparison is against the V5_5w2 blend, which is what P13 imported.

## 3. Mesh

| | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Triangles, V11.1 FBX | 94,515 | 45,536 | 17,861 |
| Triangles, V5_5w2 (current) | 99,974 | 49,975 | 19,973 |
| Vertices in the FBX / blend, V11.1 | 48,538 | 23,776 | 9,564 |
| Engine vertices, owner's native import | 82,658 | 52,741 | 26,852 |
| Engine vertices, our `SK_Warden` now | 75,603 | 45,003 | 22,347 |
| Engine vertex change | +9 % | +17 % | +20 % |
| Rest height | 289.99 cm | 290.07 cm | 290.16 cm |

Height is 290 cm as expected (rest pose; the current mesh is 290.00). Bounds in the blend frame (LOD0): X -66.6..97.5, Y -61.0..75.2, Z 0.1..290.1 cm.

**Material slots (identical in all three FBX LODs):**

| Index | Slot / material name | Triangles LOD0 | Current `SK_Warden` | Status |
|---|---|---|---|---|
| 0 | `M_Warden_Wool` | 26,516 | `M_Warden_Wool` (33,007) | same name |
| 1 | `M_Warden_BellMetal` | 9,252 | `M_Warden_BellMetal` (8,513) | same name (the mask) |
| 2 | `M_Warden_RustedIron` | 872 | `M_Warden_RustedIron` (1,331) | same name |
| 3 | `M_Warden_Skin` | 28,506 | `M_Warden_Skin` (28,506) | same name |
| 4 | `M_Warden_Leather` | 7,745 | `M_Warden_Leather` (7,241) | same name |
| 5 | `M_Warden_ChainIron` | 21,324 | `M_Warden_ChainIron` (21,376) | same name |
| 6 | `M_Warden_DimEyes` | 40 | none | **new** |
| 7 | `M_Warden_Keratin` | 260 | none | **new** |

So the first six slot indices are stable (the mask is still index 1; `LBWardenFunctionalTests` finds it by name). A reimport adds two slots and needs two materials assigned.

**Orientation.** The unrotated V11.1 FBX bounds centre is (15.45, 7.11) cm; V5_5w2's was (15.46, 7.50), and its rotated export (-7.50, 15.46). The V11.1 export uses the same `export.py` logic, the same `-Y` forward / `Z` up axes and the same facing (`-Y` in the blend). **The P13 rule applies unchanged**: the exports need the +90 deg Z turn, (x, y) to (-y, x), before the Force-Front-X import. I ran `p13_export_lods_rotated.py` on the V11.1 blend into a scratch folder: it works, writes three files, and gives bounds centre (-7.11, 15.45) as expected. Those rotated files are not committed; W1 should produce them into `SourceArt/Warden/V11_1/ue_lod/`.

**Other mesh notes**
- `reports/export.log` warns that each LOD has polygons with more than 4 vertices, so the FBX carries no tangents (18 n-gons in LOD0: slots 0, 1, 5, 7). The V5_5w2 mesh had none. UE will compute tangents on import; check the look of the normal maps, or ask the owner to triangulate.
- The blend carries 15 leftover mesh objects (`SK_Warden_LOD0/1/2.001..005`, the LOD0 ones 94-99k polygons each and not hidden from render) and 5 extra rigs. The export scripts select by exact name, so they are unaffected.

## 4. Clips (current = `SourceArt/Warden/V5_5/exports/AN_Warden_*.fbx`; P13 never changed them)

All three file hashes differ, but FBX files carry timestamps, so I imported each pair into Blender with identical settings and compared the armature-space bone positions at 5 frames per clip (110 bones).

| Clip | Frames (both) | Bones unchanged (< 0.1 cm) | Bones changed | Max difference | Worst bone |
|---|---|---|---|---|---|
| `AN_Warden_Idle` | 2-122 (4.0 s, 30 fps) | 52 | 58 | 19.5 cm | `middle_03_l` |
| `AN_Warden_Walk` | 2-62 (2.0 s) | 52 | 58 | 19.5 cm | `middle_03_l` |
| `AN_Warden_DoorwayStoop` | 2-92 (3.0 s) | 52 | 58 | 29.9 cm | `chain_l_08` |

**Verdict: not identical.**
- Unchanged: `root`, `pelvis`, `spine`, `neck`, `head`, `clavicle`, `upperarm`, `thigh`, `calf`, `foot`, `ball`, `robe`, `chain_neck`.
- Changed by a near-constant offset: `lowerarm` (up to 5.7 cm), `hand` (up to 13.7), the fingers (up to 19.5) and `chain_l/r` (up to 16.2; the stoop's left chain up to 29.9).
- This is the new arm and hand pose, so the walk and the stoop's body motion are the same.
- The Idle is nearly a held pose: the largest bone movement over the clip is 0.17 cm (0.0 in the current one).
- The owner's `check-v11_1.json` reports a clip-to-blend error of at most 0.0007 cm.

## 5. Mask (plan F0b)

| Item | V11.1 | V5_5w2 (for comparison) |
|---|---|---|
| Faces | slot 1 `M_Warden_BellMetal`, LOD0 9,156 polygons / 9,252 triangles / 4,688 vertices / 1,539 cm2 | 8,513 triangles / 4,428 vertices / 1,234 cm2 |
| Islands | 9: the shell (4,536 vertices), six mouth studs (20 each) and two small ones near the left eye. Everything in slot 1 is mask | 1 |
| Weights | **every vertex has exactly one influence, `head` = 1.0** (100 %), in LOD0, LOD1 (561 verts) and LOD2 (278 verts) | same |
| Largest non-`head` weight | none (0) | none |
| Size | 19.2 cm wide, 32.8 cm tall, 14.1 cm deep | 15.2 x 32.2 x 11.9 cm |

**Mask bounds in `head` bone space** (Blender axes; X = Warden's left, Y = up, Z = forward), cm:

| | min | max |
|---|---|---|
| X | -9.69 | 9.40 |
| Y | -6.74 | 24.51 |
| Z | 6.33 | 22.73 |

Centroid (0.73, 8.68, 15.74). World, Blender frame: X -9.6..9.6, Y -52.6..-37.1, Z 233.2..264.5 cm. In SK mesh space (Unreal, derived by the P13 rotation rule, not read from the engine): X 37.1..52.6, Y -9.6..9.6, Z 233.2..264.5, centroid (46.1, -0.4, 248.6). The mask is about 25 % larger in area than V5.5's, so P17-3's `SM_LB_WardenMask` must be cut from this blend, not the old one.

**Renders** (`Docs/ArtTest/cine/p17_f0b_mask_on.png`, `p17_f0b_mask_off.png`): Cycles, the owner's `closeups.py` "mask" camera, Idle frame 1, the owner's three lights, grey backdrop, LOD0 only, mask faces deleted in memory for the second.

**What is under the mask: a void.**
- There is no face, no skin and no head geometry. The Skin slot is forearms and hands only (Z 80-194 cm).
- A 40 x 40 ray grid through the mask outline, with the mask removed, hit the two-sided wool hood interior (935 of 985 rays), on average 17 cm behind the mask's back plane. That renders black.
- The rest of the rays hit the small leather bits at the cheeks (27) and keratin pieces just behind the mask surface (23).
- What stays on the head when the mask faces go (all 100 % `head`):
  - two thin `DimEyes` strips behind the eye slits (the orange pin-points in the render; 6.8 cm behind the mask front);
  - two keratin rings at the eye slits;
  - six tiny keratin dots at the mouth, where the six metal studs are;
  - two leather bits at the cheeks.
- A brighter test render (exposure +2.5, not committed) shows nothing else.

By plan section 4.2 (only a dark hood interior shows), **no `SM_LB_WardenHoodVoid` is needed.** The six keratin dots are visible specks once the mask lifts; they are small enough to accept.

## 6. Materials (F0 item 6)

Source: `Verification/materials-v11_1.json`, `cloth-update-v11_1.json` and the names and enum values readable in the native `.uasset` files. The numeric defaults inside the `.uasset` files are binary and were not decoded.

| Slot | Material | Parameters | Blend mode |
|---|---|---|---|
| 0 | `MI_Warden_Wool` (instance of `M_Warden_Wool`) | Weave Scale 12.2935, Detail Strength 0.5, Wetness 0.15, Cloth Brightness 0.72 (the project's own wool instance sets Cloth Brightness 0.25) | opaque, two-sided |
| 1 | `M_Warden_BellMetal` | **none**: three texture samples and constants | `BLEND_Opaque`, DefaultLit |
| 2 | `M_Warden_RustedIron` | none | opaque |
| 3 | `M_Warden_Skin` | `Skin Brightness` | opaque |
| 4 | `M_Warden_Leather` | none | opaque |
| 5 | `M_Warden_ChainIron` | none | opaque |
| 6 | `M_Warden_DimEyes` (new) | `Eye Glow`, `Eye Fade Start cm`, `Eye Fade End cm`; no textures; emissive driven by the distance to the camera | opaque |
| 7 | `M_Warden_Keratin` (new) | none; constant colour and roughness | opaque, DefaultLit |

**Does the bell-metal (mask) material have a scalar `Fade` (translucent or masked) and a scalar `TellGlow`?** No on both counts. V11.1's `M_Warden_BellMetal` has no scalar parameters at all and is `BLEND_Opaque`. Our current project `M_Warden_BellMetal` is also opaque; it has `TellGlow` and `TellGlowColor`, added by `Tools/warden/apply_p12f_art.py` (D-092), and no `Fade`. So the plan's fallback applies: P17-5a switches the mask slot to `M_LB_Invisible` (or builds a `Fade` variant). `TellGlow` must be re-added to the new `M_Warden_BellMetal` for the Warden's attack tell and the P17 `MaskProp` glow.

**Textures:** 20, in the same layout as now (6 at 4096 for wool and skin, 2 at 1024 for the wool detail, 12 at 2048). The estimate with all mips is 136.5 MB, against about 130 MB now (`p12_9_qa.md`), so about +6 MB. The `.uasset` bytes for the textures go from 35 MB to 64 MB, because the BellMetal, RustedIron, Leather and ChainIron maps are now real detailed maps (the project's BellMetal and RustedIron texture packages are only 26-66 KB). Mesh memory: the native `SK_Warden.uasset` is 35.2 MB against our 32.4 MB; the engine vertex count is up 9-20 %.

## 7. Dependents in our project (text search)

Method: bytes of the first 24 MB of each of the 1,929 `.uasset`/`.umap` files under `Content`, plus `Source/` and `Tools/`. No external-actor file mentions a Warden path (only the editor's asset registry would show soft references).

| Target | Referenced by |
|---|---|
| `SK_Warden` | 26 assets: `BP_Warden`, `BP_WardenApparition`, `LS_LB_Finale`, `ArtTest/P17/LS_P17_Spike` (git-ignored), `SK_Warden_Skeleton` and `SK_Warden_PhysicsAsset` (back-links), the 12 git-ignored Mixamo `AN_Warden_*` clips, `AM_Warden_Attack/LookAround/TurnLeft90/TurnRight90`, `BS_Warden_Locomotion`, `BS_Warden_Stoop`, and the git-ignored `Retarget/` IK and retargeter. `ABP_Warden` and `DA_WardenAnimSet` reach it through the skeleton and montages. |
| Current Warden materials | only `SK_Warden` (its six slots: five `MI_Warden_*` and `M_Warden_Leather`); the `MI_Warden_*` use `M_Warden_*` and the 20 textures. Nothing outside `Characters/Warden/` references them. |
| `SM_LB_Warden_Apparition` | `BP_WardenApparition` only (with `MI_Warden_Apparition_Body/Mask`, which stay valid) |
| `Source/` | `LBWardenFunctionalTests.cpp` finds the slot by name `M_Warden_BellMetal` and reads `TellGlow`; `LBWardenApparition.cpp` loops over all slots of the apparition mesh. Nothing hard-codes a slot index. |
| `Tools/` | `Tools/warden/*` (`p13_reimport_warden`, `apply_p12*`, `check_warden`, `p13_*`), `Tools/blender/warden/*`, `Tools/cine/p17_sequences.py` and `p17_s1_spike.py` (path constants) |

**Baked static copy that goes stale: `SM_LB_Warden_Apparition`.** Per `SourceArt/Warden/SM_LB_Warden_Apparition.fbx.json` it was made by `bake_silhouette.py` from the **V5.5** blend (not V5_5w2): LOD2, `Warden_Idle` frame 1 pose, welded, decimated to 7,389 triangles, two slots (`MAT_Body`, `MAT_Mask`), `--rotz 90`. After the swap it would still show V5.5's arm and hand pose, robe, hood and a smaller mask. Fix: re-bake from the V11_1 blend (the script's `MASTER` constant points at V5_5, so it needs a path option), re-import over the static mesh, and check the mask islands, because V11.1 has nine bell-metal islands where the script assumed one.

Also unchanged by an in-place reimport but worth a look: `SK_Warden_PhysicsAsset` (bodies follow the bones, which are identical), and `ABP_Warden`, the blend spaces and `DA_WardenAnimSet` (they reference the clips, which stay if the clips are reimported in place).

## 8. Skin weights: V11.1 lacks the P13 reweight

P13-4c reweighted the V5.5 robe (leg share cap, sleeves, feet, turn flaps, seam feather) to make V5_5w2. V11.1 was built from V5.5's weights and its robe is re-formed (median distance to the V5.5 wool vertices is 3.4 cm, so a vertex-for-vertex comparison is impossible), and its weights act like V5.5's:

| Measure | V5.5 original | V5_5w2 (in the project) | V11.1 |
|---|---|---|---|
| Wool vertices with more than 50 % on leg bones | 70 of 17,203 | 0 of 17,203 | 100 of 14,298 |
| Wool-edge stretch, max ratio (P13 metric) on MutantWalking / MutantRun / CrouchedWalking / ZombieAttack | 124 / 189 / 92 / 242 | 24 / 30 / 43 / 44 | **117 / 180 / 92 / 233** |
| Near P13-changed vertices, closer to V5.5 than to V5_5w2 | | | 2,913 vs 810 |

I ran `p13_reweight.py --mode measure` on the V11.1 LOD0 FBX with the P13 review clips (which are local only), writing the report to a scratch file. `Docs/ArtTest/warden/p13_reweight.json` was not touched. The worst edges are 0.46 cm wool edges in the shoulder and chest band, the V5.5 pattern. P13 itself did not reach its pass criterion; it shipped the reduction from about 124-242 to 24-44. Whichever integration route is used, the weights come from the FBX or native asset, so the P13 fix is lost unless it is redone on V11.1. The rules are location-based in the master frame and may carry over, but the robe changed shape, so they must be re-measured.

## Recommended integration route

**In-place FBX reimport onto our `SK_Warden`, with the native V11.1 materials and textures copied to `/Game/WardenArtV11_1/` and slots 0-7 assigned.**

1. Extend the V5.5 precedent. The mesh is reimported in place (P13's `p13_reimport_warden.py`, `reimportlods`, from `Tools/blender/warden/p13_export_lods_rotated.py` output). The materials and textures are file-copied as a reference closure (`copy_v5_5.py`) and then tuned with `apply_p12_materials.py` and `apply_p12f_art.py`, which were written to be re-applied to newly brought-in owner materials.
2. Run it headless with Unreal closed, as P13 did.
3. Reimport the three clips in place onto the existing `AN_Warden_Idle/Walk/DoorwayStoop`, so `ABP_Warden`, the blend spaces and `DA_WardenAnimSet` keep their references. The owner's README says: skeleton selected, scene/unit conversion, scale 1, custom sample rate 30, use exported duration.

**Why not the native copy.** A new `/Game/WardenArtV11_1/Meshes/SK_Warden` package would have to replace 26 references (`BP_Warden`, `BP_WardenApparition`, `LS_LB_Finale`, the montages, the blend spaces). It points at `/Game/WardenArtV5/Meshes/SK_Warden_Skeleton` and `..._PhysicsAsset`, which our project does not have (ours are at `/Game/LastBell/Characters/Warden/Meshes/`), so it needs redirectors or a second skeleton. It has no `mask` socket (the catch camera and the P17 plan depend on it). Its slots and LODs would come with the owner's import settings rather than the settings P13 proved for our asset.

**Required work, in this order (each is a W1+ step, not part of W0):**
1. **Decide the reweight (section 8).** Either accept V5.5-grade robe stretch, or run the P13 reweight on a copy of the V11.1 blend (needs a source-path option in `p13_reweight.py`) and re-measure, before generating the FBX.
2. Generate the rotated LOD exports into `SourceArt/Warden/V11_1/ue_lod/` (the script works as is).
3. Reimport (`reimportlods`). The script's `stable()` before/after check must be updated for 8 slots instead of 6 (`lod_sections` and `lod_section_material_slot` go from 6 to 8 entries); the `mask` socket must survive; LOD build settings are restored by the script.
4. Copy the native material and texture closure, assign slots 0-7 (by slot name), and re-add `TellGlow` and `TellGlowColor` to the new `M_Warden_BellMetal`. Reapply the P12 tuning values (the project's wool Cloth Brightness is 0.25, native 0.72; skin brightness 0.12). Verify the check and the `LastBell.Functional.Warden.Tell.MaskGlowFollowsState` test.
5. Re-bake `SM_LB_Warden_Apparition` from V11_1.
6. Cut `SM_LB_WardenMask` from the V11.1 blend (slot 1, all nine islands, 100 % `head`), and build the mask-lift clip (P17-3) against the V11.1 mask outline.

**Risks.**
- Reweight regression (section 8): the largest.
- Memory: the texture streaming pool needs about +6 MB, engine vertex count is up 9-20 % per LOD (LOD0 about +7k vertices), mesh asset about +3 MB, and the repo gets about +360 MB of LFS plus about +30 MB of `.uasset` textures.
- No tangents in the FBX (n-gons): check normal-map shading after the import.
- The `.blend` leftovers (15 extra meshes, 5 extra rigs) are harmless to the scripts but heavy.
- The arm and hand pose changed in all three clips, so check every clip contact point that depends on the hands (chain shackles, door-grab or mask-lift IK targets) once imported.
- Licence: V5_5 carried the Hunyuan3D/Modly licence texts in `licences/`; V11.1 ships none. The asset registry row (R-53) needs updating, as before.
- Two new slots mean 8 sections per LOD instead of 6 (two more draw calls per LOD on the Warden); `M_Warden_DimEyes` and `M_Warden_Keratin` are tiny and opaque, so the cost is small, but it was not measured (no editor).
