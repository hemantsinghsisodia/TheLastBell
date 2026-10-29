# P10-3b: cloister pieces C1-C17 and Mechanism 3 pieces M1-M4 (Blender, headless)

Spec: `Docs/plans/P10_BELLTOWER_ART.md` amendment D1.3 / D1.4 (+ D1.11 errata). Output: `SourceArt/Cloister/` (40 FBX, `LB_Cloister.blend`, `cloister_report.json`). Renders: `Docs/ArtTest/belltower/p10_3b_*.png`.
Reuses `Tools/blender/kit/kit_lib.py` and `build_kit.py` by import (neither is modified). Blender 5.2, no GUI, no editor.

```
set B="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
%B% -b --factory-startup --python Tools/blender/belltower/build_cloister.py                         # 40 FBX + LB_Cloister.blend + cloister_report.json (about 12 s)
#   optional: -- --only Vault Pier --tag t1      (substring filter on the full mesh name; writes LB_Cloister_t1.blend, merges the report)
%B% -b --factory-startup --python Tools/blender/belltower/verify_cloister.py                        # re-imports every FBX, 40/40 (exit 1 on failure)
%B% -b --factory-startup --python Tools/blender/belltower/render_cloister.py -- --set all           # Cycles, p10_3b_*.png (about 20 min on CPU); --quick for 1/4-size previews
```

## Conventions
- 1 BU = 1 cm; authoring space = Unreal space numerically; FBX via `kit_lib.export_piece_fbx` (Y mirrored at export, see `Tools/blender/kit/README.md`). Seeds are the D1 seeds. **No UCX on any piece except `SM_LB_Prop_SmallBell_A` (one convex hull)**, as D1.5 says.
- Kit-family pieces always carry the three kit slots in order `MAT_Masonry, MAT_Trim, MAT_Rubble` (unused slots stay). Roofs: `MAT_Slate, MAT_Wood`. Garth bed: `MAT_Earth`. M1 `MAT_Bronze, MAT_Iron, MAT_Band`; M2 `MAT_Iron, MAT_Wood`; M3/M4 `MAT_Trim`.
- Vertex colour white, UV0 = kit box projection (1 UV = 100 cm), smooth by 30 deg.

