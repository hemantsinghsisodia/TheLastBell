# The Last Bell

A small, polished first-person atmospheric survival horror game made in Unreal Engine 5.8.

> A bell rings from a mountain monastery whose bell tower collapsed decades ago. You climb through a night storm to find out why, restoring three ancient mechanisms, until you realise each one is weakening the prison of **The Warden**.

- **Target:** 20–30 minutes of carefully authored gameplay on a high-end Windows PC
- **Genre:** exploration, environmental puzzles, stealth and evasion. No weapons.
- **Areas:** Courtyard, Chapel, Crypt, Bell Tower

## Status

The project is built phase by phase, and each phase gets a human review gate. See [Docs/IMPLEMENTATION_PLAN.md](Docs/IMPLEMENTATION_PLAN.md).

| Phase | Status |
|---|---|
| 0 — Architecture and tooling | ✅ Approved (`phase/00-architecture`) |
| 1 — Micro vertical slice | ✅ Approved (`phase/01-micro-slice`) |
| 2 — Full greybox | 🚧 In progress |

## Requirements

- Unreal Engine **5.8** (launcher build)
- Visual Studio 2022 with the C++ game development workload (MSVC 14.44 is known to work)
- Git with **Git LFS**, which is required for `.uasset`, `.umap` and source art and audio

## Getting started

```bash
git lfs install
git clone https://github.com/hemantsinghsisodia/TheLastBell.git
```

1. Right-click `TheLastBell.uproject` and choose **Generate Visual Studio project files**, or just open the project and let Unreal build the `LastBell` module.
2. The editor opens `L_Test_MicroSlice`. Press **Play**.

**Controls:** WASD to move, mouse to look, **E** to interact.

### Dev console commands (non-shipping builds)

| Command | Effect |
|---|---|
| `lb.State.Dump` | Print the current world-state tags |
| `lb.State.Add <Tag>` / `lb.State.Remove <Tag>` | Edit the world state |
| `lb.NewGame` | Reset the state and reload the map |
| `lb.Checkpoint.Load` | Reload the last checkpoint |
| `lb.Kill` | Kill the player, which reloads the last checkpoint |

### Running the tests

```bash
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" TheLastBell.uproject -ExecCmds="Automation RunTests LastBell; Quit" -unattended -nullrhi -nosplash -nosound -log
```

This runs unit tests for world state, objectives, save and interaction, plus `LastBell.Functional.MicroSlice`, an end-to-end PIE run of the test slice.

## Architecture in brief

The game is a C++ and Blueprint hybrid built on composition. C++ owns the systems, and Blueprint owns content and puzzles.

- **World state:** progress is a set of Gameplay Tags held by `ULBWorldStateSubsystem`. Systems react to tag changes instead of referencing each other.
- **Interaction:** add a `ULBInteractableComponent` to any actor. It can require tags and grant tags, and the player only ever talks to that component.
- **Objectives:** an ordered `ULBObjectiveChainData` asset. The active objective is derived from the tags.
- **Save and checkpoints:** a single slot storing the tags, a few actor records keyed by a hand-authored `SaveId`, and the checkpoint transform. Actors restore themselves instantly on load.
- **AI (Phase 5):** State Tree plus AI Perception for a single enemy, The Warden.

Full details are in [Docs/TECHNICAL_DESIGN.md](Docs/TECHNICAL_DESIGN.md).

## Repository layout

```
Source/LastBell/      C++ runtime module (prefix LB)
Content/LastBell/     All project content (never the Content root)
Config/               Engine/game config; gameplay tags in Config/Tags/
Docs/                 Design docs, decision log, risk log, asset registry
.claude/agents/       AI sub-agent definitions used during development
ExternalAssets/       Staging for raw downloads (Incoming/ is git-ignored)
```

## Documentation

| Document | Purpose |
|---|---|
| [GAME_DESIGN](Docs/GAME_DESIGN.md) | Pillars, progression, puzzles |
| [TECHNICAL_DESIGN](Docs/TECHNICAL_DESIGN.md) | Architecture (source of truth) |
| [LEVEL_DESIGN](Docs/LEVEL_DESIGN.md) | Spatial plan |
| [AI_DESIGN](Docs/AI_DESIGN.md) | The Warden |
| [ART_DIRECTION](Docs/ART_DIRECTION.md) / [AUDIO_DESIGN](Docs/AUDIO_DESIGN.md) | Look and sound |
| [PERFORMANCE_BUDGET](Docs/PERFORMANCE_BUDGET.md) | Frame and memory budgets |
| [TEST_PLAN](Docs/TEST_PLAN.md) | Testing approach |
| [DECISIONS](Docs/DECISIONS.md) / [RISKS](Docs/RISKS.md) | Decision and risk logs |
| [ASSET_REGISTRY](Docs/ASSET_REGISTRY.md) | Source and license of every external asset |

## Licensing note

Original code and documentation belong to the author. The project currently includes Unreal Engine template content (for example `Content/Characters/Mannequins`, `Content/LevelPrototyping`), which is governed by the [Unreal Engine EULA](https://www.unrealengine.com/eula) and is placeholder only. Third-party assets are recorded with their licenses in [ASSET_REGISTRY.md](Docs/ASSET_REGISTRY.md).
