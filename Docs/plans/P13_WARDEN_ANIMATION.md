# Phase 13: Warden animation: plan

**Status: approved by the owner on 2026-11-06 ("go"). P13-0, P13-1 (13 files checked in Blender; registry 86cc8e8) and P13-2 (18df9d9, suite 108/108) done. F0, P13-3 (7e5e65d) and P13-4 (363f5ad) done. P13-5 sheet (00c5db6) shows the retarget is wrong; P13-4b done (0ca768c): arms and posture fixed. The robe and sleeve skin weights need fixing (decision with the owner). P13-6 (graph) can go ahead in parallel.**
**Branch:** `claude/phase-13-warden-animation`, from `main` (086d063).
**Rules:** D-048. The lead plans; every implementer is spawned with `model: "sonnet", effort: "high"`. Nothing starts without the owner's "go"; the owner is told before any capture over about 15 minutes; agents never run the capture tool or operate the desktop.

## 1. Goal and the owner's choices (2026-11-06)

Make the Warden move like a **slow, heavy stalker**: deliberate long strides and head turns on patrol, a long fast lope when chasing, a sudden stoop and lunge to grab. It must stoop through doors, look around at search points, turn on the spot, swing its robe and chains, keep its feet on stairs, pull the player's view to its mask when it catches them, and walk from the altar rail into the sacristy in the chapel beat.

| Question | Owner's answer |
|---|---|
| Where the animation comes from | **Mixamo motion capture.** The owner downloads the clips; we retarget them to the Warden in Unreal and tune them. Anything Mixamo lacks, our agent keys by hand |
| How it moves | **Slow, heavy stalker** |
| Extras | **All four:** robe and chain swing (physics), turning on the spot, catch camera, foot placement on stairs |
| Chapel | A real walk from the rail into the sacristy replaces the second station (fix set 1, D1) |

## 2. Exit conditions

1. Patrol (140 cm/s), search and return (170), investigate (190) and chase (420) play walk or run with **no visible foot sliding**, in the stalker feel.
2. It **stoops through every door and low stair** in section 7's table without its head passing through the lintel, including the sacristy door in the chapel beat.
3. **Attack:** the lunge reaches forward at the end of the unchanged 0.6 s windup. **Turns** step on the spot. **Look-around** plays at search points.
4. **Robe and chains** swing as it moves and settle when it stops: no jitter, no explosion.
5. **Feet** sit on stair treads; nothing pops on flat floors.
6. **Catch camera:** on a catch the view turns to the mask, holds, fades to black, then reloads. The Warden holds its grab pose.
7. **Chapel:** it forms at the rail, walks into the sacristy, stooping at the door, and fades.
8. The suite passes, with new tests for everything in this plan. **Animation adds ≤ 1.0 ms of game thread** against the same view with Phase 12's single clip. GPU stays ≤ 16.6 ms at High.
9. **The owner approves.**

## 3. What's there now (facts)

- **Rig:** `SK_Warden`, 110 bones, Unreal-mannequin names: `root`, `pelvis`, `spine_01..03`, `neck_01`, `head`, `clavicle/upperarm/lowerarm/hand_l/r`, fingers, `thigh/calf/foot/ball_l/r`. Plus `chain_neck_00..16`, `chain_l_00..11`, `chain_r_00..11` and `robe_00..07_01/02`. No IK or twist bones. Height about 286 (Idle) to 290 (Walk).
- **Physics asset:** `SK_Warden_PhysicsAsset`, 43 bodies and 42 constraints. Which bones they're on is read in F0.
- **Clips:** `AN_Warden_Idle`, `AN_Warden_Walk` and `AN_Warden_DoorwayStoop` (owner, V5.5). Walk barely moves the arms (R-52). They stay as fallbacks.
- **`BP_Warden`:** `CharacterMesh0` in single-clip mode with `AN_Warden_Idle`, `AlwaysTickPose`. Hooks: `PlayStateFeedback(NewState)`, `PlayWindupTell`, `ShowWindupTell`, `EndWindupTell`, the light and the mask glow (fix set 1).
- **AI** (`DA_WardenTuning`, unchanged by this phase): patrol 140, investigate 190, search 170, return 170, chase 420; turn rate 180°/s; look-around ±70°; search pause 2 s; attack range 140; windup 0.6 s. Movement: `bOrientRotationToMovement`, rotation rate 360.
- **Death:** `ALBCharacter::Kill()` disables input and calls `ALBGameMode::HandlePlayerDeath`, which reloads the checkpoint at once. The brain calls `Player->Kill()` when an attack lands.
- **Apparitions:** `ALBWardenApparition` (static `Body` plus `Glow`, station logic in `LBApparitionLogic`). `Apparition_Chapel` has stations at the rail (8380, −120, 0) and the sacristy (8500, −930, 0).
- **Tools:** the Unreal MCP tools can import skeletal meshes and clips, edit Blueprint event graphs, and run Control Rig and Sequencer. They **can't**:
  - create Animation Blueprints, IK Rigs or Retargeters (that call opens a dialog that freezes the editor);
  - build Animation Blueprint graphs, as far as is known; F4 tests this.

  Headless Unreal Python over the mirror project, run with the real editor closed, can create assets with factories and drive the IK Rig and Retargeter controllers.

## 4. Clips the owner downloads from Mixamo

On mixamo.com, signed in with a free Adobe account. Save every file to `ExternalAssets/Incoming/mixamo/`, which git ignores, with the file name given.

**Settings for every download:**
- FBX Binary (.fbx), **With Skin**, 30 fps, Keyframe Reduction none.
- Every slider at its default.
- Tick **In Place** whenever the option exists.
- Keep **Y Bot** as the character for every download.

We need "With Skin" because the import tool refuses clip-only FBX files.

