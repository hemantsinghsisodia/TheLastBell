# P17-3.7 item 3: villager candidates (CC0 animated human)

Date 2026-11-11, asset-curator. Brief: an adult in plain or medieval clothes (hood or cloak ideal), rigged, with a walk cycle (idle a bonus, a lantern pose a bonus), CC0 only, seen from about 60 m at night.

Note on the tool: `3d-assets-local` does not index Quaternius (its `search_assets` returned only CGTrader, BlenderKit, Grab3D and Sketchfab for human characters; the Quaternius, Kenney and Poly Haven catalogues have no animated human there). The Quaternius candidates below were found on quaternius.com and quaternius.itch.io, and the licence text was read from the pages and from the files' own `License_Standard.txt` / `License.txt`. OpenGameArt answered 403 to the page fetch and was not worked around.

## Candidates

### 1. Quaternius Modular Character Outfits - Fantasy [Standard] + Universal Animation Library 1 and 2 [Standard] (PICK)
- Provider and URLs: Quaternius (itch.io, "name your own price", $0 path used).
  - https://quaternius.itch.io/modular-character-outfits-fantasy (280 MB zip)
  - https://quaternius.itch.io/universal-animation-library (15 MB zip)
  - https://quaternius.itch.io/universal-animation-library-2 (17 MB zip)
- Licence: CC0 1.0 (page text "Free to use in personal, educational and commercial projects (CC0 License)"; also `License_Standard.txt` and `License.txt` inside each zip, which quote the CC0 1.0 Public Domain Dedication).
- Animations: not in the outfit pack; they come from the UAL packs, which use the identical 65-joint skeleton (verified: the joint lists are equal).
  - UAL1: `Idle_Loop`, `Idle_Torch_Loop`, `Walk_Loop`, `Walk_Formal_Loop`, `Jog_Fwd_Loop`, `Sprint_Loop`, plus 36 more (43 clips with `A_TPose`).
  - UAL2: `Idle_Lantern_Loop`, `Walk_Carry_Loop`, `Zombie_Walk_Fwd_Loop`, `Idle_FoldArms_Loop`, plus about 38 more (43 clips).
  - Root-motion (`_RM`) variants are included.
- Rig: UE-mannequin-style humanoid (`root`, `pelvis`, `spine_01..03`, `neck_01`, `Head`, `clavicle/upperarm/lowerarm/hand_l|r`, full fingers, `thigh/calf/foot/ball_l|r`), 65 joints, designed for retargeting to the UE5 mannequin. Hand bone for the lantern: `hand_r`.
- Poly count (read from the glTF accessors): Male_Ranger 26,982 tris (9 meshes: hood 2,136; arms 4,928; bracers 3,636; body 2,998; belts 2 x 804; boots 9,172; legs 1,128; pauldron 1,376). Male_Peasant 12,894 tris (4 meshes).
- Look: stylised-realistic game-art proportions (see the pack's Preview.jpg). Male_Ranger is hooded, leather jerkin, belts, bracers, boots: the best match for "hooded villager". Male_Peasant is shirt, trousers, boots, no head. Textures 4K-class PNG (T_Ranger_BaseColor 6.6 MB, Normal 12.7 MB, ORM 10.8 MB).
- Formats: glTF (+ .bin) for Unreal/Godot, FBX for Unity, in both Outfits (combined) and Modular Parts folders. UAL: GLB and FBX.
- Risks:
  - The outfits ship without a head (the Readme says the head comes from the Universal Base Characters kit); Male_Ranger hides this under the hood, Male_Peasant does not. At 60 m at night the hood interior reads as a dark void, which suits the shot; if it does not, add a head from Universal Base Characters [Standard] (122 MB, same rig, CC0).
  - Fantasy-ranger look (pauldron, bracers); the pauldron and bracer meshes can be dropped from the import. Colours are saturated: tone down in the material (the plan says "toned dark").
  - glTF import into UE 5.8 (Interchange) is untested here; FBX is also supplied. The skeleton differs from the project's `SK_Warden` and from the mannequin; the animations only fit this rig (or via a retarget).
  - 27k tris and 4K textures are far above what a 60 m figure needs; use a lower texture resolution or an LOD.

### 2. Quaternius Universal Base Characters [Standard] + Universal Animation Library
- https://quaternius.itch.io/universal-base-characters, CC0 (page and licence text read), Standard is 122 MB with 2 base models and 5 hairstyles, glTF/FBX, same humanoid rig and UAL animations.
- Look: plain minimal black clothing, no cloak or hood. Good as a head donor for candidate 1. Not downloaded. Risk: no period clothing.

### 3. Quaternius Ultimate Animated Character Pack / Animated Men Pack / RPG Character Pack
- https://quaternius.com/packs/ultimatedanimatedcharacter.html (50+ characters), /packs/animatedmen.html (4 humans), /packs/rpgcharacters.html (6 models). All CC0 per the pack pages, FBX/OBJ/Blend, "many animations".
- Not downloaded: the pages give no character list, animation list or rig, and the download buttons point at a placeholder; the older packs are cartoon low-poly (risk of a cartoon look and a different rig per character). Fallback if candidate 1 fails in Unreal.

### 4. Quaternius LowPoly Animated Knight
- https://quaternius.itch.io/lowpoly-animated-knight, CC0, FBX/OBJ/Blend, 8 MB, animations Idle, Walk, Run, Death, etc. A knight in armour, not a villager. Not downloaded.

### 5. Grab3D CC0 characters (Casual Man, Elderly Man, Farmer, and others)
- e.g. https://grab3d.com/models/characters/man/ (`grab3d:man`, `grab3d:elderly-man`, `grab3d:farmer`), CC0, downloadable through the tool (rigged GLB 12-13 MB).
- Rigged only, no animation clips, modern clothes (bomber jacket, cardigan) and stylised proportions. Rejected: no walk cycle.

### Rejected, not CC0 or not downloadable
BlenderKit "Royalty Free" characters (chroma 3D walk/idle series: licence is not CC0, several are paid), CGTrader animated humans (account needed, paid or custom licence), Sketchfab (no animated humans in the CC0 set; downloads need a login).

## Pick: candidate 1, `Male_Ranger` (hooded), with `Walk_Loop` / `Idle_Lantern_Loop` / `Walk_Carry_Loop`
Why: CC0 verified at the file level; hood, plain leather clothes, adult proportions; a skeleton with `hand_r` and a ready lantern-hand clip (`Idle_Lantern_Loop`) plus `Walk_Carry_Loop` (arms held forward, to be checked against a lantern held at the side) and a plain `Walk_Loop`; the rig matches the UE5 mannequin layout so the clips can be retargeted if needed.

## Downloaded (git-ignored, verified with `git check-ignore`)
`ExternalAssets/Incoming/villager_quaternius_peasant/`
- `Modular Character Outfits - Fantasy[Standard].zip` (294,347,394 bytes)
- `Universal Animation Library[Standard].zip` (15,904,933 bytes)
- `Universal Animation Library 2[Standard].zip` (18,735,003 bytes)
- `extracted/` (read-only extraction of the Male outfits and Male modular parts in glTF, the Male outfits in FBX, licence, readme, preview) and `extracted_anim/` (the UAL1 and UAL2 GLB/FBX and licence files). Nothing was executed or imported.

Folder name says "peasant" because that was the first plan; the recommended mesh is `Male_Ranger` (hooded). Import is for P17-5a-2.
