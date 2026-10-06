# THE LAST BELL — Art Direction

## Target
An intentionally authored premium Unreal environment, **not** a collage of marketplace packs. Quality comes from composition, materials, lighting, weathering, audio and motion together, not from texture resolution alone.

## Palette & light
- **Cold world:** blue-grey ambience, moonlight, lightning, rain, fog, wet stone (low roughness in puddles and streaks, high roughness on dry patches).
- **Warm islands:** candles, lanterns, ritual flames, a few old electric bulbs. Warmth reads as safety, and taking it away is a horror tool.
- **Readability:** darkness must stay readable. No crushed blacks hiding weak art. Keep a minimum exposure floor per area (see PERFORMANCE_BUDGET and Phase 14).

## Materials
Master materials in `Materials/Master/`, used through instances only:
- `M_LB_Surface` (opaque master): macro variation, detail normals, a wetness layer (darkening plus roughness), a moss or grime mask from world-aligned and vertex-paint inputs, puddle mask.
- `M_LB_Decal`, `M_LB_Glass` (stained glass), `M_LB_Foliage`, `M_LB_Water`.
- The anti-tiling strategy is macro variation plus decals plus mesh variety. Avoid 8K textures by default: hero assets get 4K, most get 2K.

## Asset identity
Must be custom or heavily customized: the **Warden** and its **mask**, the three **ritual mechanisms**, monastery **symbols** and iconography, and the **finale bell**.
Can be library-sourced (Fab, Megascans, CC0): architecture kits, rocks, ground, cliffs, debris, vegetation, generic props and furniture.

## Area mood boards (words, to become images in Phase 6)
- **Courtyard:** wind-torn, rain sheets in lightning, wet flagstones, collapsed walls, the tower silhouette against the clouds.
- **Chapel:** tall nave, moonlight through stained glass, candle clusters, broken pews, ritual chalk on the floor.
- **Crypt:** low vaults, roots through the masonry, standing water, chains, bones used sparingly, fog in the light shafts.
- **Bell Tower:** vertigo, exposed beams, an enormous cracked bell, cloth whipping in the wind, lightning backlight.

## Quality check (each visual phase)
"Would this screenshot look compelling on a Steam store page, and does it look authored rather than assembled?"
