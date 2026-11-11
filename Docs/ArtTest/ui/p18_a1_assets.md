# P18 A1: downloaded assets (fonts, key icons, UI sounds)

Task A1 of `Docs/plans/P18_UI_SETTINGS.md` (section 4). Everything is in git-ignored folders under `ExternalAssets/Incoming/` (confirmed with `git check-ignore`). Nothing was imported into Unreal; import happens in P18-2. Downloaded on 2026-11-11.

## Summary
| Set | Status | Where |
|---|---|---|
| EB Garamond (Regular, Italic, SemiBold, Bold, static TTF) + `OFL.txt` | Downloaded, verified | `ExternalAssets/Incoming/ebgaramond/` |
| Kenney Input Prompts 1.5A (CC0), keyboard and mouse | Downloaded, verified (official file) | `ExternalAssets/Incoming/kenney-input-prompts/` |
| Kenney Interface Sounds (100 files) and UI Audio (50 files), CC0 | Downloaded from a **third-party GitHub repackaging** (WAV); official zips are blocked to automated tools | `ExternalAssets/Incoming/kenney-ui-audio/` |

## 1. EB Garamond
- **Source:** `https://github.com/octaviopardo/EBGaramond12`, branch `master` (HEAD `106a4a6d377987459ae5e68673a4570f13b957fb`, 2026-03-27). Files fetched from `https://raw.githubusercontent.com/octaviopardo/EBGaramond12/master/`.
- **Designers:** Georg Duffner (original EB Garamond) and Octavio Pardo (the extended family), as listed in the repository's `AUTHORS.txt`. `CONTRIBUTORS.txt` is kept too.
- **Licence:** SIL Open Font License 1.1. `OFL.txt` (4,454 bytes) comes from the same repository and begins:
  - "Copyright 2017 The EB Garamond Project Authors (https://github.com/octaviopardo/EBGaramond12)";
  - "Copyright 2025 Deborah Khodanovich (RCS citation glyphs)";
  - "This Font Software is licensed under the SIL Open Font License, Version 1.1."
  - The licence text contains a Reserved Font Name clause. We do not modify or rename the fonts, so it does not bite. If P18-2 ever edits or subsets the font files, re-read clause 3 first.
- **Static weights are available**, so the variable font was not needed (it exists at `fonts/variable/EBGaramond[wght].ttf` and `...-Italic[wght].ttf` if wanted).
- **Format:** TrueType, one file per style. The same repository also offers OTF; the TTF set was chosen because Unreal's `UFontFace` import takes TTF reliably.

| File | Bytes | SHA-256 |
|---|---|---|
| `EBGaramond-Regular.ttf` | 627,304 | `2028dc06d3c130b4761693481436a32a8e35ed500bf58c25c53de004106125b8` |
| `EBGaramond-Italic.ttf` | 602,136 | `d4ad1d0a9390d26d6d3f176117a1d121441edb8c8632bfca52cfad084b9059cb` |
| `EBGaramond-SemiBold.ttf` | 687,548 | `ebf827a102983972abb2a1a3964afd5a7b79ca04f2ddd9e53917ce623cefdf2c` |
| `EBGaramond-Bold.ttf` | 687,396 | `0cfed122e51e3fd44ccedaef7637efed6d5bdc4ad89a6117d70241510309a186` |
| `OFL.txt` | 4,454 | `058611bd968817d532cedeab6acaa055e882d365a88523df00e7917ad7a0f704` |
| `AUTHORS.txt` | 328 | `45783f82a13fa12cea5a6e4d9e48090b806b5600f1362ea239d3549d79f0d20c` |
| `CONTRIBUTORS.txt` | 626 | `2c75931501e15be2d4f63d4fb4a4b533171025803403aeeaeb2896a9ba511a94` |

Credits line (plan section 4): "Fonts / EB Garamond, Georg Duffner and Octavio Pardo (SIL OFL 1.1)". Ship `OFL.txt` in `Content/LastBell/UI/Fonts/` (R-95).

