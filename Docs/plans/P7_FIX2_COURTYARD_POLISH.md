# P7-FIX2 — Courtyard polish: real puddles, a real key, props, mist & smoke

## Context
The owner played the approved Phase 7 courtyard (L_Monastery) and reported three problems with screenshots:
1. **Puddles are flat circular discs** (`KE_Puddle_00..11`, `KA_Puddle_01..03`: 0.4 cm cylinders with `MI_Env_PuddleCobble`) — they read as stickers, not water.
2. **The courtyard is empty** — kit walls + cobbles + a few piers; no life, no story.
3. **The chapel key is a grey cube** — `Key_Chapel` is a `BP_TagInteractable` whose `Mesh` component is still `/Engine/BasicShapes/Cube`; its stand `Plinth_Key` is a greybox cube.
Plus a request: **add props, and smoke/fog to make it horror.**

Owner decisions taken in this planning round:
- Fab packs to use: **Old Broken Pillar**, **Horror Props (wrapped bodies only)**, **Misc Props (a few items, via a staging project)**. Not Gothic props pack 1.
- Bodies in the courtyard: **one or two, deliberate** (one on an abandoned cart, one by the well house). The rest are saved for the crypt (Phase 9).
- Licensing: **CC0 + our own procedural Blender models only** (no BlenderKit "Royalty Free"). Fab assets are the owner's Fab Standard/Personal licence items.
- Process (new standing rule): **planning by the lead in Opus 5.5 at Extra (xhigh) effort; every implementation agent runs Sonnet 5.5 at High effort** (`Agent(model:"sonnet", effort:"high")`). Plans must be explicit enough that an implementer never has to guess.

This is a **fix set on the approved Phase 7**, branch `claude/p7-courtyard-polish` from `main` (2cdcac9). It pulls three small, scoped pieces forward from later phases with the owner's request as approval: the puddle layer (Phase 11), ground mist/smoke (Phase 15) and fog tuning (Phase 14). Everything else in those phases stays where it is.

Owner prop/atmosphere choices: **monks' graveyard (NE), abandoned work area (NW by the gatehouse), overgrowth, cart of the dead**; smoke = **smouldering fire pit** in the work area; fog = **low ground mist, readable** (not heavy fog).

---

## 0. Ground rules for every task (implementers must follow)
- **Agents:** spawn every implementer with `model: "sonnet", effort: "high"`. The lead (this session, Opus 5.5, effort xhigh) reviews every result (reads captures, re-checks numbers) before the next task.
- **Branch:** all commits on `claude/p7-courtyard-polish`; sub-agents never switch branches, merge or push; never stage `Source/**` unless the task says so.
- **Editor:** drive Unreal only through `Tools/mcp/ue.py` (read `Tools/mcp/MCP_NOTES.md`); `describe` a toolset before first use; check every result; only ONE agent mutates the editor at a time (tasks marked [EDITOR] are strictly sequential); save after each logical step; never edit `.uasset/.umap` outside the editor.
- **FBX import defaults** (in memory only, re-set in every fresh editor session before importing): `/Script/UnrealEd.Default__FbxStaticMeshImportData` → `vertexColorImportOption = Replace`, `bBuildNanite = true` (set `bBuildNanite=false` explicitly for meshes this plan marks "Nanite off"). Import with `import_materials=false, import_textures=false, combine_meshes=true`. Unused slots are dropped by UE, so assign materials by the slot names that actually exist.
- **GPU (6 GB, R-01/D-046):** no VolumetricCloud, no back-to-back full material recompiles (one master recompile at a time, wait for "shader compile finished" in the log), pause 3 s between captures, capture twice per pose (R-27).
- **Captures:** use the P7-004 clean-capture method (MODULAR_KIT.md §11: set `bVisible=false` on every billboard/sprite/arrow/box/sphere/capsule/brush component, capture, restore) — never save the map while helpers are hidden.
- **Gameplay safety:** never move/retag/delete any gameplay actor (doors, `CP_*`, triggers/volumes, `Trig_CourtyardEntered` X100..200 Y±200, Warden markers, kill volumes) except `Key_Chapel`/`Plinth_Key` exactly as P7F-4 specifies. Props never overlap a trigger/checkpoint volume. Keep the route lanes in §4.1 clear.
- **Collision rule for new props:** large props (cart, barrels, table, gravestones, crosses, pillar, trunk, chest, anvil, log, stump, fire-pit ring, bodies) keep simple collision (`BlockAll`) and **Interaction channel = Ignore** (so they never steal the interaction sweep). Small clutter (bucket, tools, candlestick, branches, moss, all plants, leaves decals) = **NoCollision**.
- **Done = validated:** a task is done only when its listed checks pass and its captures were looked at. Report honestly what was not verified.

---

## 1. Owner steps (Fab) — do these before task P7F-3e
- **O-1 Old Broken Pillar** (fab.com/listings/dbee3498-…): Add to My Library → in the Unreal Editor open **Window → Fab** → My Library → Old Broken Pillar → **Add to Project** (TheLastBell). Tell the lead the Content folder it created.
- **O-2 Horror Props** (fab.com/listings/6f31ba34-…, mature gate): Add to My Library → Window → Fab → **Add to Project** (TheLastBell). Tell the lead the folder name.
- **O-3 Misc Props – UB Free Pack** (fab.com/listings/e5bb46ab-…): choose the **free Personal licence** only if it fits you (otherwise skip it; the plan has fallbacks) → Add to My Library. Create an empty project: Epic Launcher → Unreal Engine 5.8 → Games → Blank, no starter content, path `C:\Hemant\FabStaging\LB_FabStaging`. Add Misc Props to **that** project (not TheLastBell). Tell the lead when done.
- **O-3b Dungeon Environment / 135+ Assets** (fab.com/listings/bb39bae4-…, free, photoreal medieval dungeon props): Add to My Library → Add to Project into the **same `LB_FabStaging`** project (it is large: demo level + a character we do not need). Its main value is the crypt (Phase 9); for this fix set we take only courtyard-relevant pieces chosen by the lead from the staging folder listing (expected: a wall lantern with iron bracket, hanging chains, an iron gibbet cage (empty), a wooden wheel). The rest stays in staging for Phase 9.
- Rejected after review: Gothic props (pack 1) and Stylized Dungeon Pack (both stylized; clash with the photoreal scans).
- Nothing is claimed, bought or accepted by an agent. If a pack is unavailable or you decide against it, the plan's fallback column applies.

---

## 2. Tasks
Order: P7F-0 → (P7F-1 ∥ P7F-2) → P7F-3 → P7F-4 → P7F-5 → P7F-6. [EDITOR] tasks never overlap.

