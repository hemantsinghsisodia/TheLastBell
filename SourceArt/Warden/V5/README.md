# Warden Art V5 — review build

Current master: `Warden_Rigged.blend`. Current exports: `exports/` (three mesh FBXs and three animation FBXs, explicit centimetres). Current maps: `textures/` (20 PNGs: wool/skin 4K, other material sets 2K, two wool detail maps 1K). Native Unreal assets live only in the isolated project's `/Game/WardenArtV5`, with a separate skeleton and review map. Revision 4 is preserved.

The matched Blender/Unreal materials apply wool brightness 0.4 and skin base-color multiplier 0.22 to keep the garment near-black and the hands subdued under the neutral review lights. These are material adjustments; source PNG resolution and packing are unchanged.

Implemented since the blockout: corrective hood/folds, opened mask window, shoulder weight transfer, reconstructed palms/digits/knuckles/tendon surfaces, new hand weights, new UVs and PBR bakes, unequal chain bind layout and per-frame clearance solving. Hands use fused and reduced triangulated surfaces, not manually authored quad topology. All 110 bone names and parents remain intact. Clips remain Idle 4s, Walk 2s and DoorwayStoop 3s at 30fps. LOD triangles are 75,764 / 37,882 / 18,941 with six slots and at most four normalized influences.

Verification: `reports/audit.json` covers structural data and sampled floor contact; `chain-collisions.json` checks every frame of every clip on every LOD for chain/wool surface intersections; `fbx-roundtrip.json` verifies all six imports and hierarchies. The isolated project's `Reports/validation-v5.json` checks saved references, texture settings and frame-by-frame animation positions against Blender. The V5 importer explicitly reimports updated textures, meshes and clips.

Visual review material: `previews/v5-neutral.png`, `v5-candle.png`, matched V4 views, `detail-*.png`, `silhouette-256.png`, and `Warden_V5_Turntable.mp4`. Actual Unreal images are in `../unreal_validation/Previews/V5`. Earlier blockout/clay images below are historical.

Acceptance remains incomplete: the hood and shoulder edges are more regular than the painted concept. Cloth edge thickness, fine hand/tendon transitions, attachment contact through every frame, close-view UV seams and temporal shimmering across LOD changes still require production art review. Automated structural/collision checks do not certify these visual requirements. The ZIPs are explicitly labelled review builds, not production-approved assets.

External automation uses installed Python 3.14.9 without pip. Blender scripts necessarily run in Blender's own embedded interpreter. Only WardenAssetValidation was launched; other Unreal projects are outside the workflow. The saved master is authoritative: rerunning an early build script alone will omit later corrections.

## Historical blockout checkpoint (superseded)

Status: IN PROGRESS. This is a shape study, not the completed revision-5 deliverable. Existing revision-4 Blender/Unreal packages remain current and untouched. Revision 4 was preserved under warden_asset/baselines/v4-dirty and unreal_validation/Baselines/v4-dirty.

Current file: Warden_ArtV5_Blockout.blend. Regenerate with installed Python 3.14.9 running scripts/run_blender.py blockout_v5.py. No pip.exe or dependency installation. The script starts from the preserved v4 master. Outputs are confined to this directory.

Implemented: forward upper-body silhouette; narrower shoulders; lowered/lengthened hands and arms; recessed mask; bent hood tip; two overlapping shoulder layers; vertical hanging robe strips; twisted rope belt; unequal wrist and neck chains; narrower/lower boots; clay front/side/three-quarter renders. All 110 bone names and parents are preserved, but bind positions changed. Original-bind.json records the original joints. Current geometry is below the 100k LOD0 ceiling.

Known unfinished work: the cloak still needs more natural draping and fewer regular edge patterns; hands need actual retopology, knuckle anatomy and finger curl; added tendon strips need integration rather than surface tubes; hood folds need sculpting; confirm mask eyes remain open and the 3–5 cm recession is geometrically correct; inspect all cloth/skin intersections. Existing UVs on source geometry are retained; additions use temporary smart-project UVs and their materials are NOT final. The clay images deliberately override materials.

Do NOT import this blockout as a completed asset. Old actions remain in the file but have NOT been adapted to the changed bind pose. New chain geometry is provisionally weighted; chains require new bind layout and clearance rebakes for all three existing clips. No revision-5 LODs, FBX exports, 20-map bake, validation report, turntable, Unreal import or ZIPs have been completed.

Next sequence: resolve shape review; rebuild hands and garment surfaces; finish UVs; bake 20 maps (skin 4K, chain iron 2K); adapt existing Idle/Walk/Stoop clips keeping durations/30fps and root motion policy; rebake chains; regenerate LODs under 100k/50k/20k; test all poses, ground/cloth clearance and 2.35 m doorway; matched v4/v5 neutral/candle renders plus 256px and 5–10m silhouette checks; close-ups at 0.5m; turntable; explicit centimetre FBX exports; separate /Game/WardenArtV5 assets/skeleton in the authorized WardenAssetValidation project; saved-reference/texture/animation verification; CRC/SHA packages.

Only the isolated WardenAssetValidation project is authorized. Never connect to another editor endpoint or modify TheLastBell. No Unreal session was launched for this shape study.
