# P8-2 editor survey (read-only), L_Monastery

Surveyed 2026-10-25 on branch `claude/phase-08-chapel` with the editor open on `/Game/LastBell/Maps/L_Monastery` (level not dirty before or after). Only get/list/find/describe/read calls and viewport/asset captures were used. All numbers are world cm, read back from the editor, unless marked "derived" (computed from read-back values) or "estimate".

Captures (editor viewport, second of two shots): `survey_clue.png` (8750, 300, 170 facing +Y), `survey_dais.png` (8300, 420, 180 looking at 8800, 0, 100), `survey_mech_silhouette.png` (8500, 0, 330 facing +X; shows the mechanism and the silhouette in the east window).

## Corrections and cautions up front

1. **Left/right is inverted in the task note.** Facing +Y (from the nave towards the clue), UE's right vector is **-X**, so "left" is **+X**. The capture confirms it: the viewport gizmo shows +X pointing left, and left-to-right the saints read green, red, amber, blue (Saint1..Saint4).
2. **`read_graph_dsl` dirties Blueprints in memory.** After the reads, `is_dirty` is True for `BP_StainedGlassClue`, `BP_PuzzleCandle`, `BP_RitualMechanism` and `BP_WardenSilhouette` (it was False before for the first two; I did not check the other two). Nothing was saved or compiled. Their EventGraph node lists show no obvious new orphan `_Event_N` nodes, but this is not proven. **Do not save these four packages** (or reload them) before the [EDITOR] phase, and tell whoever runs the next editor task.
3. **`CaptureViewport` needs `annotations` filled in** (gridSpacing 0, gridExtent 0, gridHeight 0, maxLabelDistance 0, classFilter `/Script/Engine.Actor`, maxLabels 0), and resets the connection often; a fresh MCP session per attempt works.

---

## (a) `BP_StainedGlassClue_C_1`

Actor label `Clue_StainedGlass`, class `/Game/LastBell/Blueprints/Puzzles/BP_StainedGlassClue.BP_StainedGlassClue_C`, no actor tags, location (8750, 747, 300), rotation yaw **-90**, scale 1. Variables: `Order`, `Palette`. Construction script calls `ApplyOrder`; EventGraph has only the default unused events.

Orientation: rotation yaw -90 maps local +X to world **-Y** (towards the nave), local +Y to world **+X**, local +Z up. So the BP's "front" faces -Y (the nave) and local Y+ is world +X.

`get_actor_bounds` returns X 8622..8878, Y 619..875, Z 172..544, which is inflated by the billboard sprite (+-128 around the origin). The real geometry is the Frame and the saints (below).

### Components (all children of `DefaultSceneRoot` unless noted)

| Component | Class | Mesh | Relative loc | Relative scale | Size (cm) | World bounds (min .. max) | Material | Collision |
|---|---|---|---|---|---|---|---|---|
| DefaultSceneRoot | SceneComponent | - | (8750, 747, 300) yaw -90 | 1 | - | - | - | - |
| BillboardComponent_1 | BillboardComponent | - | 0 | 0.5 | editor sprite | - | - | NoCollision |
| **Frame** | StaticMeshComponent | `/Engine/BasicShapes/Cube` | (0, 0, 122) | (0.06, 1.24, 2.44) | 6 x 124 x 244 | X 8688..8812, Y 744..750, Z 300..544 | `MI_LB_DarkWood` | **BlockAllDynamic, QueryAndPhysics** |
| **Glass** | StaticMeshComponent | `/Engine/BasicShapes/Cube` | (3.5, 0, 122) | (0.02, 1.12, 2.32) | 2 x 112 x 232 | X 8694..8806, Y 742.5..744.5, Z 306..538 | `MI_LB_StainedGlass` | NoCollision |
| Saint1Body | StaticMeshComponent | `/Engine/BasicShapes/Cone` | (5.5, 42, 96) | (0.05, 0.2, 0.6) | 5 x 20 x 60 | X 8782..8802, Y 739..744, Z 366..426 | MID of `MI_LB_StainedGlass` | NoCollision |
| Saint1Head | StaticMeshComponent | `/Engine/BasicShapes/Sphere` | (5.5, 42, 140) | (0.05, 0.16, 0.16) | 5 x 16 x 16 | X 8784..8800, Y 739..744, Z 432..448 | MID of `MI_LB_StainedGlass` | NoCollision |
| Saint1Flame | StaticMeshComponent | `/Engine/BasicShapes/Cone` | (5.5, 42, 172) | (0.05, 0.09, 0.18) | 5 x 9 x 18 | X 8787.5..8796.5, Y 739..744, Z 463..481 | `MI_LB_CandleFlame` | NoCollision |
| Saint2Body / Head / Flame | as Saint1 | | rel Y **14**, same X/Z | same | same | X 8754..8774 (body), 8756..8772 (head), 8759.5..8768.5 (flame); Y 739..744; Z as Saint1 | MID / MID / `MI_LB_CandleFlame` | NoCollision |
| Saint3Body / Head / Flame | as Saint1 | | rel Y **-14** | same | same | X 8726..8746 (body), 8728..8744, 8731.5..8740.5; Y 739..744 | MID / MID / `MI_LB_CandleFlame` | NoCollision |
| Saint4Body / Head / Flame | as Saint1 | | rel Y **-42** | same | same | X 8698..8718 (body), 8700..8716, 8703.5..8712.5; Y 739..744 | MID / MID / `MI_LB_CandleFlame` | NoCollision |

All meshes have a single default slot (`WorldGridMaterial` / `DefaultMaterial`); every one is overridden as listed. Castshadow true on all static meshes except the billboard.

Layout from the nave (Y < 747), by depth: saints at Y 739..744 (nearest the player), glass Y 742.5..744.5, frame Y 744..750 (flush with the nave face of the greybox wall at Y 750). The clue is a **free-standing plaque in front of the wall face**, not an object inside a window opening.

### Materials and parent materials
- `MI_LB_DarkWood`: MaterialInstanceConstant, parent `/Engine/BasicShapes/BasicShapeMaterial`; Color (0.10, 0.065, 0.04), Roughness 0.9.
- `MI_LB_StainedGlass` (Glass): MaterialInstanceConstant, parent **`/Engine/EngineMaterials/EmissiveMeshMaterial`**; Color (0.35, 0.40, 0.60, 1). Effective: Additive, Unlit, two-sided. See (f).
- `MI_LB_CandleFlame` (Saint flames): parent `/Engine/EngineMaterials/EmissiveMeshMaterial`; Color (12, 5, 0.8, 1) (HDR emissive amber), same for all four saints. The flames are not coloured per saint.
- Saint Body and Head: `MaterialInstanceDynamic` named `…Saint{n}{Body|Head}.MID_MI_LB_StainedGlass_0`, parent `MI_LB_StainedGlass` (so Additive Unlit EmissiveMeshMaterial); only `Color` is overridden:

