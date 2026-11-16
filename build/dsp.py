"""Pure DSP. Every function takes numpy arrays and returns numpy arrays.

No file access and no ffmpeg here, so the fiddly parts stay testable without
audio files.
"""

import numpy as np
from scipy import ndimage, signal

SR = 44100
WIN, HOP = 1024, 256


def trim_silence(x, thresh_db=-45.0):
    """Strip leading and trailing digital silence.

    Everything downstream is derived from the trimmed copy so that an offset
    means the same thing in the build, the checks and the audition page.
    """
    if x.size == 0:
        return x
    env = np.abs(x)
    peak = env.max()
    if peak <= 0:
        return x
    idx = np.flatnonzero(env > 10 ** (thresh_db / 20) * peak)
    return x[idx[0]:idx[-1] + 1] if idx.size else x


def frame(x, win=WIN, hop=HOP):
    """Overlapping frames as a (n, win) array. Returns a copy, safe to mutate."""
    if len(x) < win:
        return np.zeros((0, win))
    n = 1 + (len(x) - win) // hop
    return np.lib.stride_tricks.as_strided(
        x, (n, win), (x.strides[0] * hop, x.strides[0])).copy()


def rms_envelope(x, win=WIN, hop=HOP):
    F = frame(x, win, hop)
    if len(F) == 0:
        return np.array([np.sqrt((x ** 2).mean())]) if len(x) else np.array([0.0])
    return np.sqrt((F ** 2).mean(1))


def f0(x, sr=SR, fmin=60, fmax=500, min_strength=0.30):
    """Fundamental by autocorrelation, or None when the signal is not periodic."""
    x = np.asarray(x, dtype=float)
    if len(x) < 2 * sr // fmin:
        return None
    x = x - x.mean()
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    if ac[0] <= 0:
        return None
    lo, hi = sr // fmax, min(sr // fmin, len(ac) - 1)
    if hi <= lo:
        return None
    peak = lo + int(np.argmax(ac[lo:hi]))
    return float(sr / peak) if ac[peak] > min_strength * ac[0] else None


def voiced_ratio(x, sr=SR, fmin=60, fmax=500, periodic=0.45):
    """Share of loud frames that are periodic.

    Separates plosive consonants from vowels inside one clip. It does NOT
    separate voice from metal across different sounds -- that was measured and
    failed; see the spec, section 4.
    """
    F = frame(x)
    if len(F) == 0:
        return 0.0
    rms = np.sqrt((F ** 2).mean(1))
    if rms.max() <= 0:
        return 0.0
    F = F[rms > rms.max() * 0.15]
    if len(F) < 2:
        return 0.0
    F = (F - F.mean(1, keepdims=True)) * np.hanning(F.shape[1])
    spec = np.fft.rfft(F, F.shape[1] * 2, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :F.shape[1]]
    zero = ac[:, :1]
    ac = ac / np.where(zero > 0, zero, 1.0)
    lo, hi = sr // fmax, min(sr // fmin, F.shape[1] - 1)
    return float((ac[:, lo:hi].max(1) > periodic).mean())


def attack_ms(x, sr=SR, frac=0.9):
    """Time from onset to `frac` of peak, on the smoothed envelope."""
    env = np.abs(x)
    if env.max() <= 0:
        return 0.0
    w = max(1, int(0.002 * sr)) | 1
    env = ndimage.maximum_filter1d(env, w)
    target = env.max() * frac
    return float(np.argmax(env >= target) / sr * 1000.0)


def centroid(x, sr=SR):
    """Median spectral centroid over loud frames, in Hz."""
    F = frame(x)
    if len(F) == 0:
        F = x.reshape(1, -1)
    mag = np.abs(np.fft.rfft(F * np.hanning(F.shape[1]), axis=1))
    freqs = np.linspace(0, sr / 2, mag.shape[1])
    denom = np.maximum(mag.sum(1), 1e-12)
    return float(np.median((mag * freqs).sum(1) / denom))


