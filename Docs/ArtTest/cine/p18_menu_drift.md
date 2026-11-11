# P18-S1: the menu-drift shot and how to render it

Spec: `Docs/plans/P18_UI_SETTINGS.md` section 3. Nothing here has been rendered. The sequence is built and checked headless; the render and encode scripts are prepared and their first half (the queue manifest) was run.

## The shot: `/Game/LastBell/Cinematics/LS_LB_MenuDrift` (courtyard version, owner's choice 2026-11-11)

The first version looked down the approach lane at the gatehouse; the owner asked for the courtyard instead. 40.0 s at 30 fps (1200 frames), one spawnable CineCamera `Cam_MenuDrift` (16:9 DSLR filmback, 35 mm, f/2.8, manual focus 6000 cm), one camera-cut section 0-40 s (bCanBlend on, no eases), no fade, no audio, no markers, no characters, no other bindings. No /Game dependencies.

| | start (0 s and 40 s) | turn (20 s) |
|---|---|---|
| Location | (700, -300, 300) | (1100, -300, 300) |
| Yaw / pitch / roll | 4.5 / 6.5 / 0 | 9.5 / 6.5 / 0 |

X and yaw have three keys (0, 20, 40 s), all AUTO; all six tangents read 0.0 (the check asserts it): the camera is at rest at 0, 20 and 40 s, the loop has no seam. Peak speed 30 cm/s and 0.375 deg/s.

What is in frame (the check asserts each inside the frustum, with 2 / 1 degree margins, at 0, 5, 10, 15 and 20 s; azimuth / elevation relative to the view axis, half FOV 27.2 wide and 16.1 tall):
- the well-head lantern (3400, 0) at az +1.8 to -2.1, el -10 to -11 (centre of the frame horizontally, lower third); the south arcade row's far end (5000, -950) at az -13 to -19 and the north row's far end at +12 to +8, both at the horizon: the rows converge on the chapel either side of the well;
- the chapel door (6000, 0) at az -1.3 to -6, el -7, and the gable (apex 2215, corners 1250) at el +13 to +15;
- the belfry (12400, 2000, 3500) at az +6.6 to +2.0, el +8.5 to +9.0 and the finial (4825) at el +14.1 to +14.7, to the right of the gable apex and above the gable's right slope.

Why this pose (the brief suggested about (700, -600, 260), yaw 6, pitch 4):
- Y -300, not -600: from -600 the well is 6.5 deg left of centre and the north arcade row is out of frame; at -300 the well sits on the axis, the door near it and the two rows balance. It also keeps the camera clear of the rubble heap `KD_Heap_N` (X 560..960, Y -720..-420, Z 130) and the first bed (X 1700..).
- Z 300, not 260: the chapel west gable (parapet to Z 2215, 5300 cm away) hides the tower below about Z 3000. A line to the belfry (Z 3500) clears the gable and roof by 420 cm at the start and 300 cm at the turn, to the finial by 990 / 840 cm (the check asserts at least 150 cm). The tower deck (Z 2500) and the tower's body below the belfry stay hidden behind the chapel (clearance +12 cm at the start, negative later): what rises over the chapel is the belfry and the roof, not the tower's whole height. Raising the camera to 450 gains only about 200 cm of tower and moves the well toward the bottom edge, so it stays at 300; shifting Y north (toward Y 0 to +200) would clear the gable completely (the line then crosses X 6000 north of Y 810) but puts the well and the door off the left of the tower.
- Pitch 6.5 so that the top of the frame holds the gable apex and the finial (both about +20 deg above the camera) while the bottom edge (-9.6 deg) still shows the floor 1770 cm ahead.
- The gate wall (X 168..580) and the arch (X 0..300) are behind the camera. The camera is east of both and clear of the heap and the beds (the check asserts it). The dead snag (2300, -550, 650) stands left of centre at az -13 and the dead tree (4550, 550, 700) right of centre, both in frame as silhouettes.

