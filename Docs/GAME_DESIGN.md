# THE LAST BELL — Game Design

## Pitch
First-person atmospheric survival horror, 20–30 minutes, high-end Windows PC. A bell rings from a mountain monastery whose bell tower collapsed decades ago. The player climbs up through a night storm to investigate, restores three "ancient mechanisms", and discovers too late that each one weakens the prison of **The Warden**.

## Pillars
1. **Dread over shock.** Fear comes from anticipation, sound, silence, altered spaces and partial sightings. Jumpscares are rare and earned.
2. **Small and authored.** Four coherent spaces, polished to a premium level. No filler.
3. **Vulnerable investigator.** No weapons. The player explores, solves, hides and flees.
4. **The world remembers.** Spaces the player has already visited change after major events.

## Player verbs
Walk, sprint, crouch, look, interact (doors, levers, mechanisms, notes), toggle candle, hide by breaking line of sight, flee.
Out of scope unless approved: firearms, combat, crafting, inventory beyond key-item states, dialogue trees, multiplayer, additional major enemies.

## Progression (critical path)
| # | Beat | Area | Warden stage | Target time |
|---|---|---|---|---|
| 0 | Main Menu → New Game: the intro cinematic (about 37 s, skippable; see "The intro and the ending, as built") | Approach | — | 0.5 min |
| 1 | Arrival in the storm; the first toll has just rung (in the intro); the collapsed tower is visible | Approach → Courtyard | 1 Presence | 3–4 min |
| 2 | Get into the chapel (gate or door puzzle) | Courtyard → Chapel | 1 | 2–3 min |
| 3 | **Ritual Mechanism 1** (chapel puzzle: candles, stained glass or symbols) | Chapel | 1 → 2 | 4–5 min |
| 4 | The chapel changes; first partial sighting | Chapel | 2 Partial | 1 min |
| 5 | Descend into the crypt | Crypt | 2 → 3 | 2 min |
| 6 | **Ritual Mechanism 2** (crypt puzzle: chains, counterweights or valves) | Crypt | 3 Investigation | 4–5 min |
| 7 | Warden escalation: it physically patrols the crypt and cloister; stealth section | Crypt / cloister | 4 Patrol/Search | 3–4 min |
| 8 | **Ritual Mechanism 3** (bell sequence or counterweight restoration) | Cloister / tower base | 5 Hunt | 3–4 min |
| 9 | Climb the bell tower | Bell Tower | 5 | 2–3 min |
| 10 | Finale: the bell, the storm, the Warden freed; look-only, the Warden climbs to the player (scripted; the AI is dormant, D-116) | Bell Tower | 6 Finale | about 20 s (the Warden in sight within about 3.5 s) |
| 11 | Ending: the mask, the last view, end cards, credits (skippable) → return to menu | — | — | about 75 s (the wall-top shot, the end cards, the credits 40 s); the finale cinematic is 97.5 s in all |

Total: about 27–35 minutes on a first playthrough (the intro and the finale add about 2.1 minutes of cinematic). Phase 2 greybox timing will calibrate this.

## The intro and the ending, as built (Phase 17, D-114…D-125)
The player is **a villager from below**, sent up to find out why the bell rang. The story is a loop: the player becomes the Warden they first saw on the wall, and the next villager comes through the gate. Built with Sequencer; the spec and the final timing are in `Docs/plans/P17_CINEMATICS.md`, the architecture in `TECHNICAL_DESIGN.md` section 17.

**Beat 0, the intro (New Game only; Continue, a death reload and a checkpoint load never play it).**
- Black from the first frame. Four lines on black, then the title card later:
  1. "For forty years, no one has come back from the monastery on the ridge." (changed from "…no one has climbed to…" so it agrees with the traveller's note at the gate, which says they came up and may not leave; owner, D-114)
  2. "Its great bell fell silent the night the brothers vanished."
  3. "Tonight, the whole village heard it ring."
  4. "Someone has to go up."
- Each line stays up for 4.6 s (owner 3.10: longer than the first cut). At 21 s the picture fades in on the approach path, and the camera **cranes down** 5 m onto the player's eye height, so the whole tower shows over the cliffs and then sinks behind them as the camera settles at the spawn. Lightning **strikes the tower** at 25 s. Then the **Arrival tolls**: the great bell rings three times (stage 1, 4.5 s apart), the first at 25.4 s, with no drone under it (owner). The title "THE LAST BELL" shows at 27 s. A sparse **piano** (the owner's pick, CC0) plays under the whole intro and fades out as control returns at 35.5 s, so the player's first sounds are the storm and their own steps.
- Holding Interact for 1 s skips it (the screen fades up from black; the first toll and the world state still happen). Nothing can be saved while it plays.

