"""Bake the chosen atoms into the mod's wav files, then check them.

  python build/bake.py

Checks, all of which fail the run rather than warn:
  - the target is a real vanilla path
  - the output is no longer than the vanilla file (a longer sound overlaps
    itself when it retriggers)
  - it does not clip, does not start silent, and decays at the end
  - it is not far quieter than the file it replaces
  - no two variants inside one numbered group share an atom at the same pitch,
    which would waste the engine's free randomisation
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import auto, dsp, ffio, semantic, vanilla

ROOT = Path(__file__).resolve().parent.parent
ATOMS_DIR = ROOT / "atoms"
SPEC_JSON = ROOT / "data" / "vanilla_spec.json"
MOD_SFX = ROOT / "mod" / "resources" / "sfx"
REPORT = ROOT / "data" / "build_report.json"

MAX_DURATION_RATIO = 1.05
PEAK_CEILING = 0.95
SHORTFALL_LIMIT_DB = -6.0
ONSET_MIN_FRAC = 0.02
# A click is the waveform being cut off at non-zero amplitude. Measure the last
# 0.5 ms only: an 8 ms linear fade is still at 25% amplitude 2 ms from the end,
# so a wider window flags every sound that simply ends loudly. The thing to
# measure is whether the fade-out actually reached zero -- not whether the sound
# was still loud shortly before the end, which is normal and audible as an
# abrupt ending rather than a click. That is reported as a note instead.
CLICK_MAX_FRAC = 0.10
ABRUPT_FRAC = 0.60


AUTO_MAP = ROOT / "data" / "auto_map.json"
XFADE_MS = 18.0

# Sample rate written into the mod. All processing happens at dsp.SR; this is
# only the rate on disk. Vanilla itself ships 22.05, 44.1 and 48 kHz files, so
# the engine accepts any of them, and halving the rate halves the upload.
OUTPUT_SR = int(os.environ.get("MIYAMO_OUTPUT_SR", dsp.SR))


def full_table():
    """Hand-written picks win; the auto map fills in everything else."""
    table = {}
    if AUTO_MAP.exists():
        for path, e in json.loads(AUTO_MAP.read_text(encoding="utf-8")).items():
            table[path] = dict(e)
    for path, e in semantic.TABLE.items():
        atoms = e.get("atoms") or [e["atom"]]
        # Keep the acoustic category a hand-picked entry belongs to, so a
        # per-category preview still shows every file in that category --
        # including, especially, the ones just corrected by hand.
        cat = table.get(path, {}).get("cat") or auto.category(path)
        table[path] = {**e, "atoms": atoms, "cat": cat, "manual": True}
    return table


def bake():
    spec = {r["path"]: r for r in json.loads(SPEC_JSON.read_text(encoding="utf-8"))}
    rows, errs, skipped = [], [], []

    for path, e in full_table().items():
        atom_ids, semis = e["atoms"], e["semitones"]
        van = spec.get(path)
        if van is None:
            errs.append(f"{path}: not a vanilla path")
            continue
        if e.get("skip"):
            # Leave the game's own asset in place by not shipping a file at all.
            stale = MOD_SFX / path
            if stale.exists():
                stale.unlink()
            skipped.append(path)
            continue
        missing = [a for a in atom_ids if not (ATOMS_DIR / f"{a}.wav").exists()]
        if missing:
            errs.append(f"{path}: atoms do not exist: {', '.join(missing)}")
            continue

        parts = [ffio.read_wav(ATOMS_DIR / f"{a}.wav") for a in atom_ids]
        y = parts[0] if len(parts) == 1 else dsp.chain(parts, dsp.SR, XFADE_MS)
        if e.get("trim_to"):
            y = y[:int(e["trim_to"] * dsp.SR)]
        if semis:
            y = dsp.pitch_shift(y, semis)
        y = dsp.fade(y, dsp.SR, e["fade_in"], e["fade_out"])
        if e["cap"]:
            y = dsp.fit_duration(y, dsp.SR, van["dur"] * MAX_DURATION_RATIO)
        y, limit_db, short_db = dsp.match_rms(y, van["rms"])

        dest = MOD_SFX / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        ffio.write_wav(dest, dsp.resample(y, dsp.SR, OUTPUT_SR), OUTPUT_SR)

        peak = float(np.abs(y).max())
        k = int(0.020 * dsp.SR)
        rows.append({
            "path": path, "atoms": atom_ids, "atom": atom_ids[0],
            "cat": e.get("cat", "?"), "manual": bool(e.get("manual")),
            "semitones": semis,
            "dur": len(y) / dsp.SR, "van_dur": van["dur"],
            "rms": float(np.sqrt((y ** 2).mean())), "van_rms": van["rms"],
            "peak": peak, "limit_db": limit_db, "shortfall_db": short_db,
            "onset_frac": float(np.abs(y[:k]).max() / peak) if peak else 0.0,
            "click_frac": float(np.abs(y[-int(0.0005 * dsp.SR):]).max() / peak)
                          if peak else 0.0,
            "abrupt_frac": float(np.abs(y[-k:]).max() / peak) if peak else 0.0,
            "shorter": len(y) / dsp.SR < van["dur"] * 0.95,
            "capped": e["cap"], "same_ok": e["same_ok"],
        })

    for r in rows:
        if r["capped"] and r["dur"] > r["van_dur"] * MAX_DURATION_RATIO + 1e-3:
            errs.append(f"{r['path']}: {r['dur']:.3f}s longer than the "
                        f"{r['van_dur']:.3f}s it replaces")
        if r["peak"] > PEAK_CEILING:
            errs.append(f"{r['path']}: clips at {r['peak']:.3f}")
        if r["shortfall_db"] < SHORTFALL_LIMIT_DB:
            errs.append(f"{r['path']}: {r['shortfall_db']:+.1f} dB below vanilla")
        if r["onset_frac"] < ONSET_MIN_FRAC:
            errs.append(f"{r['path']}: starts silent ({r['onset_frac']:.3f})")
        if r["click_frac"] > CLICK_MAX_FRAC:
            errs.append(f"{r['path']}: ends at {r['click_frac']:.2f} of peak; "
                        f"the fade-out did not reach zero and it will click")

    groups = {}
    for r in rows:
        g = vanilla.group(r["path"])
        key = (g, tuple(r["atoms"]), r["semitones"])
        if key in groups and not r["same_ok"]:
            errs.append(f"{g}: {'+'.join(r['atoms'])} at {r['semitones']:+.0f} st used by both "
                        f"{groups[key]} and {r['path']}; the engine's free "
                        f"randomisation between variants is wasted. Set "
                        f"same_ok=True in semantic.py if that is deliberate.")
        groups[key] = r["path"]

    REPORT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return rows, errs, skipped


if __name__ == "__main__":
    rows, errs, skipped = bake()
    from collections import Counter, defaultdict
    cats = defaultdict(list)
    for r in rows:
        cats[r["cat"]].append(r)
    print(f"{'category':<10}{'files':>6}{'chained':>9}{'longer':>8}{'quiet':>7}")
    for c in sorted(cats):
        v = cats[c]
        print(f"{c:<10}{len(v):>6}{sum(1 for r in v if len(r['atoms'])>1):>9}"
              f"{sum(1 for r in v if r['dur']>r['van_dur']*MAX_DURATION_RATIO):>8}"
              f"{sum(1 for r in v if r['shortfall_db']<-3):>7}")
    print()
    print(f"{'file':<34}{'atoms':<28}{'dur':>7}{'van':>7}  note")
    for r in sorted(rows, key=lambda r: r["path"]):
        if not r["manual"]:
            continue
        note = " ".join(n for n, on in (
            ("shorter-than-vanilla", r["shorter"]),
            ("ends-at-full-level", r["abrupt_frac"] > ABRUPT_FRAC),
            ("LONGER-than-vanilla(may overlap itself)",
             r["dur"] > r["van_dur"] * MAX_DURATION_RATIO + 1e-3)) if on)
        name = r["path"][7:] if r["path"].startswith("player/") else r["path"]
        print(f"{name[:-4]:<34}{'+'.join(r['atoms'])[:27]:<28}"
              f"{r['dur']:>7.3f}{r['van_dur']:>7.3f}  {note}")
    print()
    if errs:
        print(f"--- {len(errs)} FAIL ---")
        for e in errs:
            print(" ", e)
        sys.exit(1)
    total = sum(p.stat().st_size for p in MOD_SFX.rglob("*") if p.is_file())
    print(f"PASS: {len(rows)} files baked into mod/resources/sfx/ "
          f"at {OUTPUT_SR} Hz, {total / 1e6:.1f} MB")
    if skipped:
        print(f"{len(skipped)} left vanilla on purpose: " + ", ".join(skipped))
