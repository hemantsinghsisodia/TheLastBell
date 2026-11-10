# Freesound: creature ambience (P16-6, D-112, CC0 only)

The owner approved four kinds of occasional, mostly distant creature ambience: bats (belfry and upper tower), owls (outdoors), far-off howls and rats (crypt). They play through the existing `ALBAmbientEmitter`; no new code. Cue names and counts come from the creature table in `Docs/plans/P16_AUDIO.md` (section "P16-6, part 1").

Log in to freesound.org, open each link, click **Download**, and save into `ExternalAssets/Incoming/freesound/` with the default file name. Skip any page that no longer says "Creative Commons 0".

How the files will be used (A2 prepares them; the owner does not need to cut anything): mono, one-shots sliced from the long files at -3 dBFS peak, howls low-passed to about 3 kHz with a synthetic tail, bat flurries kept to 2.5 s or less.
- `SFX_LB_Bat_01..06`: squeaks and wing-flutter bursts, at least 2 of them a startled flurry.
- `SFX_LB_Owl_01..04`: single hoots or hoot pairs (made to sound distant in processing).
- `SFX_LB_Howl_01..03`: one howl each (made to sound far off in processing).
- `SFX_LB_Rat_01..05`: scurries and squeaks.

Every page below was opened and read on 2026-11-10 (licence line, duration, rate, bit depth, channels, description). The audio itself was **not auditioned** (no download, no login), so "where the useful part is" comes from the author's description. Search-result cards show rating counts in brackets, not durations; all durations here come from each sound's own page. Pages were fetched at a slow pace after a rate-limit (HTTP 429) on one search.

## Minimum set (download these 15)