## 2. Kenney Input Prompts (CC0), keyboard and mouse
- **Source:** the official pack, Kenney (Assets) on itch.io, `https://kenney-assets.itch.io/input-prompts`, file `kenney_input-prompts_1.5.zip` (5,070,075 bytes, SHA-256 `ac2fcf599080b0f3ba2d174c9474db6df1a0e96ff0662580e2da79a122ab78a1`), the zero-price "No thanks, just take me to the downloads" path. The same pack is on `https://kenney.nl/assets/input-prompts` (the kenney.nl page itself returns 403 to command-line tools, so it was not used for the file).
- **Licence evidence:** `License.txt` inside the zip: "Input Prompts (1.5A), Created/distributed by Kenney (www.kenney.nl), Creation date: 11-07-2026, License: (Creative Commons Zero, CC0), http://creativecommons.org/publicdomain/zero/1.0/". Credit is optional. The kenney.nl page and the itch.io page also state CC0.
- **Extracted to:** `ExternalAssets/Incoming/kenney-input-prompts/extracted/` (779 files in all, 18 MB; the pack covers many controllers, only `Keyboard & Mouse/` is relevant).
- **Folder `extracted/Keyboard & Mouse/`:** `Default/` (64 x 64 PNG, 257 files), `Double/` (128 x 128 PNG, same names), `Vector/` (SVG), `Fonts/` (an icon font, not needed).
- **Style chosen:** the plain `keyboard_<key>.png` set (a white keycap with a dark glyph, transparent corners), at **`Double/` 128 x 128** for crisp 1080p and 4K use (downscale in Unreal; 64 x 64 is too soft at the planned prompt sizes). The kit is designed for dark backgrounds (the pack preview sits on a dark grey field). The `_outline` variants (white outline, transparent fill) are the alternative for the "high-contrast prompts" option or a quieter look. Mouse icons are white with the pressed button in red.
- **Needed keys, file names (same in `Default/` and `Double/`; add `_outline` for the outline variant):**
  - Letters: `keyboard_a.png` to `keyboard_z.png`; digits `keyboard_0.png` to `keyboard_9.png`.
  - Arrows: `keyboard_arrow_up.png`, `keyboard_arrow_down.png`, `keyboard_arrow_left.png`, `keyboard_arrow_right.png`.
  - Modifiers: `keyboard_shift.png`, `keyboard_ctrl.png`, `keyboard_alt.png`. There are also icon-style variants `keyboard_shift_icon.png`.
  - Others: `keyboard_space.png`, `keyboard_escape.png`, `keyboard_tab.png`, `keyboard_enter.png`, `keyboard_backspace.png`. Icon-style alternatives exist: `keyboard_space_icon`, `keyboard_tab_icon`, `keyboard_backspace_icon`.
  - Mouse: `mouse_left.png`, `mouse_right.png`, `mouse_scroll.png`, `mouse_scroll_up.png`, `mouse_scroll_down.png`, `mouse.png` (blank mouse), `mouse_side_back.png`, `mouse_side_forward.png`.
- **Caveat, middle button:** the pack has **no file named `mouse_middle`**. `mouse_scroll.png` shows only the wheel highlighted in red, which doubles as the middle-click icon (viewed at `Double/mouse_scroll.png`). Use it for both the wheel and the middle button.
- **Also present, not needed for the plan:** `keyboard_return.png`, F1 to F12, `keyboard_delete`, punctuation keys, `keyboard_any.png`, `keyboard_arrows*.png`. The rebinding list may want punctuation and F-keys later; they are in the same folder.
- **Suggested import (P18-2):** only the keys the game can bind (letters, digits, arrows, Shift, Ctrl, Alt, Space, Esc, Tab, Enter, Backspace, F1-F12, the mouse buttons, wheel up and down) to `/Game/LastBell/UI/KeyIcons/T_Key_<Key>`, sRGB, UI texture group, no mips, 128 x 128. About 70 textures, well under 5 MB.

## 3. Kenney UI sounds (CC0)
- **Packs:** Kenney "Interface Sounds" (v1.0, 100 files, 2020; `https://kenney.nl/assets/interface-sounds`) and Kenney "UI Audio" (50 files; `https://kenney.nl/assets/ui-audio`). Both are listed on kenney.nl as CC0.
- **Why a mirror:** `kenney.nl` answers `403 Forbidden` to command-line downloads, and the in-browser download did not land on disk either. The official zips were therefore **not** obtained, and no further attempt was made to get round the block. The files come from public GitHub repositories that repackage the unmodified Kenney sounds for Godot:
  - `https://github.com/Calinou/kenney-interface-sounds` (`master` archive, 1,727,059 bytes, SHA-256 `5dcfb259d889a6b672c308c4cc93360702125f2b177715f540cb05d7875e8c4c`);
  - `https://github.com/Calinou/kenney-ui-audio` (`master` archive, 1,697,135 bytes, SHA-256 `65512b5436e68d8941c0f615bac92ae519e37dc80bb3f7fbb3f517bd8e652620`).
  - Their READMEs state that the Ogg Vorbis originals were converted to WAV losslessly (a conversion of an already lossy codec: no extra loss, but no extra quality either). The packaging is by a third party (Calinou); the sounds are by Kenney.
- **Licence evidence:** each folder keeps Kenney's own licence text:
  - `extracted_kenney-interface-sounds/kenney-interface-sounds-master/addons/kenney_interface_sounds/LICENSE.txt`: "Interface Sounds (1.0), Created/distributed by Kenney (www.kenney.nl), Creation date: 11-02-2020, License: (Creative Commons Zero, CC0)";
  - `extracted_kenney-ui-audio/kenney-ui-audio-master/addons/kenney_ui_audio/LICENSE.txt`: "UI SFX Set by Kenney Vleugels (Kenney.nl), License (Creative Commons Zero, CC0)".
  - The GitHub licence field reads "NOASSERTION" only because the repo's own tooling files carry no SPDX tag; the audio licence is Kenney's CC0 above. **The owner may prefer to re-download the official zips by hand** (below) and swap the folder; the file names are the same.