### P7F-0 — Lead setup (lead, no agent)
1. `git switch -c claude/p7-courtyard-polish` from `main` (editor open → no old checkouts).
2. Set this session's effort to xhigh (owner request) and save a feedback memory: "plan with Opus 5.5 xhigh, implement with Sonnet 5.5 high; plans fully explicit".
3. Docs: add a "Phase 7 fix set 2 — Courtyard polish" table to `Docs/IMPLEMENTATION_PLAN.md` (tasks below); DECISIONS: **D-048** model/effort policy; **D-049** Fab packs used (Old Broken Pillar, Horror Props bodies, Misc Props items) under the owner's Fab licence, relocated to `Content/LastBell/ThirdParty/Fab/`, BlenderKit excluded; **D-050** puddles = material layer in `M_LB_Surface` (height-masked, world-noise basins), discs removed; **D-051** key = procedural mesh on a child Blueprint `BP_TagInteractable_ChapelKey`, press-to-take kept (no inspection, RouteBot cannot close inspections); **D-052** atmosphere = tuned height fog (+ second low layer, volumetric fog on) + 8 Local Fog Volumes + 9 engine fog sheets + one Niagara smoke wisp at the fire pit; VolumetricCloud removed; budget ≤ 2 ms translucency/fog (owner measures); **D-053** `Desaturation` param added to `M_LB_Surface` now (resolves D-047 in the same single master recompile). `CLAUDE.md`: add the model/effort rule under "Where things are".
4. Commit "P7F-0: plan + decisions".

### P7F-1 — CC0 downloads (asset-curator; no editor)
Use MCP `3d-assets-local` (`get_asset` then `download_asset`), **format `gltf`, resolution `2k`** (Poly Haven glTF ships JPG/PNG maps, avoiding the EXR-normal problem of the FBX downloads), into `ExternalAssets/Incoming/<provider>-<id>/` (one folder each). Verify every download (file list + sizes); failures are reported, max 2 retries.
| # | id | use |
|---|---|---|
| 1 | polyhaven:wine_barrel_01 | work area barrels |
| 2 | polyhaven:wooden_bucket_01 | well / work area |
| 3 | polyhaven:wooden_bucket_02 | variety |
| 4 | polyhaven:wooden_table_02 | work-area table |
| 5 | polyhaven:dead_tree_trunk | fallen log |
| 6 | polyhaven:tree_stump_01 | stump (axe in it) |
| 7 | polyhaven:dry_branches_medium_01 | kindling / debris |
| 8 | polyhaven:weed_plant_02 | weeds in cracks |
| 9 | polyhaven:nettle_plant | wall-base nettles |
| 10 | polyhaven:fern_02 | shaded corners |
| 11 | polyhaven:moss_01 | moss clumps |
| 12 | polyhaven:rusted_spade_01 | gravedigger spade |
| 13 | polyhaven:picke_dirty_01 | pickaxe |
| 14 | polyhaven:wooden_axe | axe in stump |
| 15 | polyhaven:wooden_candlestick | key ledge candle |
| 16 | polyhaven:rock_moss_set_02 | extra rocks |
| 17 | ambientcg:Leaking019C (2K, JPG) | wall rain-streak decals |
| 18 | ambientcg:ScatteredLeaves009 (1K) | leaf-litter decals — **only if it has an Opacity map**; otherwise skip and report |
Then add one `Docs/ASSET_REGISTRY.md` row per item (same columns as existing rows; Unreal path "pending P7F-3"). Commit registry only (Incoming is git-ignored).

