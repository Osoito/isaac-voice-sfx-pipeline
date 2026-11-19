"""Measure and classify the vanilla targets once, into vanilla_spec.json.

Reading 1.2 GB is the expensive step. Landing it as JSON means recipe and
semantic edits never touch audio again.

  python build/vanilla.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import dsp, ffio, game

ROOT = Path(__file__).resolve().parent.parent
SCOPE_LIST = ROOT / "data" / "scope_list.txt"
SCOPE_EXTRA = ROOT / "data" / "scope_pickup.txt"
SPEC_OUT = ROOT / "data" / "vanilla_spec.json"
DEFAULT_SFX = game.vanilla_sfx_dir()

BANDS = [(0.15, "<0.15"), (0.4, "0.15-0.4"), (0.8, "0.4-0.8"),
         (1.5, "0.8-1.5"), (3.0, "1.5-3"), (6.0, "3-6")]

_VARIANT = re.compile(r"[ _\-]?\d+[a-d]?$")


def band(dur):
    for hi, name in BANDS:
        if dur < hi:
            return name
    return ">6"


def group(rel):
    """Collapse a numbered variant to its group.

    The engine already picks randomly among `monster roar 1..10`, so the group
    is one decision and the members share an atom pool.
    """
    d, _, f = rel.rpartition("/")
    stem = _VARIANT.sub("", f[:-4]).strip()
    return f"{d}/{stem}" if d else stem


def measure(sfx_root, rel):
    path = Path(sfx_root) / rel
    info = ffio.wav_info(path)
    x = ffio.read_wav(path)
    return {
        "path": rel,
        "dur": info["dur"],
        "sr": info["sr"],
        "ch": info["ch"],
        "rms": float(np.sqrt((x ** 2).mean())) if len(x) else 0.0,
        "peak": float(np.abs(x).max()) if len(x) else 0.0,
        "attack_ms": dsp.attack_ms(x, info["sr"]),
        "centroid": dsp.centroid(x, info["sr"]),
        "env_class": dsp.envelope_class(x, info["sr"]),
        "band": band(info["dur"]),
        "group": group(rel),
    }


def build_spec(sfx_root, paths, out_path):
    rows = [measure(sfx_root, p) for p in paths]
    Path(out_path).write_text(json.dumps(rows, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    return rows


def load_scope(list_path=SCOPE_LIST):
    return [l.strip() for l in Path(list_path).read_text(encoding="utf-8").splitlines()
            if l.strip()]


if __name__ == "__main__":
    from collections import Counter
    paths = load_scope()
    if SCOPE_EXTRA.exists():
        paths += [p for p in load_scope(SCOPE_EXTRA) if p not in set(paths)]
    sfx = game.require(DEFAULT_SFX, "the extracted vanilla sfx tree",
                       game.EXTRACTOR_HINT)
    rows = build_spec(sfx, paths, SPEC_OUT)
    print(f"measured {len(rows)} targets -> {SPEC_OUT}")
    print("bands:", dict(Counter(r["band"] for r in rows)))
    print("envelopes:", dict(Counter(r["env_class"] for r in rows)))
