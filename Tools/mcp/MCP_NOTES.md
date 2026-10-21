# Unreal MCP notes for agents (The Last Bell)

The editor must be open on `C:\Hemant\Prj\Learning\TheLastBell`. Its MCP server is at `http://127.0.0.1:8000/mcp`.
Native MCP tools may be missing from your session. If so, use the helper **`Tools/mcp/ue.py`**:
- CLI: `python ue.py describe <toolset> [tool]` (tool list, or one tool's schema); `python ue.py <toolset> <tool> '<json args>'`.
- Library (preferred): put your script in your own scratch folder and do `sys.path.insert(0, r"C:\Hemant\Prj\Learning\TheLastBell\Tools\mcp")`, then `from ue import UE; ue = UE(); ue.call(toolset, tool, args)` (it raises on error).
- If `python` isn't on PATH in Bash, use `C:\Users\heman\AppData\Local\Python\pythoncore-3.14-64\python.exe` from PowerShell, with Windows paths. Write scripts with the Write tool; Bash heredocs with quotes often break.

## Git (IMPORTANT)
Commit ONLY to the currently checked-out `claude/*` branch. Check `git branch --show-current` first. Never switch branches, never merge, never push (see CLAUDE.md).

## Toolsets
- `editor_toolset.toolsets.blueprint.BlueprintTools`: create, compile_blueprint (`warnings_as_errors`), add_variable, write_graph_dsl / read_graph_dsl / get_graph_dsl_docs, get_default_object, list_functions, find_nodes, connect_pins, create_node and more. **Call `get_graph_dsl_docs` before writing graphs.**
- `editor_toolset.toolsets.object.ObjectTools`:
  - `get_properties {instance:{refPath}, properties:[...]}`
  - `set_properties {instance:{refPath}, values:"<JSON STRING>"}`. It refuses to change an array element AND grow the array in one call; split those into two calls.
  - `list_properties`, `search_subclasses`
- `editor_toolset.toolsets.asset.AssetTools`:
  - `find_assets {folder_path, name}`, `exists`, `duplicate {path,new_path}`, `create_folder`
  - `save_assets {asset_paths:[explicit package paths]}` (folder paths don't work)
  - `is_dirty` (pass a package path), `get_referencers`, `get_dependencies`
- `editor_toolset.toolsets.scene.SceneTools`:
  - `find_actors {name:"", tag:"", collision_channels:[]}`, `get_folders`, `get_actors_in_folder`, `set_actor_folder`
  - `add_to_scene_from_class {actor_type, name, xform}`, `add_to_scene_from_asset`, `remove_from_scene`
  - `load_level`, `get_current_level`, `trace_world {start,end}` (returns the distance)
- `editor_toolset.toolsets.actor.ActorTools`: `get_actor_transform`, `set_actor_transform {actor, xform, worldspace}`.
- `EditorToolset.EditorAppToolset`:
  - StartPIE `{options:{bSimulate:false, playMode:"PlayMode_InViewPort", warmupSeconds:N}}`, StopPIE, IsPIERunning
  - CaptureViewport (large base64; pipe it to a file)
- `EditorToolset.LogsToolset`: `GetLogEntries {category:"", pattern:"<regex>", maxEntries:N}`. Always filter; the whole log drops the connection.
- `ConfigSettingsToolset.ConfigSettingsToolset` (project settings), `UMGToolSet.UMGToolSet` (widgets; no widget animations), `editor_toolset.toolsets.material.MaterialTools`.
- `GameplayTagsToolset`: **NEVER write tags with it** (R-18/D-024). Tags are text-edited in `Config/Tags/LBGameplayTags.ini` only while the editor is closed, by the lead.
- The Slate UI automation toolset can't see editor windows, so there's no simulated key input. Use automation tests instead.

## Gotchas
- Object refs are `{"refPath": "/Game/Path/Asset.Asset"}`; BP classes are `/Game/Path/BP_X.BP_X_C`. A BP component template is `<BP>.<BP>_C:<Comp>_GEN_VARIABLE`. A placed actor's component is `<map>.<map>:PersistentLevel.<ActorName>.<Comp>`.
- Template changes do NOT propagate to placed instances that serialized the value; set instances directly.
- `write_graph_dsl` is ADDITIVE (it duplicates events). `read_graph_dsl` may spawn empty `_Event_N` orphans; delete them. Custom events can't take typed params in the DSL. Bind delegates with Create Event plus `set_create_event_function`, or an Assign node.
- Many schemas mark every parameter required; read the schema first. Check every return value.
- BoxExtent: set one axis per call and read it back.
- A headless test run (UnrealEditor-Cmd) holds .umap/.uasset files open, so saving during one fails with "MoveFile". Save first.
- Never check out older commits while the editor is open.

## Running tests (a separate process; fine with the editor open)
```
powershell -Command "$l='C:\Hemant\Prj\Learning\TheLastBell\Saved\Logs\<you>.log'; Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -ArgumentList @('C:\Hemant\Prj\Learning\TheLastBell\TheLastBell.uproject','-ExecCmds=\"Automation RunTests LastBell; Quit\"','-unattended','-nullrhi','-nosplash','-nosound','-NoP4','-log',\"-abslog=$l\") -Wait"
```
C++ can't be built in the real project while the editor is open (Live Coding plus the DLL lock). Build and test C++ in the mirror `C:\lbb` (Content is a junction to the real Content), and sync with PowerShell robocopy.

## Framework quick reference
For C++ API names, read `Source/LastBell/`; for architecture, read `Docs/TECHNICAL_DESIGN.md`. The key Blueprints are in `/Game/LastBell/Blueprints/` (Interactables: BP_Door_Base, BP_Lever, BP_TagInteractable, BP_RitualMechanism, BP_TagTrigger, BP_TagVisibility, BP_WardenSilhouette, BP_WardenPlaceholderKill, BP_KillVolume, BP_Inspectable_Note). Data is in `/Game/LastBell/Data/`.
