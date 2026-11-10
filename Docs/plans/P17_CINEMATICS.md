# Phase 17: Cinematics

**Status:** approved by the owner on 2026-11-10 ("approve"). P17-0 done. F0 items 1–5 and 7 done (6596144); the values are written into the sections below and summarised in Results. The owner accepted both story changes from F0 on 2026-11-10 ("use both suggestions"): the new Intro_1 text (section 3.1) and the `Note_Gatehouse` line (section 5).

**Hold (owner, 2026-11-10): no Blender work.** The owner has changed the Warden asset and will ask for it to be copied in later. Until then:
- **F0b** waits for the new source.
- **F0 item 6** (Warden slots, bones, `mask` socket) waits for the new `SK_Warden`.
- **P17-3** waits as well: the mask mesh, the hood void, the clip retarget and any Blender-keyed fallback.

**Not affected:**
- F0 items 1–5 and 7;
- A1, because the Mixamo clips are Y Bot downloads;
- P17-1, P17-2 and P17-4;
- S1a, which uses the current `SK_Warden` only to test the Sequencer API.

Branch `claude/phase-17-cinematics`, created from `main` at 88e164e. **The lead plans; every implementation agent is spawned with `model: "sonnet", effort: "high"`** (D-048).

Every task follows the standing rules:
- **Git:** commit on this branch only, staging by path (`git commit -m ... -- <paths>`). Never switch, merge or push.
- **Saving:**
  - explicit saves only: one package per `save_assets` call, then `is_dirty`;
  - never save the never-save list (`Tools/fx/p15_level.py` `NEVER_SAVE`, including `M_LB_Surface`, `BP_EndingTrigger` and `BP_WardenApparition`);
  - `DA_StormSettings`, `DA_StormFX` and `DA_Audio` are never saved with a debug field other than −1.
- **Tools:**
  - never `MaterialInstanceTools.set_parent`, `read_graph_dsl` or `BlueprintTools.create` of an unsupported class;
  - never Live Code a file that defines a file-static `TAutoConsoleVariable`. That is `LBStormFXSubsystem.cpp`, `LBAudioSubsystem.cpp` and the new `LBCinematicSubsystem.cpp`; close Unreal and use `Tools/build_and_test.ps1`.
- **One Unreal process at a time:**
  - one editor-mutating agent at a time;
  - headless `UnrealEditor-Cmd` runs only with the editor closed, and never two at once.
- **PIE and captures:**
  - never start PIE or run captures without the owner present;
  - before an owner session, state its length.
- **Reporting:** report honestly, and name what needs the owner's eyes.

