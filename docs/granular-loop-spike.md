# Spike: background loops by granular synthesis

Shelved on 2026-09-08 when the mod's scope narrowed to voices of interactive
entities. Kept for the "everything is Miyamo" hardcore version. Code in
`spikes/granular-loops/`.

Audition page (6 candidates, A/B against vanilla): rebuild it with
`python spikes/granular-loops/grain.py`.

## Status: technically proven, aesthetically unjudged

The method works and the numbers are good. **Nobody has said whether it sounds
right.** The scope decision that shelved it was about what the mod should cover,
not about how the loops sounded, so the listening verdict is still open. Anyone
resuming this starts by listening to the six candidates and picking one per
target, or concluding the whole approach sounds wrong.

## What was built

`spikes/granular-loops/grain.py` targets `lava_loop.wav` (10.159 s) and
`portal_loop.wav` (4.134 s), both 44.1 kHz mono, and produces three candidates
each. `prep.py` folds the audio and measurements into `page.html` to make the
audition page.

Pipeline per candidate: pick a sustained voiced segment from a source clip →
circular overlap-add granular synthesis at the target length → tone shaping →
limit to the vanilla file's RMS under a fixed budget.

## The two findings worth keeping

**Circular overlap-add makes a loop seamless by construction.** Each grain is
written at `out[(pos + arange(g)) % N]`, so a grain crossing the end wraps to
the start. No crossfade, no click, wherever grains land. The amplitude
modulation uses only whole numbers of cycles over N for the same reason.

**Every stage after it must also be circular, or the guarantee is destroyed.**
`scipy.signal.sosfilt` is causal and starts from zero state. Applying it
directly to a seamless buffer left a step at the wrap point and pushed the seam
metric from 0.28 to **11.09** — the synthesis was perfect and the filter ruined
it. Fix: tile the signal three times, filter, keep the middle copy
(`circ_filter`). The limiter has the same requirement, met with `mode="wrap"` on
the envelope follower and a circular pad before the smoothing convolution.

> This is the contract for any future `dsp.py`: **a loop-producing chain is
> circular end to end, or it is broken.** Worth an automated check rather than
> care, because the failure is inaudible in a single pass and only shows up on
> repeat.

## Measuring a seam

Correlating the last 20 ms against the first 20 ms — the first thing tried —
measures nothing. For a noise-like signal that correlation is near zero whether
the join is clean or not, so it reports failure on a perfect loop and gives no
warning on a broken one.

What works: the jump between the last and first sample, divided by the
waveform's own 99.9th-percentile sample-to-sample step.

```
seam = |y[0] - y[-1]| / percentile(|diff(y)|, 99.9)
```

At or below 1.0 the join is indistinguishable from ordinary motion inside the
wave.

| | seam |
|---|---|
| vanilla `lava_loop.wav` | 1.41 |
| vanilla `portal_loop.wav` | 11.63 |
| all six synthesised candidates | 0.02 – 0.28 |

The game's own loops are hand-cut and not seamless. Anything built this way beats
them without trying.

## Loudness

Each candidate is driven to the vanilla file's RMS under a 6 dB limiting budget,
following the handoff's rule of deriving the target from the material instead of
forcing a chosen number.

| target | vanilla RMS | reached | limiting used |
|---|---|---|---|
| `lava_loop` | 0.2124 | 0.2115 – 0.2324 | 0 – 1 dB |
| `portal_loop` | 0.4259 | 0.2789 – 0.3138 | 6 dB, still 2.7 – 3.7 dB short |

`portal_loop` is a hot file. The budget runs out before it matches. The shortfall
is reported, not hidden; raising `budget_db` would close it at the cost of
audible squashing.

## The real ceiling is the source material

Of 43 clips, only **17** contain a voiced segment of 120 ms or more, and the
longest is 0.313 s (`long-3`). Pitch is clustered at the extremes — `miyamoto`
at 115 Hz and `otsuki` at 490 Hz, with little between — so two of the three lava
candidates were forced onto the same source.

A hardcore version covering all 25 loop files and the 39 clips over 6 s would be
recycling these same ten-odd segments throughout. That is a property of the
material, not of the algorithm, and no amount of parameter tuning changes it.
Getting further means more source audio.

## Candidate parameters

| target | variant | source | grain | density | pitch (st) | tone |
|---|---|---|---|---|---|---|
| lava | A-dense-low | miyamoto | 70 ms | 110/s | -12 -10 -7 | dark |
| lava | B-med-rough | miyamoto | 45 ms | 70/s | -12 -7 -5 0 | dark |
| lava | C-long-grain | long-3 | 120 ms | 45/s | -12 -9 | dark |
| portal | A-airy | otsuki | 38 ms | 85/s | -5 0 +5 +7 | airy |
| portal | B-wide | otsuki | 28 ms | 120/s | -12 -5 0 +7 +12 | airy |
| portal | C-dark | miyamoto | 50 ms | 90/s | -7 0 +5 | airy |

Grain size is the parameter that decides whether the result reads as a texture
or as a person: short grains shred the voice into noise, long ones let syllable
identity leak back through.

## To resume

1. `python spikes/granular-loops/grain.py` then `prep.py`. Both need vanilla sfx
   extracted — see [[isaac-resource-extractor-args-crash]]; the extractor only
   works with no arguments and writes to `<Isaac install>\extracted_resources\`.
2. Listen to the six candidates and settle the open aesthetic question.
3. The remaining loop targets are the 25 files matching `*loop*` and the 39 over
   6 s, listed by `docs/` measurements. `whispering wraiths.wav` at 60 s and
   `dogma/preacher.wav` at 48.5 s are the extremes.
