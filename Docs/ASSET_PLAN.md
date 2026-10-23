# THE LAST BELL — Asset Plan (Phase 6, P6-001)

Status: discovery, 2026-10-23. Look = **grounded photoreal** (scanned or realistic PBR). Budget = **free only** (D-040). GPU target = 6 GB VRAM dev machine.

## How this was verified (read this first)
- **CC0 libraries** were queried through the local asset server (`http://127.0.0.1:8787/v1/search` and `/v1/assets/{id}`, D-041). Every Poly Haven / ambientCG row below came back from that API with licence `CC0`, `price.free = true`, and the formats/resolutions listed. 18 of them were downloaded in P6-002 (see `ASSET_REGISTRY.md`); the rest are search-verified only (listing, not downloaded).
- **Fab** is bot-walled for the server and for `WebFetch` (HTTP 403). The listing pages were read in the Browser pane instead (anonymous, no login, nothing claimed or added to a library). For each Fab listing the table says what I actually read: price text, licence terms, UE versions, formats. Where I only saw a search card (title + "Free") the row is marked **UNVERIFIED**. Prices were shown to an anonymous visitor; the owner must confirm "Free" when signed in before claiming.
- I did **not** read the full text of the "Standard License" / "UE Marketplace" / "CC BY 4.0" terms. "Standard License" is Fab's default licence; whether every use we need (shipping in a commercial game) is covered must be confirmed by the owner on the listing's licence link. CC BY 4.0 items need attribution (they are flagged).
- Not used: 3d.shep.bot (unreachable), BlenderKit (items are mostly `.blend` only, no Blender conversion step in this phase), grab3d.com (a provider the server also returns, but its models are tagged "stylized"/low-poly, e.g. its candelabra: not photoreal, rejected), Sketchfab (login), Poliigon/TurboSquid (paid or bot-walled).

