# Freesound: lightning cracks and strikes (P16-5, CC0 only)

The owner rejected the synthetic thunder cracks (`SFX_LB_Thunder_Near_*` and `SFX_LB_Thunder_Strike_*`). We keep our generated rumble and replace only the crack with a recording.

Log in to freesound.org, open each link, click **Download**, and save into `ExternalAssets/Incoming/freesound/` with the default file name. Skip any page that no longer says "Creative Commons 0".

How the files will be used (A2 prepares them, the owner does not need to cut anything):
- `SFX_LB_Thunder_Strike_01..03`: three different cracks, each with a short natural tail, from the minimum set.
- `SFX_LB_Thunder_Near_01..04`: a crack layer sliced from the same files (about the first 0.3 to 1 s of the strike), laid over the generated rumble.

Every page below was opened and read on 2026-11-09 (licence line, duration, rate, bit depth, channels). The audio itself was **not auditioned** (no download, no login), so "where the crack is" is taken from the author's description. The crack is a single transient per file in most of them; A2 locates it with a peak detector and slices there.

## Minimum set (download these 4)

1. [721072: thunder sharp dry crack 2](https://freesound.org/people/cognito%20perceptu/sounds/721072/)  (cognito perceptu; 16.9 s, 44.1 kHz 16-bit stereo WAV; "dry, sharp crack, no wind or rain, quite close, clean recording". Best fit: a distinct crack, no bed.)
2. [760214: Thunder Clap And Rumble #7](https://freesound.org/people/Kinoton/sounds/760214/)  (Kinoton; 15.0 s, 48 kHz 24-bit stereo WAV; "dry version of a single lightning strike at close distance", PCM-D100 ORTF, denoised.)
3. [567945: 200817 Thunder, pretty close crack 4pm](https://freesound.org/people/TRP/sounds/567945/)  (TRP; 15.6 s, 48 kHz 24-bit stereo FLAC; "mostly dry, pretty close, isolated thunder clap".)
4. [347853: thunder crack.wav](https://freesound.org/people/cognito%20perceptu/sounds/347853/)  (cognito perceptu; 19.0 s, 44.1 kHz 16-bit stereo WAV; loud close crack with its rumble; recorded at a low level so almost no background, but it needs a gain boost.)

## Extra candidates (ranked, continuing the numbering)

| # | Id | Title | Author | URL | Duration | Rate / ch | Licence as shown | Why it fits / where the crack is |
|---|---|---|---|---|---|---|---|---|
| 5 | 536903 | thunder dry crack rumble.wav | cognito perceptu | [link](https://freesound.org/people/cognito%20perceptu/sounds/536903/) | 10.6 s | 44.1 kHz 16-bit, stereo WAV | Creative Commons 0 | "Sharp crack with rumbling from an approaching storm, no rain or wind." Crack first, rumble after; short file, the crack is the main event. Pack "dry thunder". |
| 6 | 840628 | Closeup Thunder Strike 01 | loganzsound | [link](https://freesound.org/people/loganzsound/sounds/840628/) | 14.0 s | 44.1 kHz 24-bit, stereo WAV | Creative Commons 0 | Close-up strike (Blue Yeti Pro, Savannah). Tagged crack/boom/loud; no rain or wind mentioned on the page. Crack position not stated. |
| 7 | 616992 | 210914 Thunder, crack, pretty close, bit of distortion, urban, TORONTO 1am | TRP | [link](https://freesound.org/people/TRP/sounds/616992/) | 38.6 s | 48 kHz 24-bit, stereo WAV | Creative Commons 0 | "Single thunder crack, fairly close", with electrical clicks at the moment of the strike (nice for the Strike sounds). Author notes a bit of distortion. Long file: the crack is one event, most of the rest is tail. |
| 8 | 574412 | Thunder big crack explosive close ms 77mel 190903.flac | TRP | [link](https://freesound.org/people/TRP/sounds/574412/) | 18.0 s | 48 kHz 24-bit, stereo FLAC (mid/side) | Creative Commons 0 | "Quite close, big explosive thunder." Good for the biggest Strike (`Strike_03`). No rain or wind mentioned. |
| 9 | 437243 | Very close lightning strike. | Simon Spiers | [link](https://freesound.org/people/Simon%20Spiers/sounds/437243/) | 63.8 s | 48 kHz 24-bit, stereo WAV | Creative Commons 0 | Cloud-to-ground strike within 100 m; tagged bang/explosion/shotgun, so the onset should be very sharp. Long file (17.5 MB): slice the first seconds only. Rain/bed not described. |
| 10 | 844420 | Extreme Thunder Impact - Munich Trudering (Raw Excerpt) | TSP-Talk | [link](https://freesound.org/people/TSP-Talk/sounds/844420/) | 40.6 s | 48 kHz 32-bit float, stereo WAV | Creative Commons 0 | "Sudden, broadband impact with a sharp transient peak"; only faint distant traffic. Heavy low end, so use it for a Strike rather than the Near layer. 32-bit float: normalise down first. |

Reserve (read and acceptable, but weaker; use only if one above fails the ear test):

| Id | Title | Author | URL | Duration | Rate / ch | Licence | Note |
|---|---|---|---|---|---|---|---|
| 717907 | 230713 Thunder, close crack crash big, Stratford ON 2am | TRP | [link](https://freesound.org/people/TRP/sounds/717907/) | 36.1 s | 48 kHz stereo MP3 320 kbps | Creative Commons 0 | "Single fairly close thunderclap." Lossy source. |
| 336314 | 06/10/2014 close lightning strike | supercell10 | [link](https://freesound.org/people/supercell10/sounds/336314/) | 14.1 s | 44.1 kHz 16-bit stereo WAV | Creative Commons 0 | "Close high amp strike that knocked out power." Tagged rain; contents unverified. |
| 434359 | Close lightning strike 2018 07 07 | csengeri | [link](https://freesound.org/people/csengeri/sounds/434359/) | 36.4 s | 44.1 kHz 16-bit stereo WAV | Creative Commons 0 | Very close, popular (85 ratings), but a comment says too much initial distortion and an animal (rooster, dog) reacts on it. Dictaphone. |

Checked and rejected: 576041 "Huge Thunderclap" (a person screams in the first second, rain on a tin roof throughout); 244358 "Rain and Thunder 02" (rain bed, 1:54); 483684 (5 min storm bed, one strike under a minute in); 693540 (the crack clips and distorts, by the author's note); 743511 (mono OGG, highway bridge, traffic).

## Notes for A2 (preparing the files)
- Search-result cards show rating counts in brackets, not durations; the durations above come from each sound's own page.
- Lossless sources first (WAV/FLAC); 717907 is the only MP3 and is in reserve.
- Several files are long with a tail: cut the crack with about 0.05 s of pre-roll and a fade out by 1.5 to 3 s for the Strike sounds, and about 0.3 to 1 s for the Near layer. Keep our generated rumble under the Near layer.
- #4 (347853) was recorded at a low level because the crack was loud; expect to normalise it and watch the noise floor.
- Record each used file (id, author, licence CC0, URL) in `Docs/ASSET_REGISTRY.md`.
