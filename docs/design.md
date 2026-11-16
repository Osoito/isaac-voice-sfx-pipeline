# Design: Miyamo voice SFX mod for The Binding of Isaac

Written 2026-09-08. Supersedes nothing; extends `handoff.md`, which came from the
Chiikawa music mod and covers the parts of Isaac modding that are the same for
any audio mod. Everything stated here as a number was measured, not recalled.

---

## 1. What this is

Replace the voices of the game's living things with clips of one anime
character. The player's hurt and death cries, enemy and boss vocalisations,
mouth and body sounds, and the pill / card / rune announcements in
`voiceover/`. Doors, coins, explosions, lasers, UI and ambient loops stay
vanilla.

**Not** a total conversion. An earlier round of this design aimed at all 1590
sfx with heavy DSP, and a working prototype of the hardest part of that was
built and then shelved when the scope narrowed. It is preserved in
`docs/granular-loop-spike.md` for a possible "everything is Miyamo" version
later.

Distribution: local install first. Workshop publishing is deferred, so the
release build and preview material are out of scope for v1 but the deploy script
keeps the `--release` path from the Chiikawa mod so it stays cheap to add.

---

## 2. Environment, as verified today

`handoff.md` section 1 holds, with these corrections and additions.

| Item | Value |
|---|---|
| Vanilla sfx, extracted | `<Isaac install>\extracted_resources\resources\sfx\` |
| Extracted total | 16960 files, 1.2 GB |
| sfx files | 1586 `.wav` + 4 `.ogg` = 1590, matching `filelist.txt` exactly |
| Python | 3.13 with numpy **and scipy** — enough for all DSP here, no new deps |
| ffmpeg / ffprobe | as in handoff |

**`ResourceExtractor.exe` crashes when given its documented arguments.** It
prints `Usage: %s <isaac path> <output path>`, and passing them dies with
0xC0000005 or 0xC0000374 during unpacking — verified across six attempts in two
shells, with piped and file stdin, whole-game and single-archive inputs. Run it
with **no arguments** from its own directory; it then resolves `../../resources`
and writes to `<Isaac install>\extracted_resources\`. It prompts "Press ENTER to
continue" once, so feed it a file of newlines when running it non-interactively.
Thousands of `could not determine filename for entry <hash>` warnings are normal.

Vanilla sfx formats are mixed — 1300 mono / 286 stereo, 1455 at 44.1 kHz / 129 at
48 kHz / 2 at 22.05 kHz, all 16-bit — so the engine does not care. Output is
uniformly **44.1 kHz mono 16-bit**.

---

## 3. Source material

`Voices/` holds 43 mp3 clips totalling **39.9 s**, durations 0.368 – 2.744 s,
median 0.56 s. Three kinds: named interjections (`baga`, `iya`, `nanda`,
`yayamero`, `wusodaro`, `sukisuki`, `otsuki` ×3, `miyamo`, `miyamoto`, `梅干`),
body sounds (`cough`, `gulp`, `belly`, `laugh`, `chuckle`), and `short-1..21`
(19 files) plus `long-1..5`.

Measured limits that constrain everything downstream:

- Only **17 of 43** clips contain a voiced segment of 120 ms or longer.
- The longest sustained voiced segment in the whole set is **0.313 s**
  (`long-3`).
- Pitch clusters at the extremes: `miyamoto` at 115 Hz, `otsuki` at 490 Hz,
  little in between.

These are properties of the material. No parameter tuning changes them, and any
plan that assumes a deep well of sustained vowels is wrong.

---

## 4. Target set

### How it was derived

Filename keywords alone do not work. A regex pass missed `dog howell` (spelled
with an extra e), `boo mad`, `bluespider_die`, every `mom/hurt N`,
`bumbino/getting dizzy N`, `haunt_random_N`, and most boss `*_death` files.
`handoff.md` already warned that several hundred vanilla filenames carry no
usable semantics.

Acoustic classification was tried and **failed**, and the failure is worth
recording so nobody repeats it. Scoring each file by the fraction of frames with
a strong autocorrelation peak in the 60–500 Hz range, then validating against
subsets whose answer is known:

| group | n | mean voiced fraction |
|---|---|---|
| known voice (`player/` + `voiceover/`) | 212 | 0.34 |
| known mechanical (`feedback/` coins, keys, doors) | 21 | **0.54** |

The mechanical group scores *higher*. Coins and keys are metallic and strongly
resonant, while speech carries unvoiced consonants, so periodicity separates
"pitched" from "noisy", not "voice" from "object". Separating voice would need
formant structure and F0 drift over time. Script kept at
`spikes/acoustic-classifier/voiced.py`; do not resurrect it without a better
feature.

What worked: a keyword pass for the unambiguous cases, then **reading all 919
remaining entity-area filenames by hand** and recording the judgements as data.

### The result

| | |
|---|---|
| In scope | **590 files, 1075.0 s** |
| Reuse ratio against 39.9 s of source | **27 : 1** |
| Distinct variant groups | 397 |
| Hand decisions once `voiceover/mega` and `/reversed` derive from base | **~325** |
| Pending a listen before inclusion | 22 |

Composition, by file: `player/` 11, `voiceover/` 201, keyword-matched
vocalisations 202, mouth and body sounds 71, plus **105 hand-added** files the
keywords missed. Every one of those 105 paths was checked to exist against the
extracted tree; zero typos.

`voiceover/`'s 201 files form 196 variant groups: 124 base lines, 50 under
`mega/`, 22 under `reversed/`.

Duration: median 1.280 s, p25 0.831, p75 1.963. Only 7 files are under 0.15 s.
The transient problem that dominated the earlier full-coverage design is
essentially gone.

Files:

- `data/scope_additions.txt` — hand-reviewed additions and the 22 uncertain
  entries, marked with a trailing `?`. **Source of truth, edited by hand.**
- `data/scope_list.txt` — the 590 paths, generated by `tools/scope.py`.

### Deliberate exclusions

Three files over 20 s are out for v1: `greed sfx/whispering wraiths.wav` (60.0 s),
`dogma/preacher.wav` (48.5 s), `dogma/preacher_1.wav` (28.4 s). Filling 60 s from
39.9 s of source without obvious repetition is not possible; a bad replacement
here is worse than vanilla. The remaining 8 files between 6 s and 15 s are in
scope and use multi-atom chaining.

The 22 uncertain entries (`animal squish`, `skin pull`, `blobby wiggle`,
`finalmother/misc 1`, `gurdy/gurdy_face_*`, and others) go onto the audition page
and are settled by listening, not guessed at now.

---

## 5. Architecture

```
IssacMiyamoVoices/
  Voices/                 original mp3, read-only, never modified
  data/
    scope_additions.txt   hand-reviewed scope data
    scope_list.txt        generated: the 590 in-scope paths
  atoms/                  atom library: wav files + atoms.json
  tools/
    scope.py              builds scope_list.txt
    classify_by_name.py   the first-pass keyword classifier
  build/
    ffio.py               the only module that knows where ffmpeg is   [from Chiikawa]
    dsp.py                pure functions: numpy in, numpy out
    vanilla.py            measure + classify targets -> vanilla_spec.json
    atomize.py            split + tag Voices -> atoms/
    recipes.py            pure data: acoustic class -> synthesis recipe
    semantic.py           pure data: vanilla path -> chosen atoms
    mapping.py            pure logic, no I/O: the four above -> plan.json, validate()
    build_sfx.py          execute the plan, bake 590 wav files
    verify.py             machine checks, non-zero exit on FAIL       [structure from Chiikawa]
    audition.py           HTML listening page                          [structure proven today]
    deploy.py             install into the game, dev vs release        [from Chiikawa]
  mod/                    the shippable mod
  spikes/                 shelved experiments, see docs/
  docs/
