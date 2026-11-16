"""Cut Voices/ into a tagged atom library.

Segmentation searches for energy dips and treats the rise out of a dip as a
syllable start. Selecting by maximum short-term RMS instead lands in the middle
of a phrase every time.

  python build/atomize.py
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import dsp, ffio

ROOT = Path(__file__).resolve().parent.parent
VOICES = ROOT / "Voices"
ATOMS_DIR = ROOT / "atoms"
ATOMS_JSON = ROOT / "data" / "atoms.json"


def split_syllables(x, sr=dsp.SR, min_ms=90, floor_frac=0.18):
    """Segment on energy dips. Returns [(start_sample, end_sample), ...]."""
    env = dsp.rms_envelope(x)
    if len(env) == 0 or env.max() <= 0:
        return []
    env = env / env.max()
    active = env > floor_frac
    segs, start = [], None
    for i, on in enumerate(active):
        if on and start is None:
            start = i
        elif not on and start is not None:
            segs.append((start, i))
            start = None
    if start is not None:
        segs.append((start, len(active)))

    out = []
    for a, b in segs:
        s = a * dsp.HOP
        e = min(len(x), b * dsp.HOP + dsp.WIN)
        if (e - s) / sr * 1000.0 >= min_ms:
            out.append((s, e))
    return out


def tag_atom(src, index, seg, start_s, end_s, sr=dsp.SR):
    return {
        "id": f"{src}.{index:02d}",
        "src": src,
        "start": round(float(start_s), 4),
        "end": round(float(end_s), 4),
        "dur": round(float(end_s - start_s), 4),
        "f0": dsp.f0(seg, sr),
        "voiced_ratio": round(dsp.voiced_ratio(seg, sr), 3),
        "attack_ms": round(dsp.attack_ms(seg, sr), 1),
        "centroid": round(dsp.centroid(seg, sr), 1),
        "env_class": dsp.envelope_class(seg, sr),
        "rms": round(float(np.sqrt((seg ** 2).mean())), 4),
        "pinned": True,
    }


def build_library(voices_dir=VOICES, atoms_dir=ATOMS_DIR, out_json=ATOMS_JSON,
                  min_ms=90, floor_frac=0.18):
    atoms_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for mp3 in sorted(voices_dir.glob("*.mp3")):
        src = mp3.stem
        x = dsp.trim_silence(ffio.decode(mp3))
        for i, (s, e) in enumerate(split_syllables(x, min_ms=min_ms,
                                                   floor_frac=floor_frac)):
            seg = dsp.fade(x[s:e], dsp.SR, 2.0, 6.0)
            tag = tag_atom(src, i, seg, s / dsp.SR, e / dsp.SR)
            ffio.write_wav(atoms_dir / f"{tag['id']}.wav", seg)
            rows.append(tag)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return rows


def load_atoms(path=ATOMS_JSON):
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    from collections import Counter
    rows = build_library()
    print(f"{len(rows)} atoms from {len(set(r['src'] for r in rows))} sources")
    print("env classes:", dict(Counter(r["env_class"] for r in rows)))
    voiced = [r for r in rows if r["f0"]]
    f0s = sorted(r["f0"] for r in voiced)
    print(f"f0: {f0s[0]:.0f}-{f0s[-1]:.0f} Hz over {len(voiced)}/{len(rows)} atoms")
    d = sorted(r["dur"] for r in rows)
    print(f"durations: {d[0]:.3f} / median {d[len(d)//2]:.3f} / {d[-1]:.3f} s")