## 0. Owner choices (2026-11-10)
| Topic | Choice |
|---|---|
| Finale | **Trapped in the belfry.** After the ring, the Warden is freed below and climbs the tower while the bell tolls by itself. It reaches the top and the ending plays. |
| Movement in the finale | **Look only.** Movement locks after the ring; the player can only turn their head. |
| Meaning of the ending | **You become the Warden.** It reaches you and lifts its bell-metal mask: under it there is only darkness in the hood. It puts the mask on you. The last view is through the mask's eye slits, looking at the gate, where a lantern comes in: the next villager. The bell rings once. |
| The mask moment | **Shown with a new animation.** The Warden lifts the mask with its hands, using a new Mixamo clip that the owner downloads (local only, like the other Mixamo clips) and a separate mask mesh. |
| Last shot | **The courtyard wall top**: the spot where the player first saw the Warden on arrival (`Apparition_Courtyard`), about 57 m from the gate. The story loops. |
| Opening | **Short intro on New Game** (about 29 s, skippable). Four lines on black, a fade-in on the approach path, lightning on the tower, the first toll and the title, then the camera blends into the player's view. Continue never plays it. |
| Player | **A villager from below.** |
| Intro text | As drafted (section 3.1). The owner may reword it in the Sequencer review. |
| After the ending | **Title cards, then credits** (about 40 s, skippable), then the main menu. |
| Credits lines | **Created by Hemant Singh Sisodia**; **Developed with Claude (Anthropic)**; asset credits from `ASSET_REGISTRY`; tools (Unreal Engine 5, Blender). |
| How it is built | **Sequencer (owner's choice over a C++-only director).** Level Sequences hold the cameras, the Warden figure, the mask, the lantern and the fades, so timing is editable on a timeline. Story actions are labelled Sequencer markers that a C++ subsystem carries out. |

## 1. Outcome and acceptance
1. **New Game** (from the menu, `lb.NewGame`, or editor Play on `L_Monastery` with an empty state):
   - the screen is black from the first frame;
   - the intro plays (section 3.1) and the player can't move or interact;
   - holding Interact for 1 s skips it;
   - afterwards the view is the player's own, with no pop, and `State.Event.Arrival` is set;
   - the first toll (stage 1 × 3) plays once.
2. **Continue, a death reload and a checkpoint load** never play the intro, and the first toll doesn't repeat.
3. **Ringing the great bell:**
   - the player is eased to `LB_Cine_FinaleMark` and from then on can only look;
   - the AI Warden goes dormant (stage 6) and a scripted figure climbs the tower;
   - the bell swings on every strike;
   - the close-up shows the mask lift and the hood's darkness;
   - the through-mask shot shows the gate and the lantern, and the bell rings once;
   - then the two end cards and the credits, which can be skipped by holding Interact;
   - then the main menu, with the save deleted.
4. **Nothing is saved while a cinematic plays:** no checkpoint saves. Quitting during the finale leaves the save at `CP_TowerTop`.
5. **The storm and audio run to the very end** (R-77 part 1). The world sound fades under the end cards, and a drone carries the credits.
6. **Clean failure:** if anything fails to load (a missing sequence or clip), the game never stays locked or black. The subsystem fires the remaining must-markers, restores input and the view, and logs an Error.
7. **Tests:** the suite passes with Unreal closed, including the new `Cine.*` tests and `RouteBot.Monastery` (which now plays the intro and the finale at 8× and skips the credits). The Game target builds.
8. **Owner sign-off:** the owner approves the intro and the finale in their review sessions (P17-6, P17-7) and in the play-through (P17-8).

## 2. Architecture (C++, gameplay-programmer, Unreal closed)
New folder `Source/LastBell/Cinematics/`:

| File | Contents |
|---|---|
| `LBCinematicTypes.h` | `ELBCineTrigger`, `ELBCineCardStyle`, `ELBCreditStyle`, `ELBBellSwingAxis`, `FLBCinematicDef`, `FLBCineCard`, `FLBCreditLine`, `FLBCineMarker` |
| `LBCinematicLogic.{h,cpp}` | Pure functions: marker parsing, crossing, skip selection, ease, bell pendulum, credits speed |
| `LBCinematicSettings.{h,cpp}` | `ULBCinematicSettings` (`UPrimaryDataAsset`), asset `/Game/LastBell/Data/DA_Cinematics` |
| `LBCinematicSubsystem.{h,cpp}` | `ULBCinematicSubsystem` (`UTickableWorldSubsystem`). Defines the CVars, so it is **never Live Coded** |
| `LBCinematicWidget.{h,cpp}` | `ULBCinematicWidget` (`UUserWidget`, builds its own tree in C++; no WBP asset) |
| `LBCineAuthoringLibrary.{h,cpp}` | `ULBCineAuthoringLibrary` (`UBlueprintFunctionLibrary`): `SetCameraCutTrackCanBlend` and `GetCameraCutTrackCanBlend`, for headless authoring. Added after S1a: `UMovieSceneCameraCutTrack::bCanBlend` is a public C++ member with a bare `UPROPERTY()`, so Python can't set it. Python calls `unreal.LBCineAuthoringLibrary.set_camera_cut_track_can_blend(track, True)` |

- **`LastBell.Build.cs`:** add `"LevelSequence"`, `"MovieScene"` and `"MovieSceneTracks"` (the last for the authoring helper) to the public dependencies.
- **`ULBGameSettings`:** add `UPROPERTY(Config, EditAnywhere, Category = "Cinematics") TSoftObjectPtr<ULBCinematicSettings> CinematicSettings;`.
- **`Config/DefaultGame.ini`** (`[/Script/LastBell.LBGameSettings]`): add `CinematicSettings=/Game/LastBell/Data/DA_Cinematics.DA_Cinematics`.

### 2.1 Markers: the timeline language
Every action the sequence needs from the game is a **Sequencer marked frame** whose label follows the grammar below. Checked in the engine source: `UMovieScene::MarkedFrames` is a runtime `UPROPERTY`, not editor-only data, so markers ship in cooked builds.

**Grammar:**
- `[!]kind[:arg[,arg]]`, case-sensitive, with no spaces.
- A leading **`!`** makes a marker a **must** marker: a skip fires it if it hasn't fired yet (section 2.3).
- An unparsable label logs one Error when the cinematic loads, is ignored at runtime, and fails `Monastery.CinematicSetup`.

| Label | Action |
|---|---|
| `card:<CardId>` | The widget shows `DA_Cinematics.Cards[CardId]` (fade in, hold, fade out; times in the card) |
| `tag:<Tag>` | `ULBWorldStateSubsystem::AddState(Tag)` |
| `bell:<Stage>x<Strikes>` | `ULBAudioSubsystem::PlayBell(Stage, Strikes)` (strikes `PlayBellSpacing` 4.5 s apart) |
| `strike:<ActorTag>[,<Brightness>]` | `ULBStormSubsystem::RequestFlashAtTarget(Brightness or 1.0, 0, ELBFlashReason::Scripted, ELBFlashProfile::Auto, the first actor with ActorTag)`. No such actor: Warning, then `flash:` with the same brightness |
| `flash:<Brightness>` | `ULBStormSubsystem::RequestFlash(Brightness, 0, ELBFlashReason::Scripted)` |
| `look:<ActorTag>[,<Seconds>]` | Look assist: the control rotation eases to face the actor's location (for `LB_Cine_Warden`, its `head` bone) over Seconds (default `LookAssistSeconds` 1.5). Input is held at `Full` during the blend, then the previous lock comes back |
| `mark:<ActorTag>[,<Seconds>]` | Moves the pawn to the tagged actor (default `MarkSeconds` 1.5): XY to the actor's location; Z = actor Z + capsule half height; yaw to the actor's yaw; pitch to 0. Section 2.4 |
| `lock:<None\|Look\|Full>` | Sets the player's input lock |
| `skip:<0\|1>` | Skippable from here, or not |
| `mix:<on\|off>` | Pushes or pops `DA_Cinematics.CineFadeMix` (`SMX_LB_CineFade`) |
| `credits[:<Seconds>]` | Starts the credits roll (default `CreditsSeconds` 40) |
| `end` | Waits until the credits roll has finished (or was skipped), then calls `ULBSaveSubsystem::CompleteGame()`. The mix is **not** popped before the travel, so world sound doesn't come back over the black screen; `Deinitialize` pops it at world teardown |

Markers fire in time order. Several crossed in one tick all fire in that tick, in order. A marker never fires twice. A backward jump fires nothing.

### 2.2 `ULBCinematicSettings` (`DA_Cinematics`)
| Field | Type | Value |
|---|---|---|
| `Cinematics` | `TArray<FLBCinematicDef>` | Two rows, below |
| `Cards` | `TMap<FName, FLBCineCard>` | Section 3.3 |
| `Credits` | `TArray<FLBCreditLine>` | Generated by `Tools/cine/make_credits.py` (section 6) |
| `CreditsSeconds` | float (s) | 40 |
| `SkipHoldSeconds` | float (s) | 1.0 |
| `SkipPromptText` | FText | `Hold E to skip` (key glyphs come in Phase 18) |
| `MarkSeconds`, `LookAssistSeconds` | float (s) | 1.5, 1.5 |
| `BellActorTag` | FName | `LB_Cine_Bell` |
| `BellComponentName` | FName | `Mesh` (F0: the bell's only mesh component, its root, already Movable) |
| `BellHeadstockTag` | FName | `LB_Cine_BellHeadstock` (the actor that gives the axle point and swings with the bell; section 2.8) |
| `BellRopeTag` | FName | `LB_Cine_BellRope` (the rope that follows the wheel rim vertically; section 2.8) |
| `BellSwingAxis` | `ELBBellSwingAxis` (Pitch, Roll) | `Pitch` (F0: the wheel disc is in the XZ plane, the axle runs along world Y, and the bell's rotation is 0, so the axle is its local Y) |
| `BellSwingKickDegrees` / `BellSwingMaxDegrees` | float (deg) | 6 / 16 |
| `BellSwingPeriodSeconds` / `BellSwingDampingPerSecond` | float | 2.6 / 0.25 |
| `CineFadeMix` | `TSoftObjectPtr<USoundMix>` | `/Game/LastBell/Audio/Mix/SMX_LB_CineFade` |

`FLBCinematicDef` has these fields:
- `Id` (FName) and `Sequence` (`TSoftObjectPtr<ULevelSequence>`);
- `Trigger` (`NewGame` or `TagAdded`) with `TriggerTag`;
- `BlockingTag`: the def never starts while this tag is present;
- `InitialLock` (`ELBInputLock`), `bStartBlack`, `bSkippableAtStart`;
- `GrantOnStart` (`FGameplayTagContainer`);
- `FailSafeMarkers` (`TArray<FString>`; added in P17-1): the labels fired, in order, when the sequence can't be loaded or played, because its own markers are then unavailable. Intro: `!tag:State.Event.Arrival`. Finale: `!end`.

The two rows:

| Id | Sequence | Trigger | BlockingTag | InitialLock | bStartBlack | bSkippableAtStart | GrantOnStart |
|---|---|---|---|---|---|---|---|
| `Intro` | `/Game/LastBell/Cinematics/LS_LB_Intro` | `NewGame` | `State.Event.Arrival` | Full | true | true | — |
| `Finale` | `/Game/LastBell/Cinematics/LS_LB_Finale` | `TagAdded` `State.Event.Finale` | — | Full | false | false | `State.Warden.Stage.6` |

Every float is clamped, with units in its tooltip. No hard asset references: everything above is a soft pointer.

### 2.3 `ULBCinematicSubsystem`
- **Creation:** `ShouldCreateSubsystem` is true for Game and PIE worlds only. `GetTickableTickType` is Conditional, ticking only while a cinematic plays, the bell swings or the credits roll.
- **`OnWorldBeginPlay`:**
  1. Load the settings: `OverrideSettings` for tests, otherwise `ULBGameSettings::CinematicSettings`. If neither exists, do nothing for this world.
  2. Bind `ULBWorldStateSubsystem::OnStateChanged`.
  3. Find the bell (the first actor with `BellActorTag`), the headstock (`BellHeadstockTag`) and the rope (`BellRopeTag`), store their rest transforms (section 2.8), and bind `ULBAudioSubsystem::OnGreatBellStrike` (section 2.6).
  4. **The NewGame rule:** a `NewGame` def is chosen when all of these hold:
     - the world's package, with any PIE prefix removed (`UWorld::RemovePIEPrefix`), is `ULBGameSettings::NewGameMap`;
     - `ULBSaveSubsystem::HasPendingRestore()` is false (so not Continue, a death or a checkpoint load);
     - the world state lacks `BlockingTag`;
     - `lb.Cine.Enabled` is 1.

     The rule is decided here, before the pending restore is cleared one tick later. If chosen and `bStartBlack` is set, call `PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::Black, false)` at once, and start the cinematic on the first `Tick`.
- **`TagAdded` trigger:** when `OnStateChanged(Tag, bAdded = true)` matches a def's `TriggerTag` and `lb.Cine.Enabled` is 1, play it. `OnStateReplaced` never triggers anything.
- **`Play(Def)`:**
  1. Add `GrantOnStart`.
  2. Load the sequence synchronously; it is small and preloading is unnecessary.
  3. Parse the markers into seconds: (`FrameNumber` − playback start) ÷ tick resolution.
  4. Create the player with `ULevelSequencePlayer::CreateLevelSequencePlayer` (`bAutoPlay` false; `PlayRate` = `lb.Cine.Rate`; `bDisableMovementInput`, `bDisableLookAtInput`, `bHidePlayer` and `bHideHud` all false, since the subsystem handles them).
  5. Bind `OnFinished`, set the lock to `InitialLock`, hide the HUD (`ALBPlayerController::SetHUDHidden(true)`), create the widget, then `Play()`.

  If loading or creation fails: log an Error, then **fail safe**: fire the def's `FailSafeMarkers` in order, restore and finish.
- **`Tick`:**
  - read `Player->GetCurrentTime()` and fire the crossed markers (section 2.1);
  - advance the mark move, the look assist, the bell pendulum, the credits, the cards and the skip hold. Everything is scaled by the play rate, so tests at 8× see the same order.
- **Skip:**
  - The character's locked-interact delegates (section 2.4) call `BeginSkipHold` and `EndSkipHold`. While skippable, holding for `SkipHoldSeconds` calls `RequestSkip()`; the widget shows the prompt and a progress bar.
  - **`RequestSkip()`:** fire every must marker not yet fired (in order); jump the player to the end (`SetPlaybackPosition` with `EUpdatePositionMethod::Jump`, then `Stop`); fade the camera from black over 0.5 s (`StartCameraFade(1, 0, 0.5, Black)`); restore.
  - Skipping during the credits stops the roll, so the pending `end` completes at once.
- **Restore** (on finish, skip, stop or failure):
  - lock `None`, HUD shown;
  - destroy the sequence actor and remove the widget, unless a `CompleteGame` travel is pending;
  - `StopCameraFade()` unless travelling;
  - pop the mix if it was pushed, unless travelling (then `Deinitialize` pops it);
  - log "Cine: <Id> finished (<reason>)".
  - **With a `CompleteGame` travel pending,** the lock, HUD, fade, widget and mix are all left as they are, so the HUD doesn't flash over the black screen; the world is torn down anyway. The `lb.Cine.NoEnd` path and a failed `CompleteGame` do the full restore. (P17-1.)
- **Public API:**
  - `IsPlaying()` and `GetActiveId()`;
  - `Play(FName Id)` (BlueprintCallable, also behind `lb.Cine.Play`);
  - `RequestSkip()` and `StopCinematic()`;
  - `OverrideSettings(ULBCinematicSettings*)` plus `Rearm()` for tests;
  - delegates `OnCinematicStarted(FName)`, `OnCinematicFinished(FName)` and `OnMarkerFired(FString Label)`, for tests.
- **CVars** (non-shipping, file-static in `LBCinematicSubsystem.cpp`):
  - `lb.Cine.Enabled` (1). Setting it to 0 stops a running cinematic at once (restore, no must markers), and nothing starts afterwards.
  - `lb.Cine.Rate` (1.0, clamped 0.25–16).
  - `lb.Cine.NoEnd` (0). With 1, `end` only restores and logs "Cine: end suppressed (lb.Cine.NoEnd)", for review sessions.
  - `lb.Cine.Debug` (0). With 1, the sequence time, the next marker, the lock and the skip state show on screen.
- **Console commands** in `LBConsoleCommands.cpp` (non-shipping):
  - `lb.Cine.Play <Id>`;
  - `lb.Cine.Skip` (skips even when not skippable);
  - `lb.Cine.Stop`;
  - `lb.Cine.PlayAsset <LevelSequence path>`: plays any sequence through a temporary def (InitialLock Full, skippable), for the S1b spike and reviews.
- **Log lines** (`LogLB`):
  - "Cine: play Intro (LS_LB_Intro, 29.0 s, 9 markers)";
  - "Cine: marker '<label>' at 17.40 s";
  - "Cine: skip at 5.20 s (2 must markers fired)";
  - "Cine: end -> CompleteGame".

### 2.4 Player and controller (`ALBCharacter`, `ALBPlayerController`)
- **`ELBInputLock`** { `None`, `Look`, `Full` } goes in `Character/LBPlayerTypes.h`.
- **`ALBCharacter::SetInputLock` / `GetInputLock`.** Setting a lock other than `None`:
  - clears `MoveInput`;
  - calls `GetCharacterMovement()->StopMovementImmediately()` and `UnCrouch()`;
  - turns sprint off.

  With the lock on, the handlers behave as follows:

  | Handler | `Look` lock | `Full` lock |
  |---|---|---|
  | `Move`, Sprint, Crouch, Candle | ignored | ignored |
  | `Look` | allowed | ignored |
  | `Interact` | broadcasts `OnLockedInteractPressed` and returns | same |

  `Interact` on `Completed`/`Canceled` (new bindings) broadcasts `OnLockedInteractReleased`. **As built (P17-1):** `IA_Interact` has a Pressed trigger, so `Completed` fires one frame after the press. The release is therefore broadcast only when no key bound to Interact is still down, checked on `Completed`/`Canceled` and on every tick while a locked press is held. A lock other than `None` also cancels an open inspection. The owner checks hold-to-skip in P17-6. Both delegates are non-dynamic multicast; the subsystem binds them while it plays, so the character never includes the cinematic headers.
- **Mark move:** the subsystem eases the capsule with smoothstep from its start to the target with `SetActorLocation` each tick, and eases the control yaw along the shortest path. Movement mode is `MOVE_None` during the move, and `MOVE_Walking` again on restore. No velocity means no footsteps.
- **`ALBPlayerController::SetHUDHidden(bool)`:** sets `HUDWidget` Collapsed or `SelfHitTestInvisible`. Cinematics never use `SetMenuMode`; the input mode stays game-only, so mouse look works.

### 2.5 Warden: stage 6 is the scripted finale (D-116)
- **`LBWardenLogic::CapsForStage`:** `bActive = Stage >= 3 && Stage <= 5`.
  - At stage 6 the AI pawn goes Dormant (hidden, no collision, perception ignored) through the existing stage-gate path, so only the sequence's figure exists.
  - Update every test whose stage sweep expects stage 6 to be active, with a comment citing D-116.
  - The new unit test is `Warden.Stage6IsDormant`.
- **`State.Warden.Stage.6`'s only source** is the Finale def's `GrantOnStart`.
- **`WSpawn_Tower`** (MinStage 6) stays in the level and is unused. Record it in `AI_DESIGN`.

### 2.6 Audio additions (`LBAudioSubsystem.cpp`: never Live Code)
- **`FOnLBGreatBellStrike OnGreatBellStrike(int32 Stage, float Volume)`:** broadcast the moment any great-bell strike starts (beats, the new-game toll, ambient tolls, `PlayBell`), never for small bells.
- **`FillPlanDefaults()`:** a new first row, `{ "State.Event.Arrival", 1, 3, 0.f, 4.5f, 0 }` (stage 1 × 3, first strike at once, 4.5 s apart, Drone A).
- **`DA_Audio`** (P17-2 through `Tools/audio/p16_2_assets.py`, the single source):
  - the Arrival row in `BellBeats` (written from `FillPlanDefaults`);
  - `bNewGameToll` = **false** in `OWNER_CHOICES`, since the intro's Arrival beat replaces it;
  - the code and its test keep `bNewGameToll` (tests use their own settings).

### 2.7 Storm, save and checkpoints
- **Storm:** no code change. It stays active until `CompleteGame`'s travel, so the finale strikes and the bell sound to the end (R-77 part 1). The ending no longer pauses the game. Bell strikes stay UI sounds on the unpaused clock (P16-6); what a pause menu does with them is Phase 18 (R-77 part 2).
- **`ALBCheckpoint::CanSaveNow()`:** also false while `ULBCinematicSubsystem::IsPlaying()`. The refusal log becomes "Checkpoint '%s' refused (%s). Retrying while the player stays inside.", with the reason "the Warden is chasing" or "a cinematic is playing". `CP_Approach` therefore saves after the intro, with `State.Event.Arrival` already set. (F0: its box spans X −2750…−2650, 50 cm east of the PlayerStart at X −2800, so the save happens on the player's first steps forward, not at the spawn. No change needed.)

### 2.8 The bell swing
`LBCinematicLogic::FBellPendulum` (pure, unit tested):
- angle(t) = A·e^(−d·t)·sin(2πt/P);
- each kick adds `BellSwingKickDegrees` to A, clamped to `BellSwingMaxDegrees`;
- below 0.05° it stops, and the tick goes idle.

On `OnGreatBellStrike` the subsystem kicks the pendulum. **This applies to every great-bell strike on the map, not only in the finale:** the bell swings by itself at the TowerTop beat and at ambient tolls too, consistent with "no hand on the rope". The owner can veto this in P17-7, and it would then become finale-only with a flag.

**How the angle is applied (from F0).** The bell's origin (z 2860, the crown) is 20 cm below the axle. The headstock wraps the crown, so a bell turning under a still headstock would clip through it. Three actors therefore move together:
- **At world BeginPlay**, the subsystem finds:
  - the bell actor (`BellActorTag`) and its component `BellComponentName`;
  - the headstock actor (`BellHeadstockTag`; F0: `TWA_Headstock` at (12420, 2000, 2880), rotation 0);
  - the rope actor (`BellRopeTag`; F0: `TWA_BellRope` at (12550, 1835, 2750), the rope's top on the wheel's east rim).

  It stores each one's rest world location and rotation.
- **Axle:**
  - The pivot point P is the headstock actor's rest location.
  - The axis is the headstock's rest rotation applied to local Y for `Pitch`, or to local X for `Roll`.
- **Each tick while swinging,** with Q = FQuat(axis, angle in radians):
  - the bell component and the headstock actor each get location P + Q·(rest location − P) and rotation Q·(rest rotation);
  - the rope keeps its rest X and Y and takes the Z of P + Q·(rope rest location − P). A hanging rope stays vertical, and its top follows the rim up and down (about ±36 cm at 16°).

  All three moves use `ETeleportType::TeleportPhysics` with no sweep. At rest, every actor gets its exact rest transform back.
- **If a piece is missing,** the swing still runs:
  - with no headstock, P is the bell component's rest location and the axis is the bell's rest local axis; log a warning once;
  - with no rope, the rope step is skipped; log a warning once.
- **Mobility:** all three must be Movable. F0 found the bell's `Mesh` already Movable, and `TWA_Headstock` and `TWA_BellRope` Static, so P17-5b sets those two to Movable.
- **Clearance:** the lowest rim corner reaches about X 12587 at 16°. The frame's bounds end at X 12585, so whether the rim clips the frame's east brace is checked by eye in P17-7. If it clips, the owner lowers `BellSwingMaxDegrees`.

### 2.9 `ULBCinematicWidget` (C++ tree, no WBP; Phase 18 restyles it)
Built in `NativeOnInitialized` with `WidgetTree->ConstructWidget` (a root `UCanvasPanel`). All text colour is (0.85, 0.82, 0.76, 1); fonts are `FCoreStyle::GetDefaultFontStyle`.

| Element | Spec |
|---|---|
| `CardText` | Centred; Roboto `Light` 30; wraps at 1400; centre-justified |
| `TitleText` | Centred; Roboto `Light` 72, letter spacing 300 |
| `CreditsBox` | A `UVerticalBox`, anchored top-centre, width 1200, translated from Y = viewport height to Y = −(box height) over the roll's seconds |
| Credit line styles | `Heading` Light 36; `Name` Light 26; `Small` Regular 18 at colour × 0.7; `Gap` a 40 px spacer |
| `SkipText` | Bottom-right, 48 px margin, Regular 16, alpha 0.6, `SkipPromptText`; visible only while skippable |
| `SkipBar` | A `UProgressBar`, 120 × 3, under the prompt, showing the hold fraction |

Cards fade by render opacity. The widget draws no black itself: black comes from the camera fade (the Sequencer Fade track and the manual fade at start). Tests check the texts through `GetCardTextForTest()` and the credits line count.

### 2.10 `LBCinematicLogic` (pure, unit tested)
| Function | What it does |
|---|---|
| `ParseMarker(Label, OutMarker, OutError)` | Parses one label |
| `MarkersToFire(Sorted, PrevSeconds, CurSeconds, FiredMask)` | Markers crossed in (Prev, Cur], in order, each once |
| `MustMarkersOnSkip(Sorted, FiredMask)` | The must markers not yet fired, in order |
| `Smoothstep`, `ShortestYawLerp` | Easing helpers |
| `FBellPendulum` | Section 2.8 |
| `SwingAboutAxle(RestLocation, RestRotation, Pivot, Axis, AngleDeg)` and `RopeZAboutAxle(RopeRestLocation, Pivot, Axis, AngleDeg)` | The transforms in section 2.8 |
| `CreditsPixelsPerSecond(BoxHeight, ViewportHeight, Seconds)` | Credits scroll speed |

## 3. The script
### 3.1 Intro: `LS_LB_Intro` (30 fps, playback 0–29.0 s)
**Cards** (DA; styles in 3.3):

| Card | Text |
|---|---|
| Intro_1 | For forty years, no one has come back from the monastery on the ridge. |
| Intro_2 | Its great bell fell silent the night the brothers vanished. |
| Intro_3 | Tonight, the whole village heard it ring. |
| Intro_4 | Someone has to go up. |
| Title | THE LAST BELL |

**Timeline:**

| Time (s) | Track or marker |
|---|---|
| 0.0 | Fade track 1.0 (black); marker `skip:1` |
| 0.8 / 3.8 / 6.8 / 9.8 | `card:Intro_1` / `card:Intro_2` / `card:Intro_3` / `card:Intro_4` (each 0.3 in, 2.4 hold, 0.3 out) |
| 13.0 | Camera cut to `Cam_Intro` starts (section 13.0–27.0, ease-out 1.5 s, track `bCanBlend` true). Fade 1.0 at 13.0, eases to 0.0 at 15.5 |
| 13.0 → 27.0 | `Cam_Intro` moves from pose A to pose B, cubic ease in-out |
| 17.0 | `strike:LB_StrikeTarget_Tower,1.0` |
| 17.4 | `!tag:State.Event.Arrival` (audio: stage 1 at 17.4, 21.9 and 26.4 s; Drone A) |
| 19.0 | `card:Title` (0.8 in, 3.5 hold, 0.8 out) |
| 27.5 | `!lock:None` |
| 29.0 | End |

**`Cam_Intro`** (spawnable `CineCameraActor`):
- Filmback 16:9 DSLR, `bConstrainAspectRatio` false, aperture f/2.8, manual focus 6000 cm.
- **Pose B** is exactly the player's eye at spawn: **(−2800, 0, 152.79), yaw 0, pitch 0**. Focal 28 mm.
  - F0: floor 0.79 + capsule half height 88 + camera 64. `BaseEyeHeight` is measured from the capsule centre, so the old "floor + `BaseEyeHeight`" would be wrong.
- **Pose A is a crane-down start, 500 cm straight above B: (−2800, 0, 652.79), yaw 0, pitch +6°.** Focal 30 mm. The move from A to B is purely vertical: X, Y and yaw stay fixed, and only Z, pitch and focal length are keyed.
- **Why not "350 cm back and 80 up"** (the F0 data plus the lead's read-only traces in `Docs/ArtTest/cine/p17_f0_lead_checks.json`):
  - the spawn is 145 cm from the face of the west cliff (`KA_CliffW_00/01`, X −3245…−2945, Z 0…600), so a camera 350 cm back would sit inside it;
  - from the spawn eye, only the spire tip (`FX_StrikeTarget_Tower`, elevation 16.9°) clears the approach's north cliff (`KA_CliffN_03/04`, Z 600);
  - the belfry (Z 3000–3600) is visible from 250 cm above the eye and higher.
- **What the move shows:**
  - From A, the whole tower is visible over the cliff tops.
  - At the strike (17.0 s, camera at about Z 606), the tower is still in view.
  - As the camera passes about Z 400 (around 20 s), the belfry sinks behind the north cliff, and only the spire is left by 27.0.
  - With the 16:9 DSLR filmback, the vertical half-angle is about 18.6° at 30 mm, so the spire (elevation 15–17°, yaw +7.4°) stays in frame for the whole move.

### 3.2 Finale: `LS_LB_Finale` (30 fps, playback 0–150.0 s)
Already sounding from the tags, with no markers needed:
- the Finale beat, stage 5 × 5 at 0, 2, 4, 6 and 8 s;
- the storm's Finale strikes at 0.3 and 1.1 s.

**Timeline:**

| Time (s) | Track or marker |
|---|---|
| 0.0 | `mark:LB_Cine_FinaleMark,1.5` (GrantOnStart has already added Stage 6) |
| 1.6 | `lock:Look` |
| 12.0 | Audio on `Snd_Base` (spawnable `TargetPoint` at **(12165, 1665, 100)**, the tower base, F0): `SFX_LB_Warden_Step_01` + `SFX_LB_Warden_Chain_01`, then 0.9 s later `SFX_LB_Warden_Step_02` + `SFX_LB_Warden_Chain_02` |
| 18.0 | `bell:5x1` |
| 21.5–23.5 | Glimpse G1, **sound-only** (F0: no stair point 6–15 m below the mark's eye is in sight). `flash:0.9` at 22.0. At 22.3, on `Snd_Low` (spawnable `TargetPoint` at **(12165, 2195, 1009.1)**, `WP_TowerStairs_08` + 100): `SFX_LB_Warden_Step_03` + `SFX_LB_Warden_Chain_03`. The figure stays hidden |
| 28.0 | Audio on `Snd_Mid` (spawnable `TargetPoint` at **(12165, 1770, 1690.9)**, `WP_TowerStairs_15` + 100): `SFX_LB_Step_Wood_01`, `_02`, `_03` at pitch 0.7, 1.4 s apart |
| 30.0 | The figure (hidden) is placed at **`WP_TowerStairs_18` (12695, 2335, 2045.45)**, the top of F09, facing `WP_TowerStairs_19` |
| 36.0 | `bell:5x1` |
| 38.5 | `look:LB_Cine_StairTop,1.5` |
| 40.0–42.0 | Glimpse G2, **sound-only** (F0: no stair point 3–6 m below the eye is in sight). `flash:1.0` at 40.3. At 40.6, on the hidden figure's binding: `SFX_LB_Warden_Step_04` + `SFX_LB_Warden_Chain_04` |
| 46.0 (nominal; see the arrival row) | The hidden figure starts walking at 110 cm/s: `WP_TowerStairs_18` → `_19` → `_20` → `_21` → the centre of `Stair_F11_00` (12695, 1665, 2288.96). That is 870.5 cm, 7.9 s. The steps begin on the figure's binding, one per stride (150 cm at 110 cm/s, about 1.36 s): `SFX_LB_Step_Wood_01…06` in turn at pitch 0.7, plus `SFX_LB_Warden_Chain_01…04` in turn on every second stride. `SFX_LB_Warden_Breath_Heavy` (loop, 3D) starts on the figure |
| 54.0 | `bell:5x1` |
| 53.9 | The figure becomes visible at `Stair_F11_00` and climbs F11 at 110 cm/s. The path is `Stair_F11_13` centre (12305, 1665, 2500), then the `CINE_StairTop` floor point (12165, 1665, 2500), reached at 59.2. The player can see only F11's upper half (from `Stair_F11_07`) and the top slab (F0) |
| 57.0 | `look:LB_Cine_StairTop,1.2` |
| 59.2 → 64.1 | It turns north over 0.5 s and walks to the stop point **(12165, 2200, 2500)** (`StopDistance` 100 in front of the mark; P17-3 measures the clip's reach), facing the mark (yaw +90). F0: the lane is clear (±42 cm at floor + 20/110/200). The visible path from `Stair_F11_00` is 1118.4 cm, 10.2 s. **The arrival is fixed at 64.1.** P17-5a builds the path with the final `StopDistance`, back-computes the hidden walk's start (64.1 − total length / 110; nominal 46.0), and switches the figure visible when it reaches `Stair_F11_00` |
| 62.5 | `look:LB_Cine_Warden,1.0` |
| 64.5 | `lock:Full` |
| 65.0 | Camera cut to `Cam_Mask` (ease-in 0.8 s from the player's camera). `Cam_Mask` sits at the mark's eye, aimed at the figure's `mask` socket. Focal 35 mm, manual focus 100 → 60 cm |
| 65.5 | `AN_Warden_MaskLift` section on `WardenFigure` (slot `DefaultSlot`, blend in 0.3). Its key times (grip, lifted, extended) come from P17-3. At **grip**: the SK mask slot's `Fade` goes 1 → 0 within one frame; `SM_LB_WardenMask` becomes visible and its attach moves from bone `head` to the right-hand bone (Keep World); the hood void (if F0b needs it) becomes visible. **Lifted → extended:** the mask's `TellGlow` ramps 0 → 0.6 |
| Extended + 0.3 (nominal 72.0) | Fade 0 → 1 over 0.3 s. The figure's breath loop stops. Audio (2D): the mask meeting the face, `SFX_LB_Step_Metal_02` at pitch 0.55 layered with `SFX_LB_Warden_Chain_02` at pitch 0.7; then `SFX_LB_Warden_Breath_Slow` (loop) as the player's own breathing, until 92.0 (the owner judges the choice of cues in P17-7) |
| 75.0 | Camera cut to `Cam_WallTop`, with post-process blendable `MI_LB_PP_MaskView` at weight 1. Fade 1 → 0 over 2.0 s |
| 76.0–90.0 | `Lantern` (spawnable `PointLight`) walks along the gate axis from **(−600, 0, 110.88)** on the approach, through the passage, to **(250, 0, 110.53)** just inside the courtyard mouth. That is 850 cm, about 61 cm/s, a slow walk. Transform keys at 76.0 (linear) and 90.0 (cubic), so it slows into the stop. Bob ±3 cm at 1.1 Hz; intensity flicker ±8 % at 6 Hz (seeded keys). The lead's traces: the wall-top eye sees all 9 rays to every point from X −600 to 300; X −700 gives 6 of 9 and X −900 gives none |
| 86.0 | `bell:5x1` (heard from the tower, 64 m away) |
| 90.0 | `mix:on` (Ambience, SFX and Voice fade to 0 over 4 s) |
| 91.0 | Fade 0 → 1 over 2.0 s; the breath loop stops at 92.0 |
| 94.0 | `card:End_1` |
| 100.0 | `card:End_2` |
| 104.0 | Audio (2D) `MUS_LB_Drone_C` from 104.0 to 149.0, fade in 3 s and out 4 s |
| 106.0 | `skip:1`, then `credits:40` |
| 147.0 | `!end` |
| 150.0 | Playback end (normally unreached, because the travel starts at 147.0) |

**Spawnables:**
- **`WardenFigure`** (`SkeletalMeshActor`):
  - `SK_Warden` with `AnimClass` `ABP_Warden_C`, so locomotion, stoop, foot IK and robe physics come from the ABP; `ULBWardenAnimInstance` takes the speed from the location delta.
  - Collision NoCollision, cast shadow on, actor tag `LB_Cine_Warden`, `VisibilityBasedAnimTickOption` `AlwaysTickPose`.
  - Tracks: Transform, Visibility, Skeletal Animation, Component Material Parameter (mask slot `Fade`), and Audio (steps, breath).
  - Yaw follows the travel direction. Corners turn over at least 0.5 s while moving, so the turn-on-the-spot montages don't fire.
- **`MaskProp`** (`StaticMeshActor`): `SM_LB_WardenMask`, NoCollision; Attach, Visibility and Material Parameter (`TellGlow`) tracks.
- **`HoodVoid`** (`StaticMeshActor`): only if F0b needs it (section 4.2); attached to `head`.
- **Cameras:** `Cam_Mask` and `Cam_WallTop` (`CineCameraActor`, same filmback as `Cam_Intro`).
  - `Cam_WallTop` sits at the `Apparition_Courtyard` station (6020, 1300) at wall-top Z + 232. F0 measures the wall top; the nominal Z is 1032.
  - F0: the wall top is Z 800, so the camera is at **(6020, 1300, 1032)**. It aims at the gate passage centre (150, 0, 200): **yaw −167.51°, pitch −7.88°**, 6069.5 cm away. All 9 rays to the passage mouth are clear.
  - Focal 35 mm, manual focus 5800 cm.
- **`Lantern`** (`PointLight`): 600 lm, colour (255, 150, 70), radius 650, source radius 2, shadows on. The owner tunes the intensity in P17-7 (300–1500).
- **`Snd_Base`, `Snd_Low`, `Snd_Mid`:** `TargetPoint` spawnables (a scene root for 3D audio) at (12165, 1665, 100), (12165, 2195, 1009.1) and (12165, 1770, 1690.9). The sound climbs: the base at 12.0, about Z 1000 at 22.3, about Z 1700 at 28.0, the hidden figure at Z 2045 from 40.6, then the figure itself.

**Glimpses G1 and G2** followed the F0 sight-line rule (section 7, item 5). **Neither qualified** on any mark candidate: the belfry floor and the core hide every flight below F11, and every point in sight has a drop of at most 4.4 cm (drop = eye Z − (point Z + 245)), far short of the 3 m that G2 needs. Both are sound-only, as the rows above say. The owner judges this in P17-7. The traces see greybox collision only, so the art's open risers could show more than this. No new geometry.

### 3.3 Cards and styles (`DA_Cinematics.Cards`)
| Id | Text | Style | Hold (s) | Fade (s) |
|---|---|---|---|---|
| Intro_1…4 | Section 3.1 | Line | 2.4 | 0.3 |
| Title | THE LAST BELL | Title | 3.5 | 0.8 |
| End_1 | The bell rings for you. | Line | 3.5 | 0.8 |
| End_2 | THE LAST BELL | Title | 4.0 | 0.8 |

## 4. Assets
| Asset | Path | Made by | Notes |
|---|---|---|---|
| `LS_LB_Intro`, `LS_LB_Finale` | `/Game/LastBell/Cinematics/` | `Tools/cine/p17_sequences.py` (route from S1) | Built once. **Never rebuilt over the owner's edits:** the script refuses to overwrite unless `--rebuild` is given, and `--check` validates the invariants (section 8) |
| `DA_Cinematics` | `/Game/LastBell/Data/` | `Tools/cine/p17_assets.py` (headless) | Rows, cards and credits as above |
| `SMX_LB_CineFade` | `/Game/LastBell/Audio/Mix/` | `Tools/cine/p17_assets.py` (headless) | `SoundClassEffects`: `SCL_LB_Ambience`, `SCL_LB_SFX`, `SCL_LB_Voice` at `VolumeAdjuster` 0.0; `FadeInTime` 4.0, `FadeOutTime` 1.0, `Duration` −1, EQ off |
| `SM_LB_WardenMask` | `/Game/LastBell/Characters/Warden/Cine/` | technical-artist (Blender headless, from `SourceArt/Warden/V5_5w2/Warden_Rigged.blend`) | The mask faces only. Pivot = the `head` bone's bind transform, axes as the SK import (Force Front X), so attaching it to `head` with a zero offset matches the skinned mask. `MI_Warden_BellMetal`; Nanite off; no collision |
| `SM_LB_WardenHoodVoid` (conditional) | same | technical-artist | Section 4.2 |
| `M_LB_Void` (conditional) | `/Game/LastBell/Materials/Master/` | technical-artist | Unlit, opaque, emissive 0 (pure black) |
| `AN_Warden_MaskLift` | `/Game/LastBell/Characters/Warden/Anims/` | animation-specialist | Section 4.1. A Mixamo-derived clip is **git-ignored before its first commit** |
| `M_LB_PP_MaskView`, `MI_LB_PP_MaskView` | `/Game/LastBell/Materials/PostProcess/` | technical-artist | Section 4.3 |
| Source files | `SourceArt/Warden/P17/` | technical-artist and animation-specialist | `.blend` and FBX for the mask, the void and a Blender-keyed clip (committed); Mixamo FBX stay in `ExternalAssets/Incoming/mixamo/p17/` (ignored) |

### 4.1 The mask-lift clip
1. **A1, the owner (about 15 min):** on Mixamo with the **Y Bot**, search in this order:
   - "take off hat", "putting on hat", "helmet", "taking off", "put on", "remove";
   - "reaching out", "offering", "picking up".

   Download 2–3 clips in which **both hands go to the face or head, lift something off, and bring it forward**. Use the P13 settings: FBX Binary, With Skin, 30 fps, keyframe reduction none, In Place when offered. Save them as `ExternalAssets/Incoming/mixamo/p17/MX_<Name>.fbx`.
2. **P17-3, the animation-specialist:** retarget each clip with the P13 pipeline (`Tools/warden/p13_import.py` and `p13_retarget.py` patterns) to `AN_Warden_MaskLift_<Name>`. Add the `.gitignore` lines **first**. Measure each:
   - (a) at the grip frame, each hand bone is within 8 cm of the mask's left and right rim points, after at most a constant additive offset applied in Blender;
   - (b) `root` carries the same constant −90° yaw key as the other Mixamo clips (P13 "Facing"), so blending in from the ABP doesn't turn the body;
   - (c) a contact sheet of 5 key frames shows no arm through the hood or robe: `Docs/ArtTest/cine/p17_masklift_<name>.png`;
   - (d) the hand reach at the extended frame, which sets `StopDistance` = reach − 20 cm.

   The best passing clip becomes `AN_Warden_MaskLift`, and the table of grip, lifted, extended and length goes to the plan's Results.
3. **Fallback if none passes:** a Blender-keyed clip on the V5_5w2 rig, written to `SourceArt/Warden/P17/Warden_MaskLift.blend`. It is the project's own work, so it is committed. 6.0 s at 30 fps:
   - 0–1.5 s from the Idle frame-0 pose, the hands rise to the mask rims (IK targets);
   - 1.5–2.2 grip;
   - 2.2–3.4 lift forward and up 25 cm;
   - 3.4–4.6 lean and extend both arms forward at the player's eye height (from F0);
   - 4.6–6.0 hold.

   `root` gets the same constant −90° yaw key. The same measurements (a)–(d) apply.

### 4.2 Under the mask (decided from F0b)
- **If F0b's mask-off render shows only the dark hood interior:** nothing is added.
- **If skin or face geometry shows:** add `SM_LB_WardenHoodVoid`:
  - a concave disc that follows the mask's outline shrunk by 5 %;
  - it sits 4 cm behind the mask's inner surface and is 100 % on `head`, with the same pivot rule as the mask;
  - material `M_LB_Void`;
  - visible from the grip frame on.

### 4.3 `M_LB_PP_MaskView` (post-process, `BL_BeforeTonemapping` off, `BL_AfterTonemapping`)
The inside of a mask seen from the wearer: one fused binocular opening.

| Parameter | Value |
|---|---|
| Opening | The union of two soft ellipses centred at UV (0.40, 0.50) and (0.60, 0.50), radii (0.17, 0.085) with the aspect corrected, feather 0.06 |
| Nose bridge | A vertical band x 0.485–0.515 at alpha 0.35 |
| Outside the opening | Scene × 0.03 (`Darkness` 0.97) |
| Edge tint | The opening's feather band multiplied by (1.0, 0.55, 0.40) at strength 0.15 (`EdgeTint`), as the bronze edge catches light |
| Breath | `Breath` 0.02: the radii pulse ±2 % at 0.25 Hz |

All are scalar or vector parameters. The owner tunes them in P17-7.

## 5. Level edits (P17-5b, environment-designer [EDITOR], `Tools/cine/p17_level.py --apply/--check/--save`, Outliner folder `Cinematics`)
| Actor | Class | Placement | Tags |
|---|---|---|---|
| `CINE_FinaleMark` | `TargetPoint` | **(12165, 2300, 2500), yaw −90** (F0 mark M1: the most visible stair points, clearance 125.4 cm; M2 failed at 79.7 cm). It stands at the old `EndingTrigger`'s XY | `LB_Cine_FinaleMark` |
| `CINE_StairTop` | `TargetPoint` | **(12165, 1665, 2730)**: `WP_TowerStairs_23` (the F11 arrival on the top slab) + 230 cm head height (F0 reading B) | `LB_Cine_StairTop` |
| `Bell` (existing) | `BP_TagInteractable_GreatBell` instance | Unchanged. F0: its component `Mesh` is already **Movable**, so `--apply` doesn't touch mobility and `--check` verifies it | add `LB_Cine_Bell` |
| `TWA_Headstock` (existing, `StaticMeshActor_1498`) | `StaticMeshActor` | Unchanged transform; its `StaticMeshComponent0` mobility **Static → Movable** (section 2.8) | add `LB_Cine_BellHeadstock` |
| `TWA_BellRope` (existing, `StaticMeshActor_1499`) | `StaticMeshActor` | Unchanged transform; its `StaticMeshComponent0` mobility **Static → Movable** (section 2.8) | add `LB_Cine_BellRope` |
| `Note_Gatehouse` (existing, `BP_Inspectable_Note_C` instance) | — | Unchanged transform. Set `bodyText` on the actor **and** on its `InspectableComp` (F0: they hold identical copies) to the text below. Only the placed instance changes; the never-save `BP_Inspectable_Note` asset is not touched | — |
| `EndingTrigger` (existing) | `BP_EndingTrigger` | **Deleted from the level.** The Blueprint asset and `WBP_Ending` are left untouched and unused; deleting them is offered at review | — |

- **`Note_Gatehouse` text** (owner, 2026-11-10; only "has no rope and no clapper" → "no living hand has rung" changes). `displayName` stays "A Traveller's Note":

  > I came up the cliff path at dusk and heard it before I saw the tower. One toll, slow, from a bell the villagers swear no living hand has rung. They say it rings only for the one who is meant to hear it. I wrote this by the gate, and I am no longer sure I will leave by it.

- `LB_StrikeTarget_Tower` exists exactly once (F0: `FX_StrikeTarget_Tower` at (12530.8, 2000, 4844.8)); `--check` re-verifies it.
- **Census:** +2 actors, −1: 3102 → 3103. Then one map save.
- `--check`:
  - the tags are unique;
  - the mark is on the floor (a downward trace within 2 cm);
  - a capsule sweep (r 42, h 110) from `CINE_StairTop` to the stop point (12165, 2200, 2500) is clear. r 42 is the Warden figure's size; the player's capsule is r 34 (F0);
  - the bell's `Mesh`, `TWA_Headstock` and `TWA_BellRope` are Movable;
  - `EndingTrigger` is absent;
  - `Note_Gatehouse` `bodyText`, on both the actor and `InspectableComp`, equals the text above exactly.

## 6. Credits (`Tools/cine/make_credits.py`, run in P17-2; output `Docs/plans/p17_credits.json` and `Docs/ArtTest/cine/credits_preview.md`)
**Fixed lines, in order:**

| Style | Text |
|---|---|
| Heading | THE LAST BELL |
| Gap | |
| Small / Name | Created by / Hemant Singh Sisodia |
| Gap | |
| Small / Name | Developed with / Claude (Anthropic) |
| Gap | |
| Small / Name / Name | Made with / Unreal Engine 5 / Blender |
| Gap | |
| Small / Name | Warden base model / Generated with Tencent Hunyuan3D-2 mini, via Modly |
| Gap | |
| Small / Name | Animation / Adobe Mixamo |

**Generated from `Docs/ASSET_REGISTRY.md`:**
- **Headings:** `Models and textures` and `Sound`.
- **Each provider is one Name line:** "Poly Haven: …", "ambientCG", "Fab: <author list>", "Kenney", "Freesound: …". Authors are de-duplicated, sorted and comma-joined; a line over 90 characters wraps into several Name lines.
- **Excluded:** in-house, project-generated, the owner's own build and Epic template rows.
- **Then:** `Fonts` / "Roboto, Christian Robertson (Apache 2.0)", a Gap, and the Name line "Thank you for playing."
- **The owner reviews `credits_preview.md` in P17-6.**

## 7. F0: read-only survey (environment-designer, Sonnet high; Unreal open, PIE off; `Tools/cine/p17_f0_survey.py` → `Docs/ArtTest/cine/p17_f0.json` + `p17_f0_tables.md`; nothing set or saved; the census is unchanged)
1. **MCP:** every toolset name. For any Sequencer, LevelSequence, Movie, Widget or UMG toolset, its tool list.
2. **Spawn and the player:**
   - `PlayerStart` transform and the `CP_Approach` box;
   - from the `BP_LBCharacter` CDO: capsule radius and half height, `BaseEyeHeight`, and the camera component's relative location;
   - the exact player eye at spawn.
3. **The gatehouse:**
   - actors with bounds intersecting X −600…600, Y −500…500 (label, class, bounds), including the arch, the passage roof, `Light_Gatehouse` and `Trig_CourtyardEntered`;
   - the walkable passage centreline;
   - the lantern start and stop points: 50 cm inside each end of the roofed passage, at Z floor + 110.
4. **Wall top and tower:**
   - the `Apparition_Courtyard` station and the wall-top Z under it (a downward trace from (6020, 1300, 1500));
   - from that eye: the visibility of the passage mouth (9 rays), and the yaw and pitch to the passage centre at Z 200.
   - Every actor with a tag starting `LB_StrikeTarget_`.
   - **The bell:** components (name, class, mobility, relative transform); the headstock actor (`TWA_BellHeadstock` or the like) with its rotation and long axis; the swing axis as Pitch or Roll in the component's space.
   - **Tower top:**
     - `Top_Slab_W/N`, `Top_Rail_E/S`, `Trig_TowerTop`, `CP_TowerTop` and `Tw_Landing_06..10` (bounds);
     - `Stair_F09_*…F11_*` step boxes;
     - `WP_TowerStairs_00..24` locations.
   - **`EndingTrigger`:** class, location, `EndingSeconds`.
5. **Sight lines:**
   - **Mark candidates** (Z 2500, yaw −90 toward `CINE_StairTop`): M1 (12165, 2300), M2 (12165, 2380), M3 (12230, 2300). Each needs at least 60 cm clearance from walls, rails and the bell frame (capsule overlap).
   - **Samples:** from each eye, 9 rays to a 60 × 60 × 100 box at Z +200…+290 above the step, at points every 50 cm along `WP_TowerStairs_14…24` and the landing centres 6–10.
   - **Report:** the visible fraction per sample.
   - **Lead rule:**
     - pick the mark with the most visible samples;
     - G1 is the visible sample (fraction ≥ 0.6) between 6 and 15 m below the eye;
     - G2 is the visible sample between 3 and 6 m below;
     - `Snd_Base` goes at the tower base centre of the ring, Z 100, and `Snd_Mid` at the G2 point.
   - **Also:** the walk path length from the F11 start to the stop point along the WalkPath points.
6. **Warden:**
   - `SK_Warden` material slots: index, name, material and parent;
   - for each, whether the material has scalar `Fade` (and its blend mode) and scalar `TellGlow`;
   - skeleton bone names for the hands and the head, and the `mask` socket transform.

   If the mask slot has no `Fade`, record it: P17-5a then uses a material switch to `M_LB_Invisible` (masked, opacity 0, made in P17-3).
7. **The six notes:** `DisplayName` and `BodyText` verbatim, so the lead can check that the intro and ending fit the story. Any mismatch goes to the owner before P17-5.

**F0b (technical-artist, Blender headless, read-only; nothing saved).** Open `SourceArt/Warden/V5_5w2/Warden_Rigged.blend`:
- list the mesh objects and the material slots;
- find the mask faces (the bell-metal slot) and their vertex weights: the bones and the largest share;
- give the mask bounds in `head` bone space;
- render two neutral-lit head views to `Docs/ArtTest/cine/p17_f0b_mask_on.png` and `p17_f0b_mask_off.png` (mask faces hidden);
- report what is under the mask.

If the mask faces are not 100 % on `head`, report the largest other weight. P17-3 then rigid-binds the SM to `head` anyway, but checks the swap in-engine.

## 8. S1: Sequencer authoring spike (animation-specialist, Sonnet high; Unreal **closed**, headless Python; then S1b with Unreal open)
**S1a.** `Tools/cine/p17_s1_spike.py` builds `/Game/LastBell/ArtTest/P17/LS_P17_Spike` (10 s, 30 fps) with:
- a spawnable `CineCameraActor`, plus a camera cut section with ease-in, ease-out and `bCanBlend`;
- a spawnable `SkeletalMeshActor` (`SK_Warden`, `ABP_Warden_C`) with:
  - a 2-key transform track;
  - a visibility track;
  - a skeletal animation section (`AN_Warden_LookAround`, slot `DefaultSlot`);
  - a component material parameter track on the F0 mask slot (`Fade`);
- a spawnable `StaticMeshActor` (engine cube) with an attach track: section 1 to bone `head`, section 2 to the right-hand bone with Keep World;
- a spawnable `PointLight` with an intensity track;
- one 2D audio section, and one on the skeletal binding;
- a fade track;
- three marked frames labelled `tag:State.Test.A`, `!lock:None` and `bell:1x1`.

It saves, reloads and reads back every item, then writes `Docs/ArtTest/cine/p17_s1.json` listing, per item, "scripted OK", "needs MCP" or "needs manual editor step".

**S1a result (2026-11-10, 5ac14db; `Docs/ArtTest/cine/p17_s1.json`).** 87 of the 88 read-back checks pass after a fresh-process reload. Scripted OK:
- the spawnable camera (filmback 16:9 DSLR = 36 × 20.25 mm) and the camera cut section with its eases;
- the Warden spawnable (mesh, anim class, tag, `AlwaysTickPose`), with its transform, visibility, slot animation, and component material `Fade` tracks;
- the cube's attach track (`head`, then `hand_r` with Keep World);
- the light intensity track;
- 2D audio and audio on a binding;
- the fade track;
- the three marked frames.

The one failure is the camera cut track's `bCanBlend`, which Python can't set. Without it, `SupportsEasing` returns None and `RearrangeAllSections` strips the eases, so the cut back to gameplay would be hard. **Lead decision:** P17-1 adds `ULBCineAuthoringLibrary` (section 2), and S1a is re-run with it after the P17-1 build, before S1b. This is a third route beside MCP and an owner step. MCP doesn't cover `bCanBlend` either.

**Facts for P17-5a** (the full list is in the JSON `findings`):
- **Time units:**
  - channel `add_key` uses display frames;
  - `set_ease_in_duration` and `set_ease_out_duration` take ticks (24000 per second);
  - `add_scalar_parameter_key` takes ticks;
  - `set_range_seconds` takes seconds.
- **Spawnables:** `LevelSequence.add_spawnable_from_class` is deprecated but is the call that works headless.
- **Component tracks** (material, light intensity) need a component possessable. To get one: spawn through a `LevelSequencePlayer` in the commandlet's editor world, find the live component, then `add_possessable(<component>)`.
- **Order:** set `bCanBlend` **before** adding camera cut sections and eases.
- **Light:** the `PointLight` template defaults to Unitless intensity, so set `intensity_units` to Lumens for the Lantern's 600 lm.
- **Mask slot (provisional):** the current `SK_Warden`'s mask slot is index 1, `M_Warden_BellMetal`. The bones are `head` and `hand_r`. F0 item 6 re-checks both on the new Warden asset.

**S1b** (after P17-1, Unreal open, **owner present about 5 min**):
- `lb.Cine.Play` is pointed at the spike through a test-only def (`OverrideSettings` via a console helper `lb.Cine.PlayAsset <path>`, non-shipping);
- in PIE, the log shows the three markers firing in order;
- the camera blends in and out;
- the figure animates in the slot without turning.

**Decision:** whatever passes is scripted in P17-5a. For each failing item, the lead picks MCP or a short guided step for the owner in the Sequencer UI, written out step by step in the P17-5 brief.

**F0 result:** MCP has Sequencer authoring: `animation_toolset.toolsets.sequencer.SequencerTools`, with 140 tools.
- Its tools include `create_level_sequence`, `add_spawnable_from_class`, `create_camera`, `add_track_to_binding`, `add_section`, `set_camera_cut_binding`, `add_marked_frame` and `add_event_trigger_section`.
- There are also keyframing, outliner, condition, custom-binding, import/export and Control Rig toolsets; the tool lists are in `Docs/ArtTest/cine/p17_f0_tables.md`.
- MCP has no general editor Python: `ProgrammaticToolset.execute_tool_script` is a sandbox that only calls other tools.

The headless Python spike S1a stays the primary route, because it is repeatable with `--rebuild` and needs no open editor. MCP `SequencerTools`, with Unreal open, is the first fallback for any S1a item that fails, before an owner UI step. If camera blending back to gameplay or marker reading fails, stop and report to the owner (the architecture depends on them).

## 9. Owner sessions
| Session | Length | What | How |
|---|---|---|---|
| A1 | ~15 min | Mixamo downloads (section 4.1) | Browser; the owner's own account |
| S1b | ~5 min | Spike playback | Unreal in front |
| P17-6 | ~15 min | Intro review: text, framing, pacing, the handover to the player's view, skip; credit list preview | Press Play on `L_Monastery`. Changes are made live: the owner in Sequencer, or the lead over MCP or Python. **The owner saves only the `LS_` asset (Ctrl+S in the sequence editor), never Save All** |
| P17-7 | ~25–30 min | Finale review: mark, glimpses, approach, mask lift, void, through-mask shot, lantern, end cards, credits, bell swing everywhere (veto or keep) | `lb.Checkpoint.Load` at `CP_TowerTop`, ring the bell. `lb.Cine.NoEnd 1` for repeats; `lb.Cine.Play Finale` to repeat without a reload |
| P17-8 | ~15 min | Play-through: New Game from the menu (intro), Continue (no intro), then from `CP_TowerBase` to the menu | Packaged-like flow in PIE (New Window) |

## 10. Tests
- **Unit** (`Source/LastBellTests/Tests/LBCinematicTests.cpp`, `LastBell.Cine.*`):
  - `ParseMarkers`: every kind, `!`, every error case;
  - `MarkersCrossing`: rates 0.5, 1 and 8; several markers in one tick; no repeat; a backward jump fires nothing;
  - `SkipFiresMustOnce`;
  - `EaseAndYaw`;
  - `BellPendulum`: a kick, decay, the clamp, the stop threshold;
  - `BellAxle`, with the F0 values (pivot (12420, 2000, 2880), axis +Y):
    - `SwingAboutAxle` keeps the pivot fixed, and at 0° gives the rest transform back exactly;
    - at 16° the bell origin (12420, 2000, 2860) moves 20·sin 16° ≈ 5.5 cm in X;
    - `RopeZAboutAxle` changes only Z, by about ±36 cm at ±16° for the rope top (12550, 1835, 2750);
  - `CreditsSpeed`;
  - `CameraCutCanBlendHelper`: on a transient sequence's camera cut track, set to true and read back true; a null track returns false;
  - `Warden.Stage6IsDormant`.
- **Functional** (`LBCinematicFunctionalTests.cpp`, `LastBell.Functional.Cine.*`, on `L_Monastery` unless noted; `lb.Cine.Rate 8`):
  - `IntroOnNewGame`: `StartNewGame`; the intro starts; lock Full; HUD hidden; Arrival set once; lock None at the end; the view is the player's camera.
  - `NoIntroOnContinue`: a save with Arrival, then Continue: no intro and no stage-1 toll request.
  - `IntroSkip`: hold for 1.0 s at 2 s; Arrival set once; lock None; the camera fade is back to 0 within 1 s.
  - `FinaleOnBell`:
    - add `State.Event.Finale`; Stage 6 is present and the Warden brain is Dormant;
    - the lock goes Look, then Full; the pawn is within 5 cm of the mark;
    - `lb.Cine.Skip` in the credits; `CompleteGame` travels to `L_MainMenu`;
    - the save is gone.
  - `NoCheckpointDuringCinematic`.
  - `BellSwingsOnStrike`: `PlayBell(5,1)`, at rate 1:
    - within 0.5 s, the bell component rotates by more than 2°, the headstock actor by the same angle (±0.1°), and the rope moves in Z only (X and Y within 0.1 cm);
    - after 20 s all three are back within 0.5° and 0.5 cm of rest.
  - `DisabledByCVar`: no intro; a running one stops and restores.
  - `MissingSequenceFailsSafe`: an override def with a bad path; must markers fire; lock None.
  - `Monastery.CinematicSetup`:
    - the tagged actors exist once each (`LB_Cine_FinaleMark`, `LB_Cine_StairTop`, `LB_Cine_Bell`, `LB_Cine_BellHeadstock`, `LB_Cine_BellRope`), and the last three are Movable;
    - `EndingTrigger` is absent;
    - `DA_Cinematics` loads;
    - both sequences load, every marker parses, and the must markers listed in 3.1 and 3.2 are present;
    - the finale has a camera cut track.
- **Audio** (`LBAudioFunctionalTests.cpp`): `ArrivalBeat` (the Arrival tag gives stage 1 × 3 with the first strike at once) and `GreatBellStrikeDelegate`.
- **Updated:**
  - `RouteBot.Monastery`: rate 8; waits for the intro to finish before driving; after the ring, skips once the credits are skippable; expects `L_MainMenu` within 60 s of the ring. The `EndingSeconds` reflection helper goes.
  - Every other functional test that opens `L_Monastery` constructs `LBPie::FCineSwitch(false)` (new, beside `FWardenSwitch` in `LBRouteBot.h`) before `StartPie`. `MenuFlow` decides per test and records why.
  - The Warden stage sweeps (section 2.5).
- **Target:** the full suite passes; the count is reported. The Game target builds.

## 11. Tasks
| Task | Scope | Agent | Needs | Depends on |
|---|---|---|---|---|
| P17-0 | **Plan approval.** DECISIONS D-114 (scope and owner choices), D-115 (architecture: Sequencer visuals, labelled markers, `ULBCinematicSubsystem`; owner's choice over a C++-only director), D-116 (stage 6 = scripted finale, AI dormant), D-117 (the ending flow replaces `EndingTrigger`; the widget is built in C++; Phase 18 restyles), D-118 (credits content). RISKS R-78…R-84 and R-77 updated. `IMPLEMENTATION_PLAN` Phase 17 table. `GAME_DESIGN` open question resolved | lead | — | owner "approve" |
| F0 | Section 7 | environment-designer [EDITOR read-only] | Unreal open | P17-0 |
| F0b | Section 7 F0b | technical-artist | Blender | P17-0 |
| A1 | Section 4.1 step 1 | **owner** | — | P17-0 |
| S1a | Section 8 | animation-specialist | **Unreal closed** | F0 |
| P17-1 | Section 2 code, CVars and commands, section 10 tests; build and suite. Also adds `State.Event.Arrival` to `Config/Tags/LBGameplayTags.ini` (editor closed): `GameplayTagList=(Tag="State.Event.Arrival",DevComment="Intro played or skipped: the first toll; never repeats")`. Until P17-5b the content-dependent tests (`Monastery.CinematicSetup`, `IntroOnNewGame`, `NoIntroOnContinue`, `IntroSkip`, `FinaleOnBell`, `BellSwingsOnStrike`) are expected to fail; every other test must pass. `RouteBot.Monastery` must pass in both states: with no `DA_Cinematics` nothing plays and the old `EndingTrigger` still travels | gameplay-programmer | **Unreal closed** | P17-0 (data values come from F0 in P17-2) |
| P17-2 | `p16_2_assets.py` (Arrival row via `FillPlanDefaults`, `bNewGameToll` false in `OWNER_CHOICES`; apply, then verify). `p17_assets.py` (`DA_Cinematics` with the F0 values, including `FailSafeMarkers` per section 2.2 and `CineFadeMix` set; `SMX_LB_CineFade`). `make_credits.py`. The `DefaultGame.ini` line | gameplay-programmer (data) + audio-designer (mix) | **Unreal closed**, serial | P17-1, F0 |
| P17-3 | Mask mesh, void (if needed), `M_LB_Invisible` (if needed), the clip (4.1 steps 2–3), headless imports, `.gitignore` first | technical-artist + animation-specialist | Blender; **Unreal closed** for imports | F0b, A1, S1a |
| P17-4 | `M_LB_PP_MaskView` and its MI (route per `MCP_NOTES`) | technical-artist | as `MCP_NOTES` says | F0 |
| P17-5a | `p17_sequences.py` builds both sequences per section 3 and the S1 route; `--check` | animation-specialist | **Unreal closed** | S1a, P17-2, P17-3, P17-4 |
| S1b | Section 8 | lead + **owner** | Unreal open | P17-1 |
| P17-5b | Section 5 level edits; `--check`; one map save. Then the suite with Unreal closed | environment-designer [EDITOR] | Unreal open, then closed | P17-5a, S1b |
| P17-6 | Owner intro review (section 9) | lead + **owner** | Unreal in front | P17-5b |
| P17-7 | Owner finale review (section 9) | lead + **owner** | Unreal in front | P17-6 |
| P17-8 | QA (regression, the save and continue edges, skip spam, alt-tab, a missing clip on a fresh clone noted), the owner play-through | qa-reviewer + **owner** | | P17-7 |
| P17-9 | Docs: `TECHNICAL_DESIGN` §17 Cinematics (as built), `GAME_DESIGN` (beats 0, 1, 10, 11; ending), `AI_DESIGN` stage 6, `AUDIO_DESIGN` (Arrival beat, finale timing, cine mix), `GREYBOX_SPEC` rows 17–18, `MCP_NOTES` (Sequencer scripting), `ASSET_REGISTRY` (clip, mask, credits), `PERFORMANCE_BUDGET` note, `RISKS`, `DECISIONS`, `IMPLEMENTATION_PLAN`. Final suite with Unreal closed; Game target build; delete `ArtTest/P17` spike assets; "PHASE 17 READY FOR YOUR REVIEW" | lead + docs agent | Unreal closed | all |

**Concurrency:**
- Unreal-closed headless runs (S1a, P17-1 build and suite, P17-2, P17-3 imports, P17-5a) are strictly serial.
- Blender work (F0b, P17-3 modelling) and C++ editing run alongside them.
- A1 runs any time after approval.

## 12. Risks (added to `RISKS.md` at P17-0)
| Id | Risk | Mitigation |
|---|---|---|
| R-78 | Sequencer can't be fully authored by script (attach, slot animation, material parameter or camera-cut blending) | S1 decides per item; MCP if available; otherwise a written guided step for the owner. Stop and report if blending back to gameplay or markers fail |
| R-79 | No Mixamo clip fits: the hands miss the mask, the arms clip the hood, or the root yaw differs | Measurement gates (4.1 a–d); a Blender-keyed fallback with the matching root yaw |
| R-80 | A Mixamo-derived `AN_Warden_MaskLift` is local only, so on a fresh clone the finale plays without the lift (the figure stands, the mask still swaps and fades) | Same class as R-55; the README note; `Monastery.CinematicSetup` warns, not fails, when the clip is missing |
| R-81 | Look-only glimpses aren't seen (bad sight lines, or the player looks away) | F0 sight-line rule; look assists before G2 and the approach; sound-only fallback; the owner judges in P17-7 |
| R-82 | Functional tests on `L_Monastery` now get an intro that locks input and adds Arrival | `FCineSwitch(false)` in those tests; RouteBot plays it at 8× |
| R-83 | The SK→SM mask swap pops | Bind-space export, the head-weight check (F0b), an in-engine overlay check in P17-3; the swap happens under the hands |
| R-84 | A cinematic error leaves the player locked or the screen black | Fail-safe path (2.3), `MissingSequenceFailsSafe`, and `lb.Cine.Stop` |
| R-77 (update) | Part 1 resolved by design: the storm stays active until `CompleteGame`, and nothing pauses. Part 2 (the pause menu and bell UI sounds) stays open for Phase 18 | — |

The GPU cost of the cinematic shots is not measured in this phase (the finale close-up, the wall-top shot). It is added to the Phase 20 performance pass (a row in `PERFORMANCE_BUDGET`).

## 13. Not in this phase
- The pause menu and what it does to the bell (Phase 18). Key glyphs and rebinding in the skip prompt (Phase 18). A restyled cinematic UI and menu credits (Phase 18).
- Subtitles, voice acting, localisation, alternative endings.
- The AI Warden in the finale (it is dormant at stage 6), new geometry, a villager model, a collapsing stair.
- Movie Render Queue renders or trailers (Phase 21).
- Deleting `BP_EndingTrigger` and `WBP_Ending` (offered at review).

## Results
(Filled in as the tasks finish.)

### P17-1 (2026-11-10, e24a3ef…5f981b8)
The code in section 2 is built. The editor build is clean (no compiler warnings), and the game target built in phase A.

**Suite:** 191 passed, 5 failed (the lead checked `Saved/Logs/LBTests_All.log`), with 0 invalid tags.
- The failures are exactly the content tests expected to fail until P17-5b: `Monastery.CinematicSetup`, `IntroOnNewGame`, `IntroSkip`, `FinaleOnBell` and `BellSwingsOnStrike`.
- `RouteBot.Monastery` passes in today's state, with no `DA_Cinematics` and the old `EndingTrigger`.
- `NoIntroOnContinue` passes only because nothing plays yet, so it means something only after P17-5b.

**Additions:**
- `ULBCineAuthoringLibrary` (`bCanBlend`);
- `FLBCinematicDef.FailSafeMarkers`;
- the test `BellSwingPieces`;
- `FCineRate` beside `FCineSwitch`;
- `Slate`, `SlateCore` and `MovieSceneTracks` added as module dependencies.

**Accepted deviations,** written into sections 2.2–2.4:
- the release poll for the locked press;
- the restore with a travel pending;
- a locked pawn cancels an open inspection.

Also: `RopeZAboutAxle` is the exact rotation, giving −30.9 / +40.9 cm at ±16°, because the rope's top is 130 cm below the axle.

**Not verified yet:** the widget on screen, the skip prompt and progress bar, the credits roll, the mark move and look assist in the world, and the camera blend. These are covered by S1b, P17-6 and P17-7.

### S1a (2026-11-10, 5ac14db)
Everything scripts headless except the camera cut track's `bCanBlend`, which P17-1's `ULBCineAuthoringLibrary` sets.

**Re-run after the P17-1 build (0e5aab7):** 88 of 88 checks pass after a fresh-process reload.
- `bCanBlend` reads back true.
- The eases (1.0 s in, 1.5 s out) survive the reload, because the helper is called before the section and eases are added.
- The logs show no errors, only DeprecationWarnings. The details are in section 8. Runtime behaviour (spawning, component bindings, attach, the material fade, the blend) is for S1b. `LS_P17_Spike` is local and git-ignored, because it uses a Mixamo clip.

### F0 (2026-11-10, 6596144; lead review the same day)
Items 1–5 and 7 are done. Item 6 and F0b are on hold for the new Warden asset. The run was read-only: before and after, PIE was off and nothing was dirty (not the map, not the 14 never-save packages), and the census stayed at 3102. The lead's extra checks were also read-only (`Docs/ArtTest/cine/p17_f0_lead_checks.json`). The data is in `Docs/ArtTest/cine/p17_f0.json` and `p17_f0_tables.md`.

**Accepted values** (written into the sections above):
- **Spawn eye:** (−2800, 0, 152.79), yaw 0. The plan's formula was wrong, because `BaseEyeHeight` counts from the capsule centre.
- **Player capsule:** radius 34, half height 88.
- **Gate passage:** roofed over X 0–300, 407 cm wide, centreline Y 0.
- **Wall top:** Z 800; eye (6020, 1300, 1032); aim yaw −167.51°, pitch −7.88°.
- **Bell:**
  - its only mesh component is `Mesh`, the root, already Movable;
  - the swing axis is Pitch, with the axle at the headstock's location (12420, 2000, 2880);
  - `TWA_Headstock` and `TWA_BellRope` are Static, so P17-5b sets them Movable.
- **Mark:** M1 at (12165, 2300, 2500), yaw −90. M2 failed clearance at 79.7 cm.
- **`CINE_StairTop`:** (12165, 1665, 2730). Stop point (12165, 2200, 2500); the lane is clear. Visible path 1118.4 cm.
- **Strike target:** `FX_StrikeTarget_Tower` exists once.
- **MCP:**
  - Sequencer authoring is available (`SequencerTools`, 140 tools, plus 6 more Sequencer toolsets);
  - UMG has 23 tools;
  - there is no general editor Python.

**Lead decisions from F0:**
1. **Intro camera: a crane-down.**
   - The planned pose A (350 cm back) is inside the west cliff, and from the spawn eye the approach's north cliff hides the belfry.
   - Pose A is now 500 cm straight above the eye. The belfry is in sight from 250 cm up; the spire is in sight from every height.
2. **Glimpses G1 and G2 are sound-only.**
   - No stair point below F11 is in sight from any mark.
   - The sound climbs instead: `Snd_Base` at 12.0, `Snd_Low` at 22.3, `Snd_Mid` at 28.0, then the hidden figure from 40.6.
   - The figure first shows at `Stair_F11_00` at 53.9, rising into view on F11's upper half.
3. **Finale climb timing.**
   - The hidden walk from `WP_TowerStairs_18` starts at 46.0 (nominal), so the arrival stays at about 64.1. Every cue from 62.5 on is unchanged.
   - P17-5a back-computes the walk's start from the final `StopDistance`.
4. **Lantern path:** (−600, 0, 110.88) → (250, 0, 110.53).
   - The planned 200 cm in the roofed part over 14 s would have been a 14 cm/s crawl.
   - The wall-top eye sees the gate axis from X −600 inward.
5. **The bell swings with its headstock, and the rope follows the rim** (section 2.8). Swinging the bell alone would clip its crown through the headstock.
   - New fields `BellHeadstockTag` and `BellRopeTag`, new logic helpers, and the `BellAxle` test.
   - The bell's east rim at 16° reaches the frame's bounds edge. The owner checks it in P17-7.
6. **S1a stays headless Python.** MCP `SequencerTools` is the first fallback.
7. **`CP_Approach`** starts 50 cm east of the PlayerStart, so it saves on the first steps after the intro. No change.

**Owner decision (2026-11-10): "use both suggestions".** (a) and (b) below are accepted as recommended. Intro_1 is changed in section 3.1, and the note line is a P17-5b level edit (section 5).

**Raised to the owner:**
- **(a) Intro_1** says "For forty years no one has climbed to the monastery on the ridge." `Note_Gatehouse`, a traveller's note left at the gate, says they "came up the cliff path at dusk" and may not "leave by it".
  - **Recommended:** Intro_1 → "For forty years, no one has come back from the monastery on the ridge."
  - This keeps the traveller (who came up and never came back) and the brothers (who vanished) consistent.
  - It also makes the traveller's line "it rings only for the one who is meant to hear it" set up the ending card "The bell rings for you."
- **(b) `Note_Gatehouse`** says the villagers swear the bell "has no rope and no clapper", but a rope (`TWA_BellRope`) hangs in the belfry. `Note_Cloister` also says "no hand was on the rope".
  - **Recommended:** "…from a bell the villagers swear no living hand has rung."
  - The change is in P17-5b, on the placed instance's `bodyText` and its `InspectableComp` copy (a map edit; the never-save `BP_Inspectable_Note` asset is not touched).
  - The alternative is to keep it as unreliable village rumour.
- `Note_Cloister` fits Intro_2 and Intro_3 as written. No other mismatch.