**Beat 10, the finale (after the great bell is rung).**
- The player is eased to a mark on the belfry floor in 1.2 s and from then on can only look. The bell tolls five times by itself and **swings on every strike** (also at the other great-bell tolls on the map: the bell has no hand on its rope, and the owner kept this).
- **The Warden is in sight within about 3.5 s of the ring:** it climbs the last flight of the tower stair, still unhurried, up to the top and across the floor, and stops in front of the player. The AI Warden is dormant; this is a scripted figure.
- **The mask moment.** It lifts its bell-metal mask with both hands (the mask leaves the figure and travels in its right hand; under it there is only darkness in the hood), brings it forward to the player's eye height, and the camera **pushes in** on the mask to the player's eye. It meets the face: **black, and the sound of the mask** (metal on metal, a chain, then the player's own slow breath).
- **The last view** is through the mask's eye slits (a dark vignette with one fused opening) from the **courtyard wall top at 70 mm**, the spot where the player first saw the Warden on arrival, 57 m from the gate. A **villager walks in through the gate carrying a candle, the same candle the player carried**, and stops just inside the courtyard mouth. The great bell rings once, from the tower.
- The world sound fades away under two end cards, "The bell rings for you." and "THE LAST BELL"; the picture goes black; the **credits** roll for 40 s with the owner's strings (skippable by holding Interact); then the **main menu**, with the save deleted.

**The ending's meaning (D-114).** You become the Warden. The Warden puts its mask on the player, and the last view, from the wall top where the player first saw the Warden, shows the next villager coming through the gate with a candle: the story loops. The bell rings only "for the one who is meant to hear it" (the traveller's note at the gate, which says no living hand has rung it), and the end card says it rang for you. The opening text, that note and the arrival apparition all set this up.

## Menus and settings, as built (Phase 18, D-126…D-134)
Keyboard and mouse only (no gamepad). The menus are text in EB Garamond over a slow, looping video of the courtyard in the storm (D-129); the selected item glows like a candle flame. Up and Down (or the mouse) choose an item, Enter, Space or a click uses it, Left and Right change a value, and Escape goes back. Menu clicks and ticks are the only sounds that continue while the game is paused. The architecture is in `TECHNICAL_DESIGN.md` section 18.

**First launch.** The game opens in true fullscreen at the monitor's resolution (D-130). Before the main menu, a **brightness screen** shows a symbol that should be barely visible on a dark field, with a slider and Confirm. It appears once; the Accessibility tab's "Show brightness screen at next launch" brings it back, and Display > Brightness opens it at any time.

**Main menu** (the game's first screen):
- **Continue**, only when a save exists;
- **New Game**, which asks "This will erase your progress." when a save exists;
- **Settings**;
- **Credits**, the same roll as the ending;
- **Quit**, which asks first.

Going between the menu and the game shows a black loading screen with the title and a small flickering candle (shown at least 1 s). A reload after dying shows none.

**Pause** (Escape, in play):
- **Resume**, **Settings**, **Return to main menu** ("Unsaved progress since the last checkpoint will be lost."; the save is kept) and **Quit to desktop** (asks first).
- The game is truly paused: the world, the Warden, the storm, the thunder and tolls, the music, the bell, and a cinematic with its music all freeze, and Resume (or Escape again) continues exactly where it stopped. The picture behind the menu darkens and blurs.
- Escape while reading a note closes the note first; the next press pauses. Escape does nothing during the death fade or a level travel, and on the main menu it means Back. Losing the window's focus (alt-tab) pauses a game in play.

**Settings** (five tabs; Tab, Q and E, or PageUp and PageDown switch them):
- **Graphics:** a quality preset (Low, Medium, High, Epic), each of ten groups on its own (view distance, anti-aliasing, shadows, global illumination, reflections, post-processing, textures, effects, foliage, shading), and the resolution scale (50 to 100 %). "Custom" shows when the groups differ from the preset.
- **Display:** window mode (Fullscreen, Windowed fullscreen, Windowed), resolution, VSync, the frame-rate limit (30, 60, 90, 120, 144, Unlimited), **Show FPS counter** (a small number at the top right, off by default) and Brightness. Graphics and Display use **Apply** and **Revert**; changing the window mode or the resolution asks "Keep these display settings?" and reverts by itself after 15 s without an answer.
- **Audio:** six sliders (Master, Effects, Ambience, Music, Voice, Interface), live.
- **Controls:** mouse sensitivity, invert Y, head bob, and **key rebinding** for Move forward, back, left and right, Sprint, Crouch, Interact, Candle and Pause. Select a row and press the new key; Escape cancels. A key already used is refused with a message, and the mouse buttons cannot be the Pause key. **Reset to defaults** restores everything. The defaults are W, A, S, D, Shift, C (Ctrl always crouches too), E, F and Escape. Notes keep E and the right mouse button to close.
- **Accessibility:** field of view (70 to 110°, default 90), motion blur (off by default), film grain (on by default), high-contrast prompts (white on a dark plate with an outline) and the brightness screen at next launch.
- Audio, Controls and Accessibility apply and save at once; everything persists across a restart.

**Key prompts** show the key's icon and follow rebinding: the interact prompt in the HUD, "Hold [key] to skip" in the intro and the finale, and the Controls list.

## Puzzle rules
Puzzles are environmental, readable on sight and mechanically simple. Every solution has to be signposted in the space. No arbitrary codes without an in-world source.

## Failure
Getting caught by the Warden kills the player, with a short non-gory transition, and they reload at the last checkpoint. There are no lives and no fail menu spam. Checkpoints are placed so a death costs no more than about 2–3 minutes.

## Tone references (mood only, not to copy)
Ominous restraint in the style of Amnesia: The Dark Descent and SOMA, monastery stone and ritual, wet cold storm, warm light sources as safety.

## Open design questions (resolved in later phases)
- Is stamina needed for sprinting? Phase 3 playtest decides.
- Is object inspection needed? Phase 3, only if puzzles benefit.
- Which ending variant to use: **resolved in Phase 17 (D-114):** a single ending, "the bell rings for you". The player is trapped in the belfry, the Warden reaches them and puts its mask on them, and they become the Warden; the last view is through the mask, as the next villager's lantern comes through the gate.
- Exact puzzle choices per mechanism: Phase 2 greybox and Phase 4.
