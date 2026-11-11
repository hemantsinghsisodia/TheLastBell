"""P18-S1 part 2: write the Movie Render Queue manifest for the menu video (run by Tools/cine/p18_render_menu_drift.ps1 before the render; NOT a render itself).

Run headless (editor closed; the Movie Render Queue plugin is not enabled in TheLastBell.uproject, so it is enabled for this process only, and for the render, with -EnablePlugins):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -EnablePlugins=MovieRenderPipeline -unattended -nullrhi -nosplash -nosound -NoP4 -log -abslog=<log>
Environment (all optional):
    P18_MRQ_OUT        output directory (default <project>/Saved/MovieRenders/MenuDrift)
    P18_MRQ_END_FRAME  render only frames 0..N-1 (a test run; default the whole 1200-frame sequence)
    P18_MRQ_TEMPORAL   temporal sample count (default 1; 4 or 8 = slower and smoother, needs the AA method None, so it is switched automatically)
    P18_MRQ_CINEMATIC  1 = the engine's cinematic quality overrides (sg.*=4, view distance 50, shadow distance 10); default 0 = the project's own scalability
It saves NO project asset: the queue goes to <project>/Saved/MovieRenderPipeline/QueueManifest.utxt (git-ignored), which the render loads with
-MoviePipelineConfig="MovieRenderPipeline/QueueManifest.utxt" exactly as the editor's own "new process" executor does.
Writes <project>/Saved/MovieRenderPipeline/p18_manifest_report.json with the settings that were applied and the API names found.
"""
import json
import os
import traceback

import unreal

ROOT = r"C:\Hemant\Prj\Learning\TheLastBell"
MAP = "/Game/LastBell/Maps/L_Monastery.L_Monastery"
SEQ = "/Game/LastBell/Cinematics/LS_LB_MenuDrift.LS_LB_MenuDrift"
OUT = os.environ.get("P18_MRQ_OUT", os.path.join(ROOT, "Saved", "MovieRenders", "MenuDrift")).replace("\\", "/")
END_FRAME = int(os.environ.get("P18_MRQ_END_FRAME", "0") or 0)
TEMPORAL = int(os.environ.get("P18_MRQ_TEMPORAL", "1") or 1)
CINEMATIC = os.environ.get("P18_MRQ_CINEMATIC", "0") == "1"
REPORT = os.path.join(ROOT, "Saved", "MovieRenderPipeline", "p18_manifest_report.json")
TAG = "P18Mrq"
report = {"applied": [], "errors": [], "found": {}}


def log(msg):
    unreal.log("%s: %s" % (TAG, msg))


def setp(obj, name, value, label=None):
    try:
        obj.set_editor_property(name, value)
        report["applied"].append("%s.%s = %s" % (label or type(obj).__name__, name, value))
        return True
    except Exception as exc:  # noqa: BLE001
        report["errors"].append("%s.%s: %s" % (label or type(obj).__name__, name, str(exc).replace("\n", " | ")[:200]))
        unreal.log_warning("%s: set %s.%s failed: %s" % (TAG, label, name, exc))
        return False


