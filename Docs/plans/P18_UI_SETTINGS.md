# Phase 18: UI and settings

**Status:** approved by the owner on 2026-11-11 ("approved"). P18-0 done. Branch `claude/phase-18-ui`, from `main` at 95299af. The lead plans and reviews in Opus at medium effort, review agents run on `opus`/medium, and implementers run on `sonnet`/high (D-048, D-119). The standing rules are in `CLAUDE.md` and apply unchanged:
- git hygiene;
- the never-save list;
- saves one package at a time;
- no Live Coding of files that define CVars;
- one Unreal process at a time;
- the owner is present for PIE and captures.

## 0. Owner choices (2026-11-11)
| Topic | Choice |
|---|---|
| Menu look | **Live monastery view:** a text menu over a slow drifting view of the monastery in the storm; the selected item gets a candle-flicker highlight. The pause menu darkens and blurs the game behind it |
| Settings | **Full:** quality preset plus individual graphics options; resolution, window mode, VSync, frame cap; brightness; the 6 volume sliders; sensitivity, invert Y, head bob, field of view, motion blur, film grain, high-contrast prompts; key rebinding |
| Input | **Keyboard and mouse only.** Key icons show the current binding |
| Escape during a cinematic | **Pause everything:** the cinematic, its music, the bell, the storm and the scheduled audio freeze together; Resume continues where it stopped |
| Typeface | **EB Garamond** (SIL OFL 1.1), for the menus, HUD, cards and credits. The licence text ships in `Content/LastBell/Licenses/` (an asset-free folder, staged as non-UFS) and in the credits |
| Brightness | **A first-launch calibration screen** before the main menu, also reachable from Settings |

**Lead decisions** (the owner can veto them at approval):
- **The menu background is a seamless looping video** recorded from `L_Monastery` (a slow camera drift in the storm), played on a `MediaTexture` behind the menu. It looks live but costs almost nothing, and the menu map stays light.
  - **Not chosen:** streaming the real level behind the menu, because it would start the Warden, the triggers, the storm logic and the checkpoints inside the menu.
  - **If S1 can't render the video by script,** the fallback is a guided Movie Render Queue step for the owner (about 5 min); failing that, a still frame.
- **The UI is built in C++ widget trees** (no WBP), like `ULBCinematicWidget` (D-117). It is styled from one data asset, `DA_UIStyle`, and is testable and scriptable. `WBP_MainMenu` is retired.
- **R-64** (the game-thread Insights trace) **moves to Phase 20** (Performance), where it belongs.

## 1. Outcome and acceptance
1. **Main menu** (`L_MainMenu`), over the looping monastery video, with the title "THE LAST BELL" and these items:
   - **Continue:** only when a save exists.
   - **New Game:** confirms "This will erase your progress" when a save exists.
   - **Settings.**
   - **Credits:** the same roll as the ending, from `DA_Cinematics.Credits`.
   - **Quit:** confirms.

   Mouse hover and click work, and the arrow keys plus Enter work too. The selected item has the candle-flicker highlight.
2. **First launch:** before the menu, the brightness screen (a symbol "barely visible" on a dark field, a slider, Confirm). Saved as `bBrightnessCalibrated`, and never shown again unless the owner resets it from Settings.
3. **Pause** (Escape) everywhere in play: Resume; Settings; Return to main menu (confirm: "Unsaved progress since the last checkpoint will be lost"); Quit to desktop (confirm).
   - **The game is truly paused:** the world, the Warden, the storm, the audio schedule and the bell. The cinematics freeze, with their music.
   - **Escape again,** or Resume, continues exactly where it stopped.
   - **Escape while inspecting a note** closes the note first, as today. Escape is ignored during a death fade and during a level travel.
