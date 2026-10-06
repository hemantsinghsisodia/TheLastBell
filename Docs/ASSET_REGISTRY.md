# THE LAST BELL — Asset Registry

Every meaningful external asset is recorded here **before** it's used in a level. An asset with undetermined licensing is never used.

Pipeline: source → `ExternalAssets/Incoming/` (git-ignored) → inspect → license check → Unreal import → material/texture/collision/Nanite/LOD/scale setup → move to `Content/LastBell/...` → test → registry entry.

## Template content (Epic, already in the project)
Epic First Person template content is covered by the Unreal Engine EULA. It's placeholder only and none of it is intended to ship as hero content.

| Asset / folder | Source | License | Status | Plan |
|---|---|---|---|---|
| `/Game/Characters/Mannequins` | UE 5.8 First Person template | UE EULA | Placeholder | Keep for prototyping; review in Phase 12 |
| `/Game/FirstPerson`, `/Game/Input` | UE template | UE EULA | Reference | Superseded by `/Game/LastBell` in Phase 1 |
| `/Game/LevelPrototyping` | UE template | UE EULA | Useful for greyboxing | Keep through Phase 2 |
| `/Game/DemoTemplate` | UE 5.8 demo template | UE EULA | Not needed | Removal proposed for Phase 1 (needs approval) |

## External assets
| Asset | Source | Author | URL | License | Attribution | Acquired | Source location | Unreal path | Use | Modifications | Replaceable | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| _none yet_ | | | | | | | | | | | | |