## Pieces (bounds in UE cm, pivot at local 0; from `cloister_report.json`)
| Piece | Size | Bounds min .. max | Tris | Slots |
|---|---|---|---|---|
| `SM_LB_Cl_Wall40_400x1300_A` | 400x46x1300 | 0,-6,0 .. 400,40,1300 | 3880 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Wall40_400x1300_B` | 400x46x1300 | 0,-6,0 .. 400,40,1300 | 3706 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Wall40_100x1300` | 100x46x1300 | 0,-6,0 .. 100,40,1300 | 918 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Wall40_400x800_A` / `_B` | 400x40x800 | 0,0,0 .. 400,40,800 | 2478 / 2444 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Wall40_100x800` | 100x40x800 | 0,0,0 .. 100,40,800 | 512 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Wall40_400x450` / `100x450` | 400x40x450 / 100x40x450 | 0,0,0 .. L,40,450 | 1476 / 280 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Archway_500x40x1300` | 500x46x1000 | 0,-6,300 .. 500,40,1300 | 5156 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Archway_300x40x1300` | 300x46x970 | 0,-6,330 .. 300,40,1300 | 3479 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Pier_80x80x640` | 96x96x620 | -48,-48,0 .. 48,48,620 | 788 | Masonry, Trim, Rubble |
| `SM_LB_Cl_PierCorner_130x80x640` | 146x96x620 | -73,-48,0 .. 73,48,620 | 898 | Masonry, Trim, Rubble |
| `SM_LB_Cl_ArcadeArch_{120,170,220,270}x80` | span x 90 x 290 | 0,-45,0 .. span,45,290 | 898 / 1146 / 1370 / 1672 | Masonry, Trim, Rubble |
| `SM_LB_Cl_GarthWall_1100x100` / `800x100` | L x 34 x 100 | 0,-4,0 .. L,30,100 | 878 / 678 | Masonry, Trim, Rubble |
| `SM_LB_Cl_GarthBed_1100x800` | 1100x800x17.8 | 0,0,-8 .. 1100,800,9.8 | 13280 | Earth |
| `SM_LB_Cl_GraveSlab_200x80` | 200x80x8 | -100,-40,0 .. 100,40,8 | 152 | Masonry, Trim, Rubble |
| `SM_LB_Cl_GraveCross_60` | 34x8x60 | -17,-4,0 .. 17,4,60 | 70 | Masonry, Trim, Rubble |
| `SM_LB_Cl_GarthCross_350` | 120x120x350 | -60,-60,0 .. 60,60,350 | 248 | Masonry, Trim, Rubble |
| `SM_LB_Cl_Vault_Barrel_{830x640,770x640,770x640_Broken,770x980,570x980}` | length x span x 340 | 0,0,0 .. length,span,340 | 3012 (Broken 3304) | Masonry, Trim, Rubble |
| `SM_LB_Cl_Vault_Groin_{770x830,570x830,770x770,570x770}` | x span x y span x 340 | 0,0,0 .. Sx,Sy,340 | 17816 / 18288 / 16516 / 17864 | Masonry, Trim, Rubble |
| `SM_LB_Cl_LeanTo_1000x1050` | 1000x1050x24.3 | 0,0,-15 .. 1000,1050,9.3 | 21516 | Slate, Wood |
| `SM_LB_Cl_LeanTo_1000x1050_Hole` | 1000x1050x102.8 | 0,0,-93.5 .. 1000,1050,9.3 | 12324 | Slate, Wood |
| `SM_LB_Cl_CellDoorFrame_150x270` | 150x10x270 | -75,-8,0 .. 75,2,270 | 656 | Masonry, Trim, Rubble |
| `SM_LB_Cl_StairHouseGable_380x40x650` | 380x40x650 | 0,0,0 .. 380,40,650 | 1896 | Masonry, Trim, Rubble |
| `SM_LB_Cl_StairHouseRoof_420x640` | 420x640x217 | -0.27,0,-17.4 .. 420.3,640,200 | 8336 | Slate, Wood |
| `SM_LB_Prop_SmallBell_A` | 24x24x32 | -12,-12,-28 .. 12,12,4 (z 0 = crown top) | 1628 | Bronze, Iron, Band; 1 UCX |
| `SM_LB_Prop_SmallBellBracket_A` | 34x22x47 | 0,-11,-25 .. 34,11,22 | 892 | Iron, Wood |
| `SM_LB_Prop_BellPlaque_A` | 4x34x34 | 0,-17,-17 .. 4,17,17 | 220 | Trim |
| `SM_LB_Prop_InscriptionTablet_A` | 4x120x30 | 0,-60,-15 .. 4,60,15 | 220 | Trim |

## Deviations and readings of D1 (each is also in `cloister_report.json` notes)
1. **Four-centred section (`four_centred(span, rise, ...)`).** D1 fixes the lower arcs at span/4 and says "solve the upper radius numerically". That leaves one degree of freedom (the tangent angle). It is fixed by the apex slope (9 deg) for the archways and by upper radius = span for the vault sections.
   Numbers: C4 (500, rise 120) has **no pointed solution with r1 = span/4 = 125** (the upper-arc centre would be left of the axis for every tangent angle), so r1 is reduced to 87.5 (upper R 2959, practically straight flanks). C5 keeps r1 = 75 (R2 226.5). Vault sections keep r1 = span/4: 830 -> R2 830, 770 -> 770, 570 -> 570.
