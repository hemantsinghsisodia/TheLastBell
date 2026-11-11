# P18-S1: the menu-drift shot and how to render it

Spec: `Docs/plans/P18_UI_SETTINGS.md` section 3. Nothing here has been rendered. The sequence is built and checked headless; the render and encode scripts are prepared and their first half (the queue manifest) was run.

## The shot: `/Game/LastBell/Cinematics/LS_LB_MenuDrift`

40.0 s at 30 fps (1200 frames), one spawnable CineCamera `Cam_MenuDrift` (16:9 DSLR filmback, 35 mm, f/2.8, manual focus 6000 cm), one camera-cut section 0-40 s (bCanBlend on, no eases), no fade, no audio, no markers, no characters, no other bindings. The package has no `/Game` dependencies.

| | start (0 s and 40 s) | turn (20 s) |
|---|---|---|
| Location | (-2800, 0, 560) | (-2400, 0, 560) |
| Yaw / pitch / roll | 1.0 / 6.0 / 0 | 7.0 / 6.0 / 0 |

X and yaw have three keys (0, 20, 40 s), all AUTO. The keys at 0 and 40 s are end keys and the one at 20 s is an extremum, so all six tangents read 0.0 (the check asserts it): the camera is at rest at 0, 20 and 40 s, the loop has no seam and the turn is soft. The peak speed is 30 cm/s and 0.45 deg/s, mid-way through each half.

Why this pose and not the brief's example (2500, -1800, 250):
- From the courtyard the gate (X 0..300, west wall) and the tower (X about 12400, east) are about 120 degrees apart, so no 35 mm view holds both. The only line that frames the gatehouse and the tower together is the approach axis, the line the player walks (spawn (-2800, 0)), and `Cam_Intro` already looks down it.
- Eye height 560, not 250: at 250 the gate crown (z 800 at X 0, 2800 cm ahead) is 11 degrees above the camera and hides everything of the tower below z 3200, leaving only the belfry roof. The intro says the whole tower shows over the cliffs from 652 and sinks behind them at 152. At 560 the line to the belfry deck (z 2500) passes the gate-crown plane at z 923 at the start and 880 at the turn (+123 / +80 cm clear), and the bell at z 983 / 933.
- X starts at the player's spawn and moves toward the gate: the F0 survey found the west cliff 350 cm behind the spawn (a camera there would be inside it), so the dolly goes forward, never back. Y stays 0, the walked lane.
- The pan to the right takes the tower from 6.4 degrees right of centre (start) to 0.6 right (turn); the gate crown stays 1 to 7 degrees left of centre, just below the horizon of the frame. Landmark elevations in frame (half FOV is 27.2 deg wide, 16.1 deg tall): gate crown -1.1 to -0.3, tower deck +1.3 to +1.5, bell +2.5 to +2.7, finial +9.4 to +9.8. The check asserts every landmark is inside the frustum (with 2 / 1 degree margins) at 0, 5, 10, 15 and 20 s.

NOT verified: a live line-of-sight trace (`Tracer` of `p17_f0_survey.py` needs the editor open) and any picture. The check is analytic from the cached F0 survey (`Saved/p17_f0_scratch`). The tower is 152 m away and fills about 8 degrees of the 32 degree frame height: look at the first test frames for scale, fog and whether the cliff tops hide more than computed. To change the pose edit the constants at the top of `Tools/cine/p18_menu_drift.py` and rebuild (below).

## Files

| File | What |
|---|---|
| `Content/LastBell/Cinematics/LS_LB_MenuDrift.uasset` | the sequence |
| `Tools/cine/p18_menu_drift.py` | headless build and check (reuses `p17_sequences.py` helpers; `P17_MODE=lib` makes that file inert on import) |
| `Docs/ArtTest/cine/p18_menu_drift_check.json` | check output (77 checks) |
| `Tools/cine/p18_mrq_manifest.py` | writes the Movie Render Queue manifest `Saved/MovieRenderPipeline/QueueManifest.utxt` (git-ignored) |
| `Tools/cine/p18_render_menu_drift.ps1` | the render |
| `Tools/cine/p18_encode_menu_drift.ps1` | PNG sequence to `Content/Movies/LB_MenuDrift.mp4` |