## Megascans status (checked 2026-10-23)
- Epic forum post "Access legacy Megascans on Bridge and Quixel.com" (https://forums.unrealengine.com/t/access-legacy-megascans-on-bridge-and-quixel-com/2142664): all Megascans were free on Fab under the Fab Standard License through the end of 2024; from 2025 they are sold on Fab, "though some assets will stay free"; the legacy claim window ended 2024-12-31.
- **Still free in October 2026 (read on the listing pages, last updated 2026-10-15, Standard License):** the Quixel Megascans **sample projects** (Dark Ruins, Medieval Village, Goddess Temple, Derelict Corridor, Military Trench, Old Mine, Saloon Interior, Unfinished Building, African Slate Quarry) and a few single items (Medieval Banquet, Wooden Bench, individual "Industrial Brick Ruin ..." pieces, "Military Trenches ..." pieces, some rocks and Megaplants). Seller page: https://www.fab.com/sellers/Quixel%20Megascans (filter Free). The bulk Megascans library is paid and is **not** recommended (D-040).
- Conclusion: the free Megascans are useful as **sample-project content** (architecture-adjacent ruins, rocks, debris) and not as a full library.

## Rejected on purpose
| Item | Why |
|---|---|
| Ancient Ruins - Free Asset Pack (Hyperdense), https://www.fab.com/listings/c6bd4209-8420-499f-99b7-f47b8492b2d1 | Listing says "Generated with AI: Yes", CC BY 4.0, a single red stylized shader. Not photoreal; AI provenance is a risk. |
| Modular Courtyard 1.0 (Dan4eZ) https://www.fab.com/listings/ecd3dc8a-5888-4421-91b5-a18390ed4828 | Tagged low-poly, UE 4.27/5.0-5.4, description in Russian; wrong look. |
| Medieval Dungeon (Infuse Studio), Dungeon Environment 135+ (PackDev) as primary kits | Free but old (UE 4.2x to 5.4), partly low-poly / game-art style. Medieval Dungeon is kept as a "nice" reference/parts source for the crypt (see Fab table). |
| Gothic Revival Church 3D Model https://www.fab.com/listings/6f86770e-9433-4c00-bb39-add1908b213a | CC BY 4.0, FBX building exterior (98 MB zip), no UE-ready modules; quality not verifiable. |
| Paris, Musee de Cluny - Chapel (Zoilo) https://www.fab.com/listings/b7ca2dc5-7fe7-4925-b2cb-3e923d09ca1b | CC BY 4.0 photogrammetry of a real gothic chapel (Blender + GLB, 57 MB). Good as **vault/rib reference only**, mesh is a raw scan. |
| The Forgotten Church (Krag Studio) https://www.fab.com/listings/17385706-e2a5-46ce-b9b5-9ed267db37be | Listing page sits behind a mature-content gate; could not read it. UNVERIFIED. |

---

## Shared material library (the ~12 surfaces reused everywhere)
All Poly Haven / ambientCG, CC0, 2K JPG by default. Poly Haven materials ship `nor_gl` and `nor_dx` (Unreal = DirectX, use `nor_dx`) and an `arm` map packed AO(R)/Roughness(G)/Metal(B), which maps straight onto an Unreal ORM slot. ambientCG ships NormalGL and NormalDX. "DL" = downloaded in P6-002.

| # | Surface | Chosen | URL | Why it fits | Alternates |
|---|---|---|---|---|---|
| 1 | Hero ashlar masonry (chapel, tower, buttresses) | Poly Haven `medieval_blocks_03` (DL) | https://polyhaven.com/a/medieval_blocks_03 | Large chiselled blocks, worn edges, grey-tan (cold under moonlight) | `medieval_blocks_05` (smaller, warmer), `stone_brick_wall_001` (dark, mossy) |
| 2 | Rubble / coursed old wall (courtyard, crypt, ruins) | Poly Haven `castle_wall_varriation` (DL) | https://polyhaven.com/a/castle_wall_varriation | Irregular stones, deep mortar joints, aged | `rustic_stone_wall_02` (warm beige), `castle_wall_slates`, `mossy_stone_wall` |
| 3 | Wet flagstone / courtyard paving | Poly Haven `cobblestone_floor_08` (DL) | https://polyhaven.com/a/cobblestone_floor_08 | Worn rounded stones with dirt fill: good for a roughness-driven wet layer | `cobblestone_floor_04` (mossy), `grassy_cobblestone`, ambientCG `PavingStones142`/`PavingStones150` |
| 4 | Interior flagstone / limestone slabs (chapel, cloister) | ambientCG `Tiles139` / `Tiles143` (not DL) | https://ambientcg.com/a/Tiles139 | Cream limestone slabs (needs darkening and grime) | Poly Haven `stone_floor`, `marble_tiles` (too clean) |
| 5 | Plaster over masonry (chapel/crypt interior) | Poly Haven `plaster_brick_01` (DL) | https://polyhaven.com/a/plaster_brick_01 | Cracked plaster peeling to brick, damp | `painted_plaster_wall`, `red_plaster_weathered`, ambientCG `Plaster001` |
| 6 | Rotten / aged wood (doors, floors, scaffolds) | Poly Haven `weathered_planks` (DL) | https://polyhaven.com/a/weathered_planks | Dark brown cracked boards | `weathered_brown_planks`, `wood_planks_grey`, `old_wooden_floor_03` |
| 7 | Rusty iron | Poly Haven `rusty_metal_04` (DL) | https://polyhaven.com/a/rusty_metal_04 | Pitted corroded steel with flaking paint; separate metal map | `rusty_metal_02` (bright orange, too clean), `rusty_metal_sheet` |
| 8 | Bronze / old brass (bell, candlesticks) | ambientCG `Metal017` (DL) | https://ambientcg.com/a/Metal017 | Aged brown-bronze, rough | ambientCG `Metal013`, `Metal008` (too polished) |
| 9 | Mud / wet ground | Poly Haven `brown_mud_03` (DL) | https://polyhaven.com/a/brown_mud_03 | Glossy wet patches, stones | `brown_mud_leaves_01`, `brown_mud_02`, ambientCG `Ground109` |
| 10 | Mossy rock / moss over stone | ambientCG `Rock064` (DL) | https://ambientcg.com/a/Rock064 | Layered stone with live moss | Poly Haven `mossy_rock`, `brick_moss_001`, `lichen_rock`, ambientCG `Moss002` |
| 11 | Cliff rock (approach walls) | Poly Haven `rock_wall_02` / `rock_face_03` (not DL) | https://polyhaven.com/a/rock_wall_02 | Cliff-scale rock for the 6 m path walls | `rock_wall_13`, ambientCG `Rock051` |
| 12 | Roof slate | Poly Haven `roof_slates_03` / `castle_wall_slates` (not DL) | https://polyhaven.com/a/roof_slates_03 | Grey slate for chapel and tower roofs | `roof_slates_02`, `grey_roof_tiles_02` |
| 13 | Cloth / rope (tower banners, ropes, sacking) | Poly Haven `rough_linen`, `hessian_230`; ambientCG `Rope001` (not DL) | https://polyhaven.com/a/rough_linen | Plain coarse fabrics for the whipping cloth and rope meshes | ambientCG `Fabric085` |
| 14 | Leak/grime/stain decals | ambientCG `Leaking006` (DL, decal with opacity map) | https://ambientcg.com/a/Leaking006 | Water streak decal | The only decal CC0 source found; chalk, blood and soot decals are a **gap** (below) |

Texture budget: 2K for everything above. **4K candidates (1-2 only):** `medieval_blocks_03` (the ashlar fills the whole nave and tower at near range, so texel density matters most there) and the Gothic Statue (a single hero close-up). Everything else stays 2K, with the anti-tiling strategy in `ART_DIRECTION.md` (macro variation + decals + mesh variety) rather than bigger maps.

---

## Per-area asset families

Legend: **Gap** = no free, photoreal, downloadable asset found that meets the look; **Custom** = build in Blender/kitbash; "CC0 DL" = verified downloadable CC0 (D-041 server); "Fab" = see the owner claim table. All CC0 rows are Poly Haven (`polyhaven.com/a/<slug>`) or ambientCG (`ambientcg.com/a/<id>`) and carry formats gltf/blend/fbx/usd (models) or jpg/png (materials) at 1K-8K.

### Courtyard (wind-torn, wet flagstones, collapsed walls, tower silhouette)
| Family | Candidates | Realistic gap |
|---|---|---|
| Architecture kit (gate house, walls, arches, buttresses, well house) | (1) Fab **Dark Ruins Megascans Sample** (ruins/tomb/dungeon environment, free); (2) Fab **Medieval Village Megascans Sample**; (3) Fab **Maridalen Ruins** (photogrammetry of real medieval ruins). All Fab, claim-first. No CC0 equivalent exists. | **Large gap.** No free modular monastery kit verified. Plan = custom modular kit wearing CC0 materials, plus free Megascans pieces as hero ruins (see Architecture kit strategy). |
| Floors and ground | `cobblestone_floor_08` (DL), `cobblestone_floor_04`, `brown_mud_03` (DL), ambientCG `PavingStones142`, `Ground109` | Covered. Puddle/wet layer is the master material's job (M_LB_Surface). |
| Masonry | `castle_wall_varriation` (DL), `medieval_blocks_03` (DL), `stone_brick_wall_001` | Covered for flat walls. Broken/collapsed wall silhouettes are geometry = custom or Megascans ruin pieces. |
| Cliffs and rocks | `rock_wall_02`, `rock_wall_13` (cliff materials); models `rock_moss_set_01` (DL), `rock_moss_set_02`, `boulder_01`, `coast_land_rocks_04` | Covered (Poly Haven). Free Megascans rocks (e.g. Granite Rock, Nordic Forest cluster rocks) were seen on the Dark Ruins page carousel, not opened: UNVERIFIED. |
| Roofs, beams, wood | `weathered_planks` (DL); models `wooden_ladder_02`, `large_castle_door` | Roof frames and timber beams are custom (simple Blender trims). |
| Metal | `rusty_metal_04` (DL); model `large_iron_gate` (Josh Dean, 2K-8K) | Gate is usable as the gatehouse gate base; verify style in P6-003. |
| Props | `wooden_crate_01` (DL), `wooden_crate_02`, `wooden_bucket_01`, `wine_barrel_01`, `wooden_lantern_01` (DL), `Lantern_01` (oil lantern), `wooden_stool_01` (DL) | Good coverage of generic props. Cart/well: only stylized grab3d (rejected) -> custom or Fab (UNVERIFIED "Stone well" by Procedural). |
| Vegetation, roots, moss | models `fern_02`, `moss_01`, `dead_tree_trunk_02`, `tree_stump_01`, `bark_debris_01`, `dry_branches_medium_01`; Fab Megaplants (free items on Fab, UNVERIFIED); Fab **Dynamic Ivy Creation Pack** (verified free, Standard, but UE up to 5.4) | Ivy/creepers on masonry are a **gap** (ambientCG only has leaf atlases `LeafSet017/029`). Plan: ivy cards from the leaf sets + hand placement, or the Fab ivy pack after a version check. |
| Decals | `Leaking006` (DL); Fab **Blood Decals - 3 Free (4K)**, UE 5.8, Standard (use very sparingly) | Soot, chalk, cracks, chalk ritual marks: gap, custom decals (P6-003/Phase 11). |
| Sky / HDRI | `moonless_golf` (DL, night), `approaching_storm`, `kloofendal_overcast`, `pond_bridge_night`, `satara_night_no_lamps`; ambientCG `NightSkyHDRI003/008` (EXR) | HDRI covers fill and reflections. The storm cloud layer itself will come from Sky Atmosphere / volumetric clouds (Phase 14), not from a static HDRI. |
| Water / puddles | Wetness layer in M_LB_Surface (custom); Fab **Simple Water Puddles (Free)**, CC BY 4.0, UE 5.4-5.6 (attribution needed) | Standing-water surface (M_LB_Water) is custom. |

### Chapel (tall nave, stained glass, candles, broken pews, chalk ritual)
| Family | Candidates | Realistic gap |
|---|---|---|
| Architecture kit (nave columns, ribbed vaults, pointed arches, windows, buttresses) | Fab **Dark Ruins Megascans Sample**; Fab **Goddess Temple Megascans Sample** (temple environment, contents not itemised); Fab **Stone Pillar - Intact & Broken** (GriidArt, 5 pillars); Fab **Gothic props (pack 1)** (CC BY, 21 props). Window tracery: Fab "Circular/Square Gothic Window" (prDaria): UNVERIFIED. | **Biggest gap in the project.** No verified free gothic nave kit. Needs a custom modular kit (columns, ribs, window frames, buttresses, a nave segment) in Blender. |
| Floors | ambientCG `Tiles139/143` (limestone), `PavingStones128`, Poly Haven `old_wooden_floor_03`, `stone_floor` | Slabs need heavy grime/wet masks; fine. |
| Plaster / masonry | `plaster_brick_01` (DL), `medieval_blocks_03` (DL), `painted_plaster_wall` | Covered. |
| Wood and furniture (pews, lectern, doors) | `weathered_planks` (DL); models `wooden_stool_01` (DL), `large_castle_door`, `GothicCabinet_01`, `GothicBed_01`, `GothicCommode_01` (Kirill Sannikov), `vintage_cabinet_01`, `decorative_book_set_01` | **Pews and a lectern: gap** (none verified). Custom, simple box-and-bevel pews with `weathered_planks`. Gothic furniture models read Victorian, not monastic: use selectively. |
| Metal | `Metal017` (DL, bronze), `rusty_metal_04` (DL) | Fine. |
| Props (candles, candelabra, censers) | `brass_candleholders` (DL, Poly Haven 4K source), `Chandelier_01/02/03`, `lantern_chandelier_01`, `brass_goblets`, `brass_pot_01` | Candle flame, wax drips: gap (flame = Niagara/VFX, Phase 15). Chandeliers look Victorian: heavy re-skin needed. |
| Statuary / icons | `gothic_statue` (DL, veiled crowned chained figure), `marble_bust_01` (classical, off-style); Fab **Gargoyle Statue** (Museum Scan, glb/obj, 2K-8K) | Good coverage for 1-2 hero statues; saints/crucifix: gap, custom. |
| Vegetation | `moss_01`, `Rock064` | Light use inside; ivy through windows is a gap (see Courtyard). |
| Decals | `Leaking006` (DL) | **Chalk ritual marks: gap, custom** (also a story asset, see Custom assets). |
| Sky / light | HDRI is only for window-exterior and reflection fill | Stained glass (M_LB_Glass) is custom: no CC0 stained-glass material found. |

### Crypt (low vaults, roots, standing water, chains, sparing bones)
| Family | Candidates | Realistic gap |
|---|---|---|
| Architecture kit (barrel vaults, groin vaults, pillars, stairs, niches) | Fab **Medieval Dungeon** (Infuse Studio, free, crypt-tagged modular meshes, UE 5.0-5.4, "UE Marketplace" licence: needs version migration and a style check); Fab **Dark Ruins Megascans Sample** (tomb/dungeon tags, UE 5.5-5.8); Fab **Derelict Corridor Megascans Sample**. | **Large gap.** Same custom modular kit as the chapel (shared vault/arch trims) is the plan. Medieval Dungeon is a parts/reference source, not the kit. |
| Floors and ground | `cobblestone_floor_08` (DL), `PavingStones142`, `brown_mud_03` (DL) | Covered. |
| Walls / masonry | `plaster_brick_01` (DL), `castle_wall_varriation` (DL), `brick_moss_001`, `mossy_stone_wall` | Covered. |
| Roots and moss | models `root_cluster_01` (DL), `root_cluster_02`, `single_root`, `pine_roots`; materials `roots`, `Rock064` (DL), `moss_wood` | Covered for hero roots. Root-through-masonry blending is a master-material / hand-placement job. |
| Wood and props | models `wooden_crate_01` (DL), `wine_barrel_01`, `wooden_bucket_01`, `treasure_chest`, `wooden_ladder_02` | Good. |
| Metal (gates, grates, chain) | `rusty_metal_04` (DL); model `large_iron_gate`, `rusted_wheel_rim_01/02` | **Chains and winch parts: gap** (only stylized grab3d found). Chain links are trivial to model (torus + `rusty_metal_04`); see mechanism 2. |
| Coffins, bones, ossuary | None photoreal verified. Fab UNVERIFIED search cards: "Corpses Environment Props Pack FREE Sample" (Temporal Anomaly), "Human Skeleton" (Salt Lake Manor). | **Gap.** "Bones used sparingly" keeps this small: a few custom skull/bone clusters or one verified scan; coffins/sarcophagi custom (box + lid + decals). |
| Decals | `Leaking006` (DL), blood decals (sparingly) | Cobwebs, mould, wet streaks: gap, custom. |
| Water | custom `M_LB_Water` + wetness | Custom. |

### Bell Tower (vertigo, exposed beams, cracked bell, whipping cloth)
| Family | Candidates | Realistic gap |
|---|---|---|
| Architecture kit (tower shell, stair landings, louvred bell chamber, arches, parapet) | Same kit as the chapel/courtyard (ashlar), Fab **Medieval Village Megascans Sample** pieces, `roof_slates_03` for the cap | Tower-specific pieces (bell frame, louvres, floor hatches) are custom. |
| Floors and ground | `weathered_planks` (DL), `medieval_blocks_03` (DL) | Covered. |
| Masonry | `medieval_blocks_03` (DL; 4K hero candidate), `castle_wall_varriation` (DL) | Covered. |
| Roofs, beams, wood | `weathered_planks` (DL), `beam_wall_01` (material, odd look), `roof_planks`, model `wooden_ladder_02` | **Timber frame and bell-frame beams: custom** (square-section beams with `weathered_planks`). |
| Metal | `Metal017` (DL), `rusty_metal_04` (DL) | Fine. |
| Props | `wooden_crate_01`, ropes (ambientCG `Rope001` material only) | Ropes, pulleys: gap, custom meshes. |
| Cloth | `rough_linen`, `hessian_230` | Cloth simulation is Phase 15; texture covered. |
| Vegetation, moss | `moss_01`, `Rock064` | Light. |
| Decals | `Leaking006` (DL) | Fine. |
| Sky | storm HDRIs above; the lightning/cloud sky is a lighting/VFX task (Phases 14-15) | Backdrop clouds and lightning: not an asset download. |

---

## Custom assets (must be authored: the game's identity)
Route options: **(a)** 3d.shep.bot generation (currently unreachable, treat as a possible early blockout only), **(b)** Blender modelling (most reliable; needs a Blender step to be set up, none exists in Phase 6), **(c)** kitbash from scanned CC0 parts plus a custom material. All custom assets must still be added to `ASSET_REGISTRY.md` with their route.

| Asset | Why custom | Proposed route | Phase | Risks |
|---|---|---|---|---|
| **Warden** (creature) | Core identity; the AI uses a placeholder with a 42/110 capsule and a ~290 cm body (D-038, doors force stooping) | (b) Blender sculpt + retopo + rig, or (a) concept blockout then manual cleanup; clothing/mask via cloth sim | 12-13 | Highest-risk asset: silhouette, rig fit for the stoop animation, hands-off AI-generated meshes are not production-ready |
| **Warden mask** | Identity prop, must read clearly in dark light | (b) Blender hard-surface/sculpt; scanned bone/wood materials as the base | 12 | Reads as costume vs creature part: needs art review |
| **Mechanism 1: Chapel candle-order altar** | Unique gameplay prop (candle sequence) | (c) kitbash: stone altar custom + `brass_candleholders` (DL) + `Metal017`; candle meshes individually addressable | 7 (Chapel), logic exists (Phase 4) | Needs lightable candle sockets and a readable "order" cue |
| **Mechanism 2: Crypt chain counterweight levers + crank** | Unique gameplay prop | (b) Blender: chain links, counterweight blocks, lever and winch, `rusty_metal_04` + `weathered_planks`; crank as a small hero prop | 9 (Crypt) | Chain physics/animation (links as spline-mesh or a baked animation); keep poly count low |
| **Mechanism 3: Bell Tower four small bells** | Unique gameplay prop | (b) Blender: 4 small bells on a frame, pull ropes, `Metal017` | 10 (Bell Tower) | Four bells must read different (size/tone) for the puzzle |
| **Monastery symbols / iconography** | Brand identity, ritual marks, chalk circles, carved reliefs | (b)/(c) custom decals (Substance-style via Krita/Blender), carved relief normals | 7-10 as decals, 11 polish | Needs a reference sheet (symbol design = creative decision for the owner) |
| **Finale bell** | The ending; "enormous cracked bell" | (b) Blender: large bell with crack geometry, `Metal017` base + custom wear; separate clapper | 10 | Scale/crack readability under lightning; LOD/Nanite settings; hero 4K candidate |

Also custom or custom-adapted (from the gaps above): the **modular architecture kit**, stained glass (M_LB_Glass), pews/lectern, chains, coffins/ossuary clusters, chalk/soot/crack/blood decals, ivy, standing-water material.

---

## Fab: items the owner must claim
Free listings only. Read anonymously in the Browser pane on 2026-10-23 (no login, nothing claimed). "Free" = price element showed "Free" next to "Add to My Library"; the owner must confirm when signed in. The licence terms text itself was not read.

| Pri | Listing | URL | Seller | Covers | Licence shown | UE ver. | Notes / what it replaces |
|---|---|---|---|---|---|---|---|
| **Must** | Dark Ruins Megascans Sample | https://www.fab.com/listings/836ed2f8-e2d6-49be-98d3-59d104bd351e | Quixel Megascans | Dark fantasy ruins environment, tagged tomb/dungeon/temple/ruin/cave (project; contents not itemised on the listing) | Standard License | 5.5-5.8 | Closest free match to the mood; replaces a purchased architecture pack for hero ruins and crypt pieces. Large download; migrate only the needed assets |
| **Must** | Medieval Village Megascans Sample | https://www.fab.com/listings/2e11a225-a6ea-4781-a3e1-fe975b461894 | Quixel Megascans | Medieval stone/wood village assets, scanned props (project) | Standard License | 4.26-4.27, 5.3-5.8 | Courtyard/tower stone and timber pieces |
| **Must** | Goddess Temple Megascans Sample | https://www.fab.com/listings/471eaad7-3c05-45bd-ac37-02dddb17780f | Quixel Megascans | Photorealistic fantasy temple environment: 3D assets, decals, surfaces (project; listing says ray tracing/RTX required for the sample map; columns not individually verified) | Standard License | 4.25-4.27, 5.0-5.8 | Possible columns/stonework for chapel and crypt; needs a style check (temple, not gothic) |
| Nice | Derelict Corridor Megascans Sample | https://www.fab.com/listings/d825ff9c-77da-45a4-9619-c989e6dfdda6 | Quixel Megascans | Decayed walls, debris and clutter (project) | Standard License | 5.5-5.8 | Debris/clutter and wall-decay reference for the crypt |
| Nice | Medieval Banquet | https://www.fab.com/listings/d422ac6c-ce50-4273-8d4a-2ac594a3a2b2 | Quixel Megascans | 77 assets, FBX + JPG (tables, platters, goblets, food) | Standard License | 5.4-5.8 | Refectory/cloister set dressing |
| Nice | Wooden Bench | https://www.fab.com/listings/11e09273-0eae-4f7b-85b8-f982b46d4cac | Quixel Megascans | One scanned bench, FBX/glTF + ZBrush (649 MB zip) | Standard License | n/a (FBX) | Single bench; very large download |
| Nice | Maridalen Ruins | https://www.fab.com/listings/1bb299e1-fc4c-4115-b39a-dde723288d17 | William Faucher | Photogrammetry scan of real medieval ruins (project, Nanite), PCG samples (Megascans grass replaced by placeholders) | Standard License | 5.7-5.8 | Ruined-wall hero pieces; project, needs trimming |
| Nice | Gargoyle Statue | https://www.fab.com/listings/9c8003f0-f962-4c7e-b5e2-ee3516bfe7c2 | Museum Scan | Photogrammetry gargoyle: OBJ/GLB, 1K-8K textures, 10 MB zip | Standard License | n/a (OBJ/GLB) | Tower/chapel stone ornament |
| Nice | Stone Pillar - Intact & Broken Variations | https://www.fab.com/listings/bfc1b365-2a75-4b95-ac2f-f7f1549b88e2 | GriidArt | 5 assets (pillar, 2 broken, head, debris), BC/ORM/N | Standard License | 5.0-5.7 | Column/ruin pieces for nave and cloister |
| Nice | Medieval Dungeon | https://www.fab.com/listings/c13bd0dc-ac4d-4595-b284-f81386b2e6ef | Infuse Studio | Dungeon and crypt modular meshes + props | "UE Marketplace" licence | 4.21-5.4 | Parts/reference for the crypt; old, version migration needed; check style |
| Nice | Free Sample Dark Fantasy Gothic Environment Kitbash | https://www.fab.com/listings/338af1ae-80da-4d94-b3ef-38368e287678 | Oleg Ushenok | One gothic building (sample of a paid pack) | Standard License | 5.5-5.7 | Silhouette reference for the tower/chapel exterior; **style likely stylized: UNVERIFIED look**, check before use |
| Nice | Medieval Stone Bridge (Nanite) | https://www.fab.com/listings/4c64ce34-195b-4b45-8e14-70273cc984b5 | Pierogi3 | One bridge, Nanite, collision | Standard License | 5.7 | Optional courtyard/approach piece |
| Nice | Gothic props (pack 1) | https://www.fab.com/listings/7727a384-ec28-4773-a1da-876ad0b49457 | E.Bolday | 21 Victorian-gothic modular props (top-down oriented) | **CC BY 4.0 (attribution required)** | 5.4-5.8 | Quality at first-person distance unverified |
| Nice | Blood Decals - 3 Free PBR Decals (4K) | https://www.fab.com/listings/a4ffffd4-faa8-4e50-9ccd-278f1e7ec45c | Weasel Whistle | 3 blood decals (splatter, drips, pool) | Standard License (price element not captured; title says Free) | 5.8 | Sparingly; replaces custom blood decals |
| Nice | Simple Water Puddles (Free) | https://www.fab.com/listings/5718b8ac-27f7-4741-85ba-2cff7bf2f77d | JVAD3D Models | 8 puddle decals | **CC BY 4.0 (attribution required)** | 5.4-5.6 | Puddle decals; version older than 5.8 |
| Nice | Dynamic Ivy Creation Pack | https://www.fab.com/listings/71697e6c-508c-420b-86e1-0ffb85827f27 | Project Nature | Ivy brush meshes and branches | Standard License | 4.19-4.27, 5.0-5.4 | Ivy on masonry; old, migration and wind material check |

**UNVERIFIED (search card only, listing not opened):** Megaplants free items (Quixel Megaplants), "Circular/Square Gothic Window Type1-4" (prDaria), "Altar Ruins Free" (Underhill Labz), "Old Furniture Pack" (BB Arts), "Candle VFX" (Vefects), "Corpses Environment Props Pack FREE Sample" and "Free Dark Fantasy Stone Statue, Pedestal, and Sword" (Temporal Anomaly), "Human Skeleton" (Salt Lake Manor), "Stone well" (Procedural), "Real Stones Pack 01" (Open World Development). Search URL pattern for follow-up: `https://www.fab.com/search?q=<terms>&is_free=1&asset_formats=unreal-engine`.

Paid alternatives, not used (D-040): none recommended. (The big gothic cathedral kits on Fab, e.g. "St. Peter's Cathedral SA Environment", surfaced in web search, price not confirmed; paid kits are out of scope.)

---

## Architecture kit strategy (recommendation)
**Build a custom modular kit** (Blender, simple trims and bevelled blocks: wall segments, corner posts, pointed arches, columns, rib vaults, window frames, stair and door frames, tower shell pieces) **wearing the shared CC0 materials** (`medieval_blocks_03`, `castle_wall_varriation`, `plaster_brick_01`, tuned by `M_LB_Surface`), and use the free Megascans sample content, Maridalen Ruins and the Gargoyle/pillar assets as **hero set pieces and reference**, not as the kit. Evidence: (1) the CC0 libraries searched (Poly Haven: materials, HDRIs and many props but no building kits in any of my searches; ambientCG: materials, HDRIs, decals and a few models) returned no gothic arches, vaults or columns (searches: arch, column, pillar, church, gothic, ruins, cemetery, stairs, window, door); (2) the free Fab kits that exist are stylized, low-poly, AI-generated or old UE versions (rejected above), and the ones that are photoreal (Megascans samples, Maridalen) are projects of ruins rather than a reusable nave/crypt kit; (3) a custom kit is the only way to hit the exact floor plans in `GREYBOX_SPEC.md` (nave 1200 high, crypt corridors at least 200 wide, 35 m tower) and gives authored rather than collage results, as ART_DIRECTION requires. The kit should be authored once in Phase 7 (Chapel) and reused in Phases 8-10. The material and prop libraries above are already enough to dress it.

## Open questions for the owner
1. Claim list: confirm the three **must** Megascans samples (and any nice-to-haves) and confirm "Free" and shipping rights on the licence page.
2. Who builds the custom modular kit and the custom assets (Blender is not set up in this repo; D-041 only covers downloads)?
3. 4K hero picks: `medieval_blocks_03` and the Gothic Statue (this plan's proposal).
4. Design decisions needed for the ritual symbols/iconography before decals can be made.
