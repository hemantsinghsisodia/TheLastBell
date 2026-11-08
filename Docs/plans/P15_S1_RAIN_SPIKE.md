# P15 S1: rain occlusion spike (throwaway)

Owner approval: pending. Branch `claude/phase-15-particles`. Spec: `Docs/plans/P15_PARTICLES.md` (S1 row in section 13, section 6.1, D-104, R-65, R-66, R-69). Geometry: that plan's Results, F0.3. This spike answers questions. **Everything it builds in Unreal is deleted afterwards and is never saved.** Only its scripts and the report stay in git, as the record of the MCP method for P15-5.

## 1. Questions
- **Q1.** Does Niagara GPU distance-field collision kill falling rain under every roof type: the 4 cm planks, the 20 cm chapel slabs, the cloister lean-to and vaults, and the tower pyramid and belfry floor? And does rain still come through the openings?
- **Q2.** Does the global distance field hold data at run time with this project's settings (HWRT Lumen, `r.Lumen.TraceMeshSDFs` 0)? Q1 answers this: if nothing collides anywhere, the field is empty.
- **Q3.** Can MCP set the `Collision` module to distance-field mode? (F0.12: not provable from the schemas.)
- **Q4.** Can a splash particle rest on the first surface and show only after it lands? This needs a latched `Particles.HasCollided` read, which tests the attribute read. And does a fast fall (20000 cm/s, the section 6.1 value) tunnel through roofs, where a slow one (3000) does not?
- **Q5.** Does a second sprite renderer on one emitter work, with custom facing (0, 0, 1) and its size bound to its own attribute?
- **Q6.** What does the global distance field update cost on the GPU (R-69)?

## 2. Build (lighting-vfx, Sonnet with high effort) [EDITOR; Unreal open; the owner can be away]
**Rules.**
- Read `Tools/mcp/MCP_NOTES.md` first: the FX and fog section, and the Niagara notes.
- Use `Tools/mcp/ue.py`, with Python `C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe -I`.
- Check every result. Mutations to the same asset run one at a time.
- **Never save** anything: no asset, no map, no save-all.
- **Never** start PIE, capture, or touch the owner's desktop.
- **Never** `MaterialInstanceTools.set_parent`, `read_graph_dsl`, or `BlueprintTools.create`.
- Never save `M_LB_Surface` or any never-save Blueprint.
- Commit only the files named in section 2.6, staged by path, on this branch. Never switch, merge or push. Trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

### 2.1 Spike material (only if needed)
1. Read `/Niagara/DefaultAssets/DefaultSpriteMaterial` with MaterialTools: its blend mode and shading model.
2. **If it is translucent and unlit, and its emissive uses Particle Color:** use it.
3. **Otherwise:** create `/Game/LastBell/FX/Spike/M_LB_Spike_Unlit`:
   - Surface, Translucent, Unlit, two-sided;
   - Emissive = `ParticleColor.rgb` × `RadialGradientExponential`;
   - Opacity = `ParticleColor.a` × the same gradient.

   Compile it and validate it.

### 2.2 System `/Game/LastBell/FX/Spike/NS_LB_Rain_Spike`
- **Create:** `NiagaraToolset_System.CreateNiagaraSystem` from `/Niagara/DefaultAssets/DefaultSystem`. Remove its `Fountain` emitter.
- **User parameters** (`AddUserVariables`, defaults shown):

  | Parameter | Type | Default |
  |---|---|---|
  | `User.RainRate` | float | 1000 |
  | `User.SplashRate` | float | 200 |
  | `User.BoxSize` | Vector3 | (1400, 1100, 10) |
  | `User.SpawnOffset` | Vector3 | (0, 0, 1000) |
  | `User.RainFall` | float | 1250 |
  | `User.SplashFall` | float | 20000 |
  | `User.RainRadius` | float, cm | 10 |

