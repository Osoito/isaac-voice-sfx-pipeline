"""Classify vanilla sfx as vocal or not from the audio, not the filename.

A creature vocalisation carries a stable fundamental and a harmonic stack; a
door, a coin or an explosion does not. Measured as the fraction of non-silent
frames whose normalised autocorrelation has a strong peak in the 60-500 Hz lag
range.

Accuracy is checked against subsets whose answer is already known rather than
asserted: player/ and voiceover/ are voice by definition, and the coin, key and
door sounds in feedback/ are not.
"""
import json, os, sys, wave
import numpy as np

SFX = sys.argv[1]
OUT = sys.argv[2]
SR_MIN, SR_MAX = 60, 500
WIN, HOP = 1024, 512
PERIODIC = 0.45


def read_wav(path):
    with wave.open(path, "rb") as w:
        n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    return a, sr


def voiced_fraction(x, sr):
    """Share of loud frames that are periodic, plus the median strength."""
    if len(x) < WIN * 2:
        return 0.0, 0.0, 0.0
    n = 1 + (len(x) - WIN) // HOP
    F = np.lib.stride_tricks.as_strided(
        x, (n, WIN), (x.strides[0] * HOP, x.strides[0])).copy()
    rms = np.sqrt((F ** 2).mean(1))
    keep = rms > max(rms.max() * 0.15, 1e-4)
    F = F[keep]
    if len(F) < 3:
        return 0.0, 0.0, 0.0
    F = F - F.mean(1, keepdims=True)
    F *= np.hanning(WIN)
    spec = np.fft.rfft(F, WIN * 2, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :WIN]
    zero = ac[:, :1]
    ac = ac / np.where(zero > 0, zero, 1.0)
    lo, hi = sr // SR_MAX, min(sr // SR_MIN, WIN - 1)
    peak = ac[:, lo:hi].max(1)
    # brightness, for telling a shriek from a rumble later
    mag = np.abs(spec[:, :WIN])
    freqs = np.linspace(0, sr / 2, mag.shape[1])
    cen = float(np.median((mag * freqs).sum(1) / np.maximum(mag.sum(1), 1e-12)))
    return float((peak > PERIODIC).mean()), float(np.median(peak)), cen


rows = []
for dp, _, fns in os.walk(SFX):
    for fn in sorted(fns):
        if not fn.lower().endswith(".wav"):
            continue
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, SFX).replace(os.sep, "/")
        try:
            x, sr = read_wav(p)
        except Exception:
            continue
        frac, med, cen = voiced_fraction(x, sr)
        rows.append(dict(path=rel, dur=len(x) / sr, voiced=frac,
                         periodicity=med, centroid=cen))

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1)

# ------------------------------------------------------------------ validation
def subset(pred):
    return [r for r in rows if pred(r["path"])]


KNOWN_VOICE = subset(lambda p: p.startswith("player/") or p.startswith("voiceover/"))
KNOWN_MECH_NAMES = ("penny", "nickel", "dime", "coin", "key", "door", "lock",
                    "chest", "button", "beep", "slot")
KNOWN_MECH = subset(lambda p: p.startswith("feedback/")
                    and any(k in p for k in KNOWN_MECH_NAMES))

print("scanned %d files" % len(rows))
print()
for label, group in (("known voice (player+voiceover)", KNOWN_VOICE),
                     ("known mechanical (feedback coins/keys/doors)", KNOWN_MECH)):
    v = np.array([r["voiced"] for r in group])
    print("%-46s n=%3d  voiced frac: mean=%.2f  p10=%.2f  p90=%.2f"
          % (label, len(group), v.mean(), np.percentile(v, 10), np.percentile(v, 90)))
print()

for thr in (0.3, 0.4, 0.5, 0.6, 0.7):
    tp = sum(1 for r in KNOWN_VOICE if r["voiced"] >= thr)
    fp = sum(1 for r in KNOWN_MECH if r["voiced"] >= thr)
    allv = sum(1 for r in rows if r["voiced"] >= thr)
    print("threshold %.1f -> voice recall %3d/%3d (%.0f%%)   "
          "mech false-positive %2d/%2d   whole set flagged %4d (%.0f%%)"
          % (thr, tp, len(KNOWN_VOICE), tp / len(KNOWN_VOICE) * 100,
             fp, len(KNOWN_MECH), allv, allv / len(rows) * 100))