### Bats (5 files, for `SFX_LB_Bat_01..06`)
1. [455593: Bat chirp (close-up)](https://freesound.org/people/coelhoigor/sounds/455593/)  (coelhoigor; 30.0 s, 44.1 kHz 16-bit stereo WAV; a bat stuck in a heating duct recorded a couple of inches away with an iPhone. Best close squeak source; slice 2-3 squeaks. Possible faint duct/room noise.)
2. [404152: Bats squeak in the small cave](https://freesound.org/people/Selector/sounds/404152/)  (Selector; 1:47.8, 48 kHz 16-bit stereo WAV; Zoom H6 in a cave; tags squeak, cheep, screech, creak. Slice 2-3 squeaks; cave crunch/scrape between them is to be avoided in the slices.)
3. [806573: Bats in Lod Cave, Thailand](https://freesound.org/people/marc.om/sounds/806573/)  (marc.om; 3:00.9, 44.1 kHz 16-bit stereo WAV; "bats flying and echoing", natural reverb, high squeaks. **Startled flurry source #1**: pick the densest 2 s of flight and fade it.)
4. [546823: Bat wings](https://freesound.org/people/Gammelsmurfen778/sounds/546823/)  (Gammelsmurfen778; 23.5 s, 44.1 kHz 16-bit mono WAV; deliberate flapping made by shaking a leathery-leafed plant at a microphone, tags flap, flutter, leather. Clean, no bed. Wing-flutter bursts; also a layer under a flurry.)
5. [437935: G12-03-Bats flying.wav](https://freesound.org/people/craigsmith/sounds/437935/)  (craigsmith; 1:02.5, 48 kHz 24-bit mono WAV; a loop of bats flying, wings flapping in a circle moving closer and farther from the mic; vintage Hollywood effects transfer, author warns it may contain noise. **Startled flurry source #2**: slice the loudest pass.)

### Owls (3 files, for `SFX_LB_Owl_01..04`; hoots sliced from the files)
6. [688869: Tawny owl.wav](https://freesound.org/people/Elanor1995/sounds/688869/)  (Elanor1995; 22.6 s, 44.1 kHz 24-bit stereo WAV; tags night, winter; popular, 40 ratings, no complaints. Slice 1-2 hoots.)
7. [867131: Tawny Owl Calling at Night, 02:30, Estonia](https://freesound.org/people/inspire153/sounds/867131/)  (inspire153; 24.6 s, 48 kHz 24-bit mono WAV; phone recording at night near a wooded yard, unprocessed; the author is not fully sure of the species. Some street/room bed is possible; fine for a stormy night.)
8. [864872: Tawny Owl in Molkom, Sweden - Cleaned](https://freesound.org/people/sound368/sounds/864872/)  (sound368; 9.8 s, 44.1 kHz 32-bit float stereo WAV; noise-reduced version of Marcuspepsi's recording, two hoots, a very clean source. 32-bit float: normalise down first.)

### Howls (3 files, for `SFX_LB_Howl_01..03`)
9. [500646: Cooper Creek solitary wolf howl very clear](https://freesound.org/people/betchkal/sounds/500646/)  (betchkal; 55.4 s, 44.1 kHz 16-bit mono WAV; a real solitary wolf in Alaska, reverberant creek valley; 195 ratings, 23 comments, none about noise. Slice 1-2 howls: the best real wolf here.)
10. [640060: coyotes howling](https://freesound.org/people/SamsterBirdies/sounds/640060/)  (SamsterBirdies; 49.1 s, 44.1 kHz 24-bit stereo FLAC; coyotes at night, lightly post-processed. A pack howl for a second flavour.)
11. [503516: Distant howling pupper](https://freesound.org/people/sandboks/sounds/503516/)  (sandboks; 15.6 s, 44.1 kHz 24-bit mono WAV; a very small dog's howl, pitch-shifted and given reverb to sound like a distant wolf, tags distant, wolf. Already "far" by design; check by ear that the pitch-shift doesn't sound artificial before using it as the third.)

### Rats (4 files, for `SFX_LB_Rat_01..05`)
12. [143125: ratSqueak.wav](https://freesound.org/people/Zabuhailo/sounds/143125/)  (Zabuhailo; 10.6 s, 96 kHz 24-bit mono WAV; real pet-rat squeaks, close mic; 86 ratings, 9.5k downloads. Slice 2-3 squeaks. Resample to 48 kHz.)
13. [841571: Rodents - Brown Rats; Several Babies Squeaking, Close Perspective](https://freesound.org/people/TheKingOfGeeks360/sounds/841571/)  (TheKingOfGeeks360; 5.4 s, 48 kHz 16-bit stereo WAV; baby rats feeding, close. A soft, clustered squeak.)
14. [872940: Creature Scurry](https://freesound.org/people/RyanTheBlockhead/sounds/872940/)  (RyanTheBlockhead; 5.1 s, 44.1 kHz 16-bit stereo WAV; "a creature scurries around in the dark, echoing off the walls". Best scurry fit for a crypt. Source of the scurry (not a recorded rat); new upload, 0 comments.)
15. [333094: rat gnawing its way down through our wooden ceiling](https://freesound.org/people/ulla_petersen/sounds/333094/)  (ulla_petersen; 29.5 s, 44.1 kHz 16-bit stereo WAV; a real rat gnawing and scratching in wood, indoors at night, Zoom H2n. Slice scratch bursts as the "scrabbling" cues.)

Expected yield: bats 6+ slices from 5 files; owls 4+ hoots from 3 files; howls 3 from 3 files; rats 5 from 4 files.

## Extra candidates (ranked within each group, continuing the numbering)

| # | Id | Title | Author | URL | Duration | Rate / ch | Licence as shown | Why it fits / which part to slice |
|---|---|---|---|---|---|---|---|---|
| 16 | 320721 | bat sounds | pillonoise | [link](https://freesound.org/people/pillonoise/sounds/320721/) | 18.4 s | 44.1 kHz 16-bit, stereo WAV | Creative Commons 0 | Bats in a box at a nature-reserve station, Zoom H2, night; quiet squeaks. Bat group, spare squeak source. |
| 17 | 699232 | Silent Abbey at night.wav | clement.bernardeau | [link](https://freesound.org/people/clement.bernardeau/sounds/699232/) | 2:25.4 | 48 kHz 24-bit, stereo WAV | Creative Commons 0 | Empty Noirlac Abbey at night, "you can hear bats flying near the mics". Right setting for The Last Bell (monastic, bats, silence), but a quiet ambience bed: slice the bat fly-bys by ear. |
| 18 | 806574 | Bat Sounds, Lod Cave, Thailand | marc.om | [link](https://freesound.org/people/marc.om/sounds/806574/) | 38.3 s | 44.1 kHz mono, M4A 64 kbps | Creative Commons 0 | Colony with fluttering wings and ultrasonic calls. Lossy 64 kbps, so last resort. |
| 19 | 245768 | Hundreds of bats screaming and coming out of their nest | felix.blume | [link](https://freesound.org/people/felix.blume/sounds/245768/) | 5:00.4 | 96 kHz 24-bit, stereo WAV (165 MB) | Creative Commons 0 | Twilight roost exit, about 400 bats: the strongest startled-flurry source, but the file is 165 MB and has birds and insects in the bed. Only if 806573 and 437935 disappoint. |
| 20 | 745208 | Tawny owl hooting | Patrick_Corra | [link](https://freesound.org/people/Patrick_Corra/sounds/745208/) | 37.9 s | 48 kHz stereo, OGG 110 kbps | Creative Commons 0 | Night at the Castle of Marostica, phone; good medieval-castle mood. Lossy OGG, so a spare. |
| 21 | 528623 | Owl Slow Hoot | dandman3039 | [link](https://freesound.org/people/dandman3039/sounds/528623/) | 33.7 s | 48 kHz stereo, M4A 266 kbps | Creative Commons 0 | A large owl high in a tree in Vermont: deeper than a tawny, slow hoots. Gives variety; lossy M4A. |
| 22 | 277323 | Owl hoots.wav | Extx | [link](https://freesound.org/people/Extx/sounds/277323/) | 1:44.7 | 96 kHz 24-bit, stereo WAV (57.5 MB) | Creative Commons 0 | Many hoots, ribbon mic, clean. **Made with a Quaker Boy owl hooter (a hunting call device), not a live owl**, so it may sound slightly artificial. Resample to 48 kHz. |
| 23 | 684997 | Tawny Owls in Woodland with Campfire | ibbie | [link](https://freesound.org/people/ibbie/sounds/684997/) | 19.0 s | 48 kHz stereo, MP3 197 kbps | Creative Commons 0 | Two tawny owls answering each other at dusk (Devon). Campfire crackle in the bed and MP3, so only if a hoot-and-answer is wanted. |
| 24 | 655380 | Tawny Owl | faxfaxfax | [link](https://freesound.org/people/faxfaxfax/sounds/655380/) | 7.2 s | 44.1 kHz mono, OGG 120 kbps | Creative Commons 0 | Outside the author's window; author notes heavy noise reduction and slight clipping on the first hoot. Reserve. |
| 25 | 558725 | dogs-howling-yelping-distance-far-04.wav | Gerent | [link](https://freesound.org/people/Gerent/sounds/558725/) | 3.1 s | 44.1 kHz 16-bit, mono WAV | Creative Commons 0 | Coyotes yipping and howling at distance at night, noise-reduced. Very short; a small accent only. |
| 26 | 828478 | Crickets & Creepy Dogs Howling at Night | JoelMcDaniel | [link](https://freesound.org/people/JoelMcDaniel/sounds/828478/) | 1:30.7 | 48 kHz 24-bit, stereo WAV | Creative Commons 0 | Dogs howling and barking in the distance, ZOOM H6 plus shotgun; crickets form the bed (wrong for a stormy night, and hard to remove). Use the low-passed howl only. |
| 27 | 463694 | Dog singing during the night (Brazil) | felix.blume | [link](https://freesound.org/people/felix.blume/sounds/463694/) | 1:32.0 | 96 kHz 24-bit, stereo WAV (50.5 MB) | Creative Commons 0 | A dog answering howling dogs across a valley, ORTF. Beautiful, but crickets in the bed and one dog sings close; the far valley dogs are the part to use. |
| 28 | 353273 | Coyotes with night ambiance.wav | romancito | [link](https://freesound.org/people/romancito/sounds/353273/) | 1:55.4 | 44.1 kHz 16-bit, stereo WAV | Creative Commons 0 | Coyotes barking and howling at night with dogs reacting; crickets and a distant siren are mentioned (avoid the siren part). |
| 29 | 217767 | ratty squeaks.wav | Reitanna | [link](https://freesound.org/people/Reitanna/sounds/217767/) | 16.3 s | 48 kHz 16-bit, mono WAV | Creative Commons 0 | Two pet rats squeaking in annoyance; the author and a commenter say it is artifacty from noise reduction. A fifth squeak source if needed. |
| 30 | 143250 | rat gnawing a rusk.wav | Zabuhailo | [link](https://freesound.org/people/Zabuhailo/sounds/143250/) | 16.1 s | 96 kHz 24-bit, mono WAV | Creative Commons 0 | Close real rat gnawing; texture for "scratching" cues. |
| 31 | 463789 | Mouse Squeaks.wav | shyguy014 | [link](https://freesound.org/people/shyguy014/sounds/463789/) | 28.7 s | 44.1 kHz 16-bit, stereo WAV | Creative Commons 0 | A mouse or rat trapped and squeaking, noise-removed and amplified; sharp and loud, distressed, so use sparingly. |
| 32 | 288941 | rat-squeak.wav | toefur | [link](https://freesound.org/people/toefur/sounds/288941/) | 1.5 s | 44.1 kHz 24-bit, mono WAV | Creative Commons 0 | A synthetic rat squeak (pitch-shifted pig squeal). Clean and short; only if recorded ones are too noisy. |
| 33 | 415203 | Small Animal Scurrying Through Leaves.mp3 | Yin_Yang_Jake007 | [link](https://freesound.org/people/Yin_Yang_Jake007/sounds/415203/) | 10.3 s | 22.05 kHz mono, MP3 160 kbps | Creative Commons 0 | Scurrying in leaves: the wrong surface for a crypt and low quality (22 kHz MP3); the last resort for a scurry. |

## Weak spots (be aware)
- **Rats: the scurry is the weakest part.** Freesound has almost no clean CC0 recording of a rat running on stone. "Rat scurrying" returned one leaf-litter MP3, and "rodent scurry" and "mice scratching" returned nothing under the CC0 filter. The minimum set therefore uses a creature scurry (#14, not a real rat) and a gnawing/scratching recording (#15); real squeaks come from #12 and #13. If the owner finds this too thin, A2 can synthesize the scurries (filtered noise ticks) instead.
- **Howls:** only two real field recordings are clean (#9, #10); #11 is a pitch-shifted dog. Plenty of wolf howls exist but most are close, dry or not CC0.
- **Bats:** the flurry sources are from caves or a vintage effects transfer (#3, #5), not a belfry; the processing is where they become a belfry.

## Checked and rejected
- 574107 "Creature - Rat - Vocalizations": made with mouth sounds (a human voice).
- 557703 "Mice Sqeak.wav": the author imitated the squeak with their own voice.
- 369589 "howl.wav" (taure): the author making werewolf howls by mouth. 380156 "Howl_Echo.wav" (taure, same author, tagged werewolf, "single wolf howls with slight echo"): the page does not say it is a real wolf and the author's other upload is a human; not used.
- 134791 "Rats.mp3": a commenter says background noise ruins it; lossy.
- 585835 "Nature(RatsNest).wav": a voice line, not rats.
- 870593 "Great Horned Owls Hooting, Crickets" and 159727 "Crickets and Owl": crickets by title (not opened). Not opened and not used: 157870, 159726 (far dog barking), 558396-558398 (Gerent owl hooting), 405157, 101345.

## Notes for A2 (preparing the files)
- Sources are mixed: WAV, FLAC, plus lossy OGG/M4A/MP3 only among the extras. Lossless first.
- 32-bit float (864872) and 96 kHz (143125, 277323, 245768, 463694) files: normalise and resample to 48 kHz mono first.
- Bat squeaks sit high (above 8 kHz); keep them out of the low-pass used for the other creature groups. Keep flurries to 2.5 s or less with a fade out.
- Owls: slice one hoot or a hoot pair with about 0.05 s of pre-roll; distance comes from a mild low-pass and the `ATT_LB_Large` attenuation.
- Howls: low-pass to about 3 kHz, add a long synthetic tail, fade in and out (these are very far away).
- Record each used file (id, author, licence CC0, URL) in `Docs/ASSET_REGISTRY.md`.