```

```
Voices/*.mp3 ──atomize.py──> atoms/*.wav + atoms.json ─┐
                                                       │
extracted sfx ──vanilla.py──> vanilla_spec.json ───────┤
                                                       ├──> mapping.py ──> plan.json
                            recipes.py ────────────────┤        │
                            semantic.py ───────────────┘    validate()
                                                                │
                                          build_sfx.py ─────────┴──> mod/resources/sfx/**.wav
                                                                        │
                                                        verify.py / audition.py
```

Three separations, each so that an expensive step is not repeated for a cheap
change:

1. **Measurement from mapping.** `vanilla.py` reads 1.2 GB once and lands
   `vanilla_spec.json`. Recipe and semantic edits never touch audio again.
2. **Mapping from baking.** `mapping.py` has no I/O; it produces the full
   "which atom goes where" plan and self-checks in about a second. `build_sfx.py`
   runs the DSP and takes minutes. Changing a joke costs a second.
3. **DSP from files.** `dsp.py` takes numpy arrays and returns numpy arrays, so
   the fiddly parts are testable without audio files.

`plan.json` is committed. A one-line semantic change then shows up as a diff over
every position it affects, including the ones that were not anticipated.

---

## 6. Atom library (`atomize.py` → `atoms/`)

27:1 reuse means the 43 clips must be cut into reusable pieces.

**Splitting.** Search for energy dips, treat the rise out of a dip as a syllable
start and the next dip as its end. Do **not** select by maximum short-term RMS:
`handoff.md` section 5 records that method failing twice on the music mod because
it always lands in the middle of a phrase, and speech makes that worse.

**Trim leading and trailing digital silence from every source first**, and derive
everything downstream from the trimmed copy, so an offset means the same thing in
the build, the checks and the audition page.

**Tags**, which are what recipes select on:

| tag | why |
|---|---|
| duration | picks the duration band |
| f0 | semitones needed to reach a target pitch; also voiced/unvoiced |
| voiced ratio | separates plosive consonants (transients) from vowels (sustains) |
| attack time | impact recipes need onsets under 20 ms |
| spectral centroid | brightness matching against the vanilla file |
| envelope class | impact / sustain / crescendo / decay |
| loudness | normalisation basis |

Expect 150–300 atoms. **Review once, then pin the cut points into `atoms.json`
and stop recomputing them.** Automatic selection is mutually exclusive — editing
one unpinned cut silently relocates every other atom sharing that source — which
cost the Chiikawa mod a full review round.

---

## 7. Synthesis recipes (`recipes.py`)

`vanilla.py` classifies each target on two axes: a duration band, and an envelope
class read off the RMS curve (impact / sustain / crescendo / composite).
`recipes.py` maps the pair to a strategy.

| strategy | applies to | method |
|---|---|---|
| `TRUNC` | < 0.4 s (43 files) | take only an atom's attack segment; a plosive is already a transient |
| `DIRECT` | 0.4–1.5 s impact or decay (297 files) | one atom, pitch nudge, envelope shaping |
| `CHAIN` | 1.5–15 s (247 files) | 2–6 atoms in series, crossfaded at the joins |
| `CRESC` | crescendo envelopes | atom plus rising pitch and swelling gain |
| `LAYER` | boss roars, anything needing weight | several atoms stacked at different pitches |

**Precedence, because the two axes collide.** `CRESC` and `LAYER` are selected by
envelope class and `TRUNC` / `DIRECT` / `CHAIN` by duration, so a 2 s crescendo
matches two rows. Envelope wins: a target classified crescendo takes `CRESC`
whatever its length, and `LAYER` is only ever chosen by an explicit
`semantic.py` entry. The duration bands then decide everything left over, and the
file counts in the table above are those leftovers, which is why they sum to the
587 in-scope targets.

`GRAIN` (granular synthesis) is **not** needed here — it existed for ambient
loops, which are now out of scope. Its implementation survives in
`spikes/granular-loops/grain.py` if the hardcore version revives it.

### Two rules carried over from the spike

**Replacements do not need to match length.** Isaac's sfx are fire-and-forget; a
shorter file simply ends sooner. The binding constraint is an upper bound —
a longer file overlaps itself when the sound retriggers.

**Any chain that produces a loop must be circular end to end.** The spike found
that perfect circular granular synthesis was destroyed by a single ordinary
`scipy.signal.sosfilt`, which is causal and starts from zero state: the seam
metric went from 0.28 to 11.09. Not needed for v1's targets, but if `dsp.py` ever
grows a loop path, this belongs in its contract and in `verify.py`, because the
failure is inaudible in one pass and only appears on repeat.

---

## 8. Semantic table (`semantic.py`)

With the scope narrowed to voices, this is the primary mechanism rather than an
override layer, and it is where the mod is actually funny. Three rules reduce 397
groups to roughly 325 decisions.

**A numbered group is one decision and a pool of atoms.** `monster roar 1..10` is
a single judgement — "this is a monster roar" — plus a pool. The engine already
picks randomly among numbered variants, so distinct atoms across the group buy
runtime variety with no Lua at all. 99 groups in scope have more than one member.

**`voiceover/mega/` and `voiceover/reversed/` derive from the base lines.**
Vanilla's mega variants are the same line, deeper and heavier. Applying the same
transform to our own replacements gives consistency for free and removes 72
decisions.

**Pill and card announcements bind one effect to one atom, permanently.** If
`health down` is always the same clip, a player learns it in a few runs. The
information is re-encoded, not destroyed. This is the readability constraint
landing in the semantic layer, and it is also the best joke in the mod.

---

## 9. Constraints as checks (`mapping.py: validate()`)

Any rule that has to hold across many items belongs in code. The Chiikawa mod had
exactly one bad entry in 63 and eye inspection never found it; here there are 590.

- every target path exists in a checked-in copy of the vanilla list
- output duration ≤ vanilla duration × 1.05
- no atom is used twice within one numbered variant group
- crescendo targets produce a positively-sloped RMS regression
- no clipping; onset is not silent; tail decays
- loudness sits within tolerance of the vanilla file it replaces
- every `mega` / `reversed` entry resolves to an existing base line

Test the checks by reintroducing a fault and confirming they fire.

---

## 10. Verification, three layers

Cheapest first, so that the loop needing human ears does not also need the game.

**Layer 1 — machine, no game, no ears.** Section 9, run as part of the build,
non-zero exit on failure.

**Layer 2 — ears, no game.** A self-contained HTML page, one row per target:
vanilla and replacement side by side, waveform, the measurements. Published as an
artifact. The structure was proven today on the loop spike; drawing the *wrap
point* as well as the envelope let a numeric claim be checked by eye, and the
equivalent here is showing the replacement against the original's envelope. The
22 uncertain scope entries are settled on this page.

**Layer 3 — in game, deterministic.** A dev-only Lua file registering console
commands that fire each sound directly. It catches the three things layer 2
cannot see: a mistyped path, which **fails silently by falling back to vanilla**;
a one-shot that loops; and loudness wrong in the real mix. It prints a ready line
on load, so its absence is the signal that it failed to load.
`deploy.py --release` excludes it.

---

## 11. Deployment

`deploy.py` from the Chiikawa mod, with `MOD_DIR_NAME` and the dev-file list
changed. The properties worth keeping, all from `handoff.md` section 4:

- a marker file identifies folders this project created, and the script refuses
  to overwrite a folder it did not create, so a subscribed mod of the same name
  cannot be clobbered
- preflight: every path referenced by the build exists before anything is copied
- `<id>` and `<version>` in `metadata.xml` belong to the uploader and are pulled
  back before overwriting; the file has mixed line endings and must be patched in
  binary or with `newline=""`
- close the game and the uploader before deploying

`metadata.xml` carries `<tag id="Sound Effects"/>`. Mod folder name and
`<directory>` must match.

---

## 12. Known limits, stated up front

- **27:1 reuse.** 39.9 s of source covers 1075 s of vanilla audio. Heavy repetition
  is inherent, not a bug, and belongs in the mod description.
- **Only 17 clips have a sustained voiced segment, none longer than 0.313 s.**
  Long targets are chains of short pieces and will sound like it.
- **Three files over 20 s are not replaced.** See section 4.
- **Pitch material is bimodal** (115 Hz and 490 Hz with a gap), so pitch variety
  comes from shifting rather than from the source.
- Pill announcements change meaning-carrying audio. Mitigated by fixed binding
  (section 8), not eliminated.

---

## 13. Open questions

1. Which of the 22 uncertain files belong in scope — settled at Layer 2.
2. Whether `TRUNC` on plosives actually reads as an impact, or as a click. First
   thing to prototype after the atom library exists.
3. Mod name, folder name, and description text.

Version control was considered and declined on 2026-09-08. `plan.json` is still
worth writing to disk and keeping between runs: without diffs, the way to see
what a semantic edit changed is to compare the previous plan against the new one,
so `build_sfx.py` keeps the last plan as `plan.prev.json` and `mapping.py`
reports the delta itself.