4. **Settings,** with five tabs:
   - **Graphics:**
     - an overall preset Low/Medium/High/Epic, setting all groups;
     - per-group overrides: View distance, Anti-aliasing, Shadows, Global illumination, Reflections, Post-processing, Textures, Effects, Foliage, Shading;
     - Resolution scale;
     - "Custom" is shown once a group differs from the preset.
   - **Display:**
     - Window mode: Fullscreen / Windowed fullscreen / Windowed;
     - Resolution, from the supported list;
     - VSync;
     - Frame-rate limit: 30/60/90/120/144/Unlimited;
     - Brightness, which opens the calibration screen.

     A display-mode change shows a "Keep these settings? Reverting in 15 s" dialog.
   - **Audio:** the 6 sliders (Master, SFX, Ambience, Music, Voice, UI), live.
   - **Controls:**
     - mouse sensitivity, invert Y, head bob;
     - **key rebinding** for every gameplay action: Move ×4, Sprint, Crouch, Interact, Candle, Pause. Each shows its key icon. Duplicates are rejected with a message;
     - "Reset to defaults".
   - **Accessibility:**
     - Field of view, 70–110°;
     - Motion blur on/off;
     - Film grain on/off;
     - High-contrast prompts: white on a dark plate, plus an outline;
     - "Show brightness screen at next launch".

   Every change applies live where the engine allows. Graphics and Display use Apply / Revert, the others save at once. Everything persists across a restart.
5. **Key icons everywhere a key is named:** the HUD interact prompt, the skip prompt ("Hold [E] to skip") and the rebinding list. They follow the current binding.
6. **Restyle:** the HUD prompt and objective, the cinematic cards, the credits and the skip prompt use EB Garamond and the `DA_UIStyle` colours, consistent with the menus.
7. **Loading:** menu → game and game → menu show a black loading screen with a small flickering candle and the title (the engine `MoviePlayer` loading screen, so it also works in packaged builds).
8. **UI sounds** for hover, select, back and slider ticks, on `SCL_LB_UI`; CC0.
9. **Tests:** the suite passes, including the new UI tests (section 9). The Game target builds. **R-77 part 2 and R-90 are closed.**

## 2. Architecture (C++, `Source/LastBell/UI/`, prefix `LB`)
| File | Contents |
|---|---|
| `LBUITypes.h` | `ELBScreen` {None, MainMenu, Pause, Settings, Credits, Brightness, Confirm, Loading}; `FLBConfirmRequest`; `ELBSettingsTab` |
| `LBUIStyle.{h,cpp}` | `ULBUIStyle` (`UPrimaryDataAsset`, `/Game/LastBell/UI/DA_UIStyle`):<br>• fonts: `FSlateFontInfo` built from soft refs to the EB Garamond Regular, Italic, SemiBold and Bold `UFont` assets;<br>• colours: Ink, Dim, Accent (candle amber), Plate, Danger;<br>• sizes (title 96, heading 40, item 34, body 24, small 18 at 1080p; scaled by DPI);<br>• the flicker (speed, amplitude);<br>• `KeyIcons`: `TMap<FKey, TSoftObjectPtr<UTexture2D>>`;<br>• UI sound refs;<br>• the menu video `UMediaSource` soft ref, with the fallback `UTexture2D`;<br>• the brightness symbol texture |
| `LBUISubsystem.{h,cpp}` | `ULBUISubsystem` (`ULocalPlayerSubsystem`):<br>• the **screen stack** (push/pop, focus, input mode, cursor);<br>• `OpenPause()`/`ClosePause()` with `SetGamePaused`;<br>• confirm dialogs;<br>• the first-launch brightness gate;<br>• routing Escape: the top screen handles Back; with no screen in play it opens Pause;<br>• UI sounds;<br>• the `OnPauseChanged` delegate |
| `LBMenuWidgetBase.{h,cpp}` | `ULBMenuWidgetBase` (`UUserWidget`, its tree built in `NativeOnInitialized`, like `ULBCinematicWidget`): the item list with keyboard focus, hover, the flicker highlight, Back handling and style access |
| `LBMainMenuWidget`, `LBPauseWidget`, `LBSettingsWidget` (tabs as child panels), `LBCreditsWidget` (reuses the credits layout from `ULBCinematicWidget` through a shared helper `LBCreditsLayout`), `LBBrightnessWidget`, `LBConfirmWidget`, `LBKeyIconWidget` (an image plus a text fallback for the key) | One class per screen |
| `LBLoadingScreen.{h,cpp}` | A Slate loading screen for `GetMoviePlayer()->SetupLoadingScreen` (`bAutoCompleteWhenLoadingCompletes`, a minimum of 1.0 s), armed by the save subsystem just before a menu <-> game travel and taken back by the game instance after the map has loaded (D-133) |
| `LBGraphicsSettings.{h,cpp}` | Wraps `UGameUserSettings`: scalability groups, resolution, window mode, VSync, the frame limit, resolution scale. Applies, reverts, and runs the 15 s keep timer |