| # | Search for | Pick | Save as | Used for |
|---|---|---|---|---|
| 0 | Characters tab: "Y Bot" | Y Bot, T-pose | `MX_YBot.fbx` | Source skeleton for the retarget |
| 1 | "mutant walking" | **Mutant Walking** (In Place) | `MX_MutantWalking.fbx` | Walk, first choice |
| 2 | "zombie walk" | **Zombie Walk** (In Place) | `MX_ZombieWalk.fbx` | Walk, second choice |
| 3 | "mutant run" | **Mutant Run** (In Place) | `MX_MutantRun.fbx` | Chase run, first choice |
| 4 | "zombie running" | **Zombie Running** (In Place) | `MX_ZombieRunning.fbx` | Chase run, second choice |
| 5 | "mutant breathing idle" | **Mutant Breathing Idle** | `MX_MutantIdle.fbx` | Idle |
| 6 | "crouched walking" | **Crouched Walking** (In Place) | `MX_CrouchedWalking.fbx` | Stoop walk |
| 7 | "crouching idle" | **Crouching Idle** | `MX_CrouchingIdle.fbx` | Stoop idle |
| 8 | "turn 90" | Standing **left turn of about 90°** on the spot | `MX_TurnLeft90.fbx` | Turn |
| 9 | "turn 90" | Standing **right turn of about 90°** on the spot | `MX_TurnRight90.fbx` | Turn |
| 10 | "zombie attack" | **Zombie Attack** | `MX_ZombieAttack.fbx` | Lunge and grab, first choice |
| 11 | "mutant swiping" | **Mutant Swiping** | `MX_MutantSwiping.fbx` | Lunge and grab, second choice |
| 12 | "looking around" | Standing **look around** (head and shoulders turn, feet still) | `MX_LookAround.fbx` | Search pause |

If a name isn't found exactly, the owner picks the closest match by the description and tells the lead which one. Pairs 1/2, 3/4 and 10/11 are compared at the look test, and one of each is kept.

**Licence (R-55, checked 2026-11-06):** Adobe's Mixamo FAQ allows characters and animations royalty-free in personal and commercial projects, including video games, and states no attribution requirement. Adobe's General Terms of Use forbid distributing its content files as stand-alone files, which we apply to the raw downloads. The raw FBX files stay out of git; only the retargeted Warden clips go into Content. The asset-curator records each file in `ASSET_REGISTRY.md` with the FAQ's URL. Not legal advice.

## 5. Import and retarget (animation-specialist)

Target folders:
- `/Game/LastBell/Characters/Warden/Retarget/`: Y Bot, its clips, the IK Rigs and the Retargeter.
- `/Game/LastBell/Characters/Warden/Anims/`: Warden clips, montages and blend spaces.

New prefixes, recorded in D-093:
- `AM_` montage
- `BS_` blend space
- `IK_` IK Rig
- `RTG_` IK Retargeter

The existing `AN_` stays for sequences.

1. **Import, with Unreal open, through the MCP tools:**
   - `MX_YBot.fbx` as `SK_LB_YBot`.
   - Each clip FBX with `skeleton` = `SK_LB_YBot_Skeleton`, imported under a throwaway mesh name: keep the sequence as `AN_YBot_<Name>` (for example `AN_YBot_MutantWalking`), then delete the throwaway mesh and its physics asset (`MCP_NOTES.md`, Warden section, item 3).
   - Save each package explicitly.
2. **Retarget, with Unreal closed, in headless Python over the mirror** (`UnrealEditor-Cmd C:\lbb\TheLastBell.uproject -run=pythonscript -script=<file>`), in a new script `Tools/warden/p13_retarget.py`.
   1. First run: print `dir()` and help for `unreal.IKRigController`, `unreal.IKRetargeterController` and `unreal.IKRetargetBatchOperation`, because the API changes between versions. Write the 5.8 calls into the script and into `MCP_NOTES.md`.
   2. Create `IK_LB_YBot` (preview mesh `SK_LB_YBot`) and `IK_LB_Warden` (preview mesh `SK_Warden`) with the controllers' auto-generated retarget definitions. Each needs chains for spine, neck and head, left and right arms, and left and right legs. **The Warden's `chain_*` and `robe_*` bones belong to no chain**; physics moves them.
   3. Create `RTG_LB_YBot_To_Warden`: auto-map chains, then auto-align the retarget pose (Mixamo's T-pose against the Warden's rest pose).
   4. Batch-retarget every `AN_YBot_*` onto `SK_Warden` into `Anims/`, with names `AN_Warden_<Name>`, for example `AN_Warden_MutantWalking`.

   **Fallback** if the API can't do a step: the owner's right-click **Retarget Animations** dialog in the editor, about 3 minutes, with exact clicks given at the time. Report which route worked.
3. **Measure each Warden clip in the same headless run** and write `Docs/ArtTest/warden/p13_clips.json`:
   - length;
   - **natural speed**: average speed of the planted foot backwards in an in-place clip, `foot_l` and `foot_r` while each is lowest;
   - highest head Z across all frames, plus 50 cm for the hood tip;
   - for the attack, the **hit time**, when `hand_l` and `hand_r` are furthest forward of the pelvis.
4. **Review sheet** (lead, F5): any clip whose limbs flip, twist or stretch is rejected or fixed. Hand-keyed fixes are made in Blender on the owner's rig and exported as in P12: one clip per FBX with the mesh.

## 6. Blend spaces and montages (animation-specialist; headless Python, owner UI as fallback)

| Asset | Settings |
|---|---|
| `BS_Warden_Locomotion` (1D) | Axis `Speed` 0–450. Samples: Idle at 0 (rate 1); Walk at **140** with rate scale 140 / walk's natural speed; Run at **420** with rate scale 420 / run's natural speed. Smoothing 0.3 s. Each locomotion speed then plays at the clip's own stride, so feet don't slide at 140 and 420, and 170–190 blend between them |
| `BS_Warden_Stoop` (1D) | Axis `Speed` 0–450. Crouching Idle at 0; Crouched Walking at 140 (rate 140 / natural); Crouched Walking again at 420 (rate 420 / natural, capped at 2.0) |
| `AM_Warden_Attack` | From the chosen attack, slot `DefaultSlot`, blend in 0.15, blend out 0.25. **Play rate = hit time / 0.6**, clamped to 0.8–2.5, so the reach lands at the end of the windup |
| `AM_Warden_TurnLeft90`, `AM_Warden_TurnRight90` | Slot `DefaultSlot`, blend 0.2 / 0.2, play rate 1.5 |
| `AM_Warden_LookAround` | Slot `DefaultSlot`, blend 0.3 / 0.3, trimmed to at most 2.0 s, because the search pause is 2 s |