| Saint | Palette index | Colour name | Color (linear RGB) |
|---|---|---|---|
| Saint1 | 2 | green | (0.07, 0.65, 0.12) |
| Saint2 | 0 | red | (0.90, 0.05, 0.04) |
| Saint3 | 3 | amber | (0.95, 0.62, 0.05) |
| Saint4 | 1 | blue | (0.06, 0.18, 0.95) |

### Order and how it is encoded
- Left to right as seen from inside the nave (looking +Y; left = +X): **Saint1 green (X centre 8792), Saint2 red (8764), Saint3 amber (8736), Saint4 blue (8708)**. Confirmed in `survey_clue.png`.
- Encoding: instance variable `Order` (int array) = **[2, 0, 3, 1]** (the BP default is [0, 1, 2, 3]); `Palette` (LinearColor array) = [0] red (0.90, 0.05, 0.04), [1] blue (0.06, 0.18, 0.95), [2] green (0.07, 0.65, 0.12), [3] amber (0.95, 0.62, 0.05). `ApplyOrder` (run from the construction script) sets `Saint{k}Body` and `Saint{k}Head` `Color` = `Palette[Order[k-1]]`.
- Matching puzzle (see (b)): the sequence is candle tags 3, 1, 4, 2 = `Order[k] + 1`, which is the colours green, red, amber, blue, i.e. the same left-to-right order as the clue. The shape (cone body, sphere head, cone flame) is identical for all four; only the colour and the position encode the order.

### Template read test (no write)
`get_properties` on `/Game/LastBell/Blueprints/Puzzles/BP_StainedGlassClue.BP_StainedGlassClue_C:Glass_GEN_VARIABLE` **works**: it returned `staticMesh` = `/Engine/BasicShapes/Cube.Cube`, `relativeLocation` (3.5, 0, 122), `relativeScale3D` (0.02, 1.12, 2.32), `overrideMaterials[0]` = `MI_LB_StainedGlass`. The instance values equal the template values.

---

## (b) `BP_PuzzleCandle_C_0..3`

Class `/Game/LastBell/Blueprints/Puzzles/BP_PuzzleCandle.BP_PuzzleCandle_C`. No actor tags. Variables: `LitTag`, `BandColor`. All four have identical component layout; the actor origin is on the dais top (Z 30).

| Actor | Label | Location | `BandRing` colour (linear) | `LitTag` / tag granted and consumed |
|---|---|---|---|---|
| BP_PuzzleCandle_C_0 | Candle_P1 | (8800, -200, 30) | red (0.90, 0.05, 0.04) | `State.Chapel.Candle.1` |
| BP_PuzzleCandle_C_1 | Candle_P2 | (8820, -67, 30) | blue (0.06, 0.18, 0.95) | `State.Chapel.Candle.2` |
| BP_PuzzleCandle_C_2 | Candle_P3 | (8820, 67, 30) | green (0.07, 0.65, 0.12) | `State.Chapel.Candle.3` |
| BP_PuzzleCandle_C_3 | Candle_P4 | (8800, 200, 30) | amber (0.95, 0.62, 0.05) | `State.Chapel.Candle.4` |

Each `BandRing` is a MID of `MI_LB_StainedGlass` (Additive Unlit); `BandColor` equals the values above.

### Components (offsets from the actor origin; Z values are world, with origin Z 30)
| Component | Mesh | Relative loc | Relative scale | Size (cm) | World Z | Material | Collision |
|---|---|---|---|---|---|---|---|
| Stand | `/Engine/BasicShapes/Cylinder` | (0, 0, 15) | (0.1, 0.1, 0.3) | 10 dia x 30 | 30..60 | `MI_LB_DarkWood` | BlockAllDynamic |
| BandRing | Cylinder | (0, 0, 22) | (0.13, 0.13, 0.04) | 13 dia x 4 | 50..54 | MID of `MI_LB_StainedGlass` | BlockAllDynamic |
| Wax | Cylinder | (0, 0, 39) | (0.04, 0.04, 0.18) | 4 dia x 18 | 60..78 | `MI_LB_CandleWax` | BlockAllDynamic |
| Flame | `/Engine/BasicShapes/Sphere` | (0, 0, 50.5) | (0.04, 0.04, 0.065) | 4 x 4 x 6.5 | 77.2..83.8 | `MI_LB_CandleFlame` | NoCollision |
| FlameLight | PointLightComponent | (0, 0, 55) | - | - | at Z 85 | - | - |
| InteractComp | `LBInteractableComponent` (ActorComponent, no transform) | - | - | - | - | - | - |

- `MI_LB_CandleWax`: parent `BasicShapeMaterial`, Color (0.75, 0.68, 0.52), Roughness 0.7.
- `MI_LB_CandleFlame`: parent `EmissiveMeshMaterial`, Color (12, 5, 0.8).
- Footprint of the whole candle: 13 cm diameter (the band); height from the dais top to the flame tip 53.8 cm.