def main():
    log("python classes: " + ", ".join(sorted(n for n in dir(unreal) if n.startswith("MoviePipeline") and ("Setting" in n or "Output" in n or "Config" in n or "Deferred" in n or "Library" in n))))
    report["found"]["classes"] = sorted(n for n in dir(unreal) if n.startswith("MoviePipeline") or n.startswith("MovieGraphPipeline"))
    queue = unreal.new_object(unreal.MoviePipelineQueue)
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.set_editor_property("job_name", "MenuDrift")
    job.set_editor_property("map", unreal.SoftObjectPath(MAP))
    job.set_editor_property("sequence", unreal.SoftObjectPath(SEQ))
    log("job created: map %s sequence %s" % (MAP, SEQ))
    # legacy preset configuration (EMoviePipelineConfigMode::Preset)
    cfg = unreal.new_object(unreal.MoviePipelinePrimaryConfig)
    job.set_configuration(cfg)
    cfg = job.get_configuration()
    log("job config mode: %s, configuration %s" % (getattr(job, "get_config_mode", lambda: "?")(), cfg.get_name() if cfg else None))

    def add(cls):
        s = cfg.find_or_add_setting_by_class(cls)
        log("setting added: %s" % s.get_class().get_name())
        return s

    # 1. output: PNG sequence, 1920x1080, 30 fps, zero-padded, overwrite
    out = add(unreal.MoviePipelineOutputSetting)
    setp(out, "output_directory", unreal.DirectoryPath(OUT), "Output")
    setp(out, "file_name_format", "{sequence_name}.{frame_number}", "Output")
    setp(out, "output_resolution", unreal.IntPoint(1920, 1080), "Output")
    setp(out, "use_custom_frame_rate", True, "Output")
    setp(out, "output_frame_rate", unreal.FrameRate(30, 1), "Output")
    setp(out, "override_existing_output", True, "Output")
    setp(out, "zero_pad_frame_numbers", 4, "Output")
    setp(out, "auto_version", False, "Output")
    setp(out, "handle_frame_count", 0, "Output")
    if END_FRAME > 0:
        setp(out, "use_custom_playback_range", True, "Output")
        setp(out, "custom_start_frame", 0, "Output")
        setp(out, "custom_end_frame", END_FRAME, "Output")
    # 2. the render pass: the final colour image only
    add(unreal.MoviePipelineDeferredPassBase)
    # 3. PNG sequence (8-bit)
    png = add(unreal.MoviePipelineImageSequenceOutput_PNG)
    setp(png, "write_alpha", False, "PNG")
    # 4. anti-aliasing and warm-up: the engine warm-up lets the rain and clouds fill the sky before frame 0 (the sequence holds at frame 0);
    #    the render warm-up renders and discards frames so TSR and Lumen settle
    aa = add(unreal.MoviePipelineAntiAliasingSetting)
    setp(aa, "spatial_sample_count", 1, "AA")
    setp(aa, "temporal_sample_count", TEMPORAL, "AA")
    setp(aa, "override_anti_aliasing", True, "AA")
    setp(aa, "anti_aliasing_method", unreal.AntiAliasingMethod.AAM_TSR if TEMPORAL <= 1 else unreal.AntiAliasingMethod.AAM_NONE, "AA")
    setp(aa, "use_camera_cut_for_warm_up", False, "AA")
    setp(aa, "engine_warm_up_count", 150, "AA")
    setp(aa, "render_warm_up_count", 32, "AA")
    setp(aa, "render_warm_up_frames", True, "AA")
    # 5. game overrides: the MoviePipelineGameMode (default of this setting) has no pawn, no HUD and none of the project's gameplay
    go = add(unreal.MoviePipelineGameOverrideSetting)
    setp(go, "cinematic_quality_settings", CINEMATIC, "GameOverride")
    setp(go, "texture_streaming", unreal.MoviePipelineTextureStreamingMethod.FULLY_LOAD, "GameOverride")     # the dev GPU has 6 GB: no 'disable streaming'
    setp(go, "use_lod_zero", True, "GameOverride")
    setp(go, "disable_hlods", True, "GameOverride")
    setp(go, "flush_streaming_managers", True, "GameOverride")
    if not CINEMATIC:
        setp(go, "use_high_quality_shadows", False, "GameOverride")
        setp(go, "override_view_distance_scale", False, "GameOverride")
        setp(go, "override_grass_cull_distance_scale", False, "GameOverride")
    log("game mode override: %s" % go.get_editor_property("soft_game_mode_override"))
    report["game_mode_override"] = str(go.get_editor_property("soft_game_mode_override"))
    # save the manifest exactly as the editor's new-process executor does
    lib = None
    for n in ("MoviePipelineEditorLibrary", "MoviePipelineEditorBlueprintLibrary"):
        lib = getattr(unreal, n, None)
        if lib is not None:
            report["found"]["library"] = n
            break
    if lib is None:
        raise RuntimeError("no MoviePipelineEditorLibrary in the unreal module (plugin not enabled?)")
    res = lib.save_queue_to_manifest_file(queue)
    log("save_queue_to_manifest_file -> %s" % (res,))
    report["save_result"] = [str(x) for x in (res if isinstance(res, (list, tuple)) else [res])]
    path = os.path.join(ROOT, "Saved", "MovieRenderPipeline", "QueueManifest.utxt")
    report["manifest_exists"] = os.path.isfile(path)
    report["manifest_bytes"] = os.path.getsize(path) if os.path.isfile(path) else 0
    log("manifest %s exists=%s bytes=%s" % (path, report["manifest_exists"], report["manifest_bytes"]))


try:
    main()
except Exception:  # noqa: BLE001
    report["errors"].append(traceback.format_exc())
    unreal.log_error("%s: EXCEPTION %s" % (TAG, traceback.format_exc()))
os.makedirs(os.path.dirname(REPORT), exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as fh:
    json.dump(report, fh, indent=1)
unreal.log("%s: DONE %d settings applied, %d errors (%s)" % (TAG, len(report["applied"]), len(report["errors"]), REPORT))