Rebuild: `P18_MODE=build P18_REBUILD=1` then `P18_MODE=check`, with `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Tools/cine/p18_menu_drift.py -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>` (editor closed). Only that package is saved.

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
  -EnablePlugins=MovieRenderPipeline -MoviePipelineConfig="MovieRenderPipeline/QueueManifest.utxt" -forcelogflush -log -abslog=Saved\Logs\p18_menu_render.log
```

- The Movie Render Queue plugin is not enabled in `TheLastBell.uproject`; `-EnablePlugins=MovieRenderPipeline` enables it for the manifest and render processes only, so the project file is untouched. (Enabling it in the editor would also do, but changes the `.uproject`.)
- The manifest holds one job: map `L_Monastery`, sequence `LS_LB_MenuDrift`, a legacy preset config: PNG sequence, 1920x1080, 30 fps, file name `{sequence_name}.{frame_number}` (4 digits, from 0000), overwrite on, no handle frames; TSR with spatial 1 / temporal 1; engine warm-up 150 frames (the sequence holds at frame 0 while the rain and clouds fill), render warm-up 32 frames; game overrides with the MoviePipelineGameMode (no pawn, no HUD, none of the project's gameplay), the project's own scalability (`-Cinematic` switches to the engine's cinematic overrides), fully-load-used-textures streaming (the dev GPU has 6 GB; "disable streaming" would not fit), LOD 0, HLODs off.
- `-Temporal 4` (or 8) switches to AA method None with accumulation: smoother, 3 to 4 times the render time.
- Frames are about 2 to 4 MB each (3 to 5 GB for 1200) under `Saved/` (git-ignored). The encode is `libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p`, BT.709, 30 fps, `-g 30 -movflags +faststart -an`; it was tested on 30 synthetic frames only.
- Expected time on the RTX 4050 Laptop (6 GB), an estimate and not a measurement: start-up 2 to 4 min, warm-up 1 to 2 min, then about 0.2 to 0.5 s per frame, so 1200 frames take roughly 4 to 10 min; 10 to 20 min in all with temporal 1, 25 to 45 min with `-Temporal 4`. The `-Test` run is about 4 to 6 min, almost all start-up. The script prints the elapsed time and seconds per frame.

## What needs a human

Never run: the render itself (a game window), so the command line is checked against the engine source and the manifest round-trip only. Read `Saved/Logs/p18_menu_render.log` for `LogMovieRenderPipeline` lines on the first run. Doubts, in order:
1. `-EnablePlugins` on the render process and the `/Engine/Maps/Entry` first map are not run; the editor's own launcher passes a map name that does not exist (falls back to L_MainMenu). If the render exits at once, enable "Movie Render Queue" in the editor's plugin list and rerun.
2. Storm: the frame shows the storm at the level's default state, since the MoviePipelineGameMode runs no LB gameplay (no pawn, no triggers, no story tags). `ULBStormSubsystem` and `ULBStormFXSubsystem` are world subsystems and the rain follows the player camera manager, which the camera cut drives, but whether the default intensity equals the intro's, and whether the rain, lightning and light flicker show, is for the eye. Lightning flashes are random: a flash that straddles the join will show when the video loops.
3. Quality and VRAM at 1920x1080 native on 6 GB; try the `-Test` frames first.
4. The pose: framing, scale of the tower, whether the cliffs at the sides crowd the frame, and the tower base hidden behind the gate.
5. The first and last second of the video on loop.
6. The P18 menu code (`LBGameInstance`, in progress by another agent) is compiled into the module the render loads; it should be inert in the Entry map and L_Monastery, but if a menu appears on the render window, report it.
