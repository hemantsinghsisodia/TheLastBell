# THE LAST BELL — Level Design

## Spatial concept
A compact monastery on a mountain shelf. The **ruined bell tower** is visible from the first spawn and from most outdoor vantage points, so it acts as a constant landmark and promise. The areas stack vertically: Courtyard (surface) → Chapel (raised, inside) → Crypt (below the chapel) → cloister/tower base → Bell Tower (top). The route loops back so the player sees the courtyard and chapel again after they've changed.

```
            [BELL TOWER]  (top; reached last)
                 |
   [Tower base / cloister] —— shortcut gate (opens after Mech 3) —— [COURTYARD]
                 |                                                     |
             [CRYPT] ——— stairs ——— [CHAPEL] ——— main doors ————————┘
         (Mechanism 2)           (Mechanism 1)
```

## Areas
| Area | Role | Mood | Approx. footprint (greybox) | Key spaces |
|---|---|---|---|---|
| Courtyard | Arrival, orientation, storm exposure | Cold, wet, wind, exposed | 60×50 m | Gatehouse, well, collapsed wall, view of the tower |
| Chapel | First puzzle, first sighting | Warm candles fighting cold moonlight | 30×15 m nave plus side rooms | Nave, altar, stained glass, sacristy, crypt stair |
| Crypt | Claustrophobia, stealth introduction | Dark, wet, close; fog | ~40 m of tunnels plus 3 chambers | Ossuary, flooded passage, chain chamber (Mech 2) |
| Cloister / tower base | Hunt section, Mech 3 | Ruined, rain falling through the roof | 25×25 m | Arcade, cells, counterweight room |
| Bell Tower | Climax | Storm, height, lightning | 10×10 m footprint, about 35 m tall | Spiral or broken stairs, bell chamber, exposed top |

## Rules
- **Readability first.** Lit critical paths, landmark lighting on objectives, no pitch-black navigation.
- **Loops for stealth.** Every Warden-patrol space has at least two routes and line-of-sight breakers.
- **Altered revisits.** After each mechanism, previously visited spaces change: doors open or close, candles go out, water rises, objects move.
- **Scale.** Real-world proportions. Doors are 220–250 cm tall. Corridors are at least 180 cm wide wherever the Warden must path (Warden capsule radius about 55 cm, height about 290 cm).
- **Checkpoints** before each mechanism, after each mechanism, at the start of each Warden section and at the tower base.

## Map plan
`L_MainMenu`, `L_Monastery` (all four areas in one map, streamed where needed) and `L_Test_MicroSlice` (Phase 1). The final route is laid out in the Phase 2 greybox and this document is updated with real dimensions.