**Changes to existing code:**
- **`ULBUserSettings`:** add `Gamma` (1.8–2.6, default 2.2, applied to `GEngine->DisplayGamma`), `FieldOfView` (70–110, default 90), `bMotionBlur` (false), `bFilmGrain` (true), `bHighContrastPrompts` (false) and `bBrightnessCalibrated` (false). Each has a setter that saves and broadcasts `OnUserSettingsChanged`.
- **`ALBCharacter` / `ULBCameraFeelComponent`:** apply `FieldOfView`. Motion blur and film grain are applied as overrides on the player camera's post-process settings (`MotionBlurAmount`, `FilmGrainIntensity`), with nothing changed in the level volumes.
- **`ALBPlayerController`:**
  - binds `IA_Pause`, which calls `ULBUISubsystem::HandleBack()`;
  - `SetMenuMode` now lives in `ULBUISubsystem`, kept as a forwarder;
  - the HUD prompt uses `LBKeyIconWidget`.
- **Pause and audio (closes R-77 part 2):** P17 removed the ending's pause, so P16-6's workaround is reverted:
  - `ULBAudioSubsystem::IsTickableWhenPaused` becomes false, so the schedule freezes;
  - bell strikes are no longer `bIsUISound`, so they pause with the world;
  - the music and ambience loops pause through the world-pause audio rule. Check that `bIsUISound` is false on every game sound, so paused sounds actually pause;
  - only `SCL_LB_UI` sounds play while paused.
- **Pause and cinematics (closes R-90):**
  - `ULBCinematicSubsystem` stays non-tickable when paused;
  - the level-sequence actor ticks with the world, so it freezes;
  - test that the sequence time doesn't advance while paused, and that the camera fade and widget stay put;
  - the skip-hold timer doesn't advance while paused.
- **`ULBCinematicWidget`:** restyled from `DA_UIStyle`; the skip prompt becomes "Hold [icon] to skip", using the current Interact binding.
- **Rebinding:**
  - **Engine setup:** Enhanced Input user settings (`bEnableUserSettings` in `DefaultInput.ini` `[/Script/EnhancedInput.EnhancedInputDeveloperSettings]`); `IMC_LB_Gameplay` mappings marked player-mappable, with names and display names.
  - **Rebind call:** `UEnhancedInputUserSettings::MapPlayerKey` for the rebind, saved with `SaveSettings`.
  - **Pause key:** `IA_Pause` (new, Escape) is rebindable except to the mouse buttons.
  - **Inspection keys:** `IMC_LB_Inspect` keeps fixed keys (documented).
- **Main menu:** `BP_MenuPlayerController`'s `HUDWidgetClass` becomes `ULBMainMenuWidget`, and `WBP_MainMenu` is retired: unused, deleted at review if the owner agrees.

