# THE LAST BELL — Warden AI Design

## Goal
One memorable enemy that feels threatening but **understandable**. The player should be able to explain why the Warden found them. The Warden never knows things it couldn't have sensed.

## Escalation (driven by world-state tags)
| Stage | Trigger | Implementation | Pawn present? |
|---|---|---|---|
| 1 Presence | Game start | Scripted audio emitters, moved props, doors, shadow decals | No |
| 2 Partial Sightings | Mech 1 complete | `BP_WardenSilhouette` (non-AI animated actor) on scripted triggers: stained glass, a doorway across the nave, a reflection | No (silhouette only) |
| 3 Investigation | Enter crypt | AI pawn spawns, restricted to Investigate and Return, and reacts to loud stimuli | Yes |
| 4 Patrol / Search | Mech 2 complete | Patrol route plus Search enabled | Yes |
| 5 Hunt | Mech 3 started | Chase enabled, larger perception ranges | Yes |
| 6 Finale | Bell Tower | Scripted plus Chase hybrid (Sequencer beats with AI in between) | Yes |

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
- **Sight:** about 90° cone, range 1500–2500 cm depending on stage, peripheral detection about 0.6 s, blocked by geometry. The lantern-on state increases detection range by a tuning factor.
- **Hearing:** footsteps (crouch 0.1, walk 0.3, sprint 0.8 loudness), doors 0.6, dropped objects 0.7, ritual activation 1.0 at a world-tagged location.
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
