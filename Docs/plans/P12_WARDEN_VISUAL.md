# Phase 12: Warden visual: plan

**Status:** approved by the owner on 2026-11-04. P12-0 to P12-3 done. **At P12-3 the owner supplied their own Warden Art V5 (D-090). The tasks from P12-4 on were rewritten; "The route from P12-4 on" below is the live spec.** P12-4 in progress.
**Branch:** `claude/phase-12-warden-visual`, from `main` (0df20fc).
**Rules:** D-048 applies. The lead plans in Opus 5.5 at xhigh effort; every implementer is spawned with `model: "sonnet", effort: "high"`. Nothing starts without the owner's "go".

## The route from P12-4 on (D-090, 2026-11-04)
**This section replaces everything below about the design, budgets, `M_LB_Character`, the scripted build and tasks P12-4 to P12-7. Those sections stay as a record only.** P12-1's findings, the standing limits, the failure-mode table in P12-8 and P12-9 still apply where this section doesn't change them.

### What the owner supplied
Warden Art V5 (28 Oct), in `C:\Hemant\Prj\Learning\Warden\output\`: Blender master and FBX in `warden_art_v5`, native assets in `unreal_validation/Content/WardenArtV5` (isolated project `WardenAssetValidation`, UE 5.8.3).

| Item | V5 |
|---|---|
| Design | Pointed hood, long cracked bell-metal mask with eye slits, layered cape, rope belt, torn robe, boots, wrist shackles, neck and wrist chains |
| Height | 290 cm |
| Top of the figure by clip | Idle 290.0–290.3; Walk 288.8–291.8; DoorwayStoop 290 down to **217.4** |
| Triangles | LOD0 75,764; LOD1 37,882; LOD2 18,941 |
| Sections | 6: Wool, BellMetal, RustedIron, Skin, Leather, ChainIron |
| Skeleton | 110 bones, root `root`, ≤ 4 influences. Mannequin-like names, but 3 spine bones, no twist, metacarpal or `ik_` bones. 41 chain bones, 16 robe bones |
| Clips | `AN_Warden_Idle` 4 s, `AN_Warden_Walk` 2 s, `AN_Warden_DoorwayStoop` 3 s; 30 fps, in place |
| Textures | 20: wool and skin 4K, others 2K, two wool detail maps 1K |

**Its own README:** a review build, not production-approved; hands use reduced surfaces; hood and shoulder edges are too regular; UV seams, shimmer between LODs and fine hand transitions still need art review. The physics asset needs tuning. Its validation checks structure, not looks.

**Lead's review of the renders:**
- The hands have white flecks, and they and the forearms read too pale; forearms look like tubes where the sleeves end.
- The mask's eye slits are stair-stepped and the hood rim is jagged.
- In DoorwayStoop the head vanishes into a lump in the rendered views. The height works: 217.4 clears the 230 doors and the 224 tower door.
- Walk dips 1.31 cm below the floor.
- Materials were tuned with no Lumen, on DX11. This project uses Lumen, so nothing about how it looks here is known yet.

### P12-4: bring it in (owner, then technical-artist [EDITOR])
**Migrate wasn't possible, so the lead copied the files (2026-11-04).** The isolated project sets `DisableEnginePluginsByDefault`, so its Content Browser has no asset list and its editor has no plugin window. The owner found this. Instead of changing that project, `Tools/warden/copy_v5.py` copied what Migrate would have copied, with TheLastBell closed, into `Content/WardenArtV5/`:
- 33 assets, 42.4 MB, each checked by MD5 (`Docs/ArtTest/warden/p12_v5_copy.json`). `Preview` left out.
- Checked first: same engine build (5.8.3-58210709), no reference to `/Game` outside the set, and nothing depends on `Preview`.
- The owner's folder was only read.

**Technical-artist, no owner:**
1. `AssetTools.move` everything from `/Game/WardenArtV5/` to `/Game/LastBell/Characters/Warden/{Meshes,Anims,Materials,Textures}/`, keeping the names. Confirm references with `get_dependencies`, then remove the empty folder. Nothing stays in the Content root.
2. **`Tools/warden/check_warden.py`, read-only, prints n/n:**
   - bones 110, root `root`; height 290 ± 1;
   - 3 LODs; 6 sections, each with its material; physics asset assigned;
   - 20 textures, with sRGB and compression as in V5's `Reports/validation-v5.json`;
   - clips 4, 2 and 3 s on the same skeleton;
   - `MI_Warden_Wool` values: Weave Scale 109.94, Detail Strength 0.5, Wetness 0.15, Cloth Brightness 0.4.
3. No shader error in the log. `M_LB_Surface` and every map are not dirty. Save one package per call. Suite 79/79.
4. Copy `Warden_Rigged.blend`, `exports/*.fbx`, V5's `README.md` and the three licence texts to `SourceArt/Warden/V5/` (`licences/` for the texts). Commit. The owner's folder is read-only for us: nothing in it is changed.
5. Update the registry row's Unreal path.

**If the editor can't load an asset:** stop and report.

### P12-5: fit (technical-artist [EDITOR])
1. **Clearance table, `Docs/ArtTest/warden/p12_clearance.md`:** for every `Crypt` and `Cloister` route segment, every search point and every spawn point, the lowest ceiling above it. Traces can't do this, because the art has no collision, so read the vault, soffit, portal and door records in `Docs/plans/p9_d1_layout.json` and `p10_d1_layout.json`. List every place lower than 292 cm. This tells Phase 13 where it must stoop, and tells us if Idle clips while standing.
2. **Facing:** confirm which yaw makes `SK_Warden` face actor +X, from bounds plus a thumbnail. Expect −90.
3. **Silhouette:** `Tools/blender/warden/bake_silhouette.py` opens the copy in `SourceArt/Warden/V5/`, never saves it, poses Idle frame 1 at LOD2, merges and decimates to ≤ 8,000 triangles, and exports `SourceArt/Warden/SM_LB_Warden_Silhouette.fbx` with the pivot at the feet. Import it as a static mesh to `Characters/Warden/Meshes/`, Nanite off, no collision. It must not get a project material with a missing usage flag; `MI_LB_WardenSilhouette` is fine, because this is a static mesh.

### P12-6: read review (lead + owner; was P12-7)
Same poses, candle proxy, sheet and pass rules as the old P12-7 below, with `AN_Warden_Idle` on the temporary actors. Allowed corrections here are MI values only: `Cloth Brightness`, skin and metal brightness. **Never change a light.** Output: `Docs/ArtTest/warden/p12_read.png` and a fix list agreed with the owner.

### P12-7: fixes (technical-artist)
Only what the review shows matters at game distance. Candidates: hand flecks, pale hands, forearm and sleeve join, mask eye slits, hood rim.
- **Material or texture fix:** in this project, directly.
- **Geometry fix:** `import_file` can't import LODs, and a skeletal re-import is delete and import again (P12-1). So edit a copy of the Blender master, use the isolated project's `Scripts/import_warden_v5.py` route, then copy again with a new `copy_v5.py` run after removing the old assets. The lead asks the owner before starting one.
- **Not here:** the stoop's look, run, attack and turn clips are Phase 13.

### P12-8 and P12-9: changes from the sections below
- **P12-8:** mesh `SK_Warden`, single-node `AN_Warden_Idle`, looping, playing. Yaw from P12-5. Socket `mask` goes on bone `head`, positioned at the mask (V5 has no `mask` bone); `TellLight` attaches there. Silhouette uses `SM_LB_Warden_Silhouette`. Top of the figure is 290, so **no height offset** on the silhouettes.
- **P12-9 GPU cuts, in order, if over 16.6 ms:**
  1. Wool and skin textures 4K to 2K.
  2. LOD1 sooner, through a screen-size change.
  3. A reduced LOD0, which needs a geometry round.
- **P12-9 docs:** also `ASSET_PLAN.md` (route) and `TECHNICAL_DESIGN.md` §8 (`M_LB_Character` is not used).

### What this drops
`Tools/blender/warden/concepts.py`, the blockout sheets and `hand_test.py` stay on the branch as a record and aren't used. `blenderkit` base mesh, `hessian_230` and `brown_leather`: not used, so their registry rows are marked at P12-9.

---

## Goal
Replace the Warden's cone-and-cube placeholder with one custom, memorable creature: a very tall, stooped, robed figure with a masked head and long bare arms. It must read as the same design in the crypt, the cloister and the two distant silhouettes.

This phase builds how it **looks** and a rig that is ready for animation. How it **moves** is Phase 13.

## Exit conditions
`Docs/IMPLEMENTATION_PLAN.md` gives Phases 12–13 the exit "Unique creature, polished animation". For Phase 12 that means:
1. The owner has chosen a design, and the finished model matches it.
2. The figure and the mask read clearly at 3, 8 and 15–20 m in the game's real lighting, in the crypt and the cloister.
3. The rig bends through a range-of-motion clip without collapsing or tearing, so Phase 13 can start.
4. `BP_Warden` and both `BP_WardenSilhouette` actors use the new art. The capsule, navigation and AI are unchanged, and the suite stays 79/79.
5. GPU ≤ 16.6 ms at High with the Warden in view, in the crypt and the cloister, measured by the owner.
6. The owner approves.

## Not in this phase
| Item | Phase |
|---|---|
| Walking, chasing, attack and turn animation; Animation Blueprint; foot IK | 13 |
| Stooping through doors, robe and chain motion | 13 |
| Breath, chain and robe sounds | 16 |
| Storm wetness on the Warden | 14–15 |
| Finale staging | 17 |
| LOD chain (one LOD for now; there is one Warden on screen) | 20, unless the GPU reading needs it sooner |

**Until Phase 13 the Warden glides in one held pose,** as the placeholder does today. This is expected and isn't a defect in this phase (R-52).

---

## What the lead found (read-only, 2026-11-04)
**The placeholder**
- `BP_Warden` (parent `ALBWarden`) holds `PlaceholderBody` with `Robe`, `Shoulders`, `Neck`, `Head`, `ArmLeft`, `ArmRight`, `Mask` and `MaskCrack` (engine cones, cubes and spheres), plus `TellLight`: a hidden red point light (800, radius 160). The empty inherited `CharacterMesh0` sits at Z −110.
- Placed once in `L_Monastery` (`BP_Warden_C_0`) and in `L_Test_Warden`.
- The attack tell only switches `TellLight` on and off; `PlayStateFeedback` is empty.
- Capsule radius 42, half height 110; eye height 85 above the capsule centre. **All of this stays** (D-038).

**The silhouettes:** `BP_WardenSilhouette` has `Body` (cylinder, Z 0–260, 60 wide) and `Head` (sphere, up to Z 290), in the unlit black `MI_LB_WardenSilhouette`.

| Actor | Location | Trigger |
|---|---|---|
| `BP_WardenSilhouette_C_2` | (9150, 0, 300), behind the chapel's east window | `State.Ritual.1`, 3 s |
| `BP_WardenSilhouette_C_0` | (6020, 2300, 800), on the roofline | `State.Event.CourtyardEntered`, 3 s, moves −1000 in Y |

**Clearances on the Warden's paths**
- Crypt: ≥ 260 cm (P9 design rule); portal springing is 345 above the floor.
- Cloister: ≥ 300 cm; springing ≥ 330.
- Doors: 104 × 230, tower door 104 × 224. The nav agent is 42 / 220.

Traces can't confirm the ceilings, because the art vaults have no collision. These numbers come from the P9 and P10 layouts.

**Warden routes:** `Crypt` and `Cloister`, 7 points each; 29 search points; 3 spawn points. The chapel has no Warden path, which is good: the chapel has the least GPU room.

**GPU room at the Warden's spots (2026-11-04, Warden off):** crypt ossuary 14.13 ms (2.47 left), cloister by the bells 14.73 ms (1.87 left).

**Tools**
- `SkeletalMeshTools.import_file` exists (skeleton, physics asset and animation options), as do sockets, material slots and `get_bone_names`.
- `PhysicsAssetToolset` can build and edit physics assets. `ControlRigTools` exists.
- **`BlueprintTools` can't add or remove components,** so placeholder parts are hidden and emptied, not deleted.
- **No tool for IK Rigs, IK Retargeters or skeletal LODs.** Whether an Animation Blueprint can be created is untested; `P12-1` tests it.
- **`M_LB_Surface` has `bUsedWithSkeletalMesh` false.** Using it here would recompile the master (R-47), so the Warden gets its own small master.
- **Skeletal import has never been done in this project through these tools.** `P12-1` proves it before any art depends on it.
- The Blender MCP add-on isn't running. The project's headless Blender 5.2 route is used, as for every kit and prop so far.

**Assets checked**
- `polyhaven:hessian_230` and `polyhaven:brown_leather`: CC0.
- `blenderkit:b881b381-b12a-4057-b018-6506331564df` (Human Base Mesh, 24,459 polys): free, "Royalty Free". The curator confirms the licence text.
- `grab3d:human-hand` and `grab3d:human-body-full`: CC0, but they are jointed teaching models. **Rejected.**
- Already in the project: `T_Metal058B_*` (bronze), `T_Rusty_Metal_04_*` (iron), `T_Weathered_Planks_*` (wood).

---

## The design
### Shared by all three concepts
| Feature | Value |
|---|---|
| Full height | 290 cm, top of head (D-038). Only reached in Phase 13 (attack, finale) |
| Held-pose height | **250–258 cm**, so it fits the crypt's 260 cm spots without animation. It reads as a tall thing folded under the ceiling, and it can still rise |
| Mask centre, held pose | about Z 232: it looks down at the player (eye height about 165) |
| Width at rest | ≤ 110 cm in the held pose, arms included (D-038) |
| Shoulders | 62 cm wide: narrow for the height |
| Arms | Bare from mid-forearm; fingertips reach knee level, Z 70 standing |
| Hands | 30 cm long, thin, long-fingered, no nails needing close-up detail |
| Robe | A coarse habit, near black-brown, wet and filthy at the hem; torn hem that drags 20 cm on the ground behind |
| Feet | Mostly hidden; bare long toes show at the hem |
| Chains | Broken iron shackles, because this is a prisoner getting loose |

**Why a robe-led figure:** the robe hides most of the body, so the only visible anatomy is hands, forearms and a little of the feet. It suits Phase 13 too: slow, unnatural motion under cloth hides foot sliding better than exposed legs would.

### Three concepts for the owner to choose from
| | A: The Penitent | B: The Bell-Bearer | C: The Veiled Saint |
|---|---|---|---|
| **Head** | Deep pointed cowl, bone mask inside it | No cowl: a cracked bronze bell riveted over the whole head, mouth at the neck | Wet linen veil pulled tight over a carved oak saint's face, with an iron spike crown |
| **Mask size** | 38 tall × 22 wide | 46 tall, mouth Ø 40, crown Ø 22 | Face 30 tall; crown 7 spikes, 22 tall |
| **Face** | Two slit eyes, a diagonal crack, an iron band with rivets | No eyes; one vertical crack, dark inside; verdigris streaks | Features only show through the cloth: brow, nose, open mouth |
| **Upper body** | Habit, rope belt, shackles on both wrists with 90 cm of chain trailing | Heavy mantle over the shoulders, rope belt, a neck chain from the bell to a broken ring at the chest | Burial wrappings over the habit, veil to the waist, chain wound around the torso |
| **Mask material** | Own generated bone textures | `T_Metal058B` bronze, the same metal as the bells | `T_Weathered_Planks` oak under `hessian` linen |
| **In dark light** | Pale mask catches any light; easiest read | Dark metal: catches highlights only, reads by shape | Pale veil reads well; the iron crown gives a hard outline |
| **Story link** | The prisoner | The game's own symbol: "the bell rings for you" | Echoes the veiled, crowned, chained `GothicStatue` in the level |
| **Risk** | The most familiar look | The bell must read as a head, not a costume | Cloth over a face is the hardest to model by script |

**Lead's early view:** B is the most distinctive and ties to the game's title, but it has to prove it reads in the dark. The owner decides from the renders and can mix (for example B's bell with A's trailing chains).

### Held pose
Spine forward about 38° in total (`spine_01..05`: 6, 7, 8, 8, 9°), neck 10° forward, head 14° back up so the face looks ahead, pelvis 12 cm back to keep the head within about 45 cm of the capsule axis, knees 6°, arms hanging slightly forward, fingers curled 15°. The implementer may adjust each angle by ±5° to reach 250–258 cm, and records the final values.

---

## Tasks
| Task | Scope | Owner | Needs the human? | Depends on |
|---|---|---|---|---|
| **P12-0** | Approval; log D-089, R-49…R-52; plan table | lead + owner | "go" | — |
| **P12-1** | Pipeline spike: a test figure through Blender, FBX and Unreal | technical-artist [EDITOR], lead for the captures | **Unreal in front, about 2 minutes** | P12-0 |
| **P12-2** | Downloads; hand comparison | asset-curator, technical-artist | No | P12-0 |
| **P12-3** | Three concept blockouts and a comparison sheet | technical-artist | **Choose, about 5 minutes** | P12-1 |
| **P12-4** | Final model of the chosen concept | technical-artist | Optional look | P12-3 |
| **P12-5** | Rig, weights, held pose, range-of-motion clip, silhouette mesh | animation-specialist | No | P12-4 |
| **P12-6** | Master material, textures, Unreal import | technical-artist [EDITOR], lead for the capture | **Unreal in front, about 2 minutes** | P12-5 |
| **P12-7** | Read review in the game's real lighting | lead + owner | **Captures about 12 minutes, then judge** | P12-6 |
| **P12-8** | `BP_Warden` and silhouette swap | unreal-blueprint-engineer [EDITOR] | No | P12-7 |
| **P12-9** | QA, docs, GPU readings, playtest; "PHASE 12 READY FOR YOUR REVIEW" | qa-reviewer + lead + owner | **About 45 minutes** | all |

Editor tasks never overlap. Each one saves one package per `save_assets` call and runs the suite before its commit.

**Standing limits for every task**
- No light, level layout, navigation or `Source/` change. If a task seems to need one, stop and report.
- Never save: `M_LB_Surface` or any parent Blueprint on the project's protected list. `BP_Warden` and `BP_WardenSilhouette` are saved only in P12-8.
- Agents don't run captures. They stop and ask the lead, who tells the owner first, because Unreal must be in front.
- Never use `read_graph_dsl` on a Blueprint you aren't editing: it marks it dirty (P8). Use `find_nodes` and `get_node_infos`.
- Free assets only. Every new asset gets a row in `Docs/ASSET_REGISTRY.md`.
- **Don't operate the owner's desktop:** no synthetic key presses or window focus changes. If the editor hangs on a dialog, stop and tell the lead.
- **Don't try `BlueprintTools.create` with a class it may not support:** a refusal opens a modal dialog that freezes the editor and every MCP call until someone presses OK (P12-1).
- **Never assign an existing project material or MI to a skeletal mesh.** Their parents have `bUsedWithSkeletalMesh` false, so the editor would set the flag itself, dirty the master and recompile it (R-47). Skeletal meshes use the default material or `M_LB_Character` children only.

---

### P12-1: pipeline spike (technical-artist [EDITOR], no owner)
**Why:** this is the first skeletal mesh this project has imported. Prove the route on a throwaway figure so no art work rests on a guess.

**Files:** `Tools/blender/warden/spike_skel.py` (new); output `SourceArt/Warden/spike/`; assets in `/Game/LastBell/ArtTest/P12/`.

**The figure:** a 290 cm stick figure of tapered boxes on the core bones of the joint table (P12-5), with left-side boxes in slot `MAT_Left` and the rest in `MAT_Body`, plus a 2-second clip bending the spine and raising the left arm. It's deliberately lopsided, so `get_bounds` alone shows its orientation: a 30 cm box on the left hand only, and a 25 cm nose on the face only. No materials are assigned to it.

**Export settings to start from (`bpy.ops.export_scene.fbx`):**
- Scene unit scale 0.01, modelled in centimetres; character facing −Y, its left on +X.
- `apply_unit_scale=True`, `apply_scale_options='FBX_SCALE_NONE'`, `global_scale=1.0`, `bake_space_transform=False`.
- `object_types={'ARMATURE','MESH'}`, `add_leaf_bones=False`, `use_armature_deform_only=False`, `primary_bone_axis='Y'`, `secondary_bone_axis='X'`, `armature_nodetype='NULL'`, `mesh_smooth_type='FACE'`, `use_tspace=True`.
- Clips: `bake_anim=True`, `bake_anim_use_all_bones=True`, `bake_anim_use_nla_strips=False`, `bake_anim_use_all_actions=False`, `bake_anim_force_startend_keying=True`, `bake_anim_simplify_factor=0`.
- Armature object named `Armature`, top bone `root`. If Unreal adds an extra root bone, try naming the armature object `root` and record which worked.

**Must pass, each recorded in the plan:**
| # | Check | Pass |
|---|---|---|
| 1 | `import_file` with `import_animations`, `create_physics_asset` | Returns mesh, skeleton, physics asset, animation |
| 2 | `get_bone_names` | First bone is `root`; no `Armature` bone; count equals the source |
| 3 | `get_bounds` | Height 290 ± 1, not 100× or 0.01× |
| 4 | Orientation, from `get_bounds` of the lopsided figure, then seen in a `CaptureAssetImage` thumbnail | Nose towards +Y in mesh space, left hand's box towards +X (as `SKM_Manny_Simple`) |
| 5 | The clip plays with `AnimationSingleNode` on a temporary `SkeletalMeshActor` in Simulate (the lead captures it, about 2 minutes, Unreal in front) | Bends visibly; bones don't stretch or flip |
| 6 | `get_material_slots` | Both names survive |
| 7 | Second import over the same name, with `skeleton` set | Mesh updates; skeleton, sockets and references survive. **If not, write the safe re-import procedure** |
| 8 | Normals | No inverted faces in a `CaptureAssetImage` thumbnail; flat shading on the boxes is expected |

**Report only, for the Phase 13 plan (no pass or fail):**
- Can `BlueprintTools.create` make an Animation Blueprint, with `asset_type` `/Script/Engine.AnimBlueprint`? Can `write_graph_dsl` touch its graph?
- Can the skeleton's compatible-skeletons property be set through `set_properties`?
- Can IK Rig or Retargeter assets be created by any tool? (If not, they need a short owner UI step in Phase 13.)

**If import fails after two attempts:** stop and report. The fallback is the owner running a one-time UI import, as with the P11 Reimport.

Remove temporary actors; never save `L_Monastery`. Commit scripts and the FBX. Lead adds the results here.

**Result (technical-artist and lead, 2026-11-04; c9b5aa0, e53a570; `p12s_*`): the route works, first try, with no change to the starting settings except the axes below.** R-50 closed.

| # | Check | Result |
|---|---|---|
| 1 | Import with animation and physics asset | Pass |
| 2 | Bones | Pass: `root` first, no `Armature` bone, 41 of 41 |
| 3 | Size | Pass: height 290 |
| 4 | Orientation | Pass: nose on +Y, left on +X in mesh space. In the world, yaw −90 faces +X, which is what P12-8 uses |
| 5 | The clip plays in Simulate | Pass (lead): `p12s_p12s_front_4m` shows it nearly upright, `p12s_p12s_side_left_4m` bent with the left arm raised; nothing stretches or flips. The two shots are moments of one looping clip |
| 6 | Slots | Pass: both names survive |
| 7 | Re-import | **A direct re-import is refused** ("already exists"). See below |
| 8 | Normals | Pass, judged from a 256 px thumbnail and these two captures |

**Settings that worked:** the plan's list plus `axis_forward='Y'`, `axis_up='Z'`, `use_mesh_modifiers=True`, `path_mode='AUTO'`. Scene unit scale 0.01, 1 unit = 1 cm, no manual mirror. Armature object named `Armature`. Blender −Y becomes mesh +Y; +X stays +X.

**Re-import is delete and import again** (`Tools/warden/reimport_skeletal.py`, tested twice):
1. Record slot materials, sockets, the physics asset and every reference to the mesh.
2. `AssetTools.delete` the mesh. Skeleton, physics asset and clips stay.
3. `import_file` at the same path with `skeleton` set, `import_animations=False`, `create_physics_asset=False`.
4. Assign the physics asset again, re-add sockets, set materials by slot name.
5. Re-point every Blueprint and actor reference, and compile.

**So:** do the model's re-imports before `BP_Warden` references it (P12-8), or expect step 5 each time. Survival of a real MI through this hasn't been tested, because the spike used its own empty material; the script restores slots anyway. Renaming or re-parenting a bone hasn't been tested.

**Clips:** a clip-only FBX is refused ("produced no assets"). Each clip ships with a mesh, one clip per FBX. Import it under a throwaway mesh name with `skeleton` set, move `<name>_Anim` to `AS_...`, delete the throwaway mesh and its physics asset. Tested end to end.

**For the Phase 13 plan:**
- **An Animation Blueprint can't be created through the tools.** `BlueprintTools.create` refuses and opens a modal dialog. It needs a short owner UI step, after which the tools can be tested on its graph.
- **IK Rig and Retargeter assets can't be created either.** Also an owner UI step, if Phase 13 retargets at all.
- `compatibleSkeletons` can be set through `set_properties`.

**Disclosed:** that modal froze the editor during the spike. The agent cleared it by focusing Unreal's message window and sending Enter from PowerShell, which wasn't in its brief. A standing limit now forbids this. Temporary actor removed (2980 actors), PIE off, throttle restored; `L_Monastery` is dirty in memory only and must not be saved.

Test assets: `SK_P12_Spike`, its skeleton and physics asset, `AS_P12_Clip`, `M_P12_SpikeTest` in `ArtTest/P12`, for the phase-end decision.

### P12-2: downloads and hand comparison (asset-curator, then technical-artist)
**Download through `3d-assets-local`, one folder each in `ExternalAssets/Incoming/`:**
| Asset | Files | Use |
|---|---|---|
| `polyhaven:hessian_230` | 2K JPG: `diff`, `nor_dx`, `arm` | Robe, mantle, wrappings |
| `polyhaven:brown_leather` | 2K JPG: `diff`, `nor_dx`, `arm` | Skin creases (tinted, not used as leather) |
| `blenderkit:b881b381-b12a-4057-b018-6506331564df` | GLB | Hand and foot anatomy candidate |

Report each licence from `get_asset` and the source page, and add registry rows. **If the BlenderKit licence doesn't allow use in a commercial game, don't use the mesh** and report it.

**Hand comparison:** `Tools/blender/warden/hand_test.py` renders two hands at the same 30 cm length, with bent and straight fingers:
1. the base mesh's hand, cut off and stretched: forearm +60 %, palm and fingers +35–40 % long, thickness × 0.75;
2. a scripted hand: Skin modifier over a joint graph, subdivision, knuckle and tendon displacement.

Sheet: `Docs/ArtTest/warden/p12_hands.png`. The lead picks the better one and logs why. If the base mesh is used, record that it's a heavily changed derivative.

**Downloads result (asset-curator, e4f6280):** all three in place.
- `hessian_230` maps are 2048 × 2036, so P12-6 must resize or crop them to 2048 × 2048 before import.
- `brown_leather`'s colour map is named `_albedo_`, not `_diff_`.
- **Licence of the base mesh:** BlenderKit's page allows commercial use and "higher-level derivative works", and forbids reselling the asset even when modified. It never mentions shipping inside a game. That looks permitted, but it's a reading rather than stated wording. **Lead's decision: none of this mesh ships unless it's clearly better than the scripted hand, and then only after the owner has been asked.**

**Hand comparison result (technical-artist and lead, dfd94b2; `Docs/ArtTest/warden/p12_hands.png`): the scripted hand (version 2) is chosen.** Both are 3,880 triangles with a 40 cm forearm.

| | Base mesh | Scripted |
|---|---|---|
| Reads as | A slender, elegant human hand | A thin, skeletal hand with knobbly knuckles and long bony fingers |
| Silhouette in the candle row | Soft | Knuckles and joints show, and the rim light finds the bony outline |
| Weakest point | Too human; ragged thumb tip | Plain palm with a visible join at the knuckle row, a smooth thumb mound, blunt fingertips, a kink at the wrist |
| Licence | Not settled in explicit words | Own work, no question |

**Why:** the base mesh is cleaner, but it isn't clearly better for this creature. The scripted hand is the better monster, and the player sees it at arm's length at the closest, in the dark. So the base mesh isn't used for hands or feet, and the owner doesn't need to rule on its licence.

**Must be fixed when P12-4 takes this hand:**
1. Blend the fingers into the palm: no visible join at the knuckle row, and some webbing.
2. Metacarpal ridges strong enough to read in the back of the hand, and a thumb mound with a real shape.
3. Slightly tapered, bony fingertips instead of blunt bullets; no smudge on the ring finger.
4. No kink where the palm meets the forearm; ulna and tendons carried up the forearm.

The feet use the same method.

### P12-3: concept blockouts (technical-artist; owner chooses)
**Files:** `Tools/blender/warden/concepts.py` (seeded, headless); `Tools/blender/warden/render_concepts.py`; output `Docs/ArtTest/warden/`.

**Build:** one shared proxy body at the design's proportions, in the held pose, plus each concept's head, mask and upper garment. Blockout quality: correct silhouette and proportions and a first mask, but lofted robes with no cloth simulation or textures beyond flat tints. Use real bronze and bone-like colours so the mask's read can be judged.

**Render with Cycles at 64 samples, denoised, 1024 × 1024, on a black background:**
| Row | Content |
|---|---|
| 1 | Front, three-quarter, side |
| 2 | Pure black silhouette on mid-grey, same three angles |
| 3 | Lit from below by a warm candle at 2700 K, 2.5 m in front, 120 cm high, with a cold rim from behind |
| 4 | Scale: beside a 180 cm human proxy, and standing in a 104 × 230 door frame |
| 5 | Mask close-up, front and three-quarter |

**Sheet:** `Docs/ArtTest/warden/p12_concepts.png`, one column per concept.

**Acceptance (lead, before the owner sees it):** each concept is recognisable from row 2 alone; held-pose height is 250–258; width ≤ 110. Iterate until they look intended, not lumpy.

**Gate:** the owner picks A, B or C, or a mix. The lead records it as **D-090** and writes the exact P12-4 values into this plan before P12-4 starts. **Nothing else proceeds until the owner chooses.**

**Result (2026-11-04): all three renders are on the sheet (`2265a6e`), and none was chosen.** The owner replied with their own finished build, Warden Art V5, and the lead recommended it over the blockouts: D-090. Two findings carry over: the crypt's ≥ 260 cm rule forced a 45° head pitch in the held pose, and that held pose no longer applies, because V5 stands at 290.

### P12-4: final model (technical-artist)
**Superseded by D-090; kept as a record.**
The lead fills in the chosen concept's exact dimensions after the gate. These apply whichever is chosen.

**Files:** `Tools/blender/warden/build_warden.py` (seeded, reruns from nothing); `Tools/blender/warden/render_warden.py`; `Tools/textures/gen_warden_textures.py` (numpy and PIL, seeds 12101+); textures in `ExternalAssets/Generated/warden/` (git-ignored, rebuilt by script); `SourceArt/Warden/` for FBX and the `.blend`.

**Sections and triangle budget (LOD0 ≤ 55,000):**
| Slot | Contains | Triangles |
|---|---|---|
| `MAT_Robe` | Robe, sleeves, cowl or mantle or wrappings | ≤ 34,000 |
| `MAT_Skin` | Forearms, hands, feet | ≤ 10,000 |
| `MAT_Mask` | The mask or bell or veiled face, with crown if any | ≤ 6,000 |
| `MAT_Iron` | Shackles, chains, rivets, spikes | ≤ 5,000 |

Faces hidden under the robe are deleted, not just covered, so a body nobody sees costs no triangles.

**Robe method:**
1. Loft a clean quad grid from neckline to hem: about 90 columns × 70 rings, radius from the proportions, hem radius 45–55.
2. Pin the neckline and shoulders. Run Blender cloth for 60–90 frames over a simple collision proxy of the body, in A-pose, with a ground plane at Z 0 so the last 20 cm folds down and drags. Script each setting and use a fixed seed so the result reruns the same.
3. Tear the hem: cut by a seeded vertical noise, 6–10 ragged tongues and 3–5 small holes, all as real geometry. **No masked opacity**, because of its cost and shadow behaviour.
4. Solidify 0.6 cm so edges have thickness.

The simulated result keeps its quads, so it weights and deforms cleanly with no retopology.

**Texture sets, 2K, baked with Cycles from `build_warden.py` where they are unique:**
| Set | Base colour | Normal | ARM | Mask (R grime, G wet, B AO) |
|---|---|---|---|---|
| Robe | `hessian_230` tiled at about 80 cm in the material | `hessian_230` tiled, plus baked large folds | `hessian_230` | Baked: grime rises from the hem to about Z 80 with noise; wet at hem and shoulders; AO from the cloth |
| Skin | Generated: bloodless grey-brown, darker at joints | `brown_leather` tiled small, baked tendons | `brown_leather` | Baked: dirt in creases and under nails |
| Mask | Per concept | Baked from a displaced high-resolution copy | Per concept | Baked: grime in recesses |
| Iron | `T_Rusty_Metal_04` | same | same | Not needed |

**Verify (`Tools/blender/warden/verify_warden.py`):** budgets; manifold where required; no zero-area faces; UVs inside 0–1 on baked sets; every slot used; bounds in the A-pose as designed.

**Acceptance (lead):** renders at the same angles and lighting as P12-3 match the chosen concept and look finished at 3 m. The owner may look at `Docs/ArtTest/warden/p12_model.png`; it isn't a required stop.

**If the lead can't accept it after three rounds, stop and report to the owner with images** (R-49). Options then: simplify the design; keep the agreed silhouette with a simpler mask; or, only if the owner says so, try a free AI-generated mask as a starting point. Asset plan note: hands-off generated meshes aren't production-ready.

### P12-5: rig, weights, poses (animation-specialist)
**Superseded by D-090; kept as a record.**
**Files:** `Tools/blender/warden/rig_warden.py`; clips and FBX in `SourceArt/Warden/`.

**Joint table (cm; character faces −Y; left is +X; A-pose at 45°). Mirrored for `_r`:**
| Bone | Parent | Head position |
|---|---|---|
| `root` | — | (0, 0, 0) |
| `pelvis` | `root` | (0, 0, 128) |
| `spine_01` | `pelvis` | (0, 0, 140) |
| `spine_02` | `spine_01` | (0, −1, 155) |
| `spine_03` | `spine_02` | (0, −2, 172) |
| `spine_04` | `spine_03` | (0, −3, 190) |
| `spine_05` | `spine_04` | (0, −4, 208) |
| `neck_01` | `spine_05` | (0, −6, 226) |
| `neck_02` | `neck_01` | (0, −8, 240) |
| `head` | `neck_02` | (0, −10, 254), top of head at Z 290 |
| `mask` | `head` | Mask centre, forward of `head`; extra bone, doubles as the tell's attach point |
| `clavicle_l` | `spine_05` | (5, −3, 214) |
| `upperarm_l` | `clavicle_l` | (28, −2, 216) |
| `upperarm_twist_01_l` | `upperarm_l` | halfway along |
| `lowerarm_l` | `upperarm_l` | (69, −2, 175) |
| `lowerarm_twist_01_l` | `lowerarm_l` | halfway along |
| `hand_l` | `lowerarm_l` | (110, −2, 134) |
| fingers `<f>_metacarpal_l`, `<f>_01..03_l`; `thumb_01..03_l` | `hand_l` | Fingers: metacarpal 9, then 8, 7, 6 cm. Fit to the mesh. Fingertips about (131, −2, 113) |
| `thigh_l` | `pelvis` | (13, 0, 124) |
| `thigh_twist_01_l` | `thigh_l` | halfway along |
| `calf_l` | `thigh_l` | (14, −2, 70) |
| `calf_twist_01_l` | `calf_l` | halfway along |
| `foot_l` | `calf_l` | (15, 2, 14) |
| `ball_l` | `foot_l` | (15, −14, 3) |
| `ik_foot_root`, `ik_foot_l/_r`, `ik_hand_root`, `ik_hand_l/_r` | `root` | Copies of the target's position; no weights |

These names and this hierarchy match `SK_Mannequin`'s core, so a retarget in Phase 13 is possible. **The bones' local axes are not guaranteed to match it.** Phase 13 may use scripted clips instead, and this skeleton doesn't commit to either.

**Extra bones, all with weights:**
| Bones | Parent | Purpose |
|---|---|---|
| `robe_<F,FL,L,BL,B,BR,R,FR>_01..03`, ring Z 110, 70, 30; radius 24, 34, 44 | `pelvis` | Skirt motion in Phase 13 |
| `robe_B_04` | `robe_B_03` | The dragging tail |
| `sleeve_l_01..02`, `sleeve_r_01..02` | `lowerarm_*` | Torn sleeves |
| `hood_01`, `hood_02` (or the concept's equivalent) | `head` / `spine_05` | Cowl, mantle or veil |
| `chain_l_01..05`, `chain_r_01..05` (per concept) | per concept | Chains |

Target about 110 bones or fewer.

**Weights**
- Skin, mask, iron: automatic weights, cleaned. Mask and rigid iron pieces are 100 % on one bone.
- Robe above the pelvis: automatic weights on the spine and arms. Below: script it by position, blending the two nearest columns and two nearest rings of `robe_*`, smoothed where the zones meet.
- ≤ 4 influences per vertex, normalised, no unweighted vertices.

**Clips**
- `AS_Warden_HeldPose`: 1 frame, the held pose.
- `AS_Warden_ROM`: about 10 s, each joint in turn: spine ±30°; head ±60° turn, ±30° nod; shoulder raise 120°; elbow 120°; fingers curl 80°; knee 90°; each robe chain ±25°; each chain swing. For checking only; not shipped in play.

**Silhouette mesh:** bake the held pose, merge and decimate: `SM_LB_Warden_Silhouette`, ≤ 8,000 triangles, pivot at the feet, no UVs needed, facing as a static mesh in this project.

**Verify (extends `verify_warden.py`):** joints within 0.5 cm of the table and mirrored; influences; normalised; bone count; held-pose height 250–258 and width ≤ 110.

**Acceptance (lead):** 12 extreme frames rendered to `Docs/ArtTest/warden/p12_rom.png`. No candy-wrapper twisting at wrists or elbows, no robe through the arms in the held pose, no mask deformation. Some robe stretch at ±25° is acceptable, because Phase 13 tunes it.

### P12-6: material and import (technical-artist [EDITOR])
**Superseded by D-090; kept as a record.**
**`/Game/LastBell/Materials/Master/M_LB_Character`** (new): Opaque, Default Lit, `bUsedWithSkeletalMesh` on. Build it first on `M_P12_CharacterTest` in `ArtTest/P12`, so a shader error can't reach the real one. Other GPU apps closed, all work saved (D-053).

| Parameter | Default | Purpose |
|---|---|---|
| `BaseColorTex`, `NormalTex`, `ARMTex`, `MaskTex` | — | Textures |
| `DetailTile` | 1 | UV multiplier for tiled fabric and leather |
| `MaskUsesUV0` | true | Mask reads untiled UVs |
| `Tint`, `BrightnessMul` | white, 1 | Overall colour |
| `GrimeColor`, `GrimeStrength` | (0.03, 0.025, 0.02), 0.8 | Hem dirt from `MaskTex` R |
| `WetDarken`, `WetRoughness` | 0.5, 0.25 | Wet from `MaskTex` G |
| `AOStrength` | 1 | `MaskTex` B |
| `RimLift` | 0 | Small Fresnel term, only if the shape vanishes in the dark at P12-7 |

Skip anything subsurface, translucent or tessellated.

**Assets, under `/Game/LastBell/Characters/Warden/`:**
| Folder | Assets |
|---|---|
| `Meshes/` | `SK_LB_Warden`, its skeleton `SK_LB_Warden_Skeleton`, `PA_LB_Warden`, `SM_LB_Warden_Silhouette` |
| `Anims/` | `AS_Warden_HeldPose`, `AS_Warden_ROM` |
| `Materials/` | `MI_Warden_Robe`, `MI_Warden_Skin`, `MI_Warden_Mask`, `MI_Warden_Iron` |
| `Textures/` | `T_Warden_*`, sRGB and compression settings copied from the matching existing textures; normals as TC_Normalmap |

`PA_` and `AS_` are new prefixes, because the naming list has none for these two types. D-089 adds them.

**Physics asset:** remove what the auto-generator makes and author simple capsules on `pelvis`, `spine_03`, `spine_05`, `head`, `upperarm_*`, `lowerarm_*`, `thigh_*`, `calf_*`. Mass and constraints aren't tuned in this phase. It also gives Unreal correct bounds for a mesh taller than its capsule.

**Sockets:** `mask` (bone `mask`), `hand_l`, `hand_r`.

**`Tools/warden/check_warden.py`, read-only:** bone count and hierarchy, height, slots and their MIs, sockets, physics asset, Nanite off, one LOD, textures present. Prints n/n.

**Acceptance:** `check_warden.py` all pass; a capture shows correct materials in neutral light; no shader errors in the log; suite 79/79. Commit.

### P12-7: read review in real lighting (lead + owner at the PC)
**Why:** a creature can look fine in a render and turn into a black blob in the crypt. Judge it where the player will meet it, before wiring it in.

**Tell the owner before starting:** about 12 minutes; Unreal must stay in front and the PC left alone; "wait" stops it. Agents don't run this tool.

**Temporary actors, in the editor world, never saved:** `P12_Review_*` `SkeletalMeshActor`s, `AnimationSingleNode`, `AS_Warden_HeldPose`, plus `P12_CandleProxy`: a point light with the values read from `ULBCandleComponent`, placed at the camera. `L_Monastery` isn't saved in this task, and the actors are removed afterwards and checked against a census.

**Poses, `Tools/warden/poses/p12_read_poses.json`, written with `Tools/warden/make_read_poses.py`:**
| Spot | Figure at | Cameras, eye height, facing the figure |
|---|---|---|
| Ossuary | (8850, −2250, −600) | 3 m, 8 m, and from (7400, −2350, −440), about 15 m |
| Chain chamber | (10800, −1780, −600) | 3, 8 m, and from (10200, −2300), about 8 m at an angle |
| Cloister, by the bells | (11750, 2650, 0) | 3, 8, 18 m along the east walk |
| Cloister, west walk | (9850, 2000, 0) | 3, 8, 15 m along the walk, against the moonlit garth |

Four 3 m and 8 m views repeat with `P12_CandleProxy` on (16 shots). The lead fixes exact cameras with a dry run so that no wall blocks a view.

**Sheet:** `Docs/ArtTest/warden/p12_read.png`.

**Pass (lead, then the owner):**
- At 8 m with the candle: figure and mask are clearly a figure, with the mask as the focal point.
- At 3 m: the materials hold up. Cloth reads as cloth, skin as dried skin.
- At 15–18 m: a tall shape, recognisable by outline against the lit background.
- Without the candle in a dark spot it may be very dark. That is intended, but its outline has to be findable; `RimLift` and `BrightnessMul` are the only allowed corrections. **Never change a light.**
- The figure doesn't cut through any wall or ceiling at the patrol points used.

**Gate:** the owner says yes or lists changes. Changes loop to MI values (P12-7), or to P12-4 if the design itself must change, which is reported first with its cost.

### P12-8: wire it in (unreal-blueprint-engineer [EDITOR])
Read each template with `get_properties` first and record the old values in `Docs/ArtTest/warden/p12_8_before.json`. Use `Tools/warden/apply_p12_warden.py` (`--snapshot`, `--apply`, `--check`, `--save`, `--restore`, same style as `apply_p11_lantern.py`).

**`BP_Warden`:**
| Template | Property | Value |
|---|---|---|
| `CharacterMesh0` | `skeletalMeshAsset` | `SK_LB_Warden` |
| | `animationMode` | `AnimationSingleNode`, with `AS_Warden_HeldPose`, looping, playing |
| | `relativeLocation` | (0, 0, −110) unchanged |
| | `relativeRotation` | Yaw −90, or whatever `P12-1` proved faces +X |
| | Collision | `NoCollision` (the capsule keeps all collision) |
| `Robe`, `Shoulders`, `Neck`, `Head`, `ArmLeft`, `ArmRight`, `Mask`, `MaskCrack` | `staticMesh` | None |
| | `bVisible`, `bHiddenInGame` | false, true |
| | Collision | `NoCollision` |
| `TellLight` | All values | Unchanged |

**`TellLight` attach:** in `EventGraph`, on BeginPlay, `AttachComponentToComponent(TellLight, CharacterMesh0, "mask", SnapToTarget)`. Use the additive rule: read the existing nodes first and don't duplicate an event. Compile.

**`BP_WardenSilhouette`:** `Body.staticMesh` = `SM_LB_Warden_Silhouette`, location (0, 0, 0), scale (1, 1, 1), rotation so it faces the player's side of each view, keeping `MI_LB_WardenSilhouette`; `Head.staticMesh` = None, hidden. `TriggerTag`, `VisibleSeconds` and `MoveOffset` are unchanged. Top of the figure within 40 cm of today's Z 290, since the held pose is shorter: raise neither actor without a capture showing a need.

**Placed instances:** template changes don't reach serialized instance values. Read back `BP_Warden_C_0` in `L_Monastery` and `L_Test_Warden`, and both silhouettes. Fix only what differs, and save a map only then. Remove any `P12_` temporaries first and confirm by a census: actor count must be 2980.

**Failure modes to pin with checks (`check_warden.py --bp`, and a PIE run by the lead):**
| Condition | Expected |
|---|---|
| Warden dormant at game start (stages 1–2) | No mesh visible anywhere, `TellLight` off |
| Warden appears, stage 3, in the crypt | Mesh appears, feet on the floor: not floating or sunk by more than 3 cm |
| A stage change moves it to a new spawn | Mesh moves with the capsule |
| Attack windup | `TellLight` lights at the mask; the player dies as before |
| Checkpoint reload after a death | Warden rebuilt from tags, with the mesh, no duplicates |
| Very close to the player | Not culled by bounds; capsule collision unchanged |
| `lb.Warden.Enabled 0` | Hidden |
| Silhouettes | Shown 3 s on their tags, in black, in the chapel window and on the roofline |

**Suite:** 79/79, including `Warden.*`, `Functional.Warden.*`, `Warden.MonasteryReachability`, RouteBot and WalkPath. Capsule still 42 / 110, tuning asset untouched. Commit.

### P12-9: close
1. **QA (qa-reviewer):**
   - suite; `check_warden.py`; `verify_warden.py`;
   - no `Source/` or `Config/` change; no light or layout change (census compare, 2980 actors);
   - only `BP_Warden` and `BP_WardenSilhouette` changed among Blueprints;
   - naming, folders, registry; logs; dirty packages; git.
2. **Docs (lead):** MCP_NOTES (skeletal pipeline, export settings, safe re-import, physics asset route, FBX lessons); PERFORMANCE_BUDGET; ASSET_REGISTRY; RISKS (R-19 closed, R-49…R-52); DECISIONS; IMPLEMENTATION_PLAN; TECHNICAL_DESIGN §8 (the mesh is in `BP_Warden`, `M_LB_Character`, new prefixes); ASSET_PLAN status for the Warden and mask; `LEVEL_DESIGN.md`'s old "capsule radius about 55" line.
3. **Owner, about 10 minutes, GPU, High, same console commands as Phase 11, `lb.Warden.Enabled 0`:** the lead leaves two temporary held-pose figures in the editor, unsaved, so the reading is repeatable and nothing kills the player.
   | Spot | Reading | P11 GPU, no Warden |
   |---|---|---|
   | Crypt ossuary | 3 m and 8 m from the figure | 14.13 ms |
   | Cloister, by the bells | 3 m and 8 m from the figure | 14.73 ms |

   Then remove the figures. **If over 16.6 ms, cuts in this order:**
   1. Robe budget 34,000 → 22,000 triangles and re-export.
   2. Shadow casting off on `MAT_Iron` pieces, if separable.
   3. LOD chain moved up from Phase 20, through a short owner UI step.
4. **Owner, about 30–45 minutes, playtest with the Warden on:**
   - meet it in the crypt and cloister;
   - get caught once;
   - watch both silhouettes.
   - Judge: is it frightening or silly? Does the mask read? Does it fit the place? Remember it glides until Phase 13.
5. **"PHASE 12 READY FOR YOUR REVIEW".** It also asks about the test assets in `ArtTest/P12`, the unreferenced `BP_WardenPlaceholderKill`, and `MI_LB_WardenMask`. Merge only on "approve and merge". Phase 13 is planned only on request.

---

## Proposed log entries (added in P12-0, on approval)
- **D-089:** Warden art route.
  - Robe-led figure, scripted in headless Blender with baked cloth; own `M_LB_Character` master so `M_LB_Surface` is untouched.
  - Skeleton uses the Mannequin's core names plus own robe, chain and mask bones; one LOD at ≤ 55,000 triangles.
  - Held pose 250–258 cm.
  - New naming prefixes `PA_` and `AS_`.
  - Rejected: a full anatomical body under the robe (never seen); AI-generated meshes (asset plan); Nanite skeletal mesh (unproven here, not needed for one figure).
- **D-090:** the owner's concept choice, after P12-3.
- **R-49** (Art, H/H): a scripted creature may look lumpy or not read as a premium hero asset. Mitigation: choose at blockout cost, three acceptance rounds then stop and report, owner gate in real lighting.
- **R-50** (Tooling, M/H): skeletal import through the MCP tools is unproven here. Mitigation: P12-1 spike on a throwaway figure; owner UI import as the fallback.
- **R-51** (Performance, M/M): the Warden adds cost where 1.87–2.47 ms remains. Mitigation: triangle and section budgets, measured with the figure in view, ordered cuts.
- **R-52** (Art, M/L): the Warden glides in one pose until Phase 13. Accepted; the placeholder does the same today.
- **R-19:** closed at P12-8, once the placeholder's look is gone.

## What the owner is asked to do
| When | What | Time |
|---|---|---|
| Now | Approve this plan, or change it | — |
| P12-1, P12-6 | Keep Unreal in front for a short capture | About 2 minutes each |
| P12-3 | Choose a concept from the sheet | About 5 minutes |
| P12-7 | Keep Unreal in front during captures, then judge the sheet | About 12 minutes plus a look |
| P12-9 | GPU readings | About 10 minutes |
| P12-9 | Playtest with the Warden on | About 30–45 minutes |
| If needed | A one-time UI import, only if P12-1 fails | A few minutes |

The lead states the time and asks before each session. Any capture over about 15 minutes gets a separate "is now a good time?".
