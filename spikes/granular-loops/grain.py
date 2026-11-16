"""Prototype: granular synthesis of seamless loops from voice clips.

Throwaway spike to answer one question: can a human voice be turned into a
usable lava_loop / portal_loop without sounding broken?
"""
import json, math, os, subprocess, wave
import numpy as np
from scipy import ndimage, signal

# Override any of these with an environment variable; the defaults assume a
# checkout next to the game and ffmpeg on PATH.
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
VOICES = os.environ.get(
    "VOICES", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "..", "Voices"))
SFX = os.environ.get("ISAAC_SFX", "")  # <game>/extracted_resources/resources/sfx
OUT = os.path.dirname(os.path.abspath(__file__))
SR = 44100


def decode(path):
    """mp3/wav -> mono float64 at SR."""
    raw = subprocess.run(
        [FFMPEG, "-v", "error", "-i", path, "-f", "f32le", "-ac", "1",
         "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def trim_silence(x, thresh_db=-45.0):
    """Strip leading/trailing digital silence before anything downstream."""
    if x.size == 0:
        return x
    env = np.abs(x)
    thr = 10 ** (thresh_db / 20) * env.max()
    idx = np.flatnonzero(env > thr)
    return x[idx[0]:idx[-1] + 1] if idx.size else x


def frames(x, win, hop):
    n = 1 + max(0, (len(x) - win) // hop)
    return np.lib.stride_tricks.as_strided(
        x, (n, win), (x.strides[0] * hop, x.strides[0]), writeable=False)


def f0_autocorr(x, sr=SR, fmin=60, fmax=500):
    """Crude but adequate pitch estimate for picking dark vs bright material."""
    x = x - x.mean()
    if len(x) < sr // fmin * 2:
        return None
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    lo, hi = sr // fmax, min(sr // fmin, len(ac) - 1)
    if hi <= lo:
        return None
    peak = lo + int(np.argmax(ac[lo:hi]))
    return sr / peak if ac[peak] > 0.25 * ac[0] else None


def best_sustain(x, sr=SR, min_ms=120):
    """Longest run of loud, low-ZCR (voiced) frames -- the grain source."""
    win, hop = 1024, 256
    F = frames(x, win, hop)
    if len(F) == 0:
        return None
    rms = np.sqrt((F ** 2).mean(1))
    zcr = np.diff(np.signbit(F), axis=1).sum(1) / win
    ok = (rms > 0.35 * rms.max()) & (zcr < np.median(zcr))
    best = cur = None
    for i, v in enumerate(ok):
        if v:
            cur = i if cur is None else cur
        elif cur is not None:
            if best is None or i - cur > best[1] - best[0]:
                best = (cur, i)
            cur = None
    if cur is not None and (best is None or len(ok) - cur > best[1] - best[0]):
        best = (cur, len(ok))
    if best is None:
        return None
    a, b = best[0] * hop, best[1] * hop + win
    if (b - a) / sr * 1000 < min_ms:
        return None
    return x[a:min(b, len(x))]


def granular_loop(src, out_len, grain_ms=45, density=60, semis=(0,),
                  seed=0, am_depth=0.25, am_cycles=(2, 3)):
    """Circular overlap-add granular synthesis.

    Every grain is written with a modulo-N index, so a grain that runs past the
    end wraps to the start. The buffer is therefore seamless by construction --
    no crossfade, no click, no matter where grains land.
    """
    rng = np.random.default_rng(seed)
    N = int(out_len)
    out = np.zeros(N)
    g = int(grain_ms * SR / 1000)
    win = np.hanning(g)
    ramp = np.arange(g)
    for _ in range(int(density * N / SR)):
        ratio = 2 ** (rng.choice(semis) / 12)
        need = int(g * ratio)
        if need >= len(src) or need < 8:
            continue
        s0 = rng.integers(0, len(src) - need)
        seg = src[s0:s0 + need]
        grain = np.interp(np.linspace(0, len(seg) - 1, g),
                          np.arange(len(seg)), seg) * win
        out[(rng.integers(0, N) + ramp) % N] += grain
    # Amplitude movement that is itself periodic over N, so the loop stays seamless.
    t = np.arange(N) / N * 2 * np.pi
    am = np.ones(N)
    for c in am_cycles:
        am += am_depth / len(am_cycles) * np.sin(c * t + rng.random() * 6.28)
    return out * am


def circ_filter(sos, x):
    """Filter a loop without breaking its periodicity.

    sosfilt is causal and starts from zero state, so applying it directly to a
    seamless buffer leaves a step at the wrap point -- the granular synthesis
    can be perfect and the filter will still ruin it. Tiling three times and
    keeping the middle copy lets the filter reach steady state first.
    """
    n = len(x)
    return signal.sosfilt(sos, np.tile(x, 3))[n:2 * n]


def shape(x, kind):
    if kind == "dark":
        x = circ_filter(signal.butter(4, 900, "lowpass", fs=SR, output="sos"), x)
        return circ_filter(signal.butter(2, 40, "highpass", fs=SR, output="sos"), x)
    if kind == "airy":
        return circ_filter(
            signal.butter(4, [300, 5000], "bandpass", fs=SR, output="sos"), x)
    return x


def limit(x, ceiling=0.89, win_ms=15.0):
    """Circular soft limiter. Every stage wraps, so the loop stays seamless."""
    w = int(win_ms * SR / 1000) | 1
    env = ndimage.maximum_filter1d(np.abs(x), w, mode="wrap")
    k = np.hanning(w)
    k /= k.sum()
    pad = np.concatenate([env[-w:], env, env[:w]])
    env = np.convolve(pad, k, mode="same")[w:-w]
    return x * np.minimum(1.0, ceiling / np.maximum(env, 1e-9))


def match_rms(x, target_rms, ceiling=0.89, budget_db=6.0, iters=8):
    """Reach the target RMS using at most `budget_db` of limiting.

    Derived from the material rather than forced: if the budget runs out the
    result is quieter than vanilla and the shortfall is reported, never hidden.
    """
    r = np.sqrt((x ** 2).mean())
    if r <= 0:
        return x, 0.0, 0.0
    x = x * (target_rms / r)
    drive_db = 0.0
    for _ in range(iters):
        y = limit(x * 10 ** (drive_db / 20), ceiling)
        got = np.sqrt((y ** 2).mean())
        if got >= target_rms * 0.995 or drive_db >= budget_db:
            break
        drive_db = min(budget_db, drive_db + 1.0)
    y = limit(x * 10 ** (drive_db / 20), ceiling)
    got = np.sqrt((y ** 2).mean())
    shortfall_db = 20 * np.log10(max(got, 1e-9) / target_rms)
    return y, drive_db, shortfall_db


def seam_discontinuity(y):
    """Wrap-point jump measured against the signal's own sample-to-sample steps.

    A value near or below 1 means the join is indistinguishable from ordinary
    motion inside the waveform. Correlating the two ends, which is what the
    first version of this check did, says nothing at all about continuity.
    """
    d = np.abs(np.diff(y))
    return float(abs(y[0] - y[-1]) / (np.percentile(d, 99.9) + 1e-12))


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    with wave.open(path, "rb") as w:
        n, ch = w.getnframes(), w.getnchannels()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    return a.reshape(-1, ch).mean(1) if ch > 1 else a


# ---------------------------------------------------------------- analysis
cands = {}
print("%-28s%9s%8s%8s" % ("clip", "sustain", "f0", "rms"))
for fn in sorted(os.listdir(VOICES)):
    if not fn.lower().endswith(".mp3"):
        continue
    x = trim_silence(decode(os.path.join(VOICES, fn)))
    s = best_sustain(x)
    if s is None:
        continue
    f0 = f0_autocorr(s)
    rms = float(np.sqrt((s ** 2).mean()))
    cands[fn[:-4]] = (s, f0, rms)
    print("%-28s%8.3fs%8s%8.3f" % (
        fn[:-4], len(s) / SR, ("%.0fHz" % f0) if f0 else "--", rms))

with_f0 = {k: v for k, v in cands.items() if v[1]}
low = min(with_f0.items(), key=lambda kv: kv[1][1])
high = max(with_f0.items(), key=lambda kv: kv[1][1])
longest = max(cands.items(), key=lambda kv: len(kv[1][0]))
print("\nlowest f0 : %s (%.0f Hz)" % (low[0], low[1][1]))
print("highest f0: %s (%.0f Hz)" % (high[0], high[1][1]))
print("longest   : %s (%.3fs)" % (longest[0], len(longest[1][0]) / SR))

# ---------------------------------------------------------------- synthesis
jobs = [
    ("lava_loop.wav",   "A-dense-low",  low[0],     70, 110, (-12, -10, -7),    "dark", 1),
    ("lava_loop.wav",   "B-med-rough",  low[0],     45,  70, (-12, -7, -5, 0),  "dark", 2),
    ("lava_loop.wav",   "C-long-grain", longest[0], 120, 45, (-12, -9),         "dark", 3),
    ("portal_loop.wav", "A-airy",       high[0],    38,  85, (-5, 0, 5, 7),     "airy", 4),
    ("portal_loop.wav", "B-wide",       high[0],    28, 120, (-12, -5, 0, 7, 12), "airy", 5),
    ("portal_loop.wav", "C-dark",       low[0],     50,  90, (-7, 0, 5),        "airy", 6),
]

def to_ogg(wav_path):
    ogg = wav_path[:-4] + ".ogg"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", wav_path,
                    "-c:a", "libvorbis", "-b:a", "128k", ogg], check=True)
    return ogg


def audition_copy(y, name):
    """Bake 2-3 repetitions so the loop point is audible without relying on
    the browser's gapless playback."""
    reps = max(2, min(3, math.ceil(12.0 * SR / len(y))))
    p = os.path.join(OUT, "aud_%s.wav" % name)
    write_wav(p, np.tile(y, reps))
    return to_ogg(p), reps


print()
manifest = []
for target, name, src_key, gms, dens, semis, tone, seed in jobs:
    van = read_wav(os.path.join(SFX, target))
    tgt_rms = float(np.sqrt((van ** 2).mean()))
    y = granular_loop(cands[src_key][0], len(van), gms, dens, semis, seed)
    y, drive, short_db = match_rms(shape(y, tone), tgt_rms)
    key = "%s__%s" % (target[:-4], name)
    write_wav(os.path.join(OUT, key + ".wav"), y)
    seam = seam_discontinuity(y)
    ogg, reps = audition_copy(y, key)
    print("%-16s %-14s src=%-11s peak=%.3f rms=%.4f (van %.4f, %+.1f dB) "
          "limit=%.0fdB seam=%.2f"
          % (target, name, src_key, np.abs(y).max(), np.sqrt((y ** 2).mean()),
             tgt_rms, short_db, drive, seam))
    manifest.append(dict(target=target, variant=name, src=src_key,
                         src_f0=cands[src_key][1], src_len=len(cands[src_key][0]) / SR,
                         grain_ms=gms, density=dens, semis=list(semis), tone=tone,
                         dur=len(y) / SR, rms=float(np.sqrt((y ** 2).mean())),
                         van_rms=tgt_rms, short_db=float(short_db),
                         limit_db=float(drive), seam=seam, reps=reps,
                         ogg=os.path.basename(ogg)))

for t in ("lava_loop.wav", "portal_loop.wav"):
    van = read_wav(os.path.join(SFX, t))
    key = "%s__vanilla" % t[:-4]
    write_wav(os.path.join(OUT, key + ".wav"), van)
    ogg, reps = audition_copy(van, key)
    manifest.append(dict(target=t, variant="vanilla", src="-", src_f0=None,
                         src_len=0.0, grain_ms=0,
                         density=0, semis=[], tone="-", dur=len(van) / SR,
                         rms=float(np.sqrt((van ** 2).mean())),
                         van_rms=float(np.sqrt((van ** 2).mean())), short_db=0.0,
                         limit_db=0.0, seam=seam_discontinuity(van), reps=reps,
                         ogg=os.path.basename(ogg)))

with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print("\nwrote", OUT)