- **Two emitters,** added from the simplest template under `/Niagara/DefaultAssets/Templates/Emitters/` with a spawn-rate module (record which one):
  - **`Rain`**:
    - **Emitter data:**
      - `SimTarget` GPUComputeSim;
      - local space off;
      - fixed bounds: min (−1500, −1500, −3000), max (1500, 1500, 5500);
      - determinism off.
    - **Emitter Update:** Spawn Rate = linked `User.RainRate`.
    - **Particle Spawn:**
      - Initialize Particle: Lifetime 5, Sprite Size (2.5, 50), Color (2.5, 2.8, 3.2, 1).
      - Shape Location:
        - Box;
        - Box Size linked to `User.BoxSize`;
        - offset linked to `User.SpawnOffset`.
      - Add Velocity: an HLSL expression `float3(0, 0, -User.RainFall)`.
    - **Particle Update:**
      - remove gravity, drag and any colour or scale module from the template;
      - keep Solve Forces and Velocity;
      - add `/Niagara/Modules/Collision/Collision`:
        - Collision Enabled true;
        - distance-field mode (section 2.3);
        - kill on collision on;
        - the collision radius driven by `User.RainRadius` in cm. Record the input and the mapping you used; for example, if the module computes the radius from the sprite size × `Particle Radius Scale`, then scale = `User.RainRadius` ÷ (1.25 cm).
      - The module order must leave no stack issue of the "wrong order" kind.
    - **Renderer 0:** sprite, `alignment` VelocityAligned, `facingMode` FaceCamera, material from section 2.1.
  - **`Splash`**:
    - **Same as `Rain`, except:**
      - Spawn Rate is linked to `User.SplashRate`;
      - the velocity is `float3(0, 0, -User.SplashFall)`;
      - Lifetime is 4;
      - Sprite Size is (12, 12).
    - **Collision:**
      - distance-field mode;
      - kill on collision **off**;
      - Restitution 0, Friction 1;
      - rest state on;
      - the same radius rule, but a fixed 6 cm.
    - **Latch** (tests the attribute read; use `AddSetParametersModule`):
      - **Particle Spawn:** `Particles.Landed` (bool) = false; `Particles.RingSize` (Vector2) = (30, 30); `Particles.SpriteFacing` (Vector3) = (0, 0, 1).
      - **Particle Update, after Collision:**
        - `Particles.Landed` = HLSL `Particles.Landed || Particles.HasCollided`;
        - then `Particles.Color` = HLSL `Particles.Landed ? float4(5.0, 1.4, 0.2, 1.0) : float4(0.0, 0.0, 0.0, 0.0)`;
        - no later module may write `Particles.Color`.
    - **Renderer 0:** sprite, FaceCamera.
    - **Renderer 1** (`AddRenderer`, `NiagaraSpriteRendererProperties`): `facingMode` CustomFacingVector, `spriteFacingBinding` `Particles.SpriteFacing`, `spriteSizeBinding` `Particles.RingSize`, same material.
- **Done when:**
  - `GetSystemCompileState` passes for both emitters (GPU scripts included);
  - `GetStackIssues` lists no errors. List any warnings in the report.

### 2.3 Distance-field collision mode (Q3). Try these in order, and record every attempt.
1. **The placed module's own inputs.** After `AddModule(Collision)`, call `GetModuleTopology` and `GetModuleSchema` on the placed module (not the asset). Look for any input whose name contains Type, Mode, GPU, Distance or Depth, or whose type is an enum: static switches show up only on a placed module. Pass its enum to `NiagaraToolset_Info.UEnum_Info`. Then `SetStackInputData` with `Enum` data for the distance-field value, and read it back with `GetStackInputData`.
2. **The zero-input module.** `/Niagara/Modules/Collision/NiagaraDistanceFieldCollisions`: add it, then check the compile state, the stack issues and the topology. Record what it is.
3. **An existing emitter that already uses GPU distance-field collision.** Search the asset registry (AssetTools) for `NiagaraEmitter` and `NiagaraSystem` assets whose names contain Collision, Rain, Splash or Spark, under `/Niagara`, `/Engine` and `/Game/LastBell/ThirdParty`. Read each candidate's `Collision` inputs. If one is in distance-field mode on GPU, rebuild the emitter with `AddEmitter` using it as the template, then apply section 2.2 on top.
4. **If none work:** record "distance-field mode not reachable over MCP", and build the rest anyway. It still tests Q4 and Q5 in whatever mode the module defaults to: record the mode, and the captures will show its behaviour. Then stop and report; the lead decides the next step (a headless Unreal Python script, or fallback C).

### 2.4 Placement (editor world; folder `FX/Spike`)
For each row:
- `SceneTools.add_to_scene_from_asset(NS_LB_Rain_Spike)`;
- set the label;
- `set_actor_transform` with location, rotation (0, 0, 0) and scale (1, 1, 1);
- then `NiagaraToolset_Component.SetVariable` on its Niagara component, and read back with `GetVariable`.

The rates are about 10 drops /s per m² of box (4 × the final density, so the captures show it). Rain spawns above the highest roof.

| Label | Location | `User.BoxSize` | `User.SpawnOffset` | `User.RainRate` | `User.SplashRate` |
|---|---|---|---|---|---|
| `S1_Spike_CyN` | (2500, 1150, 0) | (1400, 1100, 10) | (0, 0, 1000) | 1540 | 200 |
| `S1_Spike_CyS` | (4500, −1150, 0) | (1400, 900, 10) | (0, 0, 1000) | 1260 | 200 |
| `S1_Spike_Chapel` | (7000, 0, 0) | (1800, 1400, 10) | (0, 0, 2500) | 2520 | 300 |
| `S1_Spike_Cloister` | (10900, 1800, 0) | (1200, 2200, 10) | (0, 0, 1500) | 2640 | 300 |
| `S1_Spike_Tower` | (12500, 2000, 2500) | (960, 960, 10) | (0, 0, 2600) | 920 | 150 |