2. **Archway pieces (C4, C5)** hold no mesh below the springing line (full-width opening), so bounds min z is 300 / 330, not 0; the pivot stays at floor level z 0. Voussoir ring radial width 40, clipped to x 0..span. The drip course (y -6..0) is on the inner face only, so bounds y are -6..40; the same for C1.
3. **Drip projects into y -6..0**: C1 and C4/C5 bounds are 46 deep, the pivot stays on the inner face (y 0).
4. **Piers (C6/C7):** base, capital (+8) and coping (+5) project on all four faces (the piers sit in rows on two axes). **Top is z 620** (D1.11 accepts the name `x640`). Bounds are 96 x 96 (146 x 96).
5. **C8:** the coping projects 5, so y bounds are -45..45 (body faces stay at +-40). Voussoir ring radial width 30, keystone seam with a 0.3 chamfer so the intrados apex stays at 0.742 x span (measured within 0.3).
6. **C9:** y -4..30 (coping), local y 0 = walk-facing face. **C10:** closed solid, z -8..9.8; the outer 35 cm band is flat at z -1 (D1.11 errata 7); six hollows under the slab centres; flat apron (r 70) at the cross. **C11:** bottom-centre pivots (D1.3 gives centres; D1.11 accepts).
7. **C12 naming.** The first number is the **span** (local y), the second the **length** (local x): `830x640` is 640 along the walk and 830 across. The section rise 340 is the **extrados** apex (bounds top z 340); the intrados apex is about z 313-314, rib soffit 25 below that. End ribs are 15 wide (two adjacent bays make one 30 rib), the mid rib is 30 wide. `_Broken`: ragged hole through shell and ribs inside x 36..612 (open over x 50..600 for y = mid +-70), the mid rib is cut into two stubs, the end arches stay (apex z 340 intact).
8. **C13:** wall ribs sit against the wall faces (x/y 30..60 from the piece edge, because the pieces tuck 30 into the walls). Outer sides: SW x0+y0, SE x1+y0, NW x0+y1, NE x1+y1. Diagonal ribs start at (25, 25) (the intrados springing) and meet at the centre.
9. **C14 hole:** the polygon lies inside x 150..850, y 0..800 and contains x 170..830, y 30..780 (jagged boundaries cannot fill the full rectangle); verified open for x 190..810, y 40..760. Slates/boards/battens are omitted, rafters are cut at the hole's upper edge, 3 rafters (x 330, 570, 750) are snapped and droop 40 / 80 / 0 (lowest z -93.5).
10. **C15 (cell door frame):** D1 puts the "recessed back panel at y +2", which is **inside the wall** (the wall piece is solid) and would be invisible. The back panel is 4 thick (y -2..+2): its visible front face is at **y -2**. A door leaf "1 cm in front of the back panel" therefore sits at **y -3**, inside the 8 cm frame depth (P10-6b/P10-5 take this number, not +1). The frame is a surround of stacked jamb blocks and a straight-sided pointed head; the opening is 110 x 250, shoulders z 220, apex 250, overall 150 x 270.
11. **C16:** the rake coping is flush with the ashlar (no projection) so the thickness stays exactly 40.
12. **C17:** the "eaves x 0 / 420 at z 0" plane is the slate **top** surface; the slate planes rise 196 to x 210, the ridge cap tops out at z 200. Rafters 12 x 15 at 60 c/c and 4 tie beams are visible from below. The lowest point (rafter tails) is z -17.4.
13. **M2:** the hook at x 25 hangs from the arm and its tip (z -5, running along Y) passes through the bell's loop (the child BP puts the loop centre at bracket z -5).

## Findings for the lead / generator
- **Roof vs vault clearance (D1 numbers).** With springing 560, crown 900 and the lean-to slate plane at 640 (eaves) -> 1200, the vault extrados stays below the slate top (smallest margin: S walk 7 cm, N 16 cm, W 16 cm, E 39 cm) but **enters the 24 cm roof build-up** (rafters + sarking): the rafter undersides are crossed by up to 21 cm on the S walk, 12 cm on N and W, none on E. It is hidden inside the roof void and nothing pokes through the slates; if it ever matters, raise the eaves (D1: 640) by about 25 cm or lower the vault rise. See `p10_3b_section_s_bay_roof_clearance.png`.
- **N roof panels:** the renders use the D1.11 errata layout (W 9500-10650 x1.15, hole 10650-11650, E 11650-12000 x0.35).
- Panel frame for the roof rotators: with local x along the eaves and local y up the slope, local z (the normal) points up only if x runs **-X** for the S walk, **+X** for N, **+Y** for W and **-Y** for E (the face-frame types). Placing the S panels with x = +X would flip them.

## Render notes
Renders are Cycles. Authoring space is the Y-mirror of Unreal's, so the render camera is mirrored (scale -1 in x) and the text is pre-mirrored: the images show the Unreal-handed view (bells I..IV left to right when facing +X). Everything that is not a deliverable mesh is render-only dressing (stand-in floors, the tower mass, door leaves, rubble, grass, lights, the numeral and inscription text).
