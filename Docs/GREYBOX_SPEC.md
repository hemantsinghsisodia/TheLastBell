# Phase 2 — Greybox Specification (L_Monastery)

This is the source of truth for the Phase 2 greybox. Units are cm; +X points north, away from the spawn. Courtyard ground is Z=0.
Everything is built from primitives using engine basic shapes and template materials. Puzzles are **stand-ins** built from existing components; the real puzzles come in Phase 4. Phase 2 is about checking the route, scale and pacing.

## Map plan (top view)
```
                                   [BELL TOWER] X12000-13000, Y1500-2500, 35 m tall
                                         |  tower door (opens on Ritual.3)
  [CHAPEL nave X6000-9000,Y±750] —— [CLOISTER X9500-12000, Y500-3000] (Mech 3)
     | main doors at X6000 (key)          |  stairs up from the crypt (east end)
     | sacristy X8000-9000,Y-750..-1500 → crypt stairs down
  [COURTYARD X0-6000, Y±2500] ←— shortcut gate (X6000,Y2000; opens on Ritual.3) — cloister
     | gatehouse at X0
  [APPROACH PATH X-3000..0, Y±200, between cliff walls]
  (CRYPT below the chapel and cloister, floor Z=-600: X7000-11500, Y-3000..500)
```

## Route and beats
| # | Area | Beat / player action | Tags set | Checkpoint |
|---|---|---|---|---|
| 1 | Approach | Spawn at X=-2800 facing +X. Narrow path between 6 m cliff walls; the tower is visible beyond the gatehouse | — | `CP_Approach` (at spawn, X=-2700) |
| 2 | Courtyard | Passing the gatehouse adds `State.Event.CourtyardEntered`. A distant bell (placeholder text) and a `BP_WardenSilhouette` on the far wall top for 3 s (Stage 1 presence) | CourtyardEntered, `State.Warden.Stage.1` | `CP_Courtyard` (X=300) |
| 3 | Courtyard | The chapel main doors are locked (prompt "Locked"). Find the **Chapel Key** inside the ruined well house in the SW corner (X1500,Y-2000). Collapsed wall rubble blocks a direct line | `State.Item.ChapelKey` | — |
| 4 | Chapel | Open the main doors (`RequiredStateTags` = ChapelKey) | `State.Door.ChapelMain.Open` | `CP_Chapel` (X=6300) |
| 5 | Chapel | Light 3 candles: nave north side (X7000,Y600), sacristy (X8600,Y-1300), choir dais (X8800,Y0) | `State.Chapel.Candle.1/2/3` | — |
| 6 | Chapel | **Ritual Mechanism 1** at the altar (X8900,Y0), which requires all 3 candles | `State.Ritual.1` | — |
| 7 | Chapel | Event: the candle actors hide, a silhouette shows behind the "stained glass" (thin translucent panel at X9000) for 3 s, and the sacristy crypt door auto-opens | `State.Warden.Stage.2` (added by mechanism Granted tags) | `CP_Chapel_After` (X8500,Y-1100) |
| 8 | Crypt | Stairs (ramps) down from the sacristy to Z=-600. Entering adds CryptEntered. The silhouette crosses a far corridor once | `State.Event.CryptEntered`, `State.Warden.Stage.3` | `CP_Crypt` (bottom of stairs) |
| 9 | Crypt | Ossuary chamber (X7500-9000, Y-3000..-2000): pick up the **Crank** | `State.Item.Crank` | — |
| 10 | Crypt | Flooded passage with a **pit** (2 m wide gap with a KillVolume below, crossed on a 1 m ledge), the death test | — | — |
| 11 | Crypt | Chain chamber (X10000-11500, Y-2500..-1000): **Ritual Mechanism 2** (winch), which requires the Crank | `State.Ritual.2`, `State.Warden.Stage.4` | `CP_Crypt_Mech2` |
| 12 | Crypt | Escalation: the stairs back to the chapel are now blocked (a `BP_TagVisibility` rubble wall appears on Ritual.2). The exit is the east stairs up to the cloister. A **Warden placeholder** stands in a side loop; touching it kills. Pass via the alternate loop | — | — |
| 13 | Cloister | Arriving adds CloisterEntered | `State.Event.CloisterEntered`, `State.Warden.Stage.5` | `CP_Cloister` |
| 14 | Cloister | Pull 3 counterweight levers spread around the arcade | `State.Cloister.Weight.1/2/3` | — |
| 15 | Tower base | **Ritual Mechanism 3** (requires all 3 weights). The tower door AND the courtyard shortcut gate open (AutoOpen) | `State.Ritual.3` | `CP_TowerBase` |
| 16 | Bell Tower | Climb the switchback ramps and platforms every 5 m to the bell chamber at Z≈3200 | `State.Event.TowerTop` (trigger) | `CP_TowerTop` |
| 17 | Finale | Interact with the **Bell** (a large cylinder) | `State.Event.Finale`, `State.Warden.Stage.6` | — |
| 18 | Ending | `BP_EndingTrigger` (listens for Finale) shows WBP_Ending ("The bell rings for you." / "THE LAST BELL"), and after 8 s calls `CompleteGame` → `L_MainMenu` | — | — |

## Objective chain (DA_ObjectiveChain_Main)
1. "Follow the sound of the bell": CourtyardEntered
2. "Find a way into the chapel": State.Door.ChapelMain.Open
3. "Light the ritual candles": Candle.1, .2, .3
4. "Use the altar mechanism": Ritual.1
5. "Descend into the crypt": CryptEntered
6. "Find a way to turn the winch": Item.Crank
7. "Raise the chains": Ritual.2
8. "Escape the crypt": CloisterEntered
9. "Set the three counterweights": Weight.1, .2, .3
10. "Release the tower mechanism": Ritual.3
11. "Climb the bell tower": TowerTop
12. "Ring the bell": Finale

## Dimensions and rules
- Exterior walls are 800 tall, interior walls 400, the chapel nave 1200, tower walls 3500. Thickness is 30–50.
- Corridors where the Warden will path (crypt, cloister) are at least 200 wide. Doors are 120×240.
- Ramps have a slope of 30° or less, which the CharacterMovement default walkable angle (44.7°) allows.
- Every area gets at least one non-shadow PointLight or RectLight, so darkness never blocks navigation (the readability rule).
- Outliner folders: `Approach`, `Courtyard`, `Chapel`, `Crypt`, `Cloister`, `BellTower`, `Gameplay/<Area>`, `Lighting`.
- Every interactable stand-in has a unique, readable label (e.g. `Candle_Nave`), and every checkpoint has a unique `CheckpointId`.