### `FlameLight` (identical on all four)
Intensity **8**, units **Candelas**, attenuation radius **300**, light colour (1.0, 0.60, 0.302) linear (about #FF994D), casts shadows **false**, inverse-squared falloff true, source radius 0, mobility Movable, no light function, volumetric scatter 1, temperature unused.

### Interaction and tags
`InteractComp`: promptText "Light candle", single use, `noiseLoudness` 0.1, `grantedStateTags` = `consumedStateTag` = the candle's `LitTag` (table above), no required tags.

### Sequence (`BP_SequencePuzzle_C_0`, label `Puzzle_Candles`, at (8650, 0, 30))
Component `SeqComp` (`LBSequencePuzzleComponent`). **Steps, in order**: `State.Chapel.Candle.3`, `State.Chapel.Candle.1`, `State.Chapel.Candle.4`, `State.Chapel.Candle.2` = candles P3 (green), P1 (red), P4 (amber), P2 (blue). `solvedTags` = `State.Chapel.CandlesSolved`.

### Lit and unlit visuals (from the BP graph)
- `RefreshLit(bLit)` calls `SetVisibility(bLit)` on **both `Flame` (the mesh) and `FlameLight`**. It is a visibility toggle, not a material swap. Wax, Stand and BandRing are never changed.
- It runs on `BeginPlay` with `WorldState.HasState(LitTag)`, and on `OnWorldStateChanged` when the changed tag equals `LitTag` (with `bAdded`). `EndPlay` unbinds.
- Both are visible in the editor (`bVisible` true), so in game the candles start unlit (no flame, no light) and a lit candle shows the 4 x 4 x 6.5 cm emissive sphere plus the 8 cd light. Any replacement mesh must leave `Flame` and `FlameLight` in place, or the BP needs new components.

---

## (c) `BP_RitualMechanism_C_1`

Label `Altar_Ritual1`, class `/Game/LastBell/Blueprints/Interactables/BP_RitualMechanism.BP_RitualMechanism_C`, no actor tags, location (8900, 0, 80), rotation 0, scale 1. Actor bounds (read back): **X 8850..8950, Y -50..50, Z 30..195**.

| Component | Class / mesh | Relative | World bounds | Material | Collision |
|---|---|---|---|---|---|
| Pedestal (root) | StaticMeshComponent, `/Engine/BasicShapes/Cube`, scale 1 | (8900, 0, 80) | X 8850..8950, Y -50..50, Z 30..130 (100 cm cube) | none (cube default `WorldGridMaterial`) | BlockAllDynamic |
| Core | StaticMeshComponent, `/Engine/BasicShapes/Cylinder`, scale (0.8, 0.8, 0.5), child of Pedestal | (0, 0, 75) | X 8860..8940, Y -40..40, Z 130..180 (80 dia x 50) | none (default material) | BlockAllDynamic |
| CoreMarker | StaticMeshComponent, Cube, scale (0.188, 0.188, 0.3), child of Core | (0, 37.5, 65) in Core space | X 8892.5..8907.5, Y 22.5..37.5, Z 180..195 (about 15 cm cube) | none (WorldGridMaterial) | BlockAllDynamic |
| InteractComp | `LBInteractableComponent` (ActorComponent, **no location or extent**) | - | - | - | - |

- Looks like: a 1 m grey/brown checker (WorldGridMaterial) cube with a smaller cylinder on top and a tiny cube at its edge (see `survey_mech_silhouette.png` and `survey_dais.png`). It stands on the dais (top Z 30), so its top is 165 cm above the dais.
- **How interaction is detected**: there is no trigger shape. `LBInteractorComponent` does `SweepSingleByChannel` from the camera, `LB_TRACE_INTERACTION` (GameTraceChannel2, default response Block), sphere radius **8 cm**, reach **200 cm**, ignoring only the player; the hit actor's `LBInteractableComponent` is used. So any component of the mechanism that blocks the Interaction channel counts (all three do), and **any other blocking geometry between the eye and the mechanism steals the hit** (an altar model around it must be NoCollision, or must not sit in the line of sight).
- Properties: promptText "Activate", deniedPromptText "Something is missing", `requiredStateTags` = `State.Chapel.CandlesSolved`, `grantedStateTags` = `State.Warden.Stage.2` + `State.Ritual.1`, `consumedStateTag` = `State.Ritual.1`, single use, `noiseLoudness` 1.0. Variables: `RitualTag` `State.Ritual.1`, `ExtraGrantedTags` `State.Warden.Stage.2`, `TurnYaw` 90, `TurnDuration` 1.5.
- Behaviour: on `State.Ritual.1` the `Core` relative yaw eases to 90 over 1.5 s and `InteractComp` is disabled.

---

## (d) `BP_WardenSilhouette_C_2`

Label `Silh_ChapelWindow`, class `/Game/LastBell/Blueprints/Interactables/BP_WardenSilhouette.BP_WardenSilhouette_C`, no actor tags, location (9150, 0, 300), rotation 0, scale 1. It stands outside the east wall, on `Window_Ledge` (top Z 300), 130 cm east of the east wall's outer face (X 9020).

| Component | Mesh | Relative | Size | World bounds | Material | Collision |
|---|---|---|---|---|---|---|
| Body | Cylinder, scale (0.6, 0.6, 2.6) | (0, 0, 130) | 60 dia x 260 | X 9120..9180, Y -30..30, Z 300..560 | `MI_LB_WardenSilhouette` | NoCollision |
| Head | Sphere, scale 0.4 | (0, 0, 270) | 40 dia | X 9130..9170, Y -20..20, Z 550..590 | `MI_LB_WardenSilhouette` | NoCollision |

- `MI_LB_WardenSilhouette` has no overrides; parent `/Game/LastBell/Materials/Master/M_LB_Silhouette`: Surface, **Opaque, Unlit**, one vector parameter `Color`, default (0.005, 0.005, 0.006), i.e. near-black.
- Whole actor bounds Z 300..590 (the stored `bHidden` is false).
- **Hidden in game by default: yes.** `EventBeginPlay` stores `StartLoc` and calls `SetActorHiddenInGame(true)`. `HandleStateChanged` shows it (`SetActorHiddenInGame(false)`, resets `Elapsed`, enables tick) when `TriggerTag` = **`State.Ritual.1`** is added to world state; Tick moves it by `MoveOffset` (currently (0, 0, 0), so it does not move) and hides it again after `VisibleSeconds` = **3 s**.
- **How to show it for a capture without saving**:
  1. In the editor viewport it is already visible (the actor is not hidden in the editor); `survey_mech_silhouette.png` shows it as a black capsule in the east window. No change needed.
  2. In PIE, it appears for 3 s when `State.Ritual.1` is added to the world state (for example, by using the ritual mechanism). It cannot be kept visible in PIE without changing the actor or the BP.
  3. Setting `VisibleSeconds` or `MoveOffset` on the placed instance would be a write; not done.

---

## (e) Actors

| Actor | Label | Class | Mesh | Material(s) | Location / scale | Collision |
|---|---|---|---|---|---|---|
| StaticMeshActor_105 | `Window_Ledge` | StaticMeshActor | `/Engine/BasicShapes/Cube` | `/Engine/BasicShapes/BasicShapeMaterial` | (9150, 0, 150), scale (3, 6, 3) -> bounds X 9000..9300, Y -300..300, Z 0..300 | BlockAll |
| StaticMeshActor_812 | **`KC_DoorTympanum`** | StaticMeshActor | `/Engine/BasicShapes/Cube` | `/Game/LastBell/ArtTest/Materials/Weathered_Planks/MI_Weathered_Planks_WA` | (6040, 0, 290), scale (0.12, 1.2, 1) -> bounds X 6034..6046, Y -60..60, Z 240..340 | BlockAll |

`StaticMeshActor_812` is the "small item above the main door": a 12 x 120 x 100 cm weathered-plank panel.

Kit west front `StaticMeshActor_654…681` (all class StaticMeshActor, collision BlockAll, no override materials, rotation yaw 90 or -90, scale 1; the materials are the mesh's slot materials `MI_Kit_Masonry`, `MI_Kit_Trim`, `MI_Kit_Rubble` in `/Game/LastBell/Environments/Kit/Materials/`):

| Actor | Label | Location | Mesh (`SM_LB_Kit_…` in `/Game/LastBell/Environments/Kit/`) | Slots |
|---|---|---|---|---|
| 654 | KC_LowS_00 | (6060, -800, 0) | Wall_400x60x800_A | Masonry, Trim, Rubble |
| 655 | KC_LowS_01 | (6000, -300, 0) | Wall_100x60x800 | Masonry, Trim |
| 656 | KC_LowS_02 | (6060, -300, 0) | Wall_100x60x800 | Masonry, Trim |
| 657 | KC_MainDoorway | (6000, 200, 0) | Doorway_Pointed_400x60x400 | Masonry, Trim, Rubble |
| 658 | KC_MainDoorUpper | (6000, 200, 400) | Wall_400x60x800_A | Masonry, Trim, Rubble |
| 659 | KC_LowN_00 | (6060, 200, 0) | Wall_100x60x800 | Masonry, Trim |
| 660 | KC_LowN_01 | (6060, 300, 0) | Wall_100x60x800 | Masonry, Trim |
| 661 | KC_LowN_02 | (6060, 400, 0) | Wall_400x60x800_B | Masonry, Trim, Rubble |
| 662 | KC_PlS_00 | (6070, -800, 0) | Trim_Plinth_400x80x60 | Trim, Rubble |
| 663 | KC_PlS_01 | (6070, -400, 0) | Trim_Plinth_100x80x60 | Trim |
| 664 | KC_PlS_02 | (6070, -300, 0) | Trim_Plinth_100x80x60 | Trim |
| 665 | KC_PlN_00 | (6070, 200, 0) | Trim_Plinth_400x80x60 | Trim, Rubble |
| 666 | KC_PlN_01 | (6070, 600, 0) | Trim_Plinth_100x80x60 | Trim |
| 667 | KC_PlN_02 | (6070, 700, 0) | Trim_Plinth_100x80x60 | Trim |
| 668 | KC_PlDoor_-200 | (6070, -200, 0) | Trim_Plinth_100x80x60 | Trim |
| 669 | KC_PlDoor_100 | (6070, 100, 0) | Trim_Plinth_100x80x60 | Trim |
| 670 | KC_LanS0 | (6000, -600, 800) | Window_Lancet_200x60x400_Blind | Masonry, Trim, Rubble |
| 671 | KC_UpS0 | (6000, -500, 800) | Wall_100x60x400 | Masonry, Trim |
| 672 | KC_LanS1 | (6000, -300, 800) | Window_Lancet_200x60x400_Blind | Masonry, Trim, Rubble |
| 673 | KC_UpS1 | (6000, -200, 800) | Wall_100x60x400 | Masonry, Trim |
| 674 | KC_UpN0 | (6000, 300, 800) | Wall_100x60x400 | Masonry, Trim |
| 675 | KC_LanN0 | (6000, 500, 800) | Window_Lancet_200x60x400_Blind | Masonry, Trim, Rubble |
| 676 | KC_UpN1 | (6000, 600, 800) | Wall_100x60x400 | Masonry, Trim |
| 677 | KC_LanN1 | (6000, 800, 800) | Window_Lancet_200x60x400_Blind | Masonry, Trim, Rubble |
| 678 | KC_Butt_S_door | (6000, -300, 0) | Buttress_100x150x800 | Masonry, Trim, Rubble |
| 679 | KC_Butt_N_door | (6000, 200, 0) | Buttress_100x150x800 | Masonry, Trim, Rubble |
| 680 | KC_Butt_S_corner | (6000, -800, 0) | Buttress_100x150x800 | Masonry, Trim, Rubble |
| 681 | KC_Butt_N_corner | (6000, 700, 0) | Buttress_100x150x800 | Masonry, Trim, Rubble |

Labels are readable: `ActorTools.get_label` returns them, and `SceneTools.find_actors` also takes a label substring.

---

## (f) `/Game/LastBell/Materials/Instances/MI_LB_StainedGlass`

MaterialInstanceConstant. Parent: **`/Engine/EngineMaterials/EmissiveMeshMaterial`**. `list_parameters`: `Color` (Vector) and `LinearColor` (Texture; inherited from the engine material, not overridden). Overrides: `vectorParameterValues` = [`Color` = (0.35, 0.40, 0.60, 1.0)]; no scalar or texture overrides. Effective base properties read back: BLEND_Additive, MSM_Unlit, twoSided true. Used by `Glass`, and as the parent of the runtime MIDs on the saints and on the candle `BandRing`.

## (g) `/Game/LastBell/Materials/Master/M_LB_Decal`

- Domain **MD_DeferredDecal**, blend mode **BLEND_Translucent**, shading model MSM_DefaultLit, decal response **MDR_ColorNormalRoughness**, not two-sided.
- Parameters and defaults:
  - group Decal: `BaseColorTex` (default `/Engine/EngineResources/WhiteSquareTexture`), `OpacityTex` and `RoughnessTex` (default `T_LB_White_Gray`), `NormalTex` (default `T_LB_FlatNormal`), `BaseColorTint` (1, 1, 1, 1), `OpacityStrength` 1, `RoughnessScale` 1, `NormalStrength` 1.
  - group Decal Shaping: `OpacityContrast` 1.5, `EdgeFadeU` 0.12, `EdgeFadeV` 0.06, `DepthFade` 0.30, `DarkenStrength` 0.35, `DecalHalfDepthCm` 128.
- 49 expressions in the graph.

---

## (h) Player character

`GlobalDefaultGameMode` (DefaultEngine.ini) is `BP_LBGameMode`; both `BP_LBGameMode` and `BP_LBGameMode_Main` use default pawn **`/Game/LastBell/Blueprints/BP_LBCharacter`** (parent `/Script/LastBell.LBCharacter`). From the class default object:

- `CharacterMovement` (component `CharMoveComp`): **MaxStepHeight 45**, **WalkableFloorAngle 44.765 deg** (WalkableFloorZ 0.71), MaxWalkSpeed 300 (crouched 300), JumpZVelocity 420, PerchRadiusThreshold 0, PerchAdditionalHeight 40, bCanWalkOffLedges true.
- Capsule (`CollisionCylinder`): **radius 34, half-height 88** (height 176).
- `FirstPersonCamera`: relative (0, 0, 64) from the capsule centre, FOV 90 (eye about 152 cm above the floor).
- `LBInteractorComponent`: trace distance 200, radius 8 (from C++ defaults).

---

## (i) Gameplay and other actors in X 6000..9020, Y -1560..810, Z -50..1300

`find_actors` with this box returns 122 actors (anything whose bounds intersect it). Gameplay-relevant ones (all have **no actor tags** unless stated):

| Actor name | Class | Label | Location | Notes |
|---|---|---|---|---|
| BP_Door_Base_C_3 | BP_Door_Base_C | Door_ChapelMain | (6020, -59, 0) | scale (1, 1.18, 1.08), bounds X 5892..6148, Y -187..69, Z -128..238 |
| BP_Door_Base_C_4 | BP_Door_Base_C | Door_Sacristy | (8020, -1150, 0) | bounds X 7892..8148, Y -1278..-1022, Z -128..220 |
| BP_Inspectable_Note_C_6 | BP_Inspectable_Note_C | Note_Nave | (7100, 238, 90.3) | yaw -12; **sits on the top of `Pew_N1` (Z 90)** |
| BP_Inspectable_Note_C_7 | BP_Inspectable_Note_C | Note_Sacristy | (8300, -1450, 90.3) | yaw 8; **sits on the top of `Sac_Table` (Z 90)** |
| BP_PuzzleCandle_C_0..3 | BP_PuzzleCandle_C | Candle_P1..P4 | see (b) | |
| BP_RitualMechanism_C_1 | BP_RitualMechanism_C | Altar_Ritual1 | (8900, 0, 80) | see (c) |
| BP_SequencePuzzle_C_0 | BP_SequencePuzzle_C | Puzzle_Candles | (8650, 0, 30) | see (b) |
| BP_StainedGlassClue_C_1 | BP_StainedGlassClue_C | Clue_StainedGlass | (8750, 747, 300) | see (a) |
| BP_TagVisibility_C_0 | BP_TagVisibility_C | Rubble_StairsBack | (7050, -1100, -320) | scale (1, 4, 5.6), bounds X 7000..7100, Y -1300..-900, Z -600..-40 |
| LBCheckpoint_6 | LBCheckpoint | CP_Chapel | (6300, 0, 92) | volume X 6250..6540, Y -300..300, Z -8..192 |
| LBCheckpoint_7 | LBCheckpoint | CP_Chapel_After | (8500, -1100, 92) | volume X 8350..8740, Y -1250..-950, Z -8..192 |
| TargetPoint_98 | TargetPoint | WP_SacristyToCrypt_00 | (8500, -1100, 0) | tags `WalkPath.SacristyToCrypt.00`, `Requires.State.Ritual.1` |
| TargetPoint_99 | TargetPoint | WP_SacristyToCrypt_01 | (8200, -1100, 0) | tag `WalkPath.SacristyToCrypt.01` |
| TargetPoint_100 | TargetPoint | WP_SacristyToCrypt_02 | (7955, -1100, -15) | tag `WalkPath.SacristyToCrypt.02` |
| TriggerVolume_19 | TriggerVolume | PCGX_DoorRecess_Chapel | (5925, 0, 100) | tag `LB_PCG_Exclude`; bounds X 5850..6000, Y -200..200, Z -50..250 |
| PointLight_2 | PointLight | Light_ChapelDoor_Warm | (5925, -140, 75) | 1000 lm, radius 420, colour (1, 0.549, 0.2196), light function `MI_LF_Lantern`, volumetric scatter 1.5 (not part of the removal list) |
| PointLight_23..28 | PointLight | Light_Chapel_0..5 | see (n) | |
| DecalActor_6 | DecalActor | Decal_Leak_E0 | (6000, -1600, 570) | bounds X 5872..6240, Y -1728..-1472, Z 442..698 (partly in the box) |
| NavMeshBoundsVolume_0 | NavMeshBoundsVolume | NavBounds_Monastery | (5000, 0, 1300) | RecastNavMesh-Warden also present |
| PCGV_Wall_ChapelFront / _Wall_EN / _Wall_ES / _OpenCobbles | PCGVolume | same | (5930, 0, 10), (5930, 1650, 10), (5930, -1650, 10), (3150, 0, 10) | bounds overlap the box edge |
| PostProcessVolume_1 | PostProcessVolume | PP_Outdoor_Night | (1350, 0, 1900) | unbound, overlaps |

Not present in the box: BP_TagInteractable, BP_TagTrigger, BP_KillVolume, BP_WardenPlaceholderKill, Warden actors.

Static meshes in the box (not gameplay): the greybox chapel `StaticMeshActor_97…121` (see (j)), the kit west front 654…681 and 812, `Stair_SacristyDown_36..39` (7895..7985, -1100, Z -322..-300), `Rail_Sac_S/N/W` (485..487 at Z 50), `KW_*` kit pieces at X 6000/6070 (623..637), `Ground_0/1/5/6`, `Rock_*`, `Ivy_*` (1142, 1144, 1145), `KE_Floor_5_*` (745..747), `SkySphere`.

---

## (j) Greybox chapel actors (labels readable)

All class StaticMeshActor, mesh `/Engine/BasicShapes/Cube`, collision BlockAll, material `BasicShapeMaterial` unless stated.

| Actor | Label | Location | Scale | World bounds |
|---|---|---|---|---|
| 97 | Chapel_N | (7520, 770, 600) | (29.6, 0.4, 12) | X 6040..9000, Y 750..790, Z 0..1200 |
| 98 | Chapel_S1 | (7170, -770, 600) | (22.6, 0.4, 12) | X 6040..8300, Y -790..-750, Z 0..1200 |
| 99 | Chapel_S2 | (8850, -770, 600) | (3, 0.4, 12) | X 8700..9000, Y -790..-750 |
| 100 | Chapel_S_Lintel | (8500, -770, 750) | (4, 0.4, 9) | X 8300..8700, Y -790..-750, Z 300..1200 |
| 101 | Chapel_E_S | (8980, -450, 600) | (0.4, 6, 12) | X 8960..9000, Y -750..-150, Z 0..1200 |
| 102 | Chapel_E_N | (8980, 450, 600) | (0.4, 6, 12) | X 8960..9000, Y 150..750 |
| 103 | Chapel_E_Sill | (8980, 0, 125) | (0.4, 3, 2.5) | X 8960..9000, Y -150..150, Z 0..250 |
| 104 | Chapel_E_Top | (8980, 0, 950) | (0.4, 3, 5) | X 8960..9000, Y -150..150, Z 700..1200 |
| 105 | Window_Ledge | (9150, 0, 150) | (3, 6, 3) | X 9000..9300, Y -300..300, Z 0..300 |
| 106 | Dais | (8730, 0, 15) | (4.6, 10, 0.3) | X 8500..8960, Y -500..500, Z 0..30 |
| 107 | Sac_W_S | (8020, -1346, 200) | (0.4, 3.88, 4) | X 8000..8040, Y -1540..-1152, Z 0..400 |
| 108 | Sac_W_N | (8020, -919, 200) | (0.4, 2.58, 4) | X 8000..8040, Y -1048..-790 |
| 109 | Sac_W_Lintel | (8020, -1100, 312) | (0.4, 1.04, 1.76) | X 8000..8040, Y -1152..-1048, Z 224..400 |
| 110 | Sac_S | (8500, -1520, 200) | (10, 0.4, 4) | X 8000..9000, Y -1540..-1500, Z 0..400 |
| 111 | Sac_E | (8980, -1165, 200) | (0.4, 7.5, 4) | X 8960..9000, Y -1540..-790 |
| 112 | Sac_Table | (8300, -1450, 45) | (3, 0.6, 0.9) | X 8150..8450, Y -1480..-1420, Z 0..90; `MI_LB_DarkWood` |
| 113 | Altar_Rail | (8470, 0, 70) | (0.4, 6, 0.8) | X 8450..8490, Y -300..300, Z 30..110 |
| 114 | Pew_N0 | (6700, 325, 45) | (1.5, 2.5, 0.9) | X 6625..6775, Y 200..450, Z 0..90 |
| 115 | Pew_S0 | (6700, -325, 45) | same | X 6625..6775, Y -450..-200 |
| 116 | Pew_N1 | (7100, 325, 45) | same | X 7025..7175, Y 200..450; `MI_LB_DarkWood` |
| 117 | Pew_S1 | (7100, -325, 45) | same | X 7025..7175, Y -450..-200 |
| 118 | Pew_N2 | (7500, 325, 45) | same | X 7425..7575, Y 200..450 |
| 119 | Pew_S2 | (7500, -325, 45) | same | X 7425..7575, Y -450..-200 |
| 120 | Pew_N3 | (7900, 325, 45) | same | X 7825..7975, Y 200..450 |
| 121 | Pew_S3 | (7900, -325, 45) | same | X 7825..7975, Y -450..-200 |

Neighbours seen while scanning: `StaticMeshActor_96` = `KZ_Pillar_Fallen` (outside the box), `_122` does not exist, `_123/_124` are Kit cliff slabs.

---

## (k) Owner-migrated flames `/Game/Dungeon/Candles/Blueprints/BP_Flame_00` and `_01`

- Parent class `/Script/Engine.Actor`. No variables. Graphs: `UserConstructionScript`, `EventGraph` (not read, to avoid dirtying the owner's assets).
- Components (template, identical in both except the particle system):
  - `SharedRoot` (SceneComponent, at the origin, scale 1, no auto-activate);
  - `SpringArm` (SpringArmComponent, relative (0.71, 0.08, 6.80), scale (0.669, 1, 1), TargetArmLength 0, collision test on);
  - `PS_Fire` (**ParticleSystemComponent**, relative (0, 0, -1.87), **scale 0.25**, auto-activate, no cast shadow). Template: `BP_Flame_00` -> `/Game/Dungeon/Fire/Particle_Systems/PS_Fire_00`; `BP_Flame_01` -> `PS_Fire_01`.
- **Light: none.** There is no PointLight, SpotLight or other light component in either BP. The flame is a particle effect only, so a light must be added separately.
- **Cascade, not Niagara**: `ParticleSystemComponent` with a `ParticleSystem` asset. Both systems depend on `/Game/Dungeon/Fire/Materials/M_Fire` (Additive, DefaultLit, used with particle sprites), `M_Fire_Details` (Translucent) and `M_Smoke` (Translucent): flame, detail layer and smoke.
- **Size of the flame: not measurable read-only.** The `ParticleSystem` has no fixed bounds (`bUseFixedRelativeBoundingBox` false, default box +-1), the emitter array is not exposed by `get_properties`, `get_actor_bounds` on the BP default object returns all zeros, and `CaptureAssetImage` does not support particle systems or Blueprints. Only the component scale (0.25, a quarter of the authored size) is known. Measure after placing one in the [EDITOR] task (bounds of the placed actor, or a PIE Simulate capture).
- No placed instance exists in the level, and nothing references the two BPs.

## (l) `/Game/LastBell/ThirdParty/Fab/HorrorProps`

### `SK_Dead_Man` (`Mesh/SK_Dead_Man`)
- Skeletal mesh, 1 LOD, 1 section, 642 vertices, 1164 triangles, **one material slot `default`** = `/Game/LastBell/ThirdParty/Fab/HorrorProps/Materials/M_Dead_man`. Skeleton `SK_Dead_Man_Skeleton`, physics asset `SK_Dead_Man_PhysicsAsset`, no sockets, no morph targets, Nanite off.
- Bones: a 6-bone chain `CATRigHub001` > `…Bone001` > … (5 levels below the hub), probably the rope and body as a pendulum chain (not verified).
- Reference-pose bounds: origin (0, -1.93, 150.21), box extent (23.88, 16.93, 116.63): **X -23.9..23.9, Y -18.9..15.0, Z 33.6..266.8**. Total height **233.2 cm**.
- **Pivot** (0, 0, 0) is at floor level under the hanging point; the mesh hangs **from Z 266.8** (top of the rope) and the body's lowest point is **33.6 cm above the pivot**.
- **Rope: yes, part of the mesh.** All three thumbnails show a thin rope going up from the knotted end of the shroud, and there is only the one `default` material slot, so the rope shares `M_Dead_man`. The rope is roughly 35..42 cm (estimate: total 233 cm minus the 191 cm length of the lying `SM_Dead_Man`; not measured). Thumbnail: a cloth-wrapped body, knotted at the top where the rope attaches, blood stain at the bottom end. In `SM_Dead_Man` the bare feet are at the opposite end from the red stain, so it appears to hang feet-up/head-down (judged from thumbnails only).
- Animations (both on `SK_Dead_Man_Skeleton`, 30 fps, no root motion, additive none):
  - `Anim_Dead_Man_Idle`: **4.000 s** (120 frames); the thumbnail pose shows a hang with the rope tilted a few degrees, so a gentle sway.
  - `Anim_Dead_Man_other`: **3.333 s** (100 frames); the thumbnail pose shows the rope leaning clearly more and the body pitched, so a bigger swing or twist (judged from the names, lengths and one thumbnail pose each; the motion itself was not played).
  - Both are flagged non-looping in the asset (`bLoop` false), so they need a looping player.

### Static versions
| Mesh | Bounds X | Y | Z | Size (cm) | Pivot |
|---|---|---|---|---|---|
| `SM_Dead_Man` | -23.9..23.9 | -87.7..103.4 | -4.6..29.2 | 47.8 x 191.1 x 33.9 | body centre in XY; Z about 5 cm below the base. Lying on its back, feet at -Y, head at +Y (red stain). 459 verts, 828 tris, Nanite on |
| `SM_Man_under_cloth` | -30.3..39.4 | -104.7..95.0 | 0..24.3 | 69.7 x 199.7 x 24.3 | bottom, XY roughly centred (cloth over a body, blood at one end). 689 verts, 1265 tris, Nanite on |

## (m) Sizes and pivots (local bounds from `StaticMeshTools.get_bounds`; all unscaled)

Pivot code: **BC** = bottom centre (min Z about 0, XY centred), **C** = centred, **T** = top, **O** = other.

### `/Game/Dungeon/Candles/Meshes/SM_Candles_Holder_00…05`
**None is floor-standing: they are all real-scale table-top candlesticks 27.4 cm tall.** There is no candelabrum taller than 27.4 cm in the Dungeon pack (`SM_Candles_Holder_01..04` all 27.3..27.4; the tallest, shown to 0.1 cm, is `_01`..`_04` at 27.4). A floor candelabrum needs a uniform scale of about 4 to 4.5 (derived: x4 gives 109.6 cm tall; x4.5 gives 123 cm).

| Mesh | Min | Max | Size (cm) | Pivot | Shape (from thumbnail) | Tris | x4 size (derived) |
|---|---|---|---|---|---|---|---|
| Holder_00 | (-8.7, -8.7, 0) | (8.7, 8.7, 1.2) | 17.5 x 17.5 x 1.2 | BC | flat round plate | 768 | 70 x 70 x 5 |
| Holder_01 | (-3.8, -3.8, 0) | (3.8, 3.8, 27.4) | 7.7 x 7.7 x 27.3 | BC | single candlestick | 8192 | 31 x 31 x 109 |
| Holder_02 | (-11.2, -3.8, 0) | (11.2, 3.8, 27.4) | 22.3 x 7.7 x 27.3 | BC | 3-arm, flat (X-wide) | 22144 | 89 x 31 x 109 |
| Holder_03 | (-11.2, -11.2, 0) | (11.2, 11.2, 27.4) | 22.3 x 22.3 x 27.3 | BC | 5-arm (thumbnail) | 36096 | 89 x 89 x 109 |
| Holder_04 | (-11.2, -11.2, 0) | (11.2, 11.2, 27.4) | 22.3 x 22.3 x 27.3 | BC | two-tier, many-arm (thumbnail) | 64000 | 89 x 89 x 109 |
| Holder_05 | (-11.2, -4.3, -0.2) | (11.0, 4.3, 27.4) | 22.1 x 8.5 x 27.6 | BC | 9-light menorah | 21464 | 88 x 34 x 110 |

Each has one material slot `MI_Candles_Holder_0n`; Nanite off. Triangle counts are LOD0 (heavy for a Nanite-off mesh at 36k..64k).

### `SM_Candle_01…10` (all pivot **BC**; Nanite off; slots `standardSurface3` unless noted)
| Mesh | Size (cm) X x Y x Z | Tris |
|---|---|---|
| 01 | 1.5 x 1.5 x 20.0 | 624 |
| 02 | 3.7 x 3.7 x 20.3 | 1184 |
| 03 | 4.0 x 4.0 x 21.3 | 992 |
| 04 | 9.0 x 9.0 x 12.8 | 992 |
| 05 | 6.5 x 6.5 x 8.0 (2 slots: `standardSurface3`, `blinn1`) | 1792 |
| 06 | 5.1 x 5.1 x 2.1 (2 slots: `standardSurface3`, `blinn2`) | 1696 |
| 07 | 7.9 x 7.9 x 11.1 | 1672 |
| 08 | 9.8 x 9.8 x 11.3 | 1576 |
| 09 | 3.2 x 3.7 x 20.3 | 1448 |
| 10 | 6.9 x 6.9 x 16.1 (slot `lambert1`) | 1256 |

(`SM_Candle_Melted_01, 02, 04, 05, 06, 08, 09, 10` also exist; not measured.)

### `/Game/Dungeon/Meshes/Skeletons`
| Mesh | Min | Max | Size (cm) | Pivot | Tris |
|---|---|---|---|---|---|
| SM_Skeleton_Pile_00 | (-56.1, -59.8, -4.9) | (43.4, 70.7, 41.2) | 99.4 x 130.5 x 46.1 | C in XY (offset about 5), base 4.9 below the pivot | 12318 |
| SM_Skeleton_Pile_01 | (-47.4, -49.9, -6.3) | (37.6, 48.3, 39.9) | 85.0 x 98.2 x 46.2 | C, base 6.3 below | 57420 |
| SM_Skeleton_Pile_02 | (-57.1, -98.1, -6.3) | (57.7, 70.8, 104.2) | 114.8 x 168.9 x 110.5 | C, base 6.3 below (tallest pile, 110 cm) | 83395 |
| SM_Skeleton_Pile_03 | (-48.5, -42.8, -6.3) | (58.1, 41.1, 33.3) | 106.6 x 84.0 x 39.7 | C, base 6.3 below | 54685 |
| SM_Skeleton_Pile_04 | (-22.8, -45.3, 0.5) | (22.7, 41.7, 28.3) | **45.5 x 86.9 x 27.9** (smallest) | C, base 0.5 above | 17700 |
| SM_Skull_02 | (-8.6, -10.6, 0.2) | (8.6, 15.4, 20.6) | 17.2 x 25.9 x 20.4 | BC (Y offset about +2.4) | 5942 |

All Nanite off; the piles have a single `MI_Skeleton_Pile_0n` slot. Pile and skull triangle counts are high (up to 83k) with Nanite off.

### `/Game/Dungeon/Meshes/Props`
| Mesh | Min | Max | Size (cm) | Pivot | Slots / Tris |
|---|---|---|---|---|---|
| SM_Scribe_Chair | (-27.3, -27.3, 0.1) | (28.2, 28.3, 126.5) | 55.5 x 55.6 x 126.4 | BC | `WorldGridMaterial` (no material set), 708 |
| SM_Dungeon_bench | (-79.7, -19.5, 0.4) | (79.7, 19.7, 51.6) | 159.4 x 39.2 x 51.2 | BC (long axis X) | `WorldGridMaterial`, 2288 |
| SM_Dungeon_chest | (-45.7, -26.7, 8.6) | (45.7, 27.2, 70.1) | 91.5 x 53.9 x 61.4 | **O: base is 8.6 cm above the pivot** (centred XY) | `WorldGridMaterial`, 736 |
| SM_Torture_Devices_Rope_00 | (-41.4, -17.7, -1.2) | (43.1, 16.5, 17.1) | 84.5 x 34.2 x 18.4 | C XY, base 1.2 below | `MI_Rope_Eight_00`, 7812 |

The Dungeon meshes with `WorldGridMaterial` need materials assigned.

### Existing Fab Dungeon meshes (`/Game/LastBell/ThirdParty/Fab/Dungeon/Meshes/Props`)
| Mesh | Min | Max | Size (cm) | Pivot | Slots / Tris |
|---|---|---|---|---|---|
| SM_Torture_Devices_Chains | (-4.6, -5.5, -117.4) | (4.6, 5.5, 0.2) | 9.3 x 11.0 x 117.6 | **T** (hangs down from the pivot) | `lambert1`, 2574, Nanite on |
| SM_Dungeon_chain_holder | (-1.0, -7.8, -8.3) | (11.9, 7.2, 6.7) | 12.9 x 15.0 x 15.0 | O: bracket, centred about (5.5, -0.3, -0.8); the attach point is at the origin | `WorldGridMaterial`, 438, Nanite on |

### Other candle-like meshes already in the project (for comparison)
- `/Game/LastBell/ArtTest/Props/Brass_Candleholders/SM_Brass_Candleholders`: X -44.9..60.4, Y -18.2..18.2, Z 0..83.5 (105 x 36 x 83.5, pivot at the bottom, off-centre in X), 5 slots.
- `/Game/LastBell/Environments/Props/CC0/WoodenCandlestick/SM_LB_CC0_WoodenCandlestick`: 9.8 x 9.8 x 22.0, BC.
- `/Game/LastBell/ThirdParty/Fab/Dungeon/Meshes/Props/SM_Torch`: X -7.5..7.9, Y 0..34.5, Z -40.6..29.7 (wall torch, pivot mid-handle).

## (n) Chapel greybox lights `PointLight_23…28` (and `PointLight_2` for the record)

All: PointLightComponent `LightComponent0`, **3000 lumens, attenuation radius 1400**, colour white (1, 1, 1), no shadows, Movable, inverse-squared falloff, no light function, source radius 0, volumetric scatter 0, indirect intensity 1.

| Actor | Label | Location |
|---|---|---|
| PointLight_23 | Light_Chapel_0 | (6700, 0, 700) |
| PointLight_24 | Light_Chapel_1 | (7600, 0, 700) |
| PointLight_25 | Light_Chapel_2 | (8300, 0, 700) |
| PointLight_26 | Light_Chapel_3 | (8800, 300, 500) |
| PointLight_27 | Light_Chapel_4 | (7000, 600, 300) |
| PointLight_28 | Light_Chapel_5 | (8500, -1150, 300) |
| PointLight_2 (keep) | Light_ChapelDoor_Warm | (5925, -140, 75): 1000 lm, radius 420, colour (1, 0.549, 0.2196), light function `MI_LF_Lantern`, volumetric scatter 1.5 |

---

## (o) Findings that can affect the plan

1. **Clue window size and position.** The clue is not in a hole; it is a plaque at the nave face. The Glass is only **112 x 232 cm** (Z 306..538, X 8694..8806) and the Frame **124 x 244** (Z 300..544, X 8688..8812), centred at X 8750. The default opening "clear 260 x 400, sill Z 160" is about 2.1x too wide and 1.6x too tall, and its sill is 140 cm below the Frame's bottom edge. Either size the opening from the Glass bounds (about 132 x 252 with 10 cm margin, sill about Z 296) or accept that the clue must be moved or rescaled, which the plan forbids for gameplay actors. The Frame (Y 744..750) sits against the nave face of a wall whose face is at Y 750, so the new 60 cm wall (face unchanged at Y 750) leaves it flush; saints and glass are on the nave side (Y 739..744.5), i.e. in front of the opening, not in it.
2. **Frame blocks.** `Frame` is `BlockAllDynamic` (QueryAndPhysics), so it blocks the player and the interaction sweep; Glass and the saints are NoCollision.
3. **Left-right inversion** in the task note (see the top). The BP, the puzzle Steps and the capture agree with each other: left to right from the nave = green, red, amber, blue.
4. **Candle meshes are BP components**, not placeable meshes; the plan's candles/candelabra are separate actors and must not cover the four `BP_PuzzleCandle` or block their sweep. Candle P2 and P3 are at X 8820, P1 and P4 at X 8800, all at Z 30 on the dais top.
5. **Interaction sweep.** The player's reach is 200 cm with an 8 cm sphere against the Interaction channel (default Block). Any BlockAll altar, candelabra, chest or rail placed on the eye line to the mechanism (X 8850..8950, Z 30..195) or to a candle will take the hit instead. Use NoCollision for decorative parts near them. Per `MCP_NOTES`, per-channel responses do not persist via `set_properties`; use `collisionProfileName`.
6. **Notes ride on greybox tops.** `Note_Nave` sits at Z 90.3 on `Pew_N1` (X 7025..7175, Y 200..450) and `Note_Sacristy` at Z 90.3 on `Sac_Table` (X 8150..8450, Y -1480..-1420). Replacement pew N1 and the sacristy table must have a top at Z about 90 under the note's XY, or the note floats or sinks (the notes are "never moved").
7. **`Window_Ledge` (StaticMeshActor_105)** is outside the east wall (X 9000..9300, Z 0..300) and is not in the plan's removal list. It overlaps the wall thickness X 9000..9020 and its top (Z 300) is 50 cm above the planned east window sill (Z 250), and the silhouette stands on it. It will show through the new east window as a block face at X 9000.
8. **`Dais` top is Z 30**; all candles and the mechanism pedestal start at Z 30. The dais is X 8500..8960; the mechanism spans X 8850..8950, so it is 10 cm from the east wall face (X 8960).
9. **Greybox walls are 40 cm thick** (Y +-750..790, X 8960..9000), the plan's new walls are 60 cm (to 810 / 9020). The clue Frame is at Y 744..750, unaffected.
10. **No floor candelabra in the Dungeon pack** (27.4 cm max). The amendment's "tallest floor-standing `SM_Candles_Holder_0x`" does not exist at native scale. Needs uniform x4 to x4.5 or another asset (see (m)).
11. **`BP_Flame` has no light and is Cascade.** Any use needs a separate light and a Cascade-capable renderer path; their size is unmeasured (see (k)).
12. **`SK_Dead_Man` hangs from Z 266.8 and its lowest point is 33.6 cm above its pivot.** Placed with the pivot on the floor, the rope top is 267 cm up; the walls top out at Z 1200 (gables to 2215 per the plan), so it needs a beam or truss to hang from, or a Z offset.
13. `PointLight_2` (door warm light, with a light function) is outside the deletion list `23..28` and stays.
14. All four puzzle BPs (and the mechanism and the silhouette) were dirtied in memory by `read_graph_dsl` (see the top).