NOT verified: a live line-of-sight trace (the editor is needed) and any picture. The clearances come from the P7 courtyard layout and the P8 chapel dimensions as written in the docs (chapel mass: gable to 2215, roof plane 1200 at Y +-810 to 2165 at Y 0, 20 thick), not from the level. Things in the garth not modelled: the vegetation (grass clumps 50-180 cm, shrubs to 234 cm in the beds; the camera at Z 300 is above all of it but they may fill the lower frame), the arcade roofed walks (Z up to 700, well below the sightline), the lantern's exact height (assumed Z 130 on the coping). To change the pose edit the constants at the top of `Tools/cine/p18_menu_drift.py` and rebuild (below).

## Files

| File | What |
|---|---|
| `Content/LastBell/Cinematics/LS_LB_MenuDrift.uasset` | the sequence |
| `Tools/cine/p18_menu_drift.py` | headless build and check (reuses `p17_sequences.py` helpers; `P17_MODE=lib` makes that file inert on import) |
| `Docs/ArtTest/cine/p18_menu_drift_check.json` | check output (102 checks) |
| `Tools/cine/p18_mrq_manifest.py` | writes the Movie Render Queue manifest `Saved/MovieRenderPipeline/QueueManifest.utxt` (git-ignored) |
| `Tools/cine/p18_render_menu_drift.ps1` | the render |
| `Tools/cine/p18_encode_menu_drift.ps1` | PNG sequence to `Content/Movies/LB_MenuDrift.mp4` |

Rebuild: `P18_MODE=build` with `P18_REBUILD=1`, then `P18_MODE=check`, with `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/cine/p18_menu_drift.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>` (editor closed). Only that package is saved.

## Render (needs the owner: it opens a game window)

```
powershell -ExecutionPolicy Bypass -File Tools\cine\p18_render_menu_drift.ps1 -Test      # 90 frames into Saved\MovieRenders\MenuDrift_test
powershell -ExecutionPolicy Bypass -File Tools\cine\p18_encode_menu_drift.ps1 -Test      # -> Saved\MovieRenders\LB_MenuDrift_test.mp4
powershell -ExecutionPolicy Bypass -File Tools\cine\p18_render_menu_drift.ps1            # all 1200 frames into Saved\MovieRenders\MenuDrift
powershell -ExecutionPolicy Bypass -File Tools\cine\p18_encode_menu_drift.ps1            # -> Content\Movies\LB_MenuDrift.mp4
```