## 3. Menu background (S1 decides)
- **Shot:** `LS_LB_MenuDrift`, built headless by the `p17_sequences` tooling.
  - A 40 s seamless loop at 30 fps.
  - A CineCamera at the courtyard edge, slowly dollying 400 cm and panning 6° across the gatehouse toward the tower, at an eye height of 250 cm.
  - The storm at its intro intensity. No Warden; the level's apparitions and Warden are hidden by a `lb.Cine.MenuShot` CVar in the capture run.
  - The first and last frames match: a ping-pong move with eased ends, so the loop is seamless.
- **S1 spike:** render it with Movie Render Queue through a headless or `-game` command line, as a PNG sequence at 1920×1080, encode to MP4 (H.264, CRF 18) with ffmpeg, then play it in the menu through `UFileMediaSource` and `UMediaPlayer` (`bLooping`) onto a `UMediaTexture`, shown in a full-screen `UImage` under a dark vignette.
  - **If MRQ can't run by script:** the owner records it from the editor (a written 5-minute guide).
  - **If media playback fails in a packaged-style build:** a still frame from the video, with a slow Ken-Burns pan in UMG.
- **Files:** the video goes in `Content/Movies/LB_MenuDrift.mp4` (the conventional folder, which packaging stages with `+DirectoriesToAlwaysStageAsNonUFS`). The source frames stay out of git.