The `DefaultSlot` group is the engine default. Play rates are stored in `DA_WardenAnimSet` (section 8), not on the montages, so they can be tuned without re-saving the clips.

### P13-4 result (363f5ad, 2026-11-06), measurements in `Docs/ArtTest/warden/p13_clips.json`
All built in headless Python on the real project with the editor closed:
- `IK_LB_YBot` and `IK_LB_Warden`, 21 chains each, no `chain_*` or `robe_*` bone in any chain;
- `RTG_LB_YBot_To_Warden`;
- 12 `AN_Warden_*` clips;
- `BS_Warden_Locomotion` and `BS_Warden_Stoop`;
- 4 `AM_Warden_*` montages;
- `DA_WardenAnimSet` (`AttackHitTime` 0.667 s, `AttackPlayRate` 1.111);
- `ABP_Warden`, with its `AnimSet` set, and `ABP_P13_Spike`. Both compile, with empty graphs.

No limb stretches (every chain stays at or below 1.000 of its reference length). **Nothing has been seen on screen.**

| Clip | Natural speed (cm/s) | Head top + 50 | Note |
|---|---|---|---|
| MutantWalking | 194.6 | 289.5 | walk at 140 plays at 0.72×; feet sink about 4 cm |
| ZombieWalk | unreliable | 281.1 | drags one foot |
| MutantRun | 296.4 | 270.4 | chase at 420 would play at 1.42× |
| ZombieRunning | 371.1 | 264.9 | chase at 1.13× |
| CrouchedWalking | 159.0 | **256.4** | **too tall for the doors** |
| CrouchingIdle | 0 | 186.0 | |
| ZombieAttack | — | 285.7 | two swipes; hit 0.667 s, reach 106 cm |
| MutantSwiping | — | 280.2 | hit 1.333 s, reach 130 cm |
| TurnLeft90 / TurnRight90 | — | ~291 | −90.0° / +102.6° |
| LookAround | — | 285.4 | trimmed to 2.0 s in the montage |

