# Miyamo Voice SFX for The Binding of Isaac: Repentance+

Replaces 673 of the game's sound effects with cut-up voice clips of one
character. Published on the Steam Workshop as item
[3798883789](https://steamcommunity.com/sharedfiles/filedetails/?id=3798883789).

43 source clips had to cover 673 slots, about 16 slots per clip, and a replacement that
is funny the first time becomes unbearable the twentieth. That is the problem
this repository solves. The pipeline cuts the clips into usable pieces, measures
what each piece sounds like, measures what each target sound demands, assigns
under stated constraints, and puts real audio in front of a human before
anything is committed to.

```
Voices/*.mp3                43 raw clips
   | build/atomize.py       cut on energy dips -> 70 atoms, tagged
   | tools/scope.py         pick 676 targets worth replacing, out of 1633
   | build/vanilla.py       measure them once -> vanilla_spec.json
   | build/auto.py          constrained assignment by acoustic fit
   | build/semantic.py      hand-picked overrides, which always win
   | build/choose.py        audition pages: candidates playable in the browser
   | build/bake.py          render, then 8 checks that fail the build
   v build/deploy.py        install, or produce an uploadable release
```

## Signal processing

`build/dsp.py` is pure numpy and scipy, no file access, so it stays testable
without audio. It provides silence trimming, framing, RMS envelope, spectral
centroid as a brightness measure, an envelope classifier (percussive, sustained,
swell), pitch shifting by resampling, and fades.

Segmentation searches for energy dips and treats the rise out of a dip as a
syllable start. Selecting by maximum short-term RMS instead, which is the
obvious approach, lands in the middle of a phrase every time.

## Why assignment needs constraints, and not only an acoustic score

A pure duration match throws away everything that makes the mod work. At 1:16,
placing each clip wherever it scores best produces a mod where the same laugh
answers a coin drop, a door and a boss. `build/auto.py` scores on duration,
envelope class, brightness and pitch, and then applies rules that are stated
once and checked over the whole set:

- Recognisable spoken words are allowed only on sounds that fire once per event,
  such as a pill identification or a boss entrance. A sound that retriggers
  within seconds turns a word into a stuck record, so a group with three or more
  numbered variants is disqualified from speech, as is any name matching a
  repeated-action pattern.
- Pickups and machines draw only from atoms no creature or player sound already
  uses, and never chain two atoms together. A coin landing is one event, so it
  gets one atom.
- Per-source budgets cap how much of the mod any one clip can account for.

`build/semantic.py` holds the choices a person made by listening. It is pure
data and it always wins over the automatic result.

## Checks that fail the build

`build/bake.py` collects every violation and fails the run. It does not warn and
carry on:

1. the target is a real vanilla path (a mistyped path fails silently in game, the
   engine falls back to its own asset, and nothing downstream can catch it)
2. every atom the entry names exists on disk
3. the output is no longer than 1.05x the file it replaces, where that bound is
   switched on; a retriggering sound would otherwise overlap itself
4. the peak stays under 0.95, so it does not clip
5. it is no more than 6 dB below the file it replaces
6. the first frames carry at least 2% of the peak, so it does not start silent
7. the last half millisecond is under 10% of the peak, so the fade reached zero
   and it will not click
8. no two variants inside one numbered group share an atom at the same pitch,
   which would waste the engine's own randomisation

Each threshold is a named constant at the top of `build/bake.py`.

`python -m pytest` covers the DSP and the atomizer. 35 tests.

## Audition pages

`build/choose.py`, `build/preview.py` and `build/all_options.py` generate
self-contained HTML with the audio inlined as base64: numbered rows, the game's
own sound against the proposed replacement, playable in place. Every judgement
about how the mod sounds was made on one of these pages, and the numbering on a
page is frozen once it has been handed over, so feedback can refer to row 38
weeks later.

The pages are not committed. They are megabytes of someone else's audio and they
regenerate in seconds.

## Layout

| Path | What it is |
|---|---|
| `build/dsp.py` | Pure DSP. numpy in, numpy out. |
| `build/ffio.py` | The only module that knows where ffmpeg is. |
| `build/atomize.py` | Clips to tagged atom library. |
| `build/vanilla.py` | Measure the targets in scope once into JSON. |
| `build/auto.py` | Constrained assignment. |
| `build/semantic.py` | Hand-picked overrides. Pure data, edited most. |
| `build/bake.py` | Render and check. |
| `build/deploy.py` | Install, release build, uninstall, dry run. |
| `tools/scope.py` | Choose which of the game's 1633 sfx are worth replacing. |
| `tests/` | pytest, 35 cases. |
| `spikes/granular-loops/` | Background loops by granular synthesis. Shelved, documented. |
| `spikes/acoustic-classifier/` | Voiced / unvoiced detection. |
| `docs/design.md` | What the mod covers and why, every number measured. |
| `docs/release-checklist.md` | Steam Workshop publishing, in order. |
| `handoff.md` | Everything verified about Isaac audio modding: paths, metadata.xml traps, the two separate volume switches that silence a correct build. |

## Running it

Needs Python 3.13 with numpy and scipy, and ffmpeg on PATH.

```powershell
python build/atomize.py
python build/vanilla.py
python build/auto.py
python build/bake.py
python build/deploy.py
```

## What is not here

No audio. The voice clips come from a commercial anime and the targets are the
game's own files; neither is mine to redistribute. `Voices/`, `atoms/` and
`mod/resources/` are excluded. Drop your own clips into `Voices/` and the
pipeline runs end to end.