## 4. Assets (P18-2; all CC0 except the OFL font)
| Asset | Source | Where |
|---|---|---|
| EB Garamond (Regular, Italic, SemiBold, Bold) | Google Fonts / the `octaviopardo/EBGaramond12` repository, SIL OFL 1.1 | `/Game/LastBell/UI/Fonts/` (`UFont` and `UFontFace`); the licence in `Content/LastBell/Licenses/OFL_EBGaramond.txt` |
| Keyboard and mouse key icons | Kenney "Input Prompts" (CC0) | `/Game/LastBell/UI/KeyIcons/T_Key_<Key>`: letters, digits, arrows, Shift, Ctrl, Alt, Space, Esc, Tab, Enter and the mouse buttons |
| UI sounds: hover, select, back, slider tick | Kenney "UI Audio" or "Interface Sounds" (CC0), prepped to the P16 standard | `/Game/LastBell/Audio/UI/SFX_LB_UI_*`, class `SCL_LB_UI` |
| Brightness symbol | Generated (a bell sigil in mid-grey, plus a near-black version) | `/Game/LastBell/UI/T_LB_BrightnessSymbol` |
| `DA_UIStyle` | Script | `/Game/LastBell/UI/` |
| `IA_Pause`; the IMC mapping changes | Script (headless) | `/Game/LastBell/Input/` (or the project's input folder) |
| Menu video | S1 | `Content/Movies/` |

The credits gain "Fonts / EB Garamond, Georg Duffner, Octavio Pardo and Deborah Khodanovich (SIL OFL 1.1)" (the Roboto line stays: P10-8d tablet and grave glyph outlines still carry it), plus Kenney (input prompts, UI audio). `make_credits.py` handles both through new `ASSET_REGISTRY` rows.

## 5. Tasks
| Task | Scope | Agent | Needs | Depends on |
|---|---|---|---|---|
| P18-0 | Plan approval; DECISIONS D-126 (scope and owner choices), D-127 (C++ UI framework, `DA_UIStyle`, the video background), D-128 (the pause semantics and the P16-6 revert); RISKS (R-77 part 2 and R-90 to close at the end; new risks below); R-64 moved to Phase 20; an `IMPLEMENTATION_PLAN` table | lead | — | owner "approve" |
| A1 | Download and verify: the fonts, Kenney input prompts, Kenney UI audio; registry rows | asset-curator | — | P18-0 |
| S1 | The menu-video spike (section 3) | animation-specialist | Unreal closed (headless), then a short owner check | P18-0 |
| P18-1 | The C++ in section 2, with the section 9 tests. Build and suite | gameplay-programmer | Unreal closed | P18-0 |
| P18-2 | Assets: font import, icons, UI sounds, `DA_UIStyle`, `IA_Pause` and the IMC changes, the Enhanced Input user-settings config, `BP_MenuGameMode` to the C++ menu, the menu video hookup | technical-artist + ui-engineer | Headless; MCP for `BP_MenuGameMode` | A1, S1, P18-1 |
| P18-3 | The HUD and cinematic-widget restyle; key icons in the prompts | ui-engineer | Unreal closed | P18-1, P18-2 |
| P18-4 | **Owner session 1** (about 20 min): first launch → brightness → menu look → settings tour → New Game → pause in play and during the intro → rebinding → back to the menu | lead + owner | Unreal open, PIE (standalone window) | P18-3 |
| P18-5 | Fixes from P18-4; QA (`qa-reviewer` on Opus): menu flows, every setting persisting across a restart, pause edge cases, rebinding conflicts | gameplay-programmer, qa-reviewer | | P18-4 |
| P18-6 | Docs (`TECHNICAL_DESIGN` section 18, `GAME_DESIGN` UI, `AUDIO_DESIGN` pause, `MCP_NOTES`), the final suite, the Game build, "PHASE 18 READY FOR YOUR REVIEW" | lead + docs agent | Unreal closed | P18-5 |

## 6. Settings details (P18-1)
- **Presets** use `UGameUserSettings::SetOverallScalabilityLevel(0..3)`; the groups use the individual setters. Show "Custom" when the groups differ.
- **Resolution list:** `UKismetSystemLibrary::GetSupportedFullscreenResolutions`. The windowed resolutions come from the list, clamped to the desktop size.
- **Frame cap:** `SetFrameRateLimit` (0 = unlimited). **VSync:** `SetVSyncEnabled`. Resolution scale is 50–100 %.
- **The keep dialog:** after Apply changes the window mode or the resolution, it confirms; with no confirmation within 15 s it reverts.
- **The FOV default (90) must match today's camera FOV;** read the current value and keep it as the default. `LBCameraFeel` applies it.
- **Gamma** is applied at startup by the game instance, before the brightness screen is decided.
- **Everything is stored in `GameUserSettings.ini`:** the engine's own settings plus `ULBUserSettings`. The Enhanced Input key mappings are saved by its user-settings save game.

## 7. Pause details (P18-1)
- **Not allowed** during a level travel, a death fade or a checkpoint load, or on the main menu (there Escape means Back).
- **Allowed** during cinematics, inspection (after Escape closes the note) and chases.
- **The candle and the HUD** stay as they are. The pause plate darkens to 60 % with a 6 px gaussian blur (a background blur widget).
- **On Return to main menu:** `ULBSaveSubsystem::ReturnToMainMenu()` keeps the save; the world unpauses first.
- **Focus loss:** alt-tab (the window losing focus) always opens the pause menu during play. The skip hold is cancelled on focus loss.

## 8. Risks (to `RISKS.md` at P18-0)
| Id | Risk | Mitigation |
|---|---|---|
| R-91 | The MRQ render or the media playback isn't scriptable or reliable | S1 decides; the fallbacks are an owner-guided render, then a still with a pan |
| R-92 | Enhanced Input user-settings rebinding has edge cases (duplicates, axis keys for Move, Escape) | Move is rebound as four separate keys; conflicts are rejected; tests; Reset to defaults |
| R-93 | A gamma or brightness change also brightens the UI | Accepted (the standard behaviour); the calibration screen shows the effect |
| R-94 | Reverting the P16-6 workaround could bring back "the bell silent at the ending" | The ending no longer pauses (P17); a test plays the finale beat across a pause and resume |
| R-95 | The OFL font licence must ship with the game | `OFL_EBGaramond.txt` staged from `Content/LastBell/Licenses/` and noted in the credits and the registry |

## 9. Tests (P18-1 / P18-3)
- **Unit:**
  - the settings clamps and persistence (round trip through the config);
  - preset ↔ Custom detection;
  - key-icon lookup for every gameplay key;
  - conflict detection in rebinding;
  - the brightness first-launch flag;
  - the keep-dialog revert timer (logic).
- **Functional:**
  - `UI.MainMenu.ContinueHiddenWithoutSave`;
  - `UI.MainMenu.NewGameConfirmsWhenSave`;
  - `UI.Pause.FreezesWorld`: the Warden doesn't move, the storm time doesn't advance, the audio schedule doesn't advance;
  - `UI.Pause.FreezesCinematic`: the sequence time is constant while paused, then resumes;
  - `UI.Pause.BellStopsAndResumes`: a scheduled strike plays after resume, not during the pause;
  - `UI.Pause.BlockedDuringTravelAndDeath`;
  - `UI.Pause.EscapeClosesInspectionFirst`;
  - `UI.Rebind.InteractChangesPromptAndSkip`;
  - `UI.Settings.FOVApplies`;
  - `UI.Brightness.FirstLaunchGate`;
  - `UI.Loading.ScreenShownOnTravel` (the movie player's loading flag).
- **Updated:**
  - `MenuFlow` and `MenuToGameInput` against the C++ menu;
  - `RouteBot` unaffected: it doesn't press Escape.

## 10. Not in this phase
- Gamepad support and controller icons (keyboard and mouse only, by the owner's choice).
- Subtitles (there's no dialogue) and localisation.
- Save slots (one slot stays).
- Achievements.
- Store-page screenshots (Phase 21).
- The game-thread trace R-64 (Phase 20).

## Results
(Filled in as the tasks finish.)

### S1 menu video (2026-11-11)
- **Built and checked:** `LS_LB_MenuDrift`, the owner's choice of a courtyard view, `p18_menu_drift.py`, check 102/102, cca35be:
  - from (700, −300, 300), looking east;
  - the well-head lantern centred, the arcades either side, the lit chapel door, and the belfry above the chapel roof;
  - a 40 s ping-pong drift.
- **The approach-path view was rejected by the owner.**
- **Rendered** with MRQ (`Tools/cine/p18_render_menu_drift.ps1`; `lb.Cine.Enabled 0`, or the intro's black fade covers the render), 1200 frames, owner present.
- **Encoded:** `Content/Movies/LB_MenuDrift.mp4`, H.264 1920×1080 at 30 fps, 40.0 s, 68.7 MB, LFS.
- **Known:** the render process crashes on the GPU thread at shutdown, after every frame is written (a Niagara dispatch), which is harmless to the output. The script verifies the frame count.

### P18-1 C++ UI framework (2026-11-11)
- **Built:** `Source/LastBell/UI/` as planned (section 2), plus `LBKeyBindings`, `LBUILogic`, `LBUIBuild` and `LBHUDWidget` (later); `ULBGameInstance`; the `ULBUserSettings` additions; the camera applies the FOV, motion blur and film grain; the pause key and the P16-6 revert (4ce1765, bbf89d2, 36dfe63).
- **Tests:** the UI unit and functional tests (d1278e3); phase B fixed the first-launch flag (reset by a stale-screen prune before the brightness screen was on the stack), made the test module build without unity and linked UMG and Slate (796e900). The content tests were red until P18-2, as expected.
- **Changed from the plan:** the loading screen is armed from the save subsystem and cleared by the game instance, not armed from a `PreLoadMap` handler (D-133); the Crouch rebinding is C only, with Ctrl a fixed second key; the HUD became a C++ widget in P18-3 (D-132).
- **Not validated here:** anything packaged (R-96), and by eye.

### P18-2 Assets and hookup (2026-11-11)
- **Built, headless (Unreal closed), by `Tools/ui/p18_2_assets.py` (it verifies in the same process, and `LB_MODE=verify` re-checks in a fresh one):** the four EB Garamond fonts (`FF_` faces and `F_` composite fonts, `OFL.txt` beside them), 53 key icons, the brightness symbol and the menu still, `MS_LB_MenuDrift`, `DA_UIStyle`, `IA_Pause` (`trigger_when_paused`), the `IMC_LB_Gameplay` mapping names, `BP_LBPlayerController.PauseAction` and `BP_MenuPlayerController.HUDWidgetClass`, the four UI sounds in `SCL_LB_UI` (via `p16_2_assets.py`), and the credits for the fonts and Kenney (7f6c55d, 9809003, 9bd6bc8).
- **Config (3b30547):** the `UIStyle` link, non-UFS staging of `Movies` and `LastBell/UI/Fonts`, and Enhanced Input user settings with `IMC_LB_Gameplay` registered through `bRegisterWithUserSettings` (without it rebinding finds no mapping; `Tools/mcp/MCP_NOTES.md`).
- **Notes for later:** the font importer needs Slate, so the script runs as `-ExecutePythonScript`, not `-run=pythonscript` (`MCP_NOTES.md`).

### P18-3 HUD and key icons (2026-11-11)
- **Built:** `ULBHUDWidget` replaces `WBP_HUD` and `WBP_Inspect` (crosshair, the prompt with a key icon bound to Interact, the objective, the relight message and the inspection overlay); `BP_LBPlayerController.HUDWidgetClass` set by `Tools/ui/p18_3_assets.py`; the key icon follows rebinding from creation (1154880, eed66c8, D-132). The cinematic widget's restyle and the "Hold [key] to skip" prompt came with P18-1 (bbf89d2).
- **Test:** `LastBell.Functional.UI.HUD.PromptKeyAndObjective`.
- **Left in place:** `WBP_HUD`, `WBP_Inspect` and `WBP_MainMenu`, unused, for the owner to approve deleting at the review.

### Owner additions during P18-4 (2026-11-11)
These are queued for P18-5, together with the session notes:
1. **True fullscreen by default on first launch.** Add `Config/DefaultGameUserSettings.ini` `[/Script/Engine.GameUserSettings]` with `FullscreenMode=0` (and `LastConfirmedFullscreenMode=0`, `PreferredFullscreenMode=0`) at the desktop resolution. A saved user setting overrides it.
2. **A "Show FPS" option** (Accessibility or Display tab; default off). It's a small HUD counter in the top-right corner, in EB Garamond, smoothed over 0.5 s, persisted in `ULBUserSettings` (`bShowFPS`), and it works in Shipping too (no `stat` console).

### P18-5 Fixes from P18-4 (2026-11-11)
- **Done:** the quality preset row cycles only Low to Epic, "Custom" is display-only (d79bb15); true fullscreen by default (addition 1) through `Config/DefaultGameUserSettings.ini` with `Version=5` (15bf5d5, D-130); Show FPS (addition 2) as `bShowFPS`, a Display tab toggle and the HUD counter (c7296fd; its tests also cover the preset cycle, graphics Apply persisting and the fullscreen config, and the `Cine.CheckpointSavesAfterCinematic` check no longer races the log: at most one save right after the end); `Tools/build_and_test.ps1 -Filter <prefix>` for targeted runs while iterating, the full suite staying the default (1c46c1b, D-131).
- **Suite:** 234 passed, 0 failed at the last recorded full run (2026-11-11 22:39, at c7296fd); 16 `LastBell.UI.*` and 17 `LastBell.Functional.UI.*` tests are new. The final suite and the Game build are still to run (P18-6).
- **QA:** the `qa-reviewer` pass (menu flows, every setting persisting across a restart, pause edge cases, rebinding conflicts) is run separately, and its report is not summarised here.
- **Closed by the code and the tests:** R-77 part 2, R-90 and R-94 (`RISKS.md`). Open: R-96 (packaged checks), R-97 (UI and video cost), R-98 (alt-tab pause), and R-92's persistence check.
