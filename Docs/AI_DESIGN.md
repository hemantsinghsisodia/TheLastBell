# THE LAST BELL — Warden AI Design

## Goal
One memorable enemy that feels threatening but **understandable**. The player should be able to explain why the Warden found them. The Warden never knows things it couldn't have sensed.

## Escalation (driven by world-state tags)
| Stage | Trigger | Implementation | Pawn present? |
|---|---|---|---|
| 1 Presence | Game start | Scripted audio emitters, moved props, doors, shadow decals | No |
| 2 Partial Sightings | Mech 1 complete | `BP_WardenApparition` (non-AI, D-092) on scripted triggers: the courtyard roofline, then the altar rail and the sacristy doorway | No (silhouette only) |
| 3 Investigation | Enter crypt | AI pawn spawns, restricted to Investigate and Return, and reacts to loud stimuli | Yes |
| 4 Patrol / Search | Mech 2 complete | Patrol route plus Search enabled | Yes |
| 5 Hunt | Mech 3 started | Chase enabled, larger perception ranges | Yes |
| 6 Finale | Bell Tower (the great bell rung) | **Fully scripted (D-116, Phase 17):** a Sequencer figure on `ABP_Warden` climbs to the player; the AI pawn is **dormant** at stage 6 | Only the sequence's figure |

## State Tree (`ST_Warden`)
```
Root
 ├─ Dormant            (no pawn activity)
 ├─ Scripted           (designer-driven MoveTo / anim montage; ignores perception)
 └─ Active
     ├─ Patrol         → on hearing(loud) or sight(partial) → Investigate
     ├─ Investigate    move to the stimulus location; "Suspicious" pause and look-around
     │                 → sight(confirmed) → Chase ; nothing found → Search
     ├─ Search         visit 2–4 nearby ALBSearchPoints (nearest-first, unvisited) for N seconds
     │                 → sight → Chase ; timeout → Return
     ├─ Chase          move to the player; lose LoS → keep the last-known location for X s → Search
     ├─ Attack         in range plus LoS → attack montage → player death
     └─ Return         go back to the patrol route
```
Stage gating: the escalation component enables or disables the Patrol, Search and Chase branches.

## Perception
- **Sight:** about 90° cone, range 1500–2500 cm depending on stage, peripheral detection about 0.6 s, blocked by geometry. The candle-on state increases detection range by a tuning factor.
- **Hearing:** footsteps (crouch 0.1, walk 0.3, sprint 0.8 loudness), doors 0.6, dropped objects 0.7, ritual activation 1.0 at a world-tagged location.
- Wiring notes for Phase 5:
  - The controller's perception config detects neutrals.
  - The player has `UAIPerceptionStimuliSourceComponent` registered for sight.
  - Noise goes through `ReportNoiseEvent(Instigator, Loudness, MaxRange, FName Tag)`. World events use the emitting actor as the instigator.
  - Perception updates are forwarded to the State Tree as events.
- Stimuli age out. The Warden only uses the remembered **last-known location**, never the live player position after losing sight.

## Fairness rules
- An audio tell before every chase start (breath or chain rattle) at least 0.5 s ahead.
- No spawning in the player's view, and no teleporting except scripted, hidden repositioning.
- Unreachable player (off the navmesh): the Warden switches to Search near the closest reachable point and never gets stuck staring.
- Chase speed is slightly below the player's sprint and above walking speed. Tuned in Phase 5.

## Debug
`lb.Warden.Debug 1` shows the state name above the pawn, perception cones, last-known location and active stimuli. The Gameplay Debugger AI category is also on, and the Visual Logger records chases.

## Not using (until shown necessary)
Behavior Trees (State Tree replaces them), EQS (designer search points instead), Smart Objects, Mass AI.

## As built in Phase 17 (D-116, D-121)
- **Stage 6 is the scripted finale and the AI is dormant.** `LBWardenLogic::CapsForStage` makes the AI active only for stages 3–5 (`bActive = Stage >= 3 && Stage <= 5`), so when the finale cinematic grants `State.Warden.Stage.6` the AI pawn goes Dormant through the normal stage gate (hidden, no collision, perception ignored). There is no chase and no Scripted state in the finale: the figure is a spawnable in `LS_LB_Finale` (`SK_Warden` with `ABP_Warden_C`, NoCollision, tag `LB_Cine_Warden`) and nothing the player does can change it. The hybrid "Scripted plus Chase" of the first design was dropped (look-only finale, no second Warden that could interfere). Test: `Warden.Stage6IsDormant`; the stage sweeps in the other Warden tests expect stage 6 inactive.
- **`WSpawn_Tower` (MinStage 6) stays in the level and is unused**, because no AI Warden exists at stage 6. Leave it, or delete it at the owner's review.
- **The Warden asset is V11.1** (the owner's new model replaced V5.5 in place; D-121): 8 material slots (two new, `M_Warden_DimEyes` and `M_Warden_Keratin`), the same skeleton and `mask` socket, the robe reweighted (the maximum wool-edge stretch ratios on the four test clips are 16.2 / 17.6 / 30.7 / 33.1, against the shipped V5.5's 23.7 / 29.6 / 43.3 / 44.2), and a re-baked apparition mesh. The AI, its `ABP_Warden` and its tuning numbers are unchanged. The owner asked for slower hand, leg and turn movement on the new model in plan 3.5; no AI tuning asset was changed in Phase 17, and the owner accepted the movement as it is in the finale review (plan 3.9).
- The ending's Warden is the same asset: it lifts its mask in `AN_Warden_MaskLift`, a Blender-keyed clip, and the mask swaps to `SM_LB_WardenMask` (`TECHNICAL_DESIGN.md` section 17).