**Lead decisions:**
1. **Facing:** the Y Bot faces +Y and the Warden +X. The retarget pose turns the pelvis +90°, and every `AN_Warden_*` from Mixamo carries a constant −90° yaw key on `root`. **Accepted.** Re-importing the Y Bot rotated would redo P13-3. Consequence: don't blend these clips with the old identity-root `AN_Warden_Idle`/`Walk`/`DoorwayStoop`.
2. **Stoop height:** procedural, no new download. The anim set gets `StoopPelvisDrop` (40 cm). The anim instance adds −`StoopPelvisDrop` × `StoopAlpha` to `PelvisOffset.Z`, and foot IK is forced on while `StoopAlpha` > 0, keeping the feet on the floor. Expected top: 256 − 40 = **216** at full stoop, and 0.7 × that drop on the stairs. Checked on the contact sheet and the playtest.
3. **Foot IK is offset-based, not absolute:**
   - The fix: each foot target = the animated foot (previous frame, component space) + (ground hit Z under that foot − the capsule's floor Z), and `PelvisOffset.Z` = the lower foot's negative offset, at most `MaxPelvisDrop`.
   - Why: P13-2 set the foot Z to the ground plus the ankle height, which would pin a swinging foot to the floor on stairs.
   - Effect: on flat floor the offsets are 0. The 4–6 cm foot sink of four clips stays and is judged by eye, because the robe mostly hides the feet.
4. **Run:** ZombieRunning fits the 420 chase better (1.13× against 1.42×). It's the lead's pick unless the sheet shows a problem; the blend space gets updated if so.
5. **The contact sheet is rendered in Blender instead of captured in Simulate.**
   - How: the 12 Warden clips are exported to FBX with the Warden mesh, in headless Unreal Python, then rendered from the front and side at 0/25/50/75 % in neutral light.
   - Why: no capture session and no owner time, and a clearer read on twists and facing. The in-game look is judged in the playtest.

### P13-2 follow-up result (8e522b9, 2026-11-06)
`Tools/build_and_test.ps1`: **110 passed, 0 failed**. New tests: `Warden.Anim.FootTargetKeepsTheSwing` and `Warden.Anim.StoopPelvis`.

- **Foot IK, as built:**
  - `FootIKLeft` and `FootIKRight` hold a **delta in the foot bone's own space**: the foot's ground offset minus the pelvis drop already applied.
  - The Two Bone IK nodes use **Bone Space**, with the effector target = the foot itself (the section 9 graph is updated).
  - That way the effector follows the foot as animated this frame, so a swinging foot keeps its lift.
  - **Why not the lead's wording:** reading last frame's foot back would have fed the IK its own output.
- **Pelvis:** `PelvisOffset.Z` = clamp(foot pelvis drop − `StoopPelvisDrop` × `StoopAlpha`, −(`MaxPelvisDrop` + `StoopPelvisDrop`), 0). `StoopPelvisDrop` is 40.
- **While stooping:** foot IK is forced on and the traces run at any speed.
- **Not seen on screen.**

### P13-5 result (00c5db6, 2026-11-06): the retarget is wrong
Sheet: `Docs/ArtTest/warden/p13_sheet_all.png`, plus one per clip.
- **Arms:** in **every clip, the idle included,** the arms stick out horizontally at shoulder height, one forward and one back.
- **Torso and robe:** they lean 20–25° and bend.
- **What's right:** the legs, feet, head height and facing.
- **Why the P13-4 numbers passed:** they only measured legs, feet, head, drift and stretch, never where the arms point or how upright the spine is.
- **Likely cause:** the Y Bot faces +Y and the Warden +X. The retarget pose was auto-aligned *before* the target pelvis was yawed 90°, and the clips were then given a −90° `root` key. So the arms were aligned to the Y Bot's T-pose along the Warden's forward axis.
- **D1 is withdrawn:** the lead's acceptance of the `root` yaw key in the P13-4 block no longer stands.

**P13-4b: fix**
1. **Re-import** the Y Bot and its 12 clips in headless Python (`AssetImportTask` + `FbxImportUI`, with the editor closed), with an **import rotation that makes the Y Bot face +X like the Warden**. Confirm the facing from bone positions, not assumed: toes and nose ahead of the heels along +X. Replace the existing assets in place.
2. **Rebuild the retargeter's retarget pose from scratch:**
   - no pelvis yaw;
   - auto-align only;
   - if the Warden's rest pose differs from the T-pose in its arms, the auto-align handles it; if it doesn't, set the target arm chains to match the source T-pose directions explicitly.
3. **Re-batch** the 12 clips over the existing `AN_Warden_*`, with **no `root` key**.
4. **New measurements (failing any of them stops the task):**
   - in MutantIdle, both hands below Z 160 and within 60 cm of the pelvis sideways;
   - the pelvis-to-neck line within 15° of vertical in MutantIdle;
   - in every clip, no hand above Z 200 except in the attacks and LookAround.
5. **Rerun the contact sheet and look at it** before reporting anything as fixed. Blend spaces, montages and the data asset keep their references; just re-verify them.

### P13-4b result (0ca768c, 2026-11-06)
- **What changed:** the Y Bot was re-imported facing +X (yaw −90; toes 14 cm ahead of the heels along +X). The retarget pose was reset and auto-aligned without a pelvis yaw, then the pelvis was reset alone and the chain bones re-aligned, so the robe hangs straight (1.6° in the idle). No `root` key.
- **New sheet** (`p13_sheet_all.png`): the arms hang at the sides, the mask faces the direction of travel, and the feet are on the floor. The 4–6 cm sink is gone.
- **Lead decisions:**
  - the idle lean check (28.6°) **passes as the intended hunch**: the source Mutant Breathing Idle leans about 24°;
  - **ZombieWalk is dropped** (zombie arms at 215 cm, drags a foot);
  - picks: **Walk = MutantWalking, Run = MutantRun, Attack = ZombieAttack**, as already in the blend spaces and montages.
- **Updated numbers:** natural walk 196.5, run 270.1; locomotion rate scales 0.7125 and 1.5550. `AttackHitTime` **1.0667 s**, `AttackPlayRate` **1.7778** (provisional until seen in motion). Crouched walk still 254 cm, so it relies on the 40 cm pelvis drop.
- **New problem, found by the lead:** in the side views of walk and run, robe panels and sleeves stretch into big flat slabs as the limbs swing. Measured on LOD0 of the V5.5 master:
  - the **hem** (wool below 60 cm, 4,827 vertices) is weighted 98 % to the `robe_*` bones, which hang from `pelvis` and aren't driven by any clip, so the legs stride through it; 105 vertices are partly on leg bones and stretch;
  - the **sleeves** (1,528 vertices) are split, 59 % arm and 39 % robe bones, so polygons between them stretch when an arm swings.

  The fix is in the skin weights (sleeves onto the arm bones; the lower robe blended towards the thighs and calves), and P13-7's physics adds sway on top. **Owner's decision (2026-11-06): our agent reweights in Blender** (P13-4c below).

### P13-4c: reweight the robe and sleeves (technical-artist; Blender headless, then a headless Unreal re-import)
**Source:** `SourceArt/Warden/V5_5/Warden_Rigged.blend`, the project's copy (md5 `4445c23d…`). **Write a new file**, `SourceArt/Warden/V5_5w/Warden_Rigged.blend`; the V5_5 copy and the owner's folder stay untouched.

**Must not change:** bone names, hierarchy, rest pose, mesh topology, vertex order and counts, UVs, material slots. Only vertex-group weights change, on **all three LODs** (`SK_Warden_LOD0/1/2`).

**Rules** (positions in the master's frame, metres; +x is the Warden's left, as `hand_l` is at x +0.42):
1. **Sleeves:**
   - **Which vertices:** wool vertices with any weight on `upperarm_*`, `lowerarm_*` or `hand_*`, or within 0.25 m of those bones' segments, with 1.0 < z < 2.3 and |x| > 0.25.
   - **New weights:** remove every `robe_*` weight. Weight the vertex to its own side's `clavicle`, `upperarm`, `lowerarm` and `hand` by inverse squared distance to each bone segment, keeping the two highest and normalising.
   - **Shoulder seam:** blend towards `spine_03` with weight 1 − smoothstep(0.25 m → 0.45 m of |x|).
   - **Smoothing:** two Laplacian smoothing passes over the sleeve region only.
2. **Lower robe:**
   - **Which vertices:** wool vertices with z < 1.57 (the hip), not already sleeve vertices.
   - **Leg share:** L(z) = 0.5 × smoothstep from z 1.57 down to 0.60.
   - **Left/right split:** left fraction f = clamp(0.5 + x / 0.60, 0.1, 0.9); the right leg gets 1 − f.
   - **Bones:** each side's share goes to `thigh` above the knee (z 0.84). Below the knee it blends to `calf` by smoothstep from 0.84 down to 0.40.
   - **Robe bones:** the existing `robe_*` weights are scaled by 1 − L.
   - **Result:** the robe follows the legs at up to half strength without splitting, and the robe bones keep the rest for physics sway.
3. **Everything else:** unchanged.

**Measured before and after** (`Tools/blender/warden/p13_reweight.py`, plus a JSON report). Over every frame of the review FBX exports of MutantWalking, MutantRun, CrouchedWalking and ZombieAttack:
- the **largest edge stretch ratio** on wool polygons (deformed length ÷ rest length), and the share of wool edges above 1.5;
- **pass:** largest ratio ≤ **1.8**, and under 0.5 % of edges above 1.5. Report the before values too.

**Look:**
- rerun the contact sheet with the new mesh (LOD0 exported from the new blend), all 12 clips, and LOOK;
- no slabs, and no robe passing through itself badly at 25 % and 75 % of walk and run.
- **Attempt limit:** if a rule makes things worse, try one variation (for example L max 0.35, or three smoothing passes), then stop and report with images.

**Export:** 3 LOD FBX with the owner's own export settings (read `C:\Hemant\Prj\Learning\Warden\output\warden_art_v5_5\scripts\export.py`, read-only), to `SourceArt/Warden/V5_5w/exports/`.

**Re-import into Unreal** (headless Python, editor closed, after the look passes): replace `SK_Warden`'s geometry and weights **in place**, keeping the asset, `SK_Warden_Skeleton`, `SK_Warden_PhysicsAsset`, the 6 slot material assignments, socket `mask` and the 3 LODs (vertex counts as before: 75,603 / 45,003 / 22,347).
- Use a re-import or LOD import that keeps the existing asset. Never delete `SK_Warden`, because every clip, Blueprint and the apparition reference it.
- Then `Tools/warden/check_warden.py --disk`, plus a read-back of slots, socket and LODs.
- If an in-place re-import can't keep those, stop and report before changing anything.

### P13-4c result (ad993fe, 2026-11-06), with the lead's review
`SourceArt/Warden/V5_5w/` holds the variation (leg share 0.35, 3 smoothing passes): only weights changed, the topology is identical, and the V5_5 copy is untouched.
- **Better:** the walk, run, crouch and attack sleeves follow the arms, and the robe moves with the legs.
- **Still wrong:**
  - **turns:** the old robe-weighted sleeve flaps fold into boxes at the hip (a regression);
  - **feet:** flat slabs remain at floor level, from 108 wool vertices at z 0.15–0.22 weighted 100 % to the foot and leg bones, plus leather hem vertices mixing robe and foot;
  - **untouched band:** shoulder and chest wool no rule covers.
- **The stretch metric failed:** largest edge ratio 45–79 against 91–242 before; stretched share 8–12 % against 4–6 %. **The lead's 1.8 / 0.5 % thresholds were unrealistic** for 1 cm edges and a 40–60 cm limb swing.
- **New acceptance from round 3 on:** by eye on the sheets. No slabs, boxes or floor fans in any of the 12 clips at 0/25/50/75 %, front and side. The largest ratio and stretched share are reported, not gated.

**P13-4c round 3** (same agent, Blender only), on top of V5_5w, written to `SourceArt/Warden/V5_5w2/`:
- **(A) Feet:** the foot-pinned wool and leather hem vertices (z < 0.30 with over 50 % weight on `foot_*` or `ball_*`) get the weights of their nearest lower-robe neighbours (the rule 2 blend), plus two smoothing passes over the band z 0–0.4.
- **(B) Turns:** the old robe-weighted sleeve flaps below the armpit (z < 1.57, the 1,342 "near the arm" vertices that were 98 % robe) go back to the master's robe weights, blended 30 % towards `spine_03` / `pelvis` by height, **not** to the forearm.
- **(C) Seams:** a 10 cm feather (smoothing) across the sleeve-to-body boundary and across the untouched shoulder and chest band edge.
- **Attempt limit:** one try plus one variation, then stop with the sheets.

### P13-4c round 3 result (c5e93b0, 2026-11-06): **V5_5w2 accepted by the lead**
Sheets: `p13w2_sheet_*.png`. Only weights changed, verified against disk; `V5_5/` is untouched.
- **Fixed:**
  - **Feet:** 576 foot-pinned wool and leather hem vertices take their nearest robe neighbours' weights plus the leg blend.
  - **Turns:** the 626 sleeve-flap vertices below the armpit are back on the robe, 30 % towards `spine_03` / `pelvis`.
  - **Seams:** feathered within 10 cm.

  No slabs, hip boxes or floor fans in any of the 12 clips.
- **Metrics:** largest wool-edge stretch 24–44, against 91–242 in V5_5 and 59–79 in V5_5w. Stretched share 5–7 %.
- **Left:** thin hem slivers at the floor in some phases, a triangular sleeve flap at the hip in CrouchedWalking, ragged sleeve wings in the attacks. These are acceptable as torn cloth and are judged again in motion. LOD1 and LOD2 got the same rules but weren't rendered.
- **Next:** re-import V5_5w2's 3 LODs into `SK_Warden` in place (headless, editor closed), as in the P13-4c block. The leather boots now follow the legs at about 26 % calf; check the feet in the engine.

## 7. Stoop zones (lead fills the numbers in F0 from live transforms; unreal-blueprint-engineer places them)

New C++ actor `ALBWardenStoopZone`: a box, no collision, editor-only sprite, with property `StoopAmount` 0–1. A world subsystem `ULBWardenStoopSubsystem` keeps the list. The Warden's anim instance asks it for the **highest `StoopAmount` among boxes containing the actor's location**, then eases towards it at 3 per second. Boxes are oriented with the wall. Each extends 150 cm on both sides of the opening, is as wide as the opening plus 20 cm each side, and runs from floor to floor + 300.

**F0 (lead, 2026-11-06, read live): exact boxes**, world-aligned, rotation 0. Centre (x, y, z) and half-extents (x, y, z) in cm.
- The `BP_Door_Base_Dungeon` actors stand at the hinge: the opening's centre is 59 cm further along +Y, for example `Door_ChapelMain` at Y −59 for a chapel door centred at 0. Half-widths along the wall are 100 to allow for that.
- Stair floors come from downward traces, which hit the visible treads (15 cm rise per 30), not a hidden ramp. So foot IK will place the feet on the steps.
- The ceiling is the ground slab underside at Z −40.

| Zone | Centre | Half-extents | StoopAmount | Why |
|---|---|---|---|---|
| `SZ_Door_Sacristy` | (8020, −1100, 150) | (150, 100, 150) | 1.0 | 104 × 230 door, crossed along X |
| `SZ_Door_ChapelMain` | (6020, 0, 150) | (150, 100, 150) | 1.0 | 104 × 230, along X |
| `SZ_Door_Shortcut` | (6020, 2000, 150) | (150, 100, 150) | 1.0 | 104 × 230, along X |
| `SZ_Door_Tower` | (12020, 2009, 150) | (150, 100, 150) | 1.0 | 104 × 224, along X |
| `SZ_Cell_N9900` / `N10500` / `N11100` | (9900 / 10500 / 11100, 3000, 150) | (100, 150, 150) | 1.0 | cell door 110 wide, shoulders 220, crossed along Y |
| `SZ_Cell_W900` / `W2700` | (9500, 900 / 2700, 150) | (150, 100, 150) | 1.0 | cell door, crossed along X |
| `SZ_Stair_Sacristy` | (7290, −1100, −285) | (140, 150, 185) | **0.7** | treads rise along +X from Z −585 (X 6820) to −60 (X 7870); under the slab until X 7400, where the tread is −300 and the head would be 34 cm into the ceiling. The zone starts about 150 cm early so the stoop is complete in time |
| `SZ_Stair_Exit` | (10650, −170, −290) | (150, 150, 190) | **0.7** | treads rise along +Y from −585 (Y −700) to −60 (Y 350); ceiling −40 over Y −190…−70, where the head would be up to 45 cm into it |
| `SZ_Chapel_SacristyDoorway` | (8500, −780, 150) | (80, 150, 150) | 0.6 | 120 × 240 springline / 340 apex, crossed along Y; chapel apparition only |

The acceptance check is per zone at the look test: the highest head Z plus 50 cm, at that zone's `StoopAmount`, is at least 5 cm below the opening's lowest point on the Warden's line. If any fails, raise that zone's amount.

## 8. Code (gameplay-programmer; Unreal closed for the real build)

Pure logic in testable functions, as in `LBWardenLogic`. No hard asset references in C++; assets come through `DA_WardenAnimSet`.

**`ULBWardenAnimSet : UPrimaryDataAsset`** (`Source/LastBell/AI/LBWardenAnimSet.h`). Saved as `/Game/LastBell/Data/DA_WardenAnimSet`.
- Montages: `Attack`, `TurnLeft90`, `TurnRight90`, `LookAround`.
- Numbers: `AttackPlayRate`, `TurnPlayRate` 1.5, `TurnTriggerDegrees` 60, `TurnCooldownSeconds` 1.0, `StoopEaseRate` 3.0, `FootTraceUp` 50, `FootTraceDown` 75, `FootIKInterpSpeed` 15, `MaxPelvisDrop` 35, `PhysicsMaxDistance` 2500.

**`ULBWardenAnimInstance : UAnimInstance`** (`Source/LastBell/AI/LBWardenAnimInstance.h/.cpp`). Variables (`BlueprintReadOnly`, category `Warden`) bound in the graph: `GroundSpeed`, `StoopAlpha`, `FootIKLeft`, `FootIKRight` (component-space effectors), `PelvisOffset`, `FootIKAlpha`, `PhysicsAlpha`.
- **Game-thread update** (`NativeUpdateAnimation`):
  - `GroundSpeed` comes from the movement component if there is one, otherwise from the owner's location change. That lets an apparition use the same anim instance.
  - `StoopAlpha` from the subsystem.
  - Two foot traces (`ECC_Visibility`), only when `GroundSpeed` < 250, giving `FootIKLeft/Right`, `PelvisOffset` (the lower foot's drop, at most `MaxPelvisDrop`) and `FootIKAlpha`. That alpha is 1 when the two feet differ by more than 5 cm, otherwise eases to 0.
  - `PhysicsAlpha` is 0 beyond `PhysicsMaxDistance` from the player camera, otherwise 1.
  - Turn detection: when `GroundSpeed` < 15, no montage is playing and the cooldown is clear, yaw change accumulated over the last 0.5 s ≥ `TurnTriggerDegrees` plays `TurnLeft90` or `TurnRight90`.
- **Calls from `BP_Warden`:**
  - `PlayAttack()` plays `Attack` at `AttackPlayRate`.
  - `PlayLookAround()`.
  - `HoldCatchPose()` pauses `Attack` at its current position. If it's before the hit time, it lets it reach the hit time first.
  - `StopAllAnimMontages(0.2)` when the state becomes Dormant.

**Pure helpers, unit tested:**
- `LBWardenAnim::StoopTarget(zones, location)`
- `EaseTowards`
- `TurnDecision(yawHistory, speed, montageActive, cooldown)`
- `PelvisAndFeet(traceHits)`
- `AttackPlayRate(hitTime, windup)`

**`ALBWardenStoopZone` and `ULBWardenStoopSubsystem`** as in section 7. Unit test: a rotated-box point-inside test.

**Catch camera** (`ALBCharacter`, tuning in `ULBPlayerTuningData`: `CatchLookSeconds` 0.25, `CatchHoldSeconds` 0.8, `CatchFadeSeconds` 0.5):
- `Kill(AActor* Killer = nullptr)`.
- **With a killer:** input off (as now), then over `CatchLookSeconds` the control rotation turns to the killer's socket `mask` (or the killer location + 230 cm if there's no socket). Hold `CatchHoldSeconds`. Then a camera fade to black over `CatchFadeSeconds`. Then `HandlePlayerDeath`, about 1.55 s after the catch.
- **With no killer** (`lb.Kill`, kill volumes): **exactly as now**.
- The brain passes the Warden as the killer. Just before `Kill`, it fires a new `BlueprintAssignable` delegate `OnPlayerCaught` on `ULBWardenBrainComponent`, which `BP_Warden` binds to call `HoldCatchPose`.
- **Tests:** existing catch tests keep their assertions on the moment of death and may only lengthen their waits for the reload. A new functional test checks the view ends within 10° of the mask before the reload starts.

**Apparition walk** (`LBApparitionLogic`, `ALBWardenApparition`):
- Station gets `WalkPath` (`TArray<FVector>`) and `WalkSpeed` (default 110 cm/s).
- New phase **Walk** between Hold and FadeOut when `WalkPath` isn't empty. The actor moves along the path at `WalkSpeed`, turning towards the next point at up to 180°/s.
- FadeOut starts when the path ends, or at once if the player comes within `MinPlayerDistance`.
- New optional component `Figure` (`USkeletalMeshComponent`, NoCollision, no shadows) and `bUseSkeletalFigure`. When it's true, `Body` is hidden, and `Figure` gets the fade instances on every slot.
- **Unit tests:** walk phase entered, finished, cut short by distance. **Functional:** a spawned apparition walks a 3-point path, finishes at the last point, then fades.

**Tick settings on `BP_Warden`'s mesh:** `VisibilityBasedAnimTickOption` = `OnlyTickMontagesWhenNotRendered` (P12 left `AlwaysTickPose`); update-rate optimisation on.

**Build:** mirror build plus filtered tests while working; then `Tools/build_and_test.ps1` with Unreal closed. Pass: everything that passed before, plus the new tests, no `Result={Fail`.

### P13-2 result (18df9d9, 2026-11-06)
`Tools/build_and_test.ps1` on the real project: **108 passed, 0 failed** (92 before plus 11 unit and 5 functional). No existing test was changed. `CatchTurnsTheViewToTheMaskBeforeTheReload`: the view went from 132.8° off the mask to 0.0° in 0.9 s, using the real `mask` socket.

- **Differs from the plan:**
  - `PelvisOffset` is a vector, because the Transform (Modify) Bone node's Translation pin needs one; only Z is used.
  - `DA_WardenAnimSet` gets `AttackHitTime`, set from `p13_clips.json`, so `HoldCatchPose` knows the hit moment.
  - `ELBApparitionPhase` now has `Walk` after `Hold`, which renumbers the later values. Nothing stores them.
  - The stoop zone has no sprite, because a billboard needs a texture reference; its box shows in the editor.
- **Behaviour notes:**
  - Turn detection ignores single-frame yaw jumps over 45°, such as the apparition's turn to face the player.
  - Speed jumps over 2000 cm/s read as 0, such as teleports.
  - Foot IK uses last frame's foot X/Y.
  - "Too close" during an apparition walk is measured to the figure.
- **Not seen:** anything with real clips, the Animation Blueprint, the skeletal figure, or the catch camera on screen.
- **For P13-7:** after a catch the brain keeps running for about 1.55 s, so `BP_Warden`'s `OnPlayerCaught` handler must also call `CharacterMovement` → `DisableMovement` (then `HoldCatchPose`). Otherwise it could walk away in its frozen pose while the view tracks it.

## 9. Animation Blueprint `ABP_Warden` (owner UI, F4)

**Create** (headless Python with `AnimBlueprintFactory` if it works without a dialog; otherwise the owner, about 1 minute): parent `LBWardenAnimInstance`, skeleton `SK_Warden_Skeleton`, at `/Game/LastBell/Characters/Warden/ABP_Warden`.

**Graph:** F4 starts with a 10-minute spike on a throwaway `ABP_P13_Spike`: can MCP `create_node` place `AnimGraphNode_BlendSpacePlayer` and connect it? If yes, the agent builds the graph below. If no, the owner builds it from this exact checklist, about 15–20 minutes, then the agent reads it back with `find_nodes`.

```
[Blend Space Player: BS_Warden_Locomotion, X ← GroundSpeed] ──A─┐
                                                                 [Blend, Alpha ← StoopAlpha] → [Slot 'DefaultSlot']
[Blend Space Player: BS_Warden_Stoop,      X ← GroundSpeed] ──B─┘
   → (local to component, added automatically)
   → [Transform (Modify) Bone: pelvis, Translation ← PelvisOffset, Add to Existing, Component Space, Alpha ← FootIKAlpha]
   → [Two Bone IK: IK bone foot_l, Effector Location Space = Bone Space, Effector Target = foot_l, Effector Location ← FootIKLeft, Joint Target calf_l (Bone Space, location 0: the animated knee is the pole), Alpha ← FootIKAlpha]
   → [Two Bone IK: IK bone foot_r, Effector Location Space = Bone Space, Effector Target = foot_r, Effector Location ← FootIKRight, Joint Target calf_r (Bone Space, location 0), Alpha ← FootIKAlpha]
   → [RigidBody: Simulation Space Component Space, LOD Threshold 1, Alpha ← PhysicsAlpha]
   → (component to local, added automatically) → [Output Pose]
```

Compile with no warnings.

### P13-6 result (5b53ceb, 2026-11-06): graph built through the editor tools; no owner step
`ABP_Warden`'s AnimGraph is built with `create_node` and `connect_pins` (the Blend Space Player has a typed form with its asset already set), with node options set through `set_properties {"Node": ...}`.
- **Chain:** two Blend Space Players → Blend (StoopAlpha) → Slot `DefaultSlot` → Local to Component → pelvis Transform (Modify) Bone → two Two Bone IK → RigidBody (LOD Threshold 1) → Component to Local → Output Pose.
- **Compile:** a strict compile reports no errors and no warnings. A deliberately broken control proved the compile does raise on errors.
- **Not seen in motion.**
- **Knee pole:** the joint target was in Parent Bone Space, which put the pole at the hip; it is being changed to Bone Space on the calf (follow-up). R-56 is closed: the tools can build anim graphs.

## 10. Robe and chain physics (animation-specialist, [EDITOR], F6)

- **F0 (read 2026-11-06): 43 bodies.**
  - Body: `pelvis`, `spine_01..03`, `neck_01`, `head`, clavicles, upper and lower arms, hands, `thumb_01_l`, `middle_01_l`, `middle_01_r`, feet.
  - Chains: `chain_neck_05`; **`chain_l_00/02/04/06/08/10`**; **only `chain_r_04`**.
  - Robe: **all 16** `robe_00..07_01/02`.
- **Missing bodies to add first**, with the PhysicsToolsets tools (`AddBody`, `SetCapsule`, `AddConstraint`; no owner step):
  - `chain_r_00/02/06/08/10`, mirroring `chain_l`'s sizes and constraints;
  - `chain_neck_01`, `chain_neck_09` and `chain_neck_13`, matching `chain_neck_05`.

  Read every body and constraint back afterwards.
- **Simulated:** every body on a `chain_*` or `robe_*` bone. **Kinematic:** everything else. Linear and angular damping 0.6 and 1.0 to start; constraints limited to 30° swing, 10° twist.
- If those bones have no bodies, the physics asset needs adding in the editor's Physics Asset tool by the owner, about 10 minutes with exact steps. Report it before going on.
- **Pass, in Simulate with the Warden walking a test loop:** settles within 1 s of stopping; no body flies off or jitters at rest; chains don't pass through the forearms by more than a few cm.

### P13-6 follow-ups (4431dab, 2026-11-06)
- **Knee pole:** Bone Space on the calf.
- **Physics:** 51 bodies (8 new: `chain_r_00/02/06/08/10`, `chain_neck_01/09/13`); 32 simulated (16 chain, 16 robe), 19 kinematic; 50 constraints. Chain and robe limits: swing 30° / 30°, twist 10°. Damping 0.6 / 1.0 on chain and robe bodies.
  - **Right and neck chain bodies** are sized to their short bones (2.5 and 1.9 cm links) instead of mirroring `chain_l` (17.5 cm). The two existing bodies, `chain_r_04` and `chain_neck_05`, were resized too.
  - **To do:** the 16 robe capsules overlap; set every chain and robe body's collision response to Disabled, so they don't collide with each other.
- **Not seen in motion.**

## 11. Hooking it up (unreal-blueprint-engineer, [EDITOR], F6)

1. **`BP_Warden`:**
   - `CharacterMesh0`: animation mode Blueprint, class `ABP_Warden_C`, and the anim set `DA_WardenAnimSet` (a property on the anim instance class default).
   - `PlayStateFeedback`: Search plus stationary for 0.3 s calls `PlayLookAround`; Dormant calls `StopAllAnimMontages`.
   - `ShowWindupTell` calls `PlayAttack`.
   - Bind `OnPlayerCaught` (in `BindtoBrain`, like the other hooks) to call `CharacterMovement` → `DisableMovement`, then `HoldCatchPose`.
   - Keep the light and glow logic from fix set 1.
2. **`M_Warden_Apparition`:** turn on `bUsedWithSkeletalMesh`, recompile, validate.
   - `BP_WardenApparition` gets a `Figure` = `SK_Warden` with `ABP_Warden`.
   - Material overrides: slot `M_Warden_BellMetal` gets `MI_Warden_Apparition_Mask`; the other five slots get `MI_Warden_Apparition_Body`.
3. **`Apparition_Chapel`:**
   - `bUseSkeletalFigure` true.
   - **One station:** the rail, (8380, −120, 0), cone 30, min distance 150, in / hold / out 1.0 / 2.5 / 1.5.
   - `WalkPath`: (8380, −380, 0), (8500, −650, 0), (8500, −1000, 0), (8250, −1100, 0).
   - `WalkSpeed` 110.
   - The second station is removed.
   - `Apparition_Courtyard` is unchanged.
4. **Stoop zones** placed in `L_Monastery` per section 7, folder `Gameplay/Warden/StoopZones`.
5. Save each package explicitly. The map is saved once, before any template edit, as in fix set 1. Then `Tools/warden/check_warden.py` gets checks for all of this.

## 12. Look test, performance and playtest (lead and owner)

**Contact sheet (lead, about 10 minutes of capture, owner told first):**
- In Simulate, temporary `SkeletalMeshActor`s show every Warden clip, single-clip mode, frozen at 0, 25, 50 and 75 % of its length, in a lit crypt room. New `Tools/warden/p13_clip_review.py`.
- Judged: broken limbs, hunch and stalker feel, crouch height, and which of each pair to keep.
- The sheet goes to the owner.

**Performance (owner, about 5 minutes, High, `stat unit`):**
- Crypt chase in view, with `ABP_Warden`.
- Then the same view with `a.ParallelAnimUpdate 1` left on and `p.RigidBodyNode 0` to see the physics share.
- Then the same view with Phase 12's single clip (lead switches it with a temporary toggle and puts it back).
- **Pass:** animation adds ≤ 1.0 ms game thread; GPU ≤ 16.6 ms.
- **Also:** the P12 crypt reading had the game thread at 17.47 ms with no AI. The performance-engineer reads the logs and a 10-second Unreal Insights trace taken by the owner (`trace.start default,task,anim` / `trace.stop`) and reports the cause. Fixing it is a separate decision.

**Owner playtest (about 30 minutes), check list:**
- walk, run, the stalker feel;
- doors and stairs;
- the attack and the catch camera;
- turns and look-around;
- robe and chains;
- feet on stairs;
- the chapel walk.

## 13. Tasks

| Task | Scope | Owner | Needs | Depends on |
|---|---|---|---|---|
| P13-0 | Plan approval; D-093, R-55…R-58; IMPLEMENTATION_PLAN table | lead + owner | — | — |
| P13-1 | Mixamo downloads (section 4) | **owner**, about 20 min | Adobe sign-in | P13-0 |
| P13-2 | Section 8 code and tests | gameplay-programmer | Unreal closed for the real build | P13-0 |
| F0 | Read the physics asset bodies, door and stair transforms; fill sections 7 and 10 | lead [EDITOR read-only] | Unreal open | P13-0 |
| P13-3 | Import (section 5.1), registry rows | animation-specialist [EDITOR], asset-curator | Unreal open | P13-1 |
| P13-4 | Retarget, measure, blend spaces, montages (5.2–5.3, 6) | animation-specialist | **Unreal closed** (headless, mirror built) | P13-3 |
| P13-5 | Contact sheet and clip choices (section 12) | lead + owner | capture | P13-4 |
| P13-6 | `ABP_Warden` and graph (section 9) | animation-specialist, **owner** if the spike fails | Unreal open | P13-5 |
| P13-7 | Physics (section 10) and hookup (section 11) | animation-specialist, unreal-blueprint-engineer [EDITOR] | | P13-6 |
| P13-8 | Performance readings, Insights trace | owner + performance-engineer | | P13-7 |
| P13-9 | QA, docs, owner playtest; "PHASE 13 READY FOR YOUR REVIEW" | qa-reviewer, lead, owner | | all |

One editor agent at a time. Each commits on this branch only: never switch, merge or push.

## 14. Risks (added to `RISKS.md` at P13-0)

| Id | Risk | Mitigation |
|---|---|---|
| R-55 | Mixamo licence: royalty-free in games per Adobe's FAQ, raw files not redistributable | Raw files stay out of git; registry rows with the FAQ link; the owner reads the terms when signing in |
| R-56 | The animation graph can't be built by our tools, so it's left to the owner's UI work | 10-minute spike first; otherwise an exact 9-node checklist, read back afterwards |
| R-57 | Human mocap on a 290 cm figure with long arms and a robe: stretched arms, robe intersections, a human-looking gait | Pairs of clips to choose from; the contact sheet; hand-keyed fixes in Blender; hunched creature clips chosen on purpose |
| R-58 | Game thread: animation and rigid-body physics add CPU where the crypt already read 17.47 ms | Parallel anim update, update-rate optimisation, physics off beyond 25 m and LOD 1, montage-only ticking when unseen; measured against a 1.0 ms limit; Insights trace for the existing cost |

## 15. Not in this phase

- Audio, including footsteps; footstep notifies come with the audio phase.
- Changes to AI timing or behaviour.
- Cloth simulation.
- The finale's full-height reveal.
- Gore.
- Any new Warden ability.