def envelope_class(x, sr=SR, rise_slope=0.25, flat_tol=0.35):
    """One of impact / crescendo / sustain / composite.

    This is the axis that decides the synthesis strategy, and for crescendo
    targets it is also the readability constraint: a boss charge-up has to stay
    a rising sound whatever it is made of.
    """
    e = rms_envelope(x)
    if len(e) < 4 or e.max() <= 0:
        return "impact"
    e = e / e.max()
    t = np.linspace(0, 1, len(e))
    slope = float(np.polyfit(t, e, 1)[0])
    if slope > rise_slope:
        return "crescendo"
    if int(np.argmax(e)) <= max(1, len(e) // 5) and e[-1] < 0.5:
        return "impact"
    mid = e[len(e) // 5: -len(e) // 5 or None]
    if len(mid) and mid.std() < flat_tol:
        return "sustain"
    return "composite"


def pitch_shift(x, semitones):
    """Resample. Pitch and length move together, as on tape.

    Formant-preserving shifting is deliberately not used: keeping the source's
    chipmunk/ogre character is part of the joke.
    """
    if semitones == 0:
        return np.asarray(x, dtype=float)
    ratio = 2 ** (semitones / 12.0)
    n = max(1, int(round(len(x) / ratio)))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def fade(x, sr=SR, in_ms=3.0, out_ms=8.0):
    """Ramp both ends so a cut never clicks."""
    y = np.array(x, dtype=float)
    a, b = int(in_ms * sr / 1000), int(out_ms * sr / 1000)
    a, b = min(a, len(y) // 2), min(b, len(y) // 2)
    if a > 0:
        y[:a] *= np.linspace(0, 1, a)
    if b > 0:
        y[-b:] *= np.linspace(1, 0, b)
    return y


def take_attack(x, sr=SR, ms=80.0):
    """The onset only. A plosive consonant is already a transient."""
    n = min(len(x), int(ms * sr / 1000))
    return fade(np.asarray(x, dtype=float)[:n], sr, in_ms=1.0,
                out_ms=min(20.0, ms * 0.4))


def chain(parts, sr=SR, xfade_ms=15.0):
    """Concatenate with equal-power crossfades at the joins."""
    parts = [np.asarray(p, dtype=float) for p in parts if len(p)]
    if not parts:
        return np.zeros(0)
    if len(parts) == 1:
        return parts[0].copy()
    x = int(xfade_ms * sr / 1000)
    out = parts[0].copy()
    for nxt in parts[1:]:
        k = min(x, len(out), len(nxt))
        if k <= 0:
            out = np.concatenate([out, nxt])
            continue
        t = np.linspace(0, np.pi / 2, k)
        head = out[:-k] if len(out) > k else np.zeros(0)
        joined = out[-k:] * np.cos(t) + nxt[:k] * np.sin(t)
        out = np.concatenate([head, joined, nxt[k:]])
    return out


def layer(parts):
    """Sum, zero-padded to the longest. Levelling is the caller's job."""
    parts = [np.asarray(p, dtype=float) for p in parts if len(p)]
    if not parts:
        return np.zeros(0)
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def fit_duration(x, sr=SR, max_seconds=None):
    """Enforce the upper bound. Never pads.

    Isaac sfx are fire-and-forget, so a short replacement simply ends sooner.
    A long one overlaps itself when the sound retriggers, which is the failure
    this guards against.
    """
    x = np.asarray(x, dtype=float)
    if max_seconds is None:
        return x
    n = int(max_seconds * sr)
    return fade(x[:n], sr, in_ms=0.0, out_ms=8.0) if len(x) > n else x


def limit(x, ceiling=0.89, win_ms=15.0, circular=False):
    """Soft limiter driven by a smoothed peak envelope.

    `circular=True` keeps a loop seamless; every stage of a loop-producing chain
    must be circular or the seamlessness of earlier stages is destroyed. Not
    needed for Phase 1 targets, kept because the spike proved the failure mode.
    """
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return x
    w = max(3, int(win_ms * SR / 1000)) | 1
    mode = "wrap" if circular else "nearest"
    env = ndimage.maximum_filter1d(np.abs(x), w, mode=mode)
    k = np.hanning(w)
    k /= k.sum()
    if circular:
        pad = np.concatenate([env[-w:], env, env[:w]])
        env = np.convolve(pad, k, mode="same")[w:-w]
    else:
        env = np.convolve(np.pad(env, w, mode="edge"), k, mode="same")[w:-w]
    return x * np.minimum(1.0, ceiling / np.maximum(env, 1e-9))


def match_rms(x, target_rms, ceiling=0.89, budget_db=6.0, circular=False):
    """Drive to `target_rms` using at most `budget_db` of limiting.

    Returns (y, drive_db, shortfall_db). A shortfall is reported, never hidden:
    the level the material can reach is a fact about the material.
    """
    x = np.asarray(x, dtype=float)
    r = np.sqrt((x ** 2).mean()) if len(x) else 0.0
    if r <= 0:
        return x, 0.0, 0.0
    x = x * (target_rms / r)
    drive = 0.0
    while drive < budget_db:
        y = limit(x * 10 ** (drive / 20), ceiling, circular=circular)
        if np.sqrt((y ** 2).mean()) >= target_rms * 0.995:
            break
        drive += 1.0
    y = limit(x * 10 ** (drive / 20), ceiling, circular=circular)
    got = np.sqrt((y ** 2).mean())
    return y, drive, float(20 * np.log10(max(got, 1e-9) / target_rms))


def seam_discontinuity(y):
    """Wrap-point jump against the waveform's own 99.9th-percentile step.

    Correlating the two ends instead measures nothing: for a noise-like signal
    that correlation is near zero whether the join is clean or not.
    """
    y = np.asarray(y, dtype=float)
    if len(y) < 3:
        return 0.0
    d = np.abs(np.diff(y))
    return float(abs(y[0] - y[-1]) / (np.percentile(d, 99.9) + 1e-12))


def extend_tail(x, sr=SR, ms=250.0, seg_ms=120.0):
    """Append a synthetic decay so a hard-ended recording does not stop dead.

    The last `seg_ms` is reversed and faded out over `ms`. Reversing avoids the
    obvious repeat an echo would give, and speech played backwards under a steep
    decay reads as a release rather than as words.
    """
    x = np.asarray(x, dtype=float)
    n = int(ms * sr / 1000)
    s = min(len(x), int(seg_ms * sr / 1000))
    if n <= 0 or s <= 0:
        return x
    seed = x[-s:][::-1]
    tail = np.resize(seed, n) * np.exp(-np.linspace(0, 5.0, n))
    return np.concatenate([x, tail])


def resample(x, from_sr, to_sr):
    """Change sample rate while keeping the duration and pitch.

    Vanilla ships files at 22.05, 44.1 and 48 kHz, so the engine does not care
    what rate a replacement uses -- which makes the rate a free lever on the
    upload size.
    """
    x = np.asarray(x, dtype=float)
    if from_sr == to_sr or len(x) == 0:
        return x
    n = max(1, int(round(len(x) * to_sr / from_sr)))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