- **Format:** WAV 44.1 kHz 16-bit; both mono and stereo files. Peak about -1 dBFS. Prep to the P16 standard (48 kHz, peak target, mono for 2D UI where it makes sense) in P18-2.
- **How the picks were made:** nobody could listen. The picks below come from measurement (`scratchpad` script: duration, peak, RMS, an estimate of the dominant frequency from zero crossings, time to 90% of the energy) plus Kenney's own file naming, looking for short, quiet, low-frequency (dull, wooden or soft, not glassy or beepy) sounds. **A listening pass is still needed** (P18-2 or the owner); the alternates are there for that.

Measured candidates (dominant frequency is a rough proxy for brightness; lower reads duller):
| Role | File (pack) | Duration | RMS | ~Freq | Note |
|---|---|---|---|---|---|
| Hover | `click_001.wav` (Interface) | 0.11 s | -27 dB | 290 Hz | Quietest and dullest: a soft thump. First choice |
| Hover | `rollover2.wav` (UI Audio) | 0.06 s | -26 dB | 1.5 kHz | Short, quiet; may be a little airy |
| Hover | `rollover5.wav` (UI Audio) | 0.13 s | -28 dB | 2.3 kHz | Quiet (peak -9 dB); brighter |
| Hover | `drop_003.wav` (Interface) | 0.20 s | -20 dB | 330 Hz | A heavier thud; use at a low volume |
| Select | `select_005.wav` (Interface) | 0.38 s | -19 dB | 560 Hz | Dull, with a short tail. First choice |
| Select | `select_004.wav` (Interface) | 0.38 s | -19 dB | 910 Hz | Same family, a touch brighter |
| Select | `click_005.wav` (Interface) | 0.02 s | -16 dB | 110 Hz | A very short low knock; wooden |
| Select | `select_007.wav` (Interface) | 0.06 s | -15 dB | 980 Hz | Short and louder; trim the gain |
| Back | `back_002.wav` (Interface) | 0.09 s | -17 dB | 190 Hz | The dullest of the four. First choice |
| Back | `back_004.wav` (Interface) | 0.09 s | -18 dB | 580 Hz | |
| Back | `back_003.wav` (Interface) | 0.09 s | -20 dB | 660 Hz | |
| Back | `back_001.wav` (Interface) | 0.07 s | -22 dB | 860 Hz | The softest |
| Slider tick | `tick_004.wav` (Interface) | 0.06 s | -16 dB | 2.0 kHz | Ticks are mid-range; first choice |
| Slider tick | `toggle_004.wav` (Interface) | 0.07 s | -17 dB | 1.96 kHz | |
| Slider tick | `click_003.wav` (Interface) | 0.02 s | -19 dB | 1.0 kHz | Very short; good for fast drags |
| Slider tick | `click_002.wav` (Interface) | 0.01 s | -16 dB | 860 Hz | The shortest and driest |

- **Suggested set for P18-2 (to confirm by ear):** hover `click_001`, select `select_005`, back `back_002`, slider tick `tick_004`. Rename on import to `SFX_LB_UI_Hover`, `SFX_LB_UI_Select`, `SFX_LB_UI_Back`, `SFX_LB_UI_SliderTick`.
- **Likely to fail by ear:** anything above about 4 kHz (`tick_001`, `tick_002`, `select_008`, `click_004`, `close_*`, `open_*`: glassy or beepy) and the `glitch_*`, `glass_*`, `bong_001`, `confirmation_*`, `error_*` families: not monastic. Kept out of the lists on purpose.
- Slider drags will retrigger the tick quickly: the UI sound player should rate-limit (plan section 2 gives `ULBUISubsystem` the UI sounds) and apply a little pitch variation.

## 4. What the owner must do manually (optional)
- **Official Kenney zips (optional):** the files used for the sounds are CC0 copies via GitHub. To use Kenney's originals instead, download in a normal browser (click "Download" then "Continue without donating"):
  - `https://kenney.nl/assets/interface-sounds` (`kenney_interface-sounds.zip`, Ogg, 100 files);
  - `https://kenney.nl/assets/ui-audio` (Ogg, 50 files);
  - and unzip next to the existing folders in `ExternalAssets/Incoming/kenney-ui-audio/` (the file names match the WAV mirror's, e.g. `click_001.ogg`).
- Nothing else is blocked: the fonts and the input prompts are complete.

## 5. Verification record
- `git check-ignore -v` confirmed all three new folders are covered by `.gitignore` line 21 (`ExternalAssets/Incoming/`).
- Nothing downloaded was executed. Archives were only unzipped; the TTFs were checked for a valid TrueType header; WAVs were only read as data by a Python script run with `-I`.
- Not done: Unreal import, listening to the sounds, a visual review of every PNG (one `Double/mouse_scroll.png` and the pack preview sheet were viewed).