The render step runs (the same line the editor's own "new process" executor builds, `MoviePipelineNewProcessExecutor.cpp`):

```
UnrealEditor-Cmd.exe "<project>\TheLastBell.uproject" "/Engine/Maps/Entry?game=/Script/MovieRenderPipelineCore.MoviePipelineGameMode"
  -game -windowed -ResX=1920 -ResY=1080 -nohmd -NoLoadingScreen -nosplash -nosound -NoP4 -unattended
  -EnablePlugins=MovieRenderPipeline -dpcvars=lb.Cine.Enabled=0 -ExecCmds="lb.Cine.Enabled 0"
  -MoviePipelineConfig="MovieRenderPipeline/QueueManifest.utxt" -forcelogflush -log -abslog=Saved\Logs\p18_menu_render.log
```

- The Movie Render Queue plugin is not enabled in `TheLastBell.uproject`; `-EnablePlugins=MovieRenderPipeline` enables it for the manifest and render processes only, so the project file is untouched. (Enabling it in the editor would also do, but changes the `.uproject`.)
- The manifest holds one job: map `L_Monastery`, sequence `LS_LB_MenuDrift`, a legacy preset config: PNG sequence, 1920x1080, 30 fps, file name `{sequence_name}.{frame_number}` (4 digits, from 0000), overwrite on, no handle frames; TSR with spatial 1 / temporal 1; engine warm-up 150 frames (the sequence holds at frame 0 while the rain and clouds fill), render warm-up 32 frames; game overrides with the MoviePipelineGameMode (no pawn, no HUD, none of the project's gameplay), the project's own scalability (`-Cinematic` switches to the engine's cinematic overrides), fully-load-used-textures streaming (the dev GPU has 6 GB; "disable streaming" would not fit), LOD 0, HLODs off.
- `-Temporal 4` (or 8) switches to AA method None with accumulation: smoother, 3 to 4 times the render time.
- Frames are about 2 to 4 MB each (3 to 5 GB for 1200) under `Saved/` (git-ignored). The encode is `libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p`, BT.709, 30 fps, `-g 30 -movflags +faststart -an`; it was tested on 30 synthetic frames only.
- Time on the RTX 4050 Laptop (6 GB): the first `-Test` run (black frames, see below) took 26 s to start, then 244 frames (150 warm-up + 90 + a few) in 33 s, about 0.13 s per frame with many first-time shader (PSO) waits. Expect the full 1200 frames in roughly 4 to 8 min in all with temporal 1 (more if the scene is heavier once the intro is off); `-Temporal 4` about 3 to 4 times the frame time. The script prints elapsed time and seconds per frame.

## First test render (2026-11-11): black frames, and why

All 90 PNGs were identical (38,667 bytes, black). The log (`Saved/Logs/p18_menu_render.log`) shows the pipeline itself worked: the Entry map and the MoviePipelineGameMode loaded, `L_Monastery` loaded, the job registered the range [0,72000) ticks (3 s) for `Cam_MenuDrift`, 150 warm-up frames then 90 frames ran (frame 244 "Finished processing Camera Cut"). The cause is the project, not the manifest: `ULBCinematicSubsystem::OnWorldBeginPlay` on `L_Monastery` treats the load as a New Game, calls `SetManualCameraFade(1, Black)` (the intro's `bStartBlack`) and plays `LS_LB_Intro` on the first tick (log lines "Cine: Intro will start on the first tick (New Game)", "Cine: play Intro (LS_LB_Intro, 37.0 s...)", markers `card:Intro_1` and `card:Intro_2` during the render). The intro keeps the picture black until 21 s. Fix: `lb.Cine.Enabled 0` (a CVar of that subsystem; `IsEnabled()` is checked before the New Game rule) set on the command line with `-dpcvars` and `-ExecCmds`, early enough for the map's BeginPlay. The render script now also warns and exits 3 if the log shows a `Cine:` start, or if every PNG has the same size; the encode script refuses identical-size frames.

The same run then crashed 6 frames after the last frame, while the pipeline was finalizing (frame 249): `EXCEPTION_ACCESS_VIOLATION 0x1` on the RHI thread in `UnrealEditor-D3D12RHI` called from the render graph with the breadcrumb `NiagaraGpuComputeDispatch` (`Saved/Crashes/UECC-Windows-2C10170644AC175E8285C8AC2B08668D_0000`; no symbols), followed by the "Application quit while Movie Pipeline was still active" lines, which are the MRQ executor reacting to that crash (an `IsInGameThread()` assert at `MoviePipeline.cpp:395` during the crash handling). All 90 files were already on disk. Cause not established; a Niagara GPU system (the rain) is in the dispatch. If it recurs with the intro off, the render script reports it as a warning when all frames exist, and the next step is to rerun with the Niagara rain off (`lb.StormFX.Enabled 0` in `-ExecCmds`, which also removes the rain from the picture) to see whether it is the rain.

## What needs a human

The first test render was black (above), so no picture has been seen yet. Read `Saved/Logs/p18_menu_render.log` (`LogMovieRenderPipeline`, `LogLB: Cine:` lines) after each run. Doubts, in order:
1. `-EnablePlugins` and the `/Engine/Maps/Entry` first map worked in the first test (plugin mounted, executor and pipeline found, map loaded).
2. Storm: the first test log shows "Storm: active with 13 linked lights, intensity 0.55" and "StormFX: active (rain on, 4 bolts)". The frame shows the storm at the level's default state, since the MoviePipelineGameMode runs no LB gameplay (no pawn, no triggers, no story tags). `ULBStormSubsystem` and `ULBStormFXSubsystem` are world subsystems and the rain follows the player camera manager, which the camera cut drives, but whether the default intensity equals the intro's, and whether the rain, lightning and light flicker show, is for the eye. Lightning flashes are random: a flash that straddles the join will show when the video loops.
3. Quality and VRAM at 1920x1080 native on 6 GB; try the `-Test` frames first.
4. The pose: framing, how much of the belfry shows over the chapel gable, whether the vegetation or the snag crowd the lower and left frame, and the lantern glow at the well.
5. The first and last second of the video on loop.
6. The P18 menu code (`LBGameInstance`, in progress by another agent) is compiled into the module the render loads; it should be inert in the Entry map and L_Monastery, but if a menu appears on the render window, report it.