**What the boxes cover:**
- the courtyard boxes cover the walk and some open ground on both sides;
- the chapel box stays inside the walls (X 6100…7900, Y ±700);
- the cloister box covers the south walk, the garth and the north walk, including the roof hole;
- the tower box stays inside the walls (X 12020…12980, Y 1520…2480) and spawns at Z 5100, above the finial.

**The map becomes dirty. This is expected; do not save.**

### 2.5 Scripts
- **`Tools/fx/s1_spike.py`** (idempotent; finds actors by exact label; never saves). Subcommands:
  - **`build`:** sections 2.1–2.3.
  - **`place`:** section 2.4.
  - **`check`:** reads back:
    - compile state, stack issues, and both emitters' topology, with the collision mode;
    - the user parameters;
    - the 5 actors' transforms and component variables.
    - It prints PASS/FAIL lines and exits nonzero on a FAIL.
  - **`set --world pie|editor [--rain-scale K] [--splash-scale K] [--splash-fall F] [--radius CM] [--off]`:** sets the user variables on all five spike components in that world, then reads them back with `GetVariable`.
    - **Scales:** `--rain-scale` and `--splash-scale` multiply the section 2.4 per-actor rates; `--off` sets both rates to 0.
    - **Which world:** `--world pie` uses only actors whose refPath contains `UEDPIE` and refuses otherwise. It finds them the way `Tools/lighting/pie_pp.py` `pie_actor` does. `--world editor` refuses `UEDPIE` refs.
    - **Errors:** it exits nonzero on any read-back mismatch.
  - **`blockers --apply|--remove`:** section 6.2, built now so it is ready. `--apply` is never run by the agent.
  - **`remove`:** deletes the 5 actors and any blockers, then the `/Game/LastBell/FX/Spike/` assets. The agent never runs it; the lead runs it after the verdict.
- **`Tools/fx/s1_diff.py`:**
  - **Inputs:** `Docs/ArtTest/fx/s1/`, prefix `p15_` (so files are `p15_<pose><suffix>.png`), the poses of `Tools/fx/poses/p15_rain.json`, and the suffixes `_off1`, `_onF`, `_onS`, `_off2`.
  - **Diff images:** for each pose, `|onF − off1|`, `|onS − off1|` and `|off2 − off1|`, each × 8 and clamped.
  - **Contact sheet** `s1_sheet.png`: one row per pose. The columns are off1, onF, onS and the three diffs, each labelled.
  - **Regions:** if `Tools/fx/poses/p15_s1_regions.json` exists (`{pose: {"roofed": [[x0, y0, x1, y1], ...], "open": [...]}}`, pixel rects at the capture resolution), it computes the mean absolute difference (MAD, in /255) per region for each of the three pairs and writes `Docs/ArtTest/fx/s1/s1_mad.md`.
  - **Optional:** `--log <path>` greps the log for the `ProfileGPU` lines that contain `GlobalDistanceField` and adds their times.
  - Test it on any two existing PNGs of the same size. It reads only PNGs and never touches Unreal.

### 2.6 Report and commit
- **`Docs/ArtTest/fx/s1/s1_build.md`:**
  - every MCP pattern that worked, with the exact tool, arguments and payload shape (this is the P15-5 recipe), and every one that failed, with its error text;
  - the Q3 answer from each section 2.3 step;
  - the latch, the second renderer and the attribute binding;
  - the material used;
  - the compile state and stack issues;
  - `check` output;
  - the map's dirty state, which is expected to be true.
- **Commit** `Tools/fx/s1_spike.py`, `Tools/fx/s1_diff.py` and `Docs/ArtTest/fx/s1/s1_build.md`. Report the commit hash.

## 3. Capture session (lead with the owner; Unreal in front; about 12 minutes)
1. `python -I Tools/lighting/pie_pp.py start` (Simulate).
2. Check that the PIE toggle works. Run `s1_spike.py set --world pie --off` and read it back. If a running PIE component ignores the change, use the slow path instead: set the variables in the editor world, then stop and start PIE between states (about 1 minute more per state).
3. Wait 6 s, then capture `_off1`:
   ```
   capture_session.py Tools/fx/poses/p15_rain.json Docs/ArtTest/fx/s1 --prefix p15_ --suffix _off1 --fg-wait 180 --max-wait 600 --force
   ```
