# P9-2: Dungeon kit measurements, test assembly, crypt survey

Phase 9 crypt art, task P9-2 (technical-artist; the editor was used read-only for Block C). All values are cm in Unreal units. Captures are in this folder (`kit_test_*.png`, `kit_pieces_*.png`).

**Contents:** 1 relocation summary (Block A) | 2 measurement table (Block B) | 3 per-piece findings | 4 grid summary | 5 test assembly findings | 6 crypt survey (Block C).

Measuring method: `get_bounds` (mesh-local, before any scale), `get_triangle_count` (source count, taken before Nanite was enabled), the mesh `BodySetup`, `trace_world` grids against the placed meshes (the trace hits the render triangles, not just the hulls), and captures in `L_Test_ArtKit` at (20000..35000, 20000..30000), a throwaway area. The pack's own demo maps do not exist in TheLastBell, so they were skipped (the staging project was not opened).

---

## 1. Block A: relocation summary

- **Moved:** 67 of the 88 files in `/Game/Dungeon` to `/Game/LastBell/ThirdParty/Fab/Dungeon/` (same sub-folders): 16 meshes, 13 MIs, `M_Tiles`, 37 textures. `/Game/Dungeon` is deleted in the editor and on disk (no leftover files; a byte scan of all `.uasset`/`.umap` finds no `/Game/Dungeon/` reference).
- **Merged duplicates (21), all consolidated onto the existing relocated copies:**
  - `M_Base` and `M_Props`: expression counts equal (13 / 5), parameter sets equal (8 / 4), every expression's parameter name, default and texture equal.
  - `MI_Skeleton_Pile_05`, `MI_Torch`, `MI_Torture_Devices_Cage`: parent, scalar, vector and texture overrides equal.
  - 16 textures (`T_Gound_Stone_BC`, `T_Dungeon_beam_*` x3, `T_Skeleton_Pile_05_Skeleton_*` x3, `T_Torch_*` x3, `T_Torture_Devices_Breaking_Wheel_*` x3, `T_Torture_Devices_Cage_*` x3): identical source file MD5 in both copies.
  - Re-pointing: `MI_Stone_00..03`, `MI_Metal_Bars`, `MI_Skeleton_Pile_05_Pole` re-parented to the existing `M_Base`; `MI_Dungeon_beam/door/halfbeam/toplock/window` to the existing `M_Props`; `MI_Dungeon_beam` textures to the existing `T_Dungeon_beam_*`; `M_Tiles` BC to the existing `T_Gound_Stone_BC`; `SM_Skeleton_Pile_05`, `SM_Charcoal_Pit`, `SM_Torture_Devices_Cage_Open` slots to the existing `MI_Skeleton_Pile_05`, `MI_Torch`, `MI_Torture_Devices_Cage`. Override counts on all re-parented MIs were verified unchanged.
  - `MI_Dungeon_beam` and `MI_Tiles` kept a stale reference to a deleted duplicate texture inside the saved package (the editor's cached texture list), so each was re-created clean (same parent and values, read back equal), assigned to its meshes, and renamed over the old name.
- **MaxTextureSize** (source sizes recorded):

| Group | Textures | Source | Cap |
|---|---|---|---|
| `Stone_00..03` (wall, arch, pillar MIs) | BC, N, AO_R_MT x4 | 4096 | **2048** |
| `Gound_Stone` (ground, `MI_Tiles`) | AO_R_MT, N | 2048 | 2048 (no-op) |
| `Gound_Stone/T_Ground_Stone_H` | height | 1024 x 512 | 2048 (no-op) |
| `Gound_Stone/T_Stone_Wall_*` (roof, `MI_Stone_Wall_00`) | BC, N, AO_R_MT, H | 2048 | 2048 (no-op) |
| `Gound_Stone/T_Gound_Stone_BC` (existing, shared with `M_Base_01`) | BC | 2048 | **raised 1024 -> 2048**: the new ground (`M_Tiles`) uses it; also used by the existing `M_Base_01`; about +2 MB resident |
| `Metal_Bars`, `Props` (door, halfbeam, toplock, window), `Skeletons` (Pile_05 pole) | BC, N, AO_R_MT x6 sets | 4096 | **1024** |
| `T_Dungeon_beam_*` (existing, used by `SM_Dungeon_beam`) | | 4096 | unchanged at 2048 (P8-4a) |

- **Nanite:** on for `SM_Wall_00/01`, `SM_Arch`, `SM_Pillar`, `SM_Roof`, `SM_Ground`, `SM_Ground_01`, `SM_Dungeon_beam`, `SM_Dungeon_halfbeam` (fallback mesh counts: 12472, 12952, 6184, 6116, 256, 255, 251, 274, 295). Off for bars, door, window, toplock, charcoal pit, open cage and the bone pile. **Heavy ones left off, as asked: `SM_Skeleton_Pile_05` 33,138 tris and `SM_Torture_Devices_Cage_Open` 8,756 tris** (the existing `Pile_00..04` are 12k-83k and also non-Nanite since P8). Say the word if the owner wants the pile on Nanite.
- **Memory impact (estimate; there is no tool for `stat streaming` here):** textures stay on disk at full source (the `.uasset`s hold the 4096 sources: **+570 MB of Git LFS**, 565 MB of it textures, 4.4 MB meshes). Resident worst case with mips, BC1/BC5, at the caps: Stone_00..03 4 x 10.7 = **42.7 MB**, Stone_Wall 13.3 MB, Gound_Stone 10.7 MB (BC now 2048: +2.0 MB), six props sets 6 x 2.7 = **16 MB**: about **83 MB**, versus about 450 MB uncapped at 4096. Texture streaming will keep less than this resident. Mesh memory is negligible (Nanite fallbacks plus 7 non-Nanite meshes under 35k tris each).
- **Material compile:** `M_Tiles` (18 expressions: 6 scalar params, 4 texture params, one `TextureCoordinate`, one `VertexNormalWS`, 6 multiplies; `TwoSided` on; displacement scaling default, tessellation off), `M_Base` (13) and `M_Props` (5) recompiled with no error and no log error. **Shader instruction counts could not be read through MCP** (no tool exposes the Material Stats panel); all three are small, single-pass opaque DefaultLit. They are not flagged `bUsedWithNanite`; the editor handles that on first use and all Nanite pieces rendered correctly in the test assembly. The owner can read instruction counts in the Material Editor Stats if wanted.
- Side effect: recompiling `M_Base` and `M_Props` re-saved them (binary-only change, parameters identical); they appear as modified in the commit.

---

## 2. Block B: measurement table

Frame: UE axes, mesh local space, before any actor scale. "Pivot" is where local (0,0,0) sits relative to the bounds. "Tris" are the source triangle counts (LOD0, taken before Nanite). Every mesh has one LOD, default collision profile `BlockAll`, QueryAndPhysics.

| Mesh | Bounds min | Bounds max | Size (X x Y x Z) | Pivot | Tris | Nanite | Material slots -> MI | Simple collision | Trace flag |
|---|---|---|---|---|---|---|---|---|---|
| `SM_Wall_00` | -320.6, -77.4, -1.3 | 320.6, 77.4, 501.7 | **641.2 x 154.8 x 503.0** | X centre, Y centre (thickness), Z bottom (z=0 is 1.3 above the lowest point) | 35,712 | on | 4: `M_Stone_01`->MI_Stone_02, `M_Stone_02`->MI_Stone_03, `M_Stone_00`->MI_Stone_01, `M_Stone_03`->MI_Stone_00 | 1 convex hull (33 verts) = the bounds block; blocks | UseDefault |
| `SM_Wall_01` | -320.6, -77.4, -1.3 | 320.6, 77.4, 501.7 | **641.2 x 154.8 x 503.0** | same as Wall_00 | 36,784 | on | 4: MI_Stone_02/03/01/00 (slots `MI_Stone_02`...`MI_Stone_00`) | 1 convex hull (33 verts) = the bounds block; **the niche is not carved** | UseDefault |
| `SM_Arch` | -96.2, -81.5, -0.4 | 215.2, 73.6, 502.9 | **311.4 x 155.1 x 503.3** (a **half** arch) | X = the leg's inner face (inner face at x -3.4, opening runs toward +X), Y centre (-3.9 offset), Z bottom | 15,100 | on | 4: MI_Stone_02/03/01/00 | 1 convex hull (34 verts) that **fills the whole bounds, opening included** | **ComplexAsSimple** (needed: the hull would close the opening) |
| `SM_Pillar` | -62.1, -70.7, -1.3 | 88.3, 75.7, 462.7 | **150.4 x 146.4 x 464.0** | **13.1 cm off the column axis in X, 2.5 in Y** (axis at about (13.1, 2.5)); Z bottom | 11,456 | on | 3: MI_Stone_02/03/01 | 1 convex hull (32 verts), the solid prism; blocks | UseDefault |
| `SM_Roof` | -239.1, -239.1, -295.8 | 239.1, 239.1, 2.4 | **478.2 x 478.2 x 298.2** | X/Y centre, **Z at the crown** (shell hangs 296 below, 2.4 above) | 512 | on | 1: MI_Stone_Wall_00 | 1 convex hull (24 verts) over the bounds | **ComplexAsSimple** |
| `SM_Ground` | -120.0, -120.0, -20.0 | 120.0, 120.0, 20.0 | 240.0 x 240.0 x 40.0 (walkable surface **200 x 200**) | X/Y centre, **walking surface at z = 0.0** (centre of the 40 thickness is not the surface) | 512 | on | 1: MI_Tiles | none | **ComplexAsSimple** |
| `SM_Ground_01` | -120.0, -120.0, -28.9 | 120.0, 120.0, 20.0 | 240.0 x 240.0 x 48.9 (surface 200 x 200) | same as Ground; centre line is a gutter 8.9 deep | 512 | on | 1: MI_Tiles | 1 convex hull (8 verts) -100..100, z -9..0.1 | **ComplexAsSimple** |
| `SM_Bars` | -117.9, -4.3, -0.5 | 115.1, 4.3, 235.3 | 233.0 x 8.6 x 235.8 | X centre (-1.4), Y centre, Z bottom | 416 | off | 1: `WorldGridMaterial`->MI_Metal_Bars | 1 convex hull (32 verts) = a solid box over the bars | UseDefault |
| `SM_Dungeon_door` | 2.4, -43.3, 0.5 | 15.8, 52.6, 182.7 | 13.4 x 95.9 x 182.2 (leaf in the **YZ plane**) | Z bottom; X 2.4-15.8 (leaf centre plane x = 9.1); Y centre +4.6 | 814 | off | 1: MI_Dungeon_door | 1 convex hull (23 verts) | UseDefault |
| `SM_Dungeon_window` | 0.8, -45.2, -19.7 | 8.3, 47.0, 22.9 | 7.5 x 92.2 x 42.6 (grille in the YZ plane) | centred in Z (-19.7..22.9), Y centre +0.9, X 0.8-8.3 | 156 | off | 1: MI_Dungeon_window | 1 convex hull (22 verts) | UseDefault |
| `SM_Dungeon_toplock` | -36.8, -35.0, 0.4 | 36.5, 38.3, 19.9 | 73.3 x 73.3 x 19.5 (round collar, grating on top) | X/Y centre (-0.2, +1.7), Z bottom | 1,764 | off | 1: MI_Dungeon_toplock | 1 convex hull (24 verts) = a solid disc (the grating is not open for collision) | UseDefault |
| `SM_Dungeon_beam` | -17.2, -75.0, 0.0 | 17.7, 75.4, 19.8 | 34.9 x 150.4 x 19.8 | X/Y centre, Z bottom; long axis Y | 324 | on | 1: MI_Dungeon_beam | 1 convex hull (32 verts) | UseDefault |
| `SM_Dungeon_halfbeam` | -18.5, -36.2, 0.0 | 17.5, 45.2, 19.9 | 36.0 x 81.4 x 19.9 | X centre; Y -36 / +45 (a stub, pivot near its middle); Z bottom | 513 | on | 1: MI_Dungeon_halfbeam | 1 convex hull (31 verts) | UseDefault |
| `SM_Charcoal_Pit` | -13.8, -13.8, -0.2 | 13.7, 14.7, 25.3 | 27.5 x 28.5 x 25.5 | X/Y centre, Z bottom | 3,226 | off | 1: MI_Torch (existing) | 1 convex hull (34 verts) | UseDefault |
| `SM_Torture_Devices_Cage_Open` | -52.4, -74.6, 0.0 | 52.4, 74.6, 267.6 | 104.8 x 149.2 x 267.6 | X/Y centre, Z bottom | 8,756 | off | 1: `lambert3`->MI_Torture_Devices_Cage (existing) | 1 convex hull (32 verts) over the bounds | UseDefault |
| `SM_Skeleton_Pile_05` | -56.1, -59.8, -4.9 | 43.4, 70.7, 241.9 | 99.5 x 130.5 x 246.8 | X/Y about the pole; Z 4.9 below the pivot (bones) up to 241.9 (skull on a **pole**) | 33,138 | off | 2: `MI_Skeleton_Pile_05_Skeleton`->MI_Skeleton_Pile_05 (existing), `..._Pole`->MI_Skeleton_Pile_05_Pole | 1 convex hull (29 verts) | UseDefault |

Lightmap UVs are present (`LightMapResolution` 64-1300, coordinate index 1-2); irrelevant under Lumen.

---

## 3. Findings per piece

### SM_Wall_00 and SM_Wall_01
- **Both faces (+Y and -Y) are finished stone masonry**, with ragged relief: the face sits at |y| of about **69 from the centre line** (traced 64-74.5), so the mesh is 138 solid plus the relief up to 77.4. The top is capped with stone tops (`kit_test_wall_top.png`); the ends are ragged and **leave a 6-10 cm dark slit** when butted at the 641.2 bounds width. The front and back are 180-degree-rotation partners (the pattern at x on one face matches the other at -x).
- **`SM_Wall_00`: plain on both faces** (only small gaps between stones; one at x -100, z 125 on the -Y face, and its 180-degree partner, is deep enough that a trace reaches the centre line). `SM_Wall_01` is the same slab, plain on its **-Y face** and with **an arched niche carved into its +Y face**: niche x about -140...+60 (centre x about -40), z about 110...270 (base to crown), widest 200 at z 160-220, depth about 25 (the back of the niche is at |y| about 45 against a face at 70), arched head. The niche is only a recess in the render mesh; the collision hull stays a solid block that fills it, so nothing can enter the niche. Rotate the wall 180 degrees (yaw 180) to put the niche on the opposite side, or mirror with X scale -1 (the niche moves to x +40). See `kit_test_pillar_niche.png`.
- The wall is a **single solid slab**: 4 materials on the same mesh (4 stone MIs, `MI_Stone_00..03` on `M_Base`, each with Tint, Brightness, Roughness, Flatness).
- Collision: one convex hull, `BlockAll`. Nanite fallback 12.5-13k tris; 35-37k source tris each, so keep Nanite on.

### SM_Arch (half arch: use it in pairs)
- Cross-section in the XZ plane, thickness along Y (146 on the leg: faces at y -73.3 and +72.8; bounds -81.5..73.6). The leg occupies **x -95 ... -3.4** (about 92 wide), rises vertically to about z 290, then the intrados curves out and up: underside height z by x (traced): x 10: 298, 20: 326, 30: 349, 40: 358, 50: 370, 60: 381, 70: 393, 80: 401, 90: 406, 100: 410, 110: 414, 120: 419, **130-210: flat at about 420**. The cut edge is at x = 215.2 with the extrados (top) at about z 480-503.
- It is a **half**: place a second copy mirrored with **X scale -1** and its pivot at the mirror position. The pair meets at x = 215.2: **clear opening between the inner leg faces = 2 x 215.2 + 2 x 3.4 = 437.3 wide; clear height 420 at the crown (flat from x 130 to 300), 290 at the springing; the full piece top is 503.** In the test the halves met with a 0.003 cm gap (bounds), with a hairline of light visible at the joint (`kit_test_end_view.png`).
- To get a **300 opening** the pair was X-scaled by 0.686 (non-uniform), yaw 90: it reads acceptably (stones about 31% narrower in the ring; see `kit_test_end_view.png`). The unscaled pair (437 wide, 420 high) stands in `kit_test_arches.png`.
- **Both Y faces and the soffit are finished.** The wall (503) and the arch (503) have the same top height, so the arch springs level with a wall's top.
- Collision: ComplexAsSimple (15,100 triangles used as collision; expect the navmesh and the player capsule to hit the render mesh). The only hull is the full block, so **do not switch it to simple collision**.

### SM_Pillar
- A **hollow octagonal tube** of stacked ashlar courses: open at the top and bottom (`kit_test_pillar_top_hollow.png` shows the sky through it from above; a downward `trace_world` through its centre also misses). The roof above and the floor below hide it, but anything that shows its top or bottom (a broken pillar, a pillar in a pit) needs caps.
- Footprint (traced at z 20/100/230/360/440): about **x -56...+79 (135 across), y -60...+68 (128 across)** around an axis at (13, 4); the largest bounding extent is 150.4 x 146.4. Effective diameter about 130-135 across the flats; the courses vary by about +-8.
- Height 464 (z -1.3...462.7), about 39 cm lower than a wall; the **roof sits above it, not on it** (the roof is a separate 298-high vault).
- The outside and the inside of the tube are finished masonry; the collision hull is a solid prism of the full bounds (blocks, no inner hollow).

### SM_Roof (a cross-vault bay, not a flat slab)
- A **vaulted bay 478.2 x 478.2 with 298 of rise, pivot at the crown** (z 0). It is a **single surface with zero thickness** (512 triangles): the underside is the finished masonry (brick-coursed vault, `kit_test_vault_inside.png`), the top is the same surface seen from above (the `M_Tiles` parent is two-sided, so it renders from both sides; **collision and `trace_world` hit only from below**, a downward trace from above returns nothing).
- Underside height (z, local) on a grid, rows y -180..+180, columns x -180..+180, step 60 (x/y +-240 is the open edge): crown **+2** along both centre lines (so each edge of the bay is a pointed arch whose crown is at z +2); at the bay edges' arch springing it is about **-110 at (+-236, +-145) and -296 at the corners**; diagonal (groin) heights: t 60: +2, 90: -2, 120: -23, 150: -63, 180: -132 (t = distance along each axis). Edge profile at x = -236 (the open side): y 0: +2, +-25: -1, +-55: -13, +-85: -34, +-115: -65, +-145: -110, beyond that the shell ends over the corner post.
- **All four sides are open arches**, so adjacent bays join edge to edge (478.1 pitch): in the assembly four bays ran continuously with no visible slit. The vault is meant to stand on corner posts at z -296 (the corners are 298 below the crown).
- No thickness: nothing to see above it; the top face needs cover (rock, ground slab) in any view that sees it. In the greybox the rock blocks and `Ground_*` slabs already cover the crypt (Z -40..0).

### SM_Ground, SM_Ground_01 (floor tiles)
- **Surface 200 x 200 inside a 240 x 240 bounds**: the collision and the visible top end at +-100 (+-105 at most); the bounds include an edge skirt. **At a 240 pitch there is a 40 cm slit between tiles** (`kit_test_floor_pitch240_gaps.png`, the dark bands). **At a 200 pitch the tiles meet** with only thin arc-shaped slivers (a few cm, the tile edges dip), `kit_test_floor_pitch200.png`.
- The walking surface is flat at **z = 0.0 on `SM_Ground`**; **`SM_Ground_01` has a gutter along X**: z -8.9 on the centre line y = 0, easing to 0 at y = +-100 (z -7.0 at |y| 30, -4.5 at 50, -2.0 at 70, -0.3 at 90); it is flat along x. Both are cobble paving with a pale runner of stones down the middle (along X); one side only (collision on the top only, nothing below).
- 512 triangles each; the one-sided collision (ComplexAsSimple) means no hull; the navmesh sees the top.

### SM_Bars, SM_Dungeon_door, SM_Dungeon_window, SM_Dungeon_toplock (`kit_pieces_props_closeup.png`, `kit_pieces_door_toplock.png`, `kit_pieces_window.png`)
- **Bars:** iron grate in the **XZ plane**, 233.0 wide x 235.8 high x 8.6 thick, **about 11 vertical bars with two horizontal rails**; pivot bottom-centre. The collision is **one solid hull over the whole grate** (it blocks the openings between bars for rays and capsules).
- **Door:** an **arched plank door with iron straps and a ring/latch handle** in the **YZ plane** (leaf 13.4 thick, 95.9 wide, 182.2 high). Both faces finished; the strap and handle face is +X. Pivot is not at the hinge edge: bottom, 9 cm in front of the leaf's centre plane, 4.6 off the leaf's centre in Y. Place it by bounds.
- **Window:** a **timber-framed grille** (10 vertical bars in a frame, 92.2 wide x 42.6 high x 7.5 thick), YZ plane, centred in Z; both faces finished. Fits a niche or a cell opening.
- **Toplock:** a **round stone collar with an iron grating on top**, 73.3 diameter x 19.5 high (a well/manhole lid). The collar is mossy; the grating is open for light but the collision hull is solid. Pivot bottom-centre. Candidate for **floor/ceiling grates only at 73 cm wide**; a ceiling moon-grate bigger than that needs `SM_Bars` or our own piece.

### SM_Dungeon_beam, SM_Dungeon_halfbeam
- A wooden **post/brace with a forked end** (beam 34.9 x 150.4 x 19.8, long axis Y; halfbeam 36.0 x 81.4 x 19.9, a stub with the pivot near the middle of the stub). Both pivots are at the bottom (z 0). Not a long beam: 150 cm is the longest, 20 cm thick; shoring in the greybox would need several or a stretched scale (the texture stretches).

### SM_Charcoal_Pit, SM_Torture_Devices_Cage_Open, SM_Skeleton_Pile_05
- **Charcoal pit:** an iron basket brazier, 27.5 x 28.5 x 25.5. Tiny; a warm light source only at close range.
- **Open cage:** the hanging cage with the door open, 104.8 x 149.2 x 267.6 (taller than the closed cage's 86 x 86 x 268), pivot bottom-centre.
- **Skeleton pile 05 is a skeleton impaled on a pole** (a 242-high stake with a skeleton and a bone pile at its foot, 99.5 x 130.5 x 246.8), not a flat pile; its 33k triangles are non-Nanite like the existing piles.

---

## 4. The grid

| Piece | Grid size | Notes |
|---|---|---|
| **Wall** | **641.2 long x 154.8 thick x 503.0 tall**; pivot bottom-centre of the slab (centre of length, centre of thickness) | Both faces finished; face at about 69 from the centre line (relief 64-74.5), bounds 77.4. **Tile pitch for a seamless join: 626 horizontally and 495 vertically (about 15 and 8 overlap)**; at 641.2/503.0 the dark seam is 6-10 cm wide, at 632/499 a hairline, at 626/495 invisible (`kit_test_wall_seams_641_632_626_620.png`). |
| **Wall centre offset** | for an inner clear width **W**, wall centre at **y = +-(W/2 + 72)**, so W 300 puts the walls at +-222 (inner faces at +-153 +-5, so the worst-case clear width is about 290) | The stone relief means a clear width of 300 is "300 +0/-10". |
| **Arch** | half arch **311.4 x 155.1 x 503.3**; pair (one mirrored with X scale -1, joint at x = 215.2): **opening 437.3 wide x 420 clear at the crown (290 to the springing), 503 overall** | Scale X by 0.686 for a 300 opening (used in the test). |
| **Pillar** | **footprint about 135 x 128 (bounds 150.4 x 146.4), 464 tall, hollow octagon** | Axis 13 cm off the pivot in X. |
| **Roof** | **478.1 x 478.1 bay, 298 rise (+2.4 above the pivot), pivot at the crown**; adjacent bays at 478.1 pitch join | Thin single surface; underside only. Crown at z=0; edge arch springing at -110 (at y +-145) and corners at -296. |
| **Ground** | **200 x 200 usable (240 x 240 bounds, 40 thick), pivot at the centre, surface at z = 0** | Use a **200 pitch** (a 240 pitch leaves 40 cm slits). |

Heights that matter for a 300-wide corridor: with walls 503 tall (z 0..502) the vault crown can sit anywhere above; at the wall line (y = +-150) the vault underside runs from the crown (bay centre) down to crown-110 at the bay seams (x = +-239), so to keep the ceiling above the wall top set the crown at **wall height + 110 = about 612** (used in the test); with the crown at 560 (the greybox ceiling, floor to roof) the underside at the wall line at the bay seams is at 450, below the wall top (503), so the wall tops would poke through the vault surface near the bay seams (hidden behind the rock in the greybox, not in free-standing walls).

---

## 5. Test assembly (`L_Test_ArtKit`, throwaway; restored)

Built at (20000, 24000, 0): 3 walls per side (mixed `SM_Wall_00/01`, right side yawed 180), a 10 x 3 floor of alternating `SM_Ground`/`SM_Ground_01` at 200 pitch, 4 `SM_Roof` bays at 478.1 pitch with the crown at z 612, a 300-wide corridor (walls at y +-222, then re-pitched to 626), a 0.686-scaled arch pair across the far end, an unscaled arch pair beyond, a `SM_Pillar` half-embedded in the left wall at mid length, and 3 point lights. Separate: 2x2 wall groups at pitches 641.2/503, 632/499, 626/495, 620/491.

Captures (this folder):
- `kit_test_inside_a.png`, `kit_test_inside_b.png` (inside, looking down the corridor: wall, floor, vault, niche, pillar),
- `kit_test_end_view.png` (from the end, through the scaled arch pair and back along the corridor), `kit_test_arches.png` (scaled and unscaled arch pairs),
- `kit_test_exterior.png` (the assembly from outside), `kit_test_vault_inside.png`, `kit_test_pillar_niche.png`, `kit_test_floor_pitch200.png`, `kit_test_floor_pitch240_gaps.png`, `kit_test_wall_seams_641_632_626_620.png`, `kit_test_wall_top.png`, `kit_test_pillar_top_hollow.png`,
- `kit_pieces_architecture.png` (wall front/back, arch front/back, pillar, roof), `kit_pieces_props_closeup.png`, `kit_pieces_door_toplock.png`, `kit_pieces_window.png`.
(The captures are over-exposed in places: the lights were 2500 cd shadow-casting point lights, with auto exposure.)

How the pieces snap:
- **Walls side by side:** seamless at a **626 pitch** (15 cm overlap); at the 641.2 bounds width there is a 6-10 cm dark slit (and light leaks through it). The stone coursing matches across the seam in the 2x2 tests (all `SM_Wall_00`); mixed `00`/`01` neighbours in the corridor showed no obvious slit at 626 in the captures (not inspected close up). Do not butt the bounds.
- **Walls stacked:** seamless at a **495 vertical pitch** (8 cm overlap); at 503 a dark hairline row of 1-3 cm shows. A stack of two gives about 1000 high. The wall bottom has 1.3 cm below the pivot, so set z = 0 on a flat floor.
- **Walls, floor, roof:** the walls stand on the tile top (z 0); the 200 floor tiles reach under the walls; the vault crown has to sit about 110 above the wall top for the bay seams not to cut into the walls. **The vault corners (z -296 below the crown) land inside the wall thickness**, so the corridor reads as a barrel-vault passage from inside, with lunette gaps above the wall tops outside (`kit_test_exterior.png`: the vault humps above the wall; behind the walls those gaps need rock, which the greybox already provides).
- **Arch to wall:** the arch legs (92 wide x 146 deep) sit across the corridor end with the leg's inner face at the corridor edge (pivot y = corridor edge + 3.4 x scale). Its 155 depth matches the wall's 154.8 thickness, so its faces line up with the wall faces. A mirrored pair joins at the crown (bounds met within 0.003 cm).
- **Pillar:** engaged in a wall (axis on the wall's inner face line, 2.5 cm trim for the pivot offset) it reads as a pier and leaves 230 of a 300 corridor; its hollow ends are hidden by the roof and the floor.
- **Floor:** at 200 pitch continuous but for thin edge slivers; `SM_Ground_01`'s gutter is 8.9 deep, so mixing `Ground`/`Ground_01` in a row leaves a gutter that stops at the tile edges (visible as a step in `kit_test_floor_pitch200.png`): keep to one type per run or use the gutter tile as a row down the centre.
- **Lighting look:** the stone MIs read as pale warm limestone/sandstone (the 4 `MI_Stone_*` tints), far brighter and cleaner than the dark wet crypt of the owner's brief: **the architecture needs a darker tint, and the moss/grime/wetness layers, to sit in a very dark crypt**.

### Impact for D1 (lead)
1. The roof is a 478-square cross-vault: a corridor 300-400 wide is covered by one bay per 478 of length; **the Warden headroom (260) is met at the wall line only if the crown is at least 370 above the floor** (crown 612 gives 502 at the bay seams).
2. The arch is a half-piece: **a pair gives a 437-wide x 420-high opening**; narrower openings need X scaling.
3. Walls and arches already carry the same wall height (503), so arches and walls tile to one course line; the pillar is 39 lower and needs a 39 cm cap/plinth if it carries something.
4. `SM_Wall_01`'s niche (200 wide x 160 tall x 25 deep, one face) is a free ossuary niche unit; deeper burial niches need our own piece (P9-3).
5. Floor: 200 pitch, not 240.

---

## 6. Block C: crypt survey (`L_Monastery`, read-only)

Folders queried: `Crypt` (and `Crypt/Stairs`, `Crypt/Railings`), `Gameplay/Crypt`, `Lighting/Crypt`, `WalkPaths/*`, `AI/*`, filtered to X 6200-11800, Y -3200..700, Z -1000..0 (centre of the actor bounds). Nothing was changed; `L_Monastery` stayed not dirty. No actor has actor tags (every `tags` list is empty). `read_graph_dsl` was **not used**: no Blueprint was dirtied.

### 6.1 `Crypt` folder: greybox shell (33 `StaticMeshActor`s, engine Cube mesh, `BlockAll`)

| Label | Bounds [min]..[max] |
|---|---|
| Rock_000 | [6200, -3200, -600]..[11800, -2900, -40] |
| Rock_001 | [9000, -2900, -600]..[11800, -2500, -40] |
| Rock_002 | [6200, -2900, -600]..[7500, -2500, -40] |
| Rock_003 | [9000, -2500, -600]..[10000, -2460, -40] |
| Rock_004 | [6600, -2200, -600]..[7500, -2000, -40] |
| Rock_005 | [9000, -2100, -600]..[10000, -2000, -40] |
| Rock_006 | [6600, -2000, -600]..[10000, -1400, -40] |
| Rock_007 | [6800, -1400, -600]..[10000, -1300, -40] |
| Rock_008 | [10300, -1500, -600]..[11200, -1100, -40] |
| Rock_009 | [8000, -1300, -600]..[10000, -900, -40] |
| Rock_010 | [6800, -900, -600]..[10000, -800, -40] |
| Rock_011 | [6200, -2500, -600]..[6300, -800, -40] |
| Rock_012 | [6200, -800, -600]..[10000, -700, -40] |
| Rock_013 | [11500, -2500, -600]..[11800, -700, -40] |
| Rock_014 | [6200, -700, -600]..[10500, 500, -40] |
| Rock_015 | [10800, -700, -600]..[11800, 500, -40] |
| Rock_016 | [6200, 500, -600]..[11800, 700, -40] |
| CryptFloor_0 | [6200, -3200, -640]..[9300, 700, -600] |
| CryptFloor_1 | [9800, -3200, -640]..[11800, 700, -600] |
| CryptFloor_2 | [9300, -3200, -640]..[9800, -2300, -600] |
| CryptFloor_3 | [9300, -2100, -640]..[9800, 700, -600] |
| Pit_Floor | [9300, -2300, -940]..[9800, -2100, -900] |
| Pit_W | [9260, -2300, -900]..[9300, -2100, -640] |
| Pit_E | [9800, -2300, -900]..[9840, -2100, -640] |
| Pit_N | [9260, -2100, -900]..[9840, -2060, -640] |
| Pit_S | [9300, -2340, -900]..[9800, -2300, -640] |
| Prop_Crypt_0 | [7650, -2810, -600]..[7950, -2690, -530] |
| Prop_Crypt_1 | [8550, -2810, -600]..[8850, -2690, -530] |
| Prop_Crypt_2 | [7800, -2200, -600]..[8000, -2100, -540] |
| Prop_Crypt_3 | [8500, -2200, -600]..[8700, -2100, -540] |
| Prop_Crypt_4 | [10920, -2380, -600]..[11080, -2220, -510] |
| Prop_Crypt_5 | [11250, -1850, -600]..[11350, -1550, -540] |
| Plinth_Crank | [8375, -2725, -600]..[8425, -2675, -530] |

Materials: these blocks use the engine `BasicShapeMaterial` or `WorldGridMaterial` (no project material yet); collision `BlockAll` on all of them. Spaces and widths from the blocks are listed in `Docs/plans/P9_CRYPT_ART.md`.

### 6.2 Stairs and railings
- `Crypt/Stairs`: 80 steps (40 `Stair_SacristyDown_00..39`, 40 `Stair_CryptUp_00..39`); each step is a solid block from Z -600 up to its top, **30 cm run x 15 cm rise**. Sacristy stair: steps along +X from X 6800 to 8000, width Y -1300..-900 (400); top of step n at Z -600 + 15 (n+1), the last (39) reaches Z 0 at X 7970-8000. Crypt-exit stair: steps along +Y from Y -700 to 500, width X 10500-10800 (300); step 00 [10500, -700, -600]..[10800, -670, -585], step 39 [10500, 470, -600]..[10800, 500, 0].
- Railings (ground level, outside the crypt box): `Rail_Sac_S` at (7700, -1305, 50); `Rail_Sac_N` at (7700, -895, 50); `Rail_Sac_W` at (7395, -1100, 50); `Rail_Up_W` at (10495, 195, 50); `Rail_Up_E` at (10805, 195, 50); `Rail_Up_S` at (10650, -105, 50).

### 6.3 `Gameplay/Crypt` and the Warden
| Label | Class | Bounds | Location |
|---|---|---|---|
| Warden | BP_Warden_C | [8808, -2688, -600]..[9160, -2432, -198] | (8920, -2560, -490) |
| WSpawn_Crypt | LBWardenSpawnPoint | [10900, -930, -660]..[11380, -770, -500] | (11380, -850, -600) |
| Trig_CryptEntered | BP_TagTrigger_C | [6600, -1300, -600]..[6800, -900, -300] | (6700, -1100, -450) |
| CP_Crypt | LBCheckpoint | [6400, -1350, -608]..[6790, -850, -408] | (6550, -1100, -508) |
| Kill_Pit | BP_KillVolume_C | [9300, -2300, -900]..[9800, -2100, -620] | (9550, -2200, -760) |
| CP_Crypt_Mech2 | LBCheckpoint | [10500, -1800, -608]..[10890, -1500, -408] | (10650, -1650, -508) |
| Rubble_StairsBack | BP_TagVisibility_C | [7000, -1300, -600]..[7100, -900, -40] | (7050, -1100, -320) |
| Gate_CryptExit | BP_TagVisibility_C | [10500, -700, -600]..[10800, -640, -40] | (10650, -670, -320) |
| Clue_Diagram | BP_EngravedDiagram_C | [10792, -1633, -458]..[11048, -1377, -202] | (10920, -1505, -330) |
| Lever_C | BP_DialLever_C | [10672, -1631, -728]..[10928, -1375, -472] | (10800, -1503, -600) |
| Lever_A | BP_DialLever_C | [10912, -1631, -728]..[11168, -1375, -472] | (11040, -1503, -600) |
| Lever_B | BP_DialLever_C | [10792, -1631, -728]..[11048, -1375, -472] | (10920, -1503, -600) |
| Crank_Winch | BP_TagInteractable_C | [8388, -2712, -530]..[8412, -2688, -505] | (8400, -2700, -518) |
| Winch_Ritual2 | BP_RitualMechanism_C | [10750, -2050, -600]..[10850, -1950, -435] | (10800, -2000, -550) |

### 6.4 Crypt Blueprints in detail
Interaction note: `LBInteractableComponent`, `LBDialComponent` and `LBInspectableComponent` are **non-scene ActorComponents: they have no location**. Interaction is a trace against the actor's primitive components; every mesh component of these Blueprints has collision `BlockAllDynamic` (`QueryAndPhysics`), so the visible meshes are what the interaction trace hits. World bounds below are the actor bounds from `get_actor_bounds` (they include text components, so they overstate the visible mesh).

**Clue_Diagram** (BP_EngravedDiagram)
- Actor: location (10920, -1505, -330), rotation rot(0, -90.0, 0), scale (2.5, 2.5, 2.5); bounds (10792, -1633, -458)..(11048, -1377, -202).
- Variables: text = BALANCE THE CHAINS|A - HIGH   B - LOW   C - MIDDLE.
- `DefaultSceneRoot` (Scene root): rel loc (10920, -1505, -330)
- `BillboardComponent_1` (editor billboard)
- `Plaque` (StaticMesh, parent DefaultSceneRoot): mesh `Cube`, materials `MI_LB_Stone`, rel loc (0, 0, 0), rel scale (0.04, 1, 0.7), collision `BlockAllDynamic`
- `Engraving` (TextRender): text 'BALANCE THE CHAINS\nA - HIGH   B - LOW   C - MIDDLE', size 7, rel loc (2.2, 0, 0)
- Reading: a stone plaque (cube scaled 0.04 x 1 x 0.7 under actor scale 2.5 = **10 deep x 250 wide x 175 high**) centred at Z -330 (floor -600, so its centre is 270 up), actor yaw -90 so it faces **-Y** and sits against the south face of `Rock_008` (Y -1500; the plaque spans y -1510..-1500). The text (white-gold, size 7 x scale 2.5) is 2.2 x 2.5 = 5.5 in front of the plaque centre. It shows nothing on a tag (always visible, static). The readable text: BALANCE THE CHAINS / A - HIGH   B - LOW   C - MIDDLE.
- Greybox-only mesh: the plaque is the engine cube with `MI_LB_Stone`; the engraving is a text component. Anything that replaces the plaque must keep the text readable at 2 m (cap height 7 x 2.5 = 17.5 cm world size).

**Lever_A** (BP_DialLever; Lever_B and Lever_C are identical but for the values below)
- Actor: location (11040, -1503, -600), rotation rot(0, -90.0, 0), scale (1, 1, 1); bounds (10912, -1631, -728)..(11168, -1375, -472).
- Variables: lockTag = `State.Ritual.2`; labelText = A; notchPitch = 35; moveDuration = 0.4; startPitch = 0; targetPitch = 0.
- `DefaultSceneRoot` (Scene root): rel loc (11040, -1503, -600)
- `BillboardComponent_1` (editor billboard)
- `Backplate` (StaticMesh, parent DefaultSceneRoot): mesh `Cube`, materials `MI_LB_DarkWood`, rel loc (0, 0, 45), rel scale (0.06, 0.3, 0.9), collision `BlockAllDynamic`
- `HandlePivot` (Scene, parent DefaultSceneRoot): rel loc (6, 0, 45)
- `Arm` (StaticMesh, parent HandlePivot): mesh `Cylinder`, materials `MI_LB_Iron`, rel loc (22.5, 0, 0), rel scale (0.03, 0.03, 0.45), collision `BlockAllDynamic`
- `Weight` (StaticMesh, parent HandlePivot): mesh `Sphere`, materials `MI_LB_Bronze`, rel loc (47, 0, 0), rel scale (0.1, 0.1, 0.1), collision `BlockAllDynamic`
- `Rail` (StaticMesh, parent DefaultSceneRoot): mesh `Cube`, materials `MI_LB_Iron`, rel loc (46, 12, 45), rel scale (0.03, 0.04, 0.6), collision `BlockAllDynamic`
- `NotchLow` (StaticMesh, parent DefaultSceneRoot): mesh `Cube`, materials `MI_LB_Bronze`, rel loc (46, 12, 22.06), rel scale (0.06, 0.05, 0.03), collision `BlockAllDynamic`
- `NotchMid` (StaticMesh, parent DefaultSceneRoot): mesh `Cube`, materials `MI_LB_Bronze`, rel loc (46, 12, 45), rel scale (0.06, 0.05, 0.03), collision `BlockAllDynamic`
- `NotchHigh` (StaticMesh, parent DefaultSceneRoot): mesh `Cube`, materials `MI_LB_Bronze`, rel loc (46, 12, 67.94), rel scale (0.06, 0.05, 0.03), collision `BlockAllDynamic`
- `Label` (TextRender): text 'A', size 16, rel loc (3.6, 0, 82)
- `DialComp` (LBDialComponent): positionTags = `State.Crypt.Dial.A.0`, `State.Crypt.Dial.A.1`, `State.Crypt.Dial.A.2`; initialIndex = 1; bLocked = False
- `InteractComp` (LBInteractableComponent): promptText = Move counterweight; bEnabled = True; deniedPromptText = It won't move; requiredStateTags = none; grantedStateTags = none; bSingleUse = False; consumedStateTag = `None`; bInspectOnInteract = False; noiseLoudness = 0.5
- Lever_A at X 11040, Lever_B at X 10920, Lever_C at X 10800, all Y -1503, Z -600, yaw -90 (they face **-Y**, mounted on the south face of `Rock_008`, Y -1500, in a row 120 apart; the clue plaque is above Lever_B). Each lever is a 6 deep x 30 wide x 90 high `MI_LB_DarkWood` backplate (centre rel z 45, so it spans Z -600..-510) with an iron arm (3 cm cylinder, 90 long, pivoting at `HandlePivot`), a bronze weight (sphere, 10 cm), an iron rail and three 6 x 5 x 3 bronze notches (low z 22.1, mid 45, high 67.9, x 46, y 12) and a text label (size 16, z 82). The label sits at rel z 82 (Z -518) and the notches span Z -578..-532, so the whole lever lives in Z -600..-510 (90 high), the plate against the rock face at Y -1500 (its depth is 6, so Y -1506..-1500 with the 3 cm axis in front). `HandlePivot` at rel (6, 0, 45); `notchPitch` 35.
- Lever_B: labelText B, dial tags `State.Crypt.Dial.B.0/1/2` (initial index 1). Lever_C: labelText C, `State.Crypt.Dial.C.0/1/2`, initial index 1 (Lever_A: `State.Crypt.Dial.A.0/1/2`). All three: `lockTag` `State.Ritual.2` (the levers lock once the ritual fires), prompt 'Move counterweight', denied 'It won't move', noise 0.5.

**Winch_Ritual2** (BP_RitualMechanism)
- Actor: location (10800, -2000, -550), rotation rot(0, 0, 0), scale (1, 1, 1); bounds (10750, -2050, -600)..(10850, -1950, -435).
- Variables: ritualTag = `State.Ritual.2`; extraGrantedTags = `State.Warden.Stage.4`; combinedTags = `State.Warden.Stage.4`, `State.Ritual.2`; turnYaw = 90; turnDuration = 1.5.
- `Pedestal` (StaticMesh, parent root): mesh `Cube`, materials none (engine default), rel loc (10800, -2000, -550), rel scale (1, 1, 1), collision `BlockAllDynamic`
- `Core` (StaticMesh, parent Pedestal): mesh `Cylinder`, materials none (engine default), rel loc (0, 0, 75), rel scale (0.8, 0.8, 0.5), collision `BlockAllDynamic`
- `CoreMarker` (StaticMesh, parent Core): mesh `Cube`, materials none (engine default), rel loc (0, 37.5, 65), rel scale (0.19, 0.19, 0.3), collision `BlockAllDynamic`
- `InteractComp` (LBInteractableComponent): promptText = Activate; bEnabled = True; deniedPromptText = Something is missing; requiredStateTags = `State.Item.Crank`, `State.Crypt.Dial.A.2`, `State.Crypt.Dial.B.0`, `State.Crypt.Dial.C.1`; grantedStateTags = `State.Warden.Stage.4`, `State.Ritual.2`; bSingleUse = True; consumedStateTag = `State.Ritual.2`; bInspectOnInteract = False; noiseLoudness = 1
- Greybox shape: a 100 x 100 x 100 cube pedestal (centre Z -550, so Z -600..-500) with a cylinder core (rel z 75, scale 0.8/0.8/0.5) and a cube marker (rel (0, 37.5, 65)); no override materials (engine default). On interaction the core turns `turnYaw` 90 over `turnDuration` 1.5 s.
- Requires: `State.Item.Crank`, `State.Crypt.Dial.A.2`, `State.Crypt.Dial.B.0`, `State.Crypt.Dial.C.1`; grants `State.Warden.Stage.4` and `State.Ritual.2` (single use, consumes `State.Ritual.2`).

**Crank_Winch** (BP_TagInteractable)
- Actor: location (8400, -2700, -517.5), rotation rot(0, 0, 0), scale (0.25, 0.25, 0.25); bounds (8387.5, -2712.5, -530)..(8412.5, -2687.5, -505).
- Variables: useStateTag = `State.Item.Crank`; bHideOnUse = True; bInspectable = False.
- `Mesh` (StaticMesh, parent root): mesh `Cube`, materials none (engine default), rel loc (8400, -2700, -517.5), rel scale (0.25, 0.25, 0.25), collision `BlockAllDynamic`
- `InteractComp` (LBInteractableComponent): promptText = Take crank; bEnabled = True; deniedPromptText = ; requiredStateTags = none; grantedStateTags = `State.Item.Crank`; bSingleUse = True; consumedStateTag = `State.Item.Crank`; bInspectOnInteract = False; noiseLoudness = 0.20000000298023224
- `InspectableComp` (LBInspectableComponent): displayName = ; bodyText = ; bKeepOnClose = True
- A 25 cm cube (actor scale 0.25 on the engine cube) at (8400, -2700, -517.5) on `Plinth_Crank` (the plinth is [8375, -2725, -600]..[8425, -2675, -530]). Prompt 'Take crank', grants `State.Item.Crank`, single use, `bHideOnUse` (the actor hides when taken).

**Rubble_StairsBack** (BP_TagVisibility)
- Actor: location (7050, -1100, -320), rotation rot(0, 0, 0), scale (1, 4, 5.6); bounds (7000, -1300, -600)..(7100, -900, -40).
- Variables: triggerTag = `State.Ritual.2`; bVisibleWhenTagPresent = True; hideAfterSeconds = 0.
- `Mesh` (StaticMesh, parent root): mesh `Cube`, materials none (engine default), rel loc (7050, -1100, -320), rel scale (1, 4, 5.6), collision `BlockAllDynamic`
- **Shows when `State.Ritual.2` is present** (`bVisibleWhenTagPresent` = true, so it is hidden at the start and appears when the ritual fires); `hideAfterSeconds` 0. Stands across the sacristy stair's lower end: a cube 100 x 400 x 560 at X 7000-7100, Y -1300..-900, Z -600..-40 (the full width of the 400-wide stair, floor to ceiling), so the way back up to the chapel is closed after the ritual.
- From the Blueprint's asset strings (the graph itself was not read): the actor uses `SetActorHiddenInGame` and `SetActorEnableCollision` plus a timer, i.e. **the whole actor is hidden and its collision switched off together**.

**Gate_CryptExit** (BP_TagVisibility)
- Actor: location (10650, -670, -320), rotation rot(0, 0, 0), scale (3, 0.6, 5.6); bounds (10500, -700, -600)..(10800, -640, -40).
- Variables: triggerTag = `State.Ritual.2`; bVisibleWhenTagPresent = False; hideAfterSeconds = 0.
- `Mesh` (StaticMesh, parent root): mesh `Cube`, materials none (engine default), rel loc (10650, -670, -320), rel scale (3, 0.6, 5.6), collision `BlockAllDynamic`
- **Visible until `State.Ritual.2` is present** (`bVisibleWhenTagPresent` = false: visible at the start, hides when the ritual fires); `hideAfterSeconds` 0. A cube 300 x 60 x 560 at X 10500-10800, Y -700..-640, Z -600..-40 across the foot of the exit stair (the first stair step is at Y -700..-670 under it). Same hide/collision behaviour as above.

**Kill_Pit** (BP_KillVolume)
- Actor: location (9550, -2200, -760), rotation rot(0, 0, 0), scale (1, 1, 1); bounds (9300, -2300, -900)..(9800, -2100, -620).
- `Trigger` (Box): extent (250, 100, 140), collision `OverlapOnlyPawn`, hidden in game True
- Box trigger 500 x 200 x 280 (extent 250/100/140) centred (9550, -2200, -760): X 9300-9800, Y -2300..-2100, Z -900..-620; the pit floor is at Z -900 and the pit mouth at -640, so the top of the box is 20 above the floor slabs. Collision `OverlapOnlyPawn`, QueryOnly, hidden in game; no meshes; the kill fires on begin overlap of a pawn.

### 6.5 `Lighting/Crypt` (14 `PointLight`s)
| Label | Location |
|---|---|
| Light_Crypt_0 | (6550, -1100, -250) |
| Light_Crypt_1 | (6450, -1900, -250) |
| Light_Crypt_2 | (7050, -2350, -250) |
| Light_Crypt_3 | (7400, -1100, -250) |
| Light_Crypt_4 | (7800, -2450, -250) |
| Light_Crypt_5 | (8700, -2450, -250) |
| Light_Crypt_6 | (9500, -2250, -300) |
| Light_Crypt_7 | (10300, -2000, -250) |
| Light_Crypt_8 | (11000, -2000, -250) |
| Light_Crypt_9 | (10150, -1300, -250) |
| Light_Crypt_10 | (11350, -1300, -250) |
| Light_Crypt_11 | (10300, -900, -250) |
| Light_Crypt_12 | (11000, -900, -250) |
| Light_Crypt_13 | (10650, -350, -200) |

### 6.6 AI markers and WalkPaths inside the crypt box
- **Warden** (`BP_Warden_C_0`, folder `AI`): placed at (8920, -2560, -490) (bounds [8808, -2688, -600]..[9160, -2432, -198]).
- `AI/Spawn`: `WSpawn_Crypt` `LBWardenSpawnPoint` at (11380, -850, -600) (also `WSpawn_Cloister` (9000, 2000, 0) and `WSpawn_Tower` (12165, 1665, 0), outside the crypt).
- `AI/Patrol` (crypt, 7): Patrol_Crypt_01 (8200, -2450, -600); Patrol_Crypt_02 (8850, -2250, -600); Patrol_Crypt_03 (10200, -2300, -600); Patrol_Crypt_04 (10800, -1780, -600); Patrol_Crypt_05 (11350, -900, -600); Patrol_Crypt_06 (10650, -950, -600); Patrol_Crypt_07 (10150, -1300, -600).
- `AI/Search` (crypt, 15): Search_Crypt_01 (6450, -1000, -600); Search_Crypt_02 (7650, -2250, -600); Search_Crypt_03 (8250, -2650, -600); Search_Crypt_04 (8925, -2750, -600); Search_Crypt_05 (10150, -2400, -600); Search_Crypt_06 (10900, -1650, -600); Search_Crypt_07 (11380, -1400, -600); Search_Crypt_08 (10150, -880, -600); Search_Crypt_09 (6450, -1700, -600); Search_Crypt_10 (6450, -2300, -600); Search_Crypt_11 (7000, -2350, -600); Search_Crypt_12 (9100, -2380, -600); Search_Crypt_13 (10500, -2150, -600); Search_Crypt_14 (10650, -800, -600); Search_Crypt_15 (10150, -1700, -600).
- `WalkPaths/SacristyToCrypt` (`TargetPoint`s): 00 (8500, -1100, 0); 01 (8200, -1100, 0); 02 (7955, -1100, -15); 03 (7565, -1100, -210); 04 (7145, -1100, -420); 05 (6905, -1100, -540); 06 (6770, -1100, -600); 07 (6550, -1100, -600).
- `WalkPaths/FloodedLedge` (`TargetPoint`s): 00 (8750, -2380, -600); 01 (9050, -2380, -600); 02 (9350, -2380, -600); 03 (9650, -2380, -600); 04 (9950, -2380, -600); 05 (10250, -2380, -600).
- `WalkPaths/CryptToCloister` (`TargetPoint`s): 00 (10650, -1650, -600); 01 (11100, -2000, -600); 02 (11425, -1900, -600); 03 (11425, -1450, -600); 04 (11425, -900, -600); 05 (10900, -900, -600); 06 (10650, -730, -600); 07 (10650, -265, -375); 08 (10650, 155, -165); 09 (10650, 485, 0); 10 (10650, 700, 0).
- `WalkPaths/TowerStairs` (25 points, X 12150-12835, Y 1665-2335, up the tower) is outside the crypt and not listed.

### 6.7 Navigation
- **`NavMeshBoundsVolume_0` (label `NavBounds_Monastery`)**: one volume, scale (83, 37, 23) at (5000, 0, 1300), bounds **[-3300, -3700, -1000]..[13300, 3700, 3600]**: it covers the whole crypt (X 6200-11800, Y -3200..700, Z -600..-40) with 400 of margin below the floor. There is no other volume.
- **`RecastNavMesh-Warden` exists** (one actor, bounds [-3976, -3976, -890]..[13916, 3976, 3550]): agent radius 42, height 220, max slope 44, tile size 1000, runtime generation **Dynamic**, cell sizes 38/14/19 with cell height 10 and max step height 35, tile pool 1024, not force-rebuilt on load. (Dynamic generation means new colliding meshes rebuild the nav tiles in the editor and at runtime: the `ComplexAsSimple` arch/roof/ground meshes will cost nav-build time.) No `NavModifierVolume`s. The saved nav data was not inspected for validity (it needs a rebuild after the structure pass).

### 6.8 What is above the crypt ceiling (Z -40..0)
`trace_world` straight up from Z -300 (to Z 3000), then the actors at the hit point:

| Start | First hit above | Actors at the hit | Topmost hit from 3000 down |
|---|---|---|---|
| (7000, -2500, -300) | Z -40 | Ground_0 | Z 0 (ground top) |
| (8000, -1100, -300) | Z -40 | Ground_1 (borderline X 8000; also the stair top step `Stair_SacristyDown_39`) | Z 439 (chapel roof) |
| (10500, -2000, -300) | Z -40 | Ground_1 / Ground_3 | Z 0 (ground top) |
| (10650, -900, -300) | Z -40 | Ground_3 | Z 0 (ground top) |
| (6450, -1100, -300) | Z -40 | Ground_0 | Z 0 (ground top) |

- **Above the crypt is the world ground slab** (`Ground_0` X -3000..7400, `Ground_1` X 8000..10500, `Ground_2` X 10800..13400, `Ground_3` X 10500..10800 Y -3600..-100, `Ground_4` X 10500..10800 Y 500..3600, `Ground_5`/`Ground_6` X 7400..8000; all Cube slabs Z -40..0, Y -3600..3600 unless stated): the underside of the slab is the crypt ceiling at Z -40, and its top is the courtyard/chapel/cloister floor at Z 0. At (8000, -1100) the topmost surface is the chapel roof at Z 439.
- The slab is cut by two openings (the stair shafts): **X 7400-8000, Y -1300..-900** (the sacristy stair: `Ground_5` X 7400-8000 Y -3600..-1300 and `Ground_6` X 7400-8000 Y -900..3600 frame it; an upward trace from (7700, -1100, -300) hits nothing, from (7700, -2500, -300) it hits `Ground_5` at Z -40) and **X 10500-10800, Y -100..500** (the exit stair up to the cloister: `Ground_3` ends at Y -100 and `Ground_4` starts at Y 500).
- The crypt ceiling is therefore the underside of a 40-thick slab with the open air or the chapel above it, and **nothing is above the roof of the crypt that needs to be dressed**: the roof art only needs to look right from below (the vault top is hidden by the slab).

### 6.9 Items to flag
1. Every crypt Blueprint's meshes are engine cubes with `BlockAll`/`BlockAllDynamic`; replacing the greybox shell with the Dungeon pieces must keep the greybox collision (or the same volumes) so the stairs, the Warden path and the navmesh stay valid.
2. `Rubble_StairsBack` and `Gate_CryptExit` hide and un-collide the **whole actor** on the tag; art placed as child components of those actors would hide with them, art placed as separate actors would not.
3. The pit: ledge at Y -2460..-2300 (`Rock_003`/`CryptFloor_2`), pit walls `Pit_W/E/N/S` (40 thick), floor Z -900; nothing was touched.
4. All `Lighting/Crypt` lights and the 14 `AI` markers are inside the crypt box and unchanged.

---

## 7. Validation and state left behind

- **L_Test_ArtKit:** loaded, 84 temporary actors then 18 more (`TMP9_*`) placed and removed; the actor list after is identical to the one before (289 actors, none extra, none missing), the map was never saved, and after reloading `L_Monastery` the map shows no git change.
- **L_Monastery:** not dirty at any point; no actor changed. The editor is left on `L_Monastery`.
- **Blueprints dirtied:** none (`read_graph_dsl` was not used; the `BP_TagVisibility` behaviour above comes from strings in the saved asset, not from reading the graph).
- **Not validated (needs a human or a later task):** shader instruction counts (Material Stats), true resident texture memory (`stat streaming`), the look under the final crypt lighting, the navmesh over the real structure (Phase 9 structure task), Warden reachability with the new meshes.