### P7F-2 — Blender: CC0 conversion + new procedural props (technical-artist; headless Blender, no editor)
**2a. `Tools/blender/props/convert_cc0.py`** (new; reuse `Tools/blender/kit/kit_lib.py` export helpers, same FBX settings: `axis_forward='Y', axis_up='Z'`, cm units, `ue_y_flip`, `mesh_smooth_type='OFF'`). For each P7F-1 model: import the glTF; apply transforms; split/join as listed below; set **pivot = bottom-centre** (XY centre of bounds, min Z = 0); rename meshes `SM_LB_CC0_<Name>[_NN]`; keep original material names as slot names; add one `UCX_` box (bounds) for "collision" items, none for "NoCollision" items; export FBX + copy its texture files to `SourceArt/Props/CC0/<Name>/` (CC0 → allowed in git, LFS). Splits: `rock_moss_set_02` → one FBX per rock; `fern_02` → one per clump; `dry_branches_medium_01` → keep joined; all others joined into one mesh. Collision: barrel, table, trunk(log), stump, rocks = UCX box; bucket, plants, moss, tools, candlestick, branches = none.
**2b. `Tools/blender/props/build_props.py`** (new, procedural, seeded, reusing `kit_lib` box/prism/hull/bevel; add `cylinder(r, h, segs)` and `ring(r_out, r_in, h, segs)` helpers to `kit_lib.py`). Pivot = bottom-centre. Vertex colour white. Slots named as listed. Each piece gets `UCX_<name>_NN` boxes as listed. Exact pieces (cm):
| Mesh | Shape | Slots | UCX |
|---|---|---|---|
| `SM_LB_Prop_Key_Chapel` | Medieval iron key lying flat, length along X, total 15.6: **bow** = ring r_out 2.6 / r_in 1.5, thickness 0.7, centred X −5.4, with a cross of two bars (0.4 wide) inside the ring; **collars** = 2 cylinders along X r 0.75 len 0.5 at X −2.6…−2.1 and −1.6…−1.1; **shaft** = cylinder along X r 0.42 from X −2.8 to +7.6 with a hemispherical tip; **bit** = block X 4.6…6.8, Y −0.3…−2.2, thickness 0.55 centred on the shaft axis, with two ward notches 0.35 wide × 0.9 deep cut from the outer edge at X 5.3 and 6.1; 16-segment cylinders; 0.08 bevel; < 3k tris | `MAT_Iron` | 1 box 17 × 7 × 12, Z 0…12 (deliberately taller than the visual so the 8 cm interaction sweep hits the key before the ledge top; it also keeps the RouteBot's bounds-centre target above the ledge) |
| `SM_LB_Prop_KeyLedge_50x50x70` | Weathered stone pedestal replacing `Plinth_Key`: base course 54×54×10 (2 cm chamfer), shaft 46×46×52 with seeded chipped corners (3–6 cm chips), top slab 52×52×8 with a worn dip (top face displaced −0.5…−1.0 cm by noise **outside** a flat 22 × 22 cm centre that stays exactly at Z 70, where the key lies); total height 70 | `MAT_Trim` | 1 box 50×50×70 |
| `SM_LB_Prop_Gravestone_A` | Round-top slab 60w × 14d × 95h, top a half-ellipse, 1.5 cm chamfer, seeded edge chips (min Z = 0 like every prop; the level sinks gravestones 6 cm into the ground) | `MAT_Stone` | 1 box |
| `SM_LB_Prop_Gravestone_B` | Gabled-top slab 55 × 14 × 85 with an incised latin cross relief (1 cm deep, arms 4 cm wide, 40 tall) on the +Y face | `MAT_Stone` | 1 box |
| `SM_LB_Prop_Gravestone_C` | Broken slab 60 × 14 × 45 with a fractured, seeded jagged top; plus a separate fallen fragment mesh `SM_LB_Prop_Gravestone_C_Frag` 50 × 14 × 30 | `MAT_Stone` | 1 box each |
| `SM_LB_Prop_Gravestone_D` | Small rough marker 35 × 20 × 45, irregular hull-based stone | `MAT_Stone` | hull |
| `SM_LB_Prop_StoneCross_A` | Latin cross 55 wide × 18 deep × 150 tall (arms 16×16 section at Z 100…116, upright 18×18), on a base block 40 × 30 × 20; chamfers 1.5, seeded chips | `MAT_Stone` | 3 boxes |
| `SM_LB_Prop_WoodCross_A` | Two beams 8 × 6 section: upright 120, arm 55 at Z 80…88, lashed with 3 rope rings (ring r 5, section 1.2) | `MAT_Wood`, `MAT_Rope` | 2 boxes |
| `SM_LB_Prop_GraveMound_A` | Low earth mound 200 × 90 × 22, smooth noisy dome | `MAT_Earth` | none (walkable; NoCollision in level) |
| `SM_LB_Prop_HandCart_A` | Two-wheeled monastery hand-cart: bed 170 × 100 (frame 8×8 beams, 6 floor planks 15 wide × 3 thick with 2 cm gaps), side boards 25 high × 2.5 thick, two shafts 8×7 extending 110 forward of the bed, axle at bed centre, 2 wheels Ø100 (rim ring section 6 × 5, 10 spokes 4 × 4, hub Ø16 × 20), iron tyre ring section 6 × 1.2 on each wheel; bed top at Z 75 when level | `MAT_Wood`, `MAT_Iron` | 3 boxes (bed+shafts, 2 wheels) |
| `SM_LB_Prop_FirePit_A` | Ring of 9 hull-based stones (25–35 cm) on a circle Ø110; inside 3 charred logs (cylinders r 6–7, len 55–65, crossed, seeded rotation) and an ash disc Ø80 × 2 | `MAT_Stone`, `MAT_Charred` | 1 box (stones ring) |
Also **`verify_props.py`** (pivot bottom-centre ±1 cm, dims ±1 cm per table, slot names exactly as listed, UCX counts as listed, vertex colours white, positive volume) and **`render_props.py`** (Workbench review renders → `Docs/ArtTest/props/*.png`). Outputs: `SourceArt/Props/Procedural/*.fbx`, `LB_Props.blend`, `props_report.json`. `README.md` with commands. All verify checks must pass. LOOK at the renders; iterate until the key reads as a key at arm's length, gravestones/cross read as weathered stone, the cart reads as a medieval cart.

### P7F-3 — Materials, imports, Fab relocation, key Blueprint (technical-artist) [EDITOR]
**3a. Height texture.** Import `ExternalAssets/Incoming/polyhaven-cobblestone_floor_08/polyhaven-cobblestone_floor_08/cobblestone_floor_08_disp_2k.jpg` as `/Game/LastBell/ArtTest/Materials/Cobblestone_Floor_08/T_Cobblestone_Floor_08_H`: sRGB **off**, Compression `TC_Alpha` (BC4), MaxTextureSize 2048, LODGroup World.

**3b. `M_LB_Surface` — one edit session, ONE recompile.** First read the existing six triplanar Custom nodes and copy their texture-sampling pattern (texture-object inputs + shared wrap sampler). Add:
- Static switch **`bPuddles`** (default **false** → every existing MI compiles exactly as before).
- Params (group "Puddles"): `PuddleHeightTex` (Texture2D, default `T_LB_White_Gray`), `PuddleAmount` 0.45, `PuddleNoiseScaleCm` 900, `PuddleEdgeSharpness` 10, `PuddleDampRim` 0.15, `PuddleWaterTint` (0.30, 0.32, 0.35), `PuddleRoughness` 0.04, `PuddleNormalFlatten` 0.95, `PuddleUpFacingMin` 0.85, `WetnessVariation` 0.4.
- **`HeightUV`** = StaticSwitch(`bWorldAlignedUV`): true → `AbsoluteWorldPosition.xy / WorldTileSizeCm` (identical to the triplanar Z-plane UV, so water lines up with the visible stone gaps); false → `TexCoord0 * UVScale`.
- One Custom node **`LB_PuddleMask`** (output Float3) with inputs `WorldPos` (AbsoluteWorldPosition), `NormalWS` (VertexNormalWS), `HeightUV`, `MacroTex` (existing MacroTex texture object), `HeightTex` (PuddleHeightTex), and the scalars. Code:
  ```hlsl
  float2 nUV = WorldPos.xy / PuddleNoiseScaleCm;
  float a = Texture2DSample(MacroTex, MacroTexSampler, nUV).r;
  float b = Texture2DSample(MacroTex, MacroTexSampler, nUV * 2.37 + float2(0.37, 0.71)).r;
  float basin = saturate(((a * 0.6 + b * 0.4) - (1.0 - PuddleAmount)) * 3.0);
  float h = Texture2DSample(HeightTex, HeightTexSampler, HeightUV).r;
  float up = saturate((NormalWS.z - PuddleUpFacingMin) / max(1.0 - PuddleUpFacingMin, 1e-3));
  float water = saturate((basin - h) * PuddleEdgeSharpness) * up;
  float damp  = saturate((basin + PuddleDampRim - h) * PuddleEdgeSharpness) * up;
  return float3(water, damp, basin);
  ```
  (adapt sampler names to the pattern the existing nodes use; behaviour must be identical).
- Wiring when `bPuddles` = true (StaticSwitch true branch; false branch = current graph unchanged): `WetTotal = max(saturate(Wetness + basin * WetnessVariation), damp)` replaces `Wetness` in the existing wetness math (BaseColor × lerp(1, 0.55, WetTotal); Roughness × lerp(1, 0.3, WetTotal), floor 0.04). Then water on top: `BaseColor = lerp(BC, BC * PuddleWaterTint, water)`; `Roughness = lerp(R, PuddleRoughness, water)`; tangent `Normal = normalize(lerp(N, float3(0,0,1), water * PuddleNormalFlatten))`.
- **`Desaturation`** scalar (group Color, default 0): `BC = lerp(BC, dot(BC, float3(0.299, 0.587, 0.114)).xxx, Desaturation)`, applied after BaseColorTint/BrightnessMul, before wetness.
- Recompile once; wait for shader compilation to finish in the log; zero errors. **Regression check:** capture `CaptureAssetImage` of `MI_Kit_Floor`, `MI_Kit_Masonry`, `MI_Kit_Cliff`, `MI_Medieval_Blocks_03` before and after; mean absolute pixel difference ≤ 2/255 (default values must not change anything).

**3c. Material instances** (`/Game/LastBell/Environments/Courtyard/Materials/` unless stated):
| MI | Parent | Values |
|---|---|---|
| `MI_Env_Floor_Puddled` | MI_Kit_Floor | bPuddles ✓, PuddleHeightTex = T_Cobblestone_Floor_08_H, PuddleAmount 0.45, PuddleNoiseScaleCm 900, Wetness 0.35, others default |
| `MI_Env_Floor_Puddled_Approach` | MI_Env_Floor_Puddled | PuddleAmount 0.55, PuddleNoiseScaleCm 600 |
| `MI_Kit_Cliff` (edit) | — | Desaturation 0.55, BaseColorTint (0.45, 0.50, 0.58), BrightnessMul 1.3 |
| `MI_Prop_Key_Iron` | MI_Rusty_Metal_04 (UV0 path) | UVScale 6, BrightnessMul 0.75, RoughnessMin 0.25, RoughnessMax 0.75, Desaturation 0.15 |
| `MI_Prop_Stone_Grave` | MI_Rock_064_WA | WorldTileSizeCm 120, Desaturation 0.6, BaseColorTint (0.62, 0.63, 0.65), BrightnessMul 1.1, MacroStrength 0.6 |
| `MI_Prop_Wood_Weathered` | MI_Weathered_Planks | UVScale 1, Desaturation 0.3, BrightnessMul 0.8 |
| `MI_Prop_Iron_Rusty` | MI_Rusty_Metal_04 | UVScale 2 |
| `MI_Prop_Rope` | MI_Weathered_Planks | BaseColorTint (0.45, 0.38, 0.28), UVScale 4 |
| `MI_Prop_Earth` | MI_Brown_Mud_03_WA | WorldTileSizeCm 200, Wetness 0.3 |
| `MI_Prop_Charred` | MI_Weathered_Planks | BaseColorTint (0.08, 0.07, 0.065), BrightnessMul 0.6, RoughnessMin 0.7 |
Slot mapping for procedural props: `MAT_Iron`→MI_Prop_Iron_Rusty (key: MI_Prop_Key_Iron), `MAT_Stone`→MI_Prop_Stone_Grave, `MAT_Trim`→MI_Kit_Trim, `MAT_Wood`→MI_Prop_Wood_Weathered, `MAT_Rope`→MI_Prop_Rope, `MAT_Earth`→MI_Prop_Earth, `MAT_Charred`→MI_Prop_Charred. Fire-pit stones `MAT_Stone` → MI_Kit_Rubble instead.
CC0 props: one MI each (`MI_CC0_<Name>`, child of `M_LB_Surface`, `bUseARM` ✓ with the glTF `_arm` map; normals from `nor_gl` with `bFlipGreenChannel` ✓; BaseColor sRGB; ARM `TC_Masks`; MaxTextureSize 1024 for bucket, tools, candlestick; 2048 for the rest).

**3d. New master `M_LB_Foliage`** (`/Game/LastBell/Materials/Master/`): Blend **Masked**, Shading **TwoSidedFoliage**, TwoSided ✓, OpacityMaskClipValue 0.33, Used with Nanite ✓ and Instanced Static Meshes ✓, no WPO. Params: `BaseColorTex`, `BaseColorTint` (1,1,1), `BrightnessMul` 1, `Desaturation` 0.25, static switch `bSeparateOpacity` (false → OpacityMask = BaseColorTex.a; true → `OpacityTex`.r), `NormalTex` (+flip-green textures), static switch `bUseARM` (`ARMTex` G = roughness) else `RoughnessTex`, `SubsurfaceColor` = BaseColor × `TranslucencyTint` (0.6, 0.7, 0.4) × `TranslucencyStrength` 0.4. One `MI_Foliage_<Name>` per plant; plant textures MaxTextureSize 1024.

**3e. New master `M_LB_Mist`** (`/Game/LastBell/Materials/Master/`, for the Niagara smoke sprites): Translucent, **Unlit**, TwoSided, Used with Niagara Sprites ✓, Apply Fogging ✓. `Emissive = MistColor × MistBrightness × ParticleColor.rgb`. `Opacity = saturate(ParticleColor.a × N × R × DepthFade(150) × CameraDepthFade(length 250, offset 50))`, where `N = pow(T(uv×1.0 + time×(0.010, 0.004)) × T(uv×1.7 + time×(−0.007, 0.006)), 1.5)` with `T` = engine cloud texture `/Engine/EngineVolumetrics/Fogsheet/Textures/T_EV_FogSheet_CloudTex_01` (find its exact path with an asset search; no free smoke texture exists — verified), and `R = pow(smoothstep(0, 1, 1 − saturate(length(uv − 0.5) × 2)), 1.6)`. Defaults MistColor (0.42, 0.47, 0.56), MistBrightness 0.6. MI: `MI_FX_SmokeWisp` in `/Game/LastBell/FX/Materials/` (MistColor (0.20, 0.20, 0.22), MistBrightness 0.5).
**3e-2. Fog-sheet MI.** Duplicate engine `MI_Fogsheet_HideClose` (`/Engine/EngineVolumetrics/Fogsheet/…`) to `/Game/LastBell/FX/Materials/MI_FX_FogSheet_Ground` (keep the engine parent). Read its parameter list first; set the colour parameter to (0.40, 0.45, 0.55), the opacity/density parameter to 25 % of its default, any panning speed to 50 % of default; record all values in the commit message. Engine content is covered by the UE EULA (registry row "Epic engine content").

**3f. Imports.** Converted CC0 FBX → `/Game/LastBell/Environments/Props/CC0/<Name>/`; procedural FBX → `/Game/LastBell/Environments/Props/Procedural/`. Nanite ON for everything except `SM_LB_Prop_Key_Chapel` and the candlestick (Nanite OFF, 1 auto LOD). Verify bounds vs `props_report.json` (±1 cm), slots, collision present only where listed.

**3g. Fab relocation** (after O-1…O-3 and owner step O-4 below):
- Move (rename asset with redirector fix-up) Old Broken Pillar assets → `/Game/LastBell/ThirdParty/Fab/OldBrokenPillar/`; Horror Props → `/Game/LastBell/ThirdParty/Fab/HorrorProps/`. From Horror Props keep: the **rope-bound burlap body (lying)**, the **cloth-shrouded body (grey/white sheet)** and the **hanging wrapped body** (reserved for the crypt, Phase 9). Delete the **metal stretcher** and **black body bag** (and textures/materials only they use). Delete the emptied Fab install folders; "Fix Up Redirectors" on `/Game`. Enable Nanite on the kept meshes; confirm simple collision exists.
- **Pick list from staging:** the lead lists `C:\Hemant\FabStaging\LB_FabStaging\Content\**` (file names only, read-only) and writes the exact asset names to migrate into `Docs/ArtTest/courtyard_polish/fab_picklist.md`: from Misc Props **Anvil, Chest, Trunk, CarpenterTools**; from Dungeon Environment the wall lantern + bracket, a hanging chain, an empty iron cage and a wooden wheel (exact names from the listing).
- **O-4 (owner, ~5 min):** open `LB_FabStaging`, select exactly the meshes in `fab_picklist.md` → right-click → Asset Actions → **Migrate** → target `C:\Hemant\Prj\Learning\TheLastBell\Content`. The agent then moves them to `/Game/LastBell/ThirdParty/Fab/MiscProps/` and `/Game/LastBell/ThirdParty/Fab/Dungeon/` (+ redirector fix-up).
- One `ASSET_REGISTRY.md` row per Fab asset (source Fab, author, URL, licence "Fab Standard License (free)" / "Fab Personal licence (free tier)" for Misc Props).
- Fallbacks if the owner skipped a pack: no pillar → use `SM_LB_Kit_Pier_Broken_100x100x350` lying on its side; no Horror Props → the cart stays empty and both body beats are dropped (nothing substituted); no Misc Props → omit anvil/chest/trunk/tools.

**3h. Key Blueprint.** Create child Blueprint `/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_ChapelKey` (parent `BP_TagInteractable`). In the child's defaults set the inherited `Mesh` component: StaticMesh `SM_LB_Prop_Key_Chapel`, material 0 `MI_Prop_Key_Iron`, relative transform identity, collision response for the Interaction channel (`ECC_GameTraceChannel2`) **Block**, root `DefaultSceneRoot` Mobility **Movable**. Compile + save. (Do NOT edit `BP_TagInteractable` itself — the crank, candles, bell and the PlayerFeel test use it.)
Commit P7F-3 in 2–3 checkpoints.

### P7F-4 — Level dressing in `L_Monastery` (environment-designer) [EDITOR]
All coordinates are world cm (ground Z = 0; slab tops 1.5). "Place at (x, y)" = put the actor so its **world-bounds centre XY = (x, y)** and **bounds min Z = 0** (or the stated Z), then apply the stated yaw. Our converted/procedural meshes have bottom-centre pivots, so location = (x, y, 0) directly; Fab meshes may not — always re-seat by bounds. Scale 1 unless stated. Every new actor gets the listed label and Outliner folder. Collision per §0. After each block, save.

**4.1 Lanes that must stay free of collision props (2D distance from any collision prop's bounds to the segment ≥ 60 cm; check with a script and list the result):**
- L-A gate→well: (310, 0) → (1250, −300) → (1500, −1600) → (1500, −1850)
- L-B well→chapel door: (1500, −1800) → (5850, 0), plus the door recess X 5850…6000 × Y −200…200
- L-C well→shortcut: (1500, −1800) → (5850, 2000), plus the recess X 5850…6000 × Y 1800…2200
- L-D gate→door: (450, 0) → (2400, −400) → (3500, −500) → (5800, 0)
- L-E gate→shortcut: (450, 0) → (2600, 500) → (4500, 700) → (5300, 1400) → (5780, 2000)
- Approach corridor X −3000…0, Y −200…200: no new collision props at all.
- Never place anything inside `Trig_CourtyardEntered` (X 100…200, Y ±200), `CP_Courtyard` (X 300…400, Y ±300), `CP_Approach` (X −2750…−2650, Y ±200).

**4.2 Remove the discs, apply real puddles, hide the grid seams**
- Delete 33 disc actors: `KA_Puddle_00…03`, `KA_Mud_00…03`, `KE_Puddle_00…11`, `KE_Mud_00…12` (all `/Engine/BasicShapes/Cylinder`, scale Z 0.004).
- Set the material override of all 36 `KE_Floor_i_j` slabs to `MI_Env_Floor_Puddled` and of `KA_Floor_0…2` to `MI_Env_Floor_Puddled_Approach` (replacing the per-slab Wet/Damp checkerboard that showed 10 m tile seams).
- `Ground_0`: material override `WorldGridMaterial` → `MI_Kit_Floor` (the grid showed through the 1.5 cm slab seams; chapel floor art is Phase 8).
- After these, delete the now-unreferenced MIs `MI_Env_PuddleCobble`, `MI_Env_DampPatch`, `MI_Env_Puddle`, `MI_Env_Floor_Wet`, `MI_Env_Floor_Damp` (check references first; keep any that are still referenced and report).
- Acceptance (captures 01/02/04/06): water visible on roughly 15–35 % of the visible floor, irregular outlines, water filling the gaps between cobbles first, reflective; no circles, no tile seams. If coverage is off, tune only `PuddleAmount` (0.35…0.55) and `PuddleNoiseScaleCm` (700…1100) on the two MIs.

**4.3 The key** (`Gameplay/Courtyard`)
- Delete `Plinth_Key` (StaticMeshActor_62, cube). Place `SM_LB_Prop_KeyLedge_50x50x70` as label **`Plinth_Key`** at (1500, −2050, 0), yaw 0, folder `Courtyard`, Mobility Static, collision BlockAll; then try setting its Interaction channel (`ECC_GameTraceChannel2`) response to **Ignore** (custom collision profile) and read it back — if it does not persist, leave BlockAll and say so (the key's tall UCX covers it).
- Spawn `BP_TagInteractable_ChapelKey` at **(1500, −2050, 70)**, rotation (0, **65**, 0), scale **1** (the old actor had 0.2), folder `Gameplay/Courtyard`. Before deleting the old `Key_Chapel`, dump all its actor + component properties to `Docs/ArtTest/courtyard_polish/key_before.json`. The child class already carries the instance values found by the survey (PromptText "Take key", GrantedStateTags [State.Item.ChapelKey], bSingleUse true, ConsumedStateTag State.Item.ChapelKey, NoiseLoudness 0.2, UseStateTag State.Item.ChapelKey, bHideOnUse true, bInspectable false, InspectableComp bKeepOnClose true) — if 3h could not put any of them on the child CDO, set them on the new instance and read them back. Then delete the old actor and label the new one **`Key_Chapel`**. Read back and diff against `key_before.json`: only class, mesh, location Z and scale may differ.
- Candle: `SM_LB_CC0_WoodenCandlestick` at (1478, −2068, 70), yaw 20, NoCollision. Light **`Light_KeyLedge_Warm`** (PointLight) at (1450, −2100, 118): 180 lm, attenuation radius 220, colour (255, 158, 82), CastShadows false, Movable, VolumetricScatteringIntensity 1.5 (the flame itself comes with Phase 15 VFX — note it).

**4.4 Abandoned work area (NW, zone X 320…1950, Y 1050…2480)** — folder `Courtyard/Dressing/WorkArea`
| Label | Mesh | Place at | Yaw | Notes |
|---|---|---|---|---|
| KX_FirePit | SM_LB_Prop_FirePit_A | (1150, 1650) | 0 | collision ring |
| KX_Barrel_0 | SM_LB_CC0_WineBarrel01 | (400, 2410) | 0 | standing |
| KX_Barrel_1 | SM_LB_CC0_WineBarrel01 | (480, 2330) | 40 | standing |
| KX_Barrel_2 | SM_LB_CC0_WineBarrel01 | (600, 2410) | 0 | **lying**: pitch 90, axis along X, re-seat min Z 0 |
| KX_Bucket_0 | SM_LB_CC0_WoodenBucket01 | (1050, 2380) | 15 | NoCollision |
| KX_Bucket_1 | SM_LB_CC0_WoodenBucket02 | (1260, 1470) | 0 | tipped: roll 90, re-seat; NoCollision |
| KX_Table | SM_LB_CC0_WoodenTable02 | centre X 1300, bounds max Y = 2470 | 0 | long axis along X |
| KX_Tools | Fab CarpenterTools | on the table top centre (trace the top Z) | 10 | NoCollision; omit if O-3 skipped |
| KX_Chest | Fab Chest | centre X 1550, bounds max Y = 2480 | 180 | lid toward the courtyard; omit if O-3 skipped |
| KX_Trunk | Fab Trunk | centre Y 1900, bounds min X = 320 | 90 | omit if O-3 skipped |
| KX_Anvil | Fab Anvil | (1650, 2150) | 15 | omit if O-3 skipped |
| KX_Log | SM_LB_CC0_DeadTreeTrunk | (950, 1250) | 10 | uniform-scale down if longer than 400 cm |
| KX_Stump | SM_LB_CC0_TreeStump01 | (1750, 1500) | 0 | |
| KX_Axe | SM_LB_CC0_WoodenAxe | blade embedded 4 cm into the stump top centre, handle up-and-out, pitch −35 | 30 | NoCollision |
| KX_Branches_0 | SM_LB_CC0_DryBranchesMedium01 | (1290, 1700) | 0 | NoCollision |
| KX_Branches_1 | SM_LB_CC0_DryBranchesMedium01 | (520, 2050) | 120 | NoCollision |
| KX_Wheel | Dungeon wooden wheel | X 1800, leaning on the north wall, bounds max Y = 2485, tilted 12° from vertical toward the wall | 0 | omit if not in the pack |
| KX_WallLantern | Dungeon wall lantern + bracket | on the west curtain's inner face (X 300) at Y 1600, bracket top Z 230, facing +X | — | omit if not in the pack |
| Light_WorkArea_Lantern | PointLight | (345, 1600, 215) | — | 600 lm, radius 600, colour (255, 140, 56), no shadows, VolumetricScatteringIntensity 2; only if the lantern was placed |
| Light_FirePit_Ember | PointLight | (1150, 1650, 30) | — | 250 lm, radius 260, colour (255, 90, 30), no shadows, VolumetricScatteringIntensity 1.5 |
Optional iron cage: only if the Dungeon pack has both an iron cage and a wall hook/bracket — hang the empty cage from the courtyard face of `KG_ButtN` (X 450, Y 650) with its top at Z 420 and bottom ≥ Z 260; otherwise omit.

**4.5 Monks' graveyard (NE, zone X 2200…4400, Y 1150…2300)** — folder `Courtyard/Dressing/Graveyard`. Stones face **−Y** (toward the nave, so the player reads them); gravestones and crosses are sunk 6 cm (Z −6); mounds lie in front (south) of their stone, long axis along Y (yaw 90).
| Label | Mesh | Place at (x, y) | Yaw | Notes |
|---|---|---|---|---|
| KY_Stone_A0 | Gravestone_A | (2400, 2050) | 0 | |
| KY_Cross_S0 | StoneCross_A | (2800, 2050) | 0 | |
| KY_Stone_B0 | Gravestone_B | (3200, 2050) | 180 | relief faces −Y |
| KY_Stone_C0 | Gravestone_C | (3600, 2050) | 0 | |
| KY_Stone_C0_Frag | Gravestone_C_Frag | (3690, 1960) | 35 | lying: pitch 80, re-seat min Z 0 |
| KY_Cross_W0 | WoodCross_A | (4000, 2050) | 0 | roll 7 (leaning) |
| KY_Stone_D0 | Gravestone_D | (2500, 1550) | 15 | |
| KY_Stone_A1 | Gravestone_A | (2900, 1550) | 8 | roll 6 (leaning) |
| KY_Stone_B1 | Gravestone_B | (3300, 1550) | 175 | |
| KY_Mound_0…5 | GraveMound_A | in front of KY_Stone_A0, Cross_S0, Stone_B0, Stone_D0, Stone_A1, Stone_B1: (stone x, stone y − 120) | 90 | NoCollision |
| KY_FreshGrave | GraveMound_A | (3700, 1430) | 90 | scale Z 1.4 (fresher, higher) ; NoCollision |
| KY_Spade | SM_LB_CC0_RustedSpade01 | blade tip 20 cm below the fresh mound surface at (3700, 1400), upright, roll 12 | 0 | NoCollision |
| KY_Pickaxe | SM_LB_CC0_PickeDirty01 | (3820, 1520), lying flat, min Z 0 | 30 | NoCollision |
| KY_Branches | SM_LB_CC0_DryBranchesMedium01 | (2700, 2200) | 60 | NoCollision |
| KY_Rock_0 | SM_LB_CC0_RockMossSet02_01 | (4450, 2250) | 0 | collision |

**4.6 Cart of the dead + well-house body (S)** — folder `Courtyard/Dressing/Dead`
| Label | Mesh | Placement | Notes |
|---|---|---|---|
| KZ_Cart | SM_LB_Prop_HandCart_A | centre (2900, −2050), yaw 200; tip it forward so the shafts rest on the ground: pitch the cart about its axle ≈ 15° front-down, then lower until both wheel bottoms and both shaft tips are within 3 cm of the ground (verify with 4 down-traces; report the values) | collision |
| KZ_Body_Cart | Horror Props rope-bound burlap body | lying on the cart bed, aligned with the bed's long axis, roll 5°, resting on the traced bed surface | NoCollision; omit if O-2 skipped |
| KZ_Body_Well | Horror Props cloth-shrouded body | centre (1800, −2000), yaw 90 (long axis along Y, along the well house's east wall), lying, min Z 0 | NoCollision; omit if O-2 skipped |
| KZ_Pillar_Fallen | Fab Old Broken Pillar | lying (pitch 90) at centre (3750, −2150), yaw 75; whole bounds within X 3350…4150, Y −2400…−1900 | collision; fallback: `SM_LB_Kit_Pier_Broken_100x100x350` lying |
| (swap) | Fab Old Broken Pillar | if its footprint ≤ 110 × 110 cm: replace the meshes of `KD_Pier_S1` and `KD_Pier_N2` (keep their locations, bottom Z 0); otherwise keep the kit broken piers | |

**4.7 Overgrowth** — folder `Courtyard/Dressing/Overgrowth`, all NoCollision, `MI_Foliage_*` materials. Format (x, y, yaw, scale):
- Weeds `SM_LB_CC0_WeedPlant02`: (1000, 2450, 0, 1.0) (2550, 2440, 40, 1.1) (4520, 2440, 75, 1.2) (5250, 2450, 120, 0.9) (1300, −2450, 15, 1.0) (1700, −2440, 60, 1.2) (3700, −2440, 100, 1.1) (4900, −2450, 150, 0.9) (2060, 960, 30, 0.7) (3060, −960, 80, 0.7) (4060, 960, 130, 0.7) (5060, −960, 170, 0.7) (2300, 300, 20, 0.6) (3700, −350, 70, 0.6) (4400, 600, 110, 0.6) (5200, −500, 160, 0.6) (1000, −1650, 45, 0.9) (700, −450, 90, 0.8)
- Nettles `SM_LB_CC0_NettlePlant`: (600, 2450, 0, 1.0) (2050, 2440, 30, 1.0) (3300, 2440, 60, 1.1) (5700, 2440, 90, 1.0) (2300, −2440, 120, 1.0) (4300, −2440, 150, 1.1) (5940, −1650, 0, 0.9) (5940, 1450, 45, 0.9)
- Ferns `SM_LB_CC0_Fern02_01…04` (cycle the 4 clumps): (2350, 2300, 0) (4250, 2300, 60) (1250, −2300, 30) (1760, −2200, 90) (3150, 2300, 120) (5800, 2300, 150), scale 1.0
- Moss `SM_LB_CC0_Moss01`: (340, 1300) (340, −1300) (2000, 850) (3000, −850) (4000, 850) (5000, −850) (2600, 1700) (3500, 1800) (900, −1850) (1850, −1600) (5600, −2200) (5600, 2200), yaw 0/45/90/… cycling, scale 1.0
- Rocks `SM_LB_CC0_RockMossSet02_02/03` (collision): (1150, −1950, 20) (5700, −2250, 110)

**4.8 Decals** — folder `Courtyard/Dressing/Decals`
- `MI_Decal_Leaking019C` (child of `M_LB_Decal`, Leaking019C textures; OpacityStrength 1.6, DarkenStrength 0.3, EdgeFadeU 0.12, EdgeFadeV 0.06, DepthFade 0.3, DecalHalfDepthCm = the decal actor's DecalSize.X). Six DecalActors projecting onto inner wall faces, DecalSize X 40 (depth), Y/Z matched to the texture aspect with height 300, top at Z 720: north face (Y 2500, facing −Y) at X 1300, 2900, 5300; south face (Y −2500, facing +Y) at X 2500, 4300; east face (X 6000, facing −X) at Y −1600.
- Only if P7F-1 #18 was downloaded: `MI_Decal_Leaves` (opacity from its map), 6 floor decals projecting down (pitch −90), DecalSize (60, 300, 300) at (500, 2300) (2600, 1300) (4100, 2200) (600, −2300) (5600, −2250) (2200, −1500).

**4.9 Walk-path tests (data-driven, no C++)** — folder `Gameplay/WalkPaths`
`FLBWalkPathRunner` (`Source/LastBellTests/Tests/LBWalkPathTests.cpp:82-126`) discovers `ATargetPoint` actors tagged `WalkPath.<Name>.<NN>` and walks them with real movement input. Read the Z convention of the existing `WalkPath.SacristyToCrypt.*` points first and use the same height above the floor. Add three paths:
- `WalkPath.CourtyardKey.00…04`: (450, 0) (1250, −300) (1500, −1550) (1500, −1850) (1520, −1950)
- `WalkPath.CourtyardDoor.00…03`: (450, 0) (2400, −400) (3500, −500) (5800, 0)
- `WalkPath.CourtyardShortcut.00…04`: (450, 0) (2600, 500) (4500, 700) (5300, 1400) (5780, 2000)
No `Requires.*` tags (the doors are not passed). These make `LastBell.Functional.WalkPath.Monastery` fail if a prop ever blocks a courtyard route (closing R-21 for the courtyard).
Commit P7F-4 in checkpoints (4.2–4.3, 4.4–4.6, 4.7–4.9).

### P7F-5 — Atmosphere: fog, mist, smoke, light fixes (lighting-vfx) [EDITOR]
**5a. Fix what the survey found** (old → new):
- `DirectionalLight_1` (moon): rotation (0, 0, 0) → **pitch −38, yaw 35, roll 0** (P7-004 intended this but it did not stick); read back.
- `VolumetricCloud_1`: **delete** (D-046 bans volumetric clouds on the 6 GB GPU; the sky sphere is the sky). Check the sky still looks the same.
- `SkyLight_1`: `bRealTimeCapture` true → **false** (so the specified cubemap is used; cheaper); recapture.
- Grey-box fills `Light_Courtyard_0…6` and `Light_Approach_0…2` (white 3000/1800 lm, they flatten the night): colour → (140, 168, 255), intensity → courtyard 700 lm (Light_Courtyard_6 over the well: 300 lm), approach 500 lm, `VolumetricScatteringIntensity` → **0** (no fog blobs). Leave `Light_Courtyard_7` (east passage) and every interior light untouched.
- Warm lights `Light_Gatehouse_Warm`, `Light_Well_Warm`, `Light_ChapelDoor_Warm`, `Light_KeyLedge_Warm`, `Light_WorkArea_Lantern`, `Light_FirePit_Ember`: `VolumetricScatteringIntensity` → 2.0 (lantern halos in fog).
**5b. Height fog** (`ExponentialHeightFog_1`): location Z −200 → **0**; FogDensity 0.02 → **0.035**; FogHeightFalloff 0.2 → **0.35**; SecondFogData density 0 → **0.06**, falloff 0.2 → **1.5**, offset 0 → **−100**; FogInscatteringLuminance → (0.020, 0.032, 0.060); FogMaxOpacity 1 → 0.95; **bEnableVolumetricFog → true**, ScatteringDistribution 0.2 → **0.55**, Albedo → (0.82, 0.86, 0.95), ExtinctionScale → **1.2**, ViewDistance 6000 → **5000**, StartDistance → 100, NearFadeInDistance → 200.
**5c. Local Fog Volumes** (class `/Script/Engine.LocalFogVolume`; none exist yet), folder `Lighting/Fog`. For each: place at the centre (Z 0), then scale so its **world bounds** match the target extents (read bounds back), set HeightFogExtinction / RadialFogExtinction / HeightFogFalloff / HeightFogOffset as given (read the defaults first; record them). FogAlbedo (0.80, 0.84, 0.92).
| Label | Centre (x, y) | Target extent X × Y × Z (cm) | HeightFogExtinction | RadialFogExtinction |
|---|---|---|---|---|
| LFV_Approach_W | (−2300, 0) | 1400 × 700 × 300 | 1.0 | 0.2 |
| LFV_Approach_E | (−900, 0) | 1400 × 700 × 300 | 1.0 | 0.2 |
| LFV_Gate | (450, 0) | 600 × 1200 × 250 | 0.6 | 0.1 |
| LFV_Graveyard | (3300, 1750) | 2600 × 1300 × 300 | 1.5 | 0.3 |
| LFV_Well | (1500, −2000) | 1200 × 1000 × 250 | 0.5 | 0.1 |
| LFV_CollapsedWall | (900, −1100) | 900 × 1500 × 250 | 1.0 | 0.2 |
| LFV_SouthAisle | (3900, −1900) | 2600 × 1200 × 250 | 1.0 | 0.2 |
| LFV_ChapelFront | (5500, 0) | 900 × 1800 × 250 | 0.8 | 0.15 |
HeightFogFalloff: set so the mist is densest at the floor and nearly gone by ~120 cm (start from the default, adjust, record the final value); HeightFogOffset 0.
**5d. Fog sheets** (engine `S_EV_FogSheet_01` + `MI_FX_FogSheet_Ground`, folder `Lighting/Fog`): vertical cards, bottom at Z 0, scaled to the width × height given, normal facing the stated direction (toward where the player looks from):
FS_App_0 (−2600, 0) 400 × 180 facing −X; FS_App_1 (−1600, 0) 400 × 180 facing −X; FS_App_2 (−700, 0) 400 × 180 facing −X; FS_Collapsed (1100, −1050) 700 × 150 facing −X; FS_NW (900, 1900) 800 × 150 facing −Y; FS_Grave_0 (2600, 1250) 900 × 160 facing −Y; FS_Grave_1 (3900, 1350) 900 × 160 facing −Y; FS_South_0 (3400, −1900) 1000 × 150 facing +Y; FS_South_1 (4800, −2000) 900 × 150 facing +Y.
Acceptance: no visible hard card edge in any review capture; if one shows, halve its opacity or delete it (report which).
**5e. Smoke wisp (Niagara)** `NS_LB_SmokeWisp` in `/Game/LastBell/FX/Niagara/`: `NiagaraToolset_System.CreateNiagaraSystem` (template `/Niagara/DefaultAssets/DefaultSystem`), `AddEmitter` from `/Niagara/DefaultAssets/Templates/Emitters/Fountain`, then: SpawnRate 5/s; lifetime 6–9 s; initial colour (0.22, 0.22, 0.24, 0.35); sprite size 60–90; velocity in a cone (axis +Z, angle 12°) 30–45 cm/s; gravity off; drag 0.6; Curl Noise Force strength 20, frequency 0.02; Scale Sprite Size over life 1 → 3.5; alpha over life 0 → 1 at 15 % → 0 at 100 %; sprite renderer material `MI_FX_SmokeWisp`, sort by view depth; fixed bounds (−250, −250, 0)…(250, 250, 700). Place a NiagaraActor `FX_FirePit_Smoke` at (1150, 1650, 25). Check `GetSystemCompileState` and `GetStackIssues` are clean. **Fallback:** if CreateNiagaraSystem/AddEmitter cannot produce a working system, skip the smoke (keep the ember light) and report exactly which call failed.
**5f. Exposure.** Re-tune only `PP_Outdoor_Night` (EV100 min = max, currently 2) within 1.0…2.0 to meet: capture `04_courtyard_chapel_front` mean sRGB luma 0.10–0.20; darkest 5 % of pixels > 0.015 (not crushed); the chapel door lantern and the gate arch clearly readable. Measure with a small Python script on the PNGs and report the numbers.
**5g. Readability gates:** from the spawn (−2800, 0, 170) facing +X the gate arch (28 m) is clearly visible; from `CP_Courtyard` (350, 0, 170) facing +X the chapel front (56 m) reads as a silhouette with its door lantern; inside the well house the key is visible at 2 m. If fog breaks any gate, lower `LFV_*` extinction / height-fog density first.
Commit P7F-5.

### P7F-6 — QA and owner review (qa-reviewer; lead reviews) [EDITOR for captures]
1. `powershell -ExecutionPolicy Bypass -File Tools\mirror_build_and_test.ps1` after the map is saved → **78/78 pass**, and the log shows the three new `[WalkPath] Courtyard* PASS` lines plus `RouteBot.Monastery` passing (the key pickup).
2. Lane check script output (§4.1) — all ≥ 60 cm.
3. Output Log: no new errors; list warnings.
4. Clean captures (eye height 170, twice per pose) to `Docs/ArtTest/courtyard_polish/`: 01 spawn→approach (−2800, 0) yaw 0; 02 approach mid (−1500, 0) yaw 0; 03 gate→courtyard (100, 0) yaw 0; 04 courtyard→chapel (500, 0) yaw 0; 05 key close-up (1500, −1880, 150) yaw −90 pitch −35; 06 graveyard (3300, 700) yaw 90; 07 cart (2600, −1350) yaw −60; 08 work area + smoke (1300, 900) yaw 100; 09 collapsed wall (1300, −700) yaw 200; 10 puddles close (2200, −300, 160) yaw 0 pitch −25; 11 aerial (3000, 0, 4000) pitch −60; 12 chapel interior check (6500, 0) yaw 0 (must look unchanged except outdoor fog).
5. **Owner checks (human, in PIE on the RTX 4050):** `stat fps` ≥ 60 at 1080p in the courtyard; `stat gpu` — note the ms for VolumetricFog, Translucency, LocalFogVolumes, Lumen (budget: translucency + fog + Niagara ≤ 2 ms total); walk all routes; take the key (it should look like an iron key and vanish when taken); check puddles at different angles; feel of the mist.
6. Docs (lead): add to `Tools/mcp/MCP_NOTES.md` the FBX import defaults, the clean-capture method, the Niagara create flow and the "component edits on BP instances don't persist → use a child BP" rule; update `ASSET_REGISTRY.md` (all new rows), `RISKS.md` (R-21 courtyard covered by WalkPaths; new R-28 translucency/fog cost, measured by the owner).
7. Report **"P7-FIX2 READY FOR YOUR REVIEW"** with captures, numbers, known issues; stop. Merge only on the owner's approval.

---

## 3. Critical files and assets
- Plan/decisions: `Docs/IMPLEMENTATION_PLAN.md`, `Docs/DECISIONS.md` (D-048…D-053), `Docs/ASSET_REGISTRY.md`, `Docs/RISKS.md`, `Tools/mcp/MCP_NOTES.md`, `CLAUDE.md`.
- Blender: `Tools/blender/kit/kit_lib.py` (add `cylinder`, `ring`), new `Tools/blender/props/{convert_cc0,build_props,verify_props,render_props}.py`, `SourceArt/Props/`.
- Materials: `/Game/LastBell/Materials/Master/M_LB_Surface` (puddles, Desaturation), new `M_LB_Foliage`, `M_LB_Mist`; MIs under `/Game/LastBell/Environments/Courtyard/Materials/`, `/Game/LastBell/FX/Materials/`.
- Blueprint: new `/Game/LastBell/Blueprints/Interactables/BP_TagInteractable_ChapelKey` (parent `BP_TagInteractable`, untouched).
- Map: `/Game/LastBell/Maps/L_Monastery` (Approach, Courtyard, Lighting folders only).
- Reused code (no changes): `LBWalkPathTests.cpp` (data-driven paths), `LBRouteBot.cpp` (finds the key by `GrantedStateTags`), `ULBInteractableComponent`, `ULBInteractorComponent` (8 cm sweep, simple collision, Interaction channel).

## 4. Verification (end-to-end)
- Automated: 78/78 including WalkPath Courtyard{Key,Door,Shortcut} and RouteBot.Monastery; `verify_props.py` all pass; material regression pixel check ≤ 2/255; lane-distance script; luma script for exposure.
- Visual: 12 clean captures reviewed by the lead against the acceptance criteria in 4.2, 5d, 5f, 5g.
- Human: owner playtest + `stat gpu` numbers on the RTX 4050.
- Git: everything on `claude/p7-courtyard-polish`; merge to `main` only after explicit owner approval.