4. `set --world pie --rain-scale 1 --splash-scale 1 --splash-fall 20000`, wait 6 s, capture `_onF`.
5. `set --world pie --splash-fall 3000`, wait 6 s, capture `_onS`.
6. `set --world pie --off`, wait 6 s, capture `_off2` (the noise floor).
7. **(Q6, optional, 1 minute)** The owner clicks into the Simulate viewport. The lead sets the rain on again. The owner types `r.ProfileGPU.ShowUI 0`, then `ProfileGPU`, and the lead reads `GlobalDistanceField` from `Saved/Logs/TheLastBell.log`.
8. `pie_pp.py stop`.

## 4. Poses (`Tools/fx/poses/p15_rain.json`: x, y, z, pitch, yaw)

| Pose | Where | What it shows |
|---|---|---|
| `s1_cy_n_up` (2500, 1024, 170, 85, 90) | under north plank `2_0` (row 0), looking up | the plank underside (rain-free) beside the uncovered row 1 (rain) |
| `s1_cy_n_floor` (2250, 1024, 150, −15, 0) | under row 0, looking east along the floor | no orange splash under row 0; splashes in the gaps on the left |
| `s1_cy_s_up` (4700, −1188, 170, 85, −90) | under south plank `3_2`, looking up | the plank underside beside the uncovered patches |
| `s1_ch_hole_up` (7000, 0, 170, 66.5, −140.1) | nave floor, looking at the `Ch_Roof_S1` hole | a rain column only through the hole |
| `s1_ch_floor` (7400, 250, 250, −12.6, −143.4) | nave, looking at the floor under the hole | splashes only on the floor under the hole (X 6250…6750, Y −643…−193) |
| `s1_cl_s_walk` (10850, 900, 170, 5, 90) | south cloister walk, looking north into the garth | rain and splashes in the garth, none in the walk |
| `s1_cl_n_hole` (10450, 2650, 170, 15, 0) | north walk, looking east at the hole | a rain column at X 10900…11270, none elsewhere under the vault |
| `s1_tw_belfry` (12500, 2150, 2670, 25, −135) | belfry, looking south-west | rain through the south-west collapse only |
| `s1_tw_mid_stair` (12835, 1665, 1534, 10, 180) | mid stair | no rain at all (the belfry floor stops it) |

## 5. Verdict rules (the lead, written into the main plan's Results before P15-4)
The lead first draws the roofed and open pixel rects for each pose from `_onF` and its diff image, into `p15_s1_regions.json`. Then `s1_diff.py` runs.

- **A passes:**
  - in every roofed region, MAD(`onF` vs `off1`) and MAD(`onS` vs `off1`) are ≤ MAD(`off2` vs `off1`) + 1/255;
  - the open regions and the openings show rain in the diff images;
  - orange splash dots appear only where the sky is open.
- **A passes with slow splashes only:** `onF` leaks splashes where `onS` does not. Section 6.1 then uses the slower fall and a short visibility delay instead of 20000 cm/s.
- **Planks leak, everything else holds:** blockers (section 6.2).
- **Nothing collides anywhere:** Q2 fails, or Q3 couldn't set the mode. Go to fallback C (section 6.3).
- **Q6:** the global distance field update cost goes into the performance budget. Over 1.0 ms is a reason to prefer C even if A works.

## 6. Follow-ups by outcome (each needs the owner's "go")
- **6.1 Pass:** P15-5 builds `NS_LB_Rain` with the recipe from `s1_build.md`. The lead removes the spike (`s1_spike.py remove`); the map stays unsaved.
- **6.2 Blockers (about 5 minutes of the owner's time):**
  - `s1_spike.py blockers --apply` places hidden boxes:
    - engine `Cube`, 40 cm thick, its top 5 cm under each plank row's lowest edge, covering each row's XY;
    - `bRenderInMainPass` false, `bRenderInDepthPass` false, `bVisibleInRayTracing` false;
    - `bAffectDistanceFieldLighting` true, cast shadow false, NoCollision.
  - Then capture the three courtyard poses again with `_onF` and `_off`. If that holds, P15-6 places the final blockers.
  - If it doesn't: a visible cube with a fully masked-out material is the next variant, then C.
- **6.3 Fallback C (its own short plan):**
  - Occlusion moves into the materials.
  - A roof-height texture, `T_LB_FX_RoofHeight`, at 25 cm per texel over the level's XY bounds. Each texel holds the lowest roof underside Z (0 = open sky). It is generated by a script from the F0 roof data.
  - `M_LB_Rain` and `M_LB_Splash` clip the pixels whose world Z is below the roof Z at their XY.
  - It needs no distance field and has no thickness limit.

## 7. Clean-up
- After the verdict, `s1_spike.py remove` deletes everything the spike created in Unreal.
- The map stays dirty and unsaved until P15-6 saves it deliberately. If Unreal is closed before then, choose **Don't Save**.
- The captures, the diffs, `s1_mad.md` and the verdict are committed, under `Docs/ArtTest/fx/s1/`.
