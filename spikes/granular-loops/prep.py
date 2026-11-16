"""Build the audition page: fold measurements + audio into page.html."""
import base64, json, os, wave
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
SR = 44100
ENV_POINTS = 260
WRAP_MS = 12.0
WRAP_POINTS = 200


def read_wav(path):
    with wave.open(path, "rb") as w:
        n, ch = w.getnframes(), w.getnchannels()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    return a.reshape(-1, ch).mean(1) if ch > 1 else a


def envelope(x, n=ENV_POINTS):
    """Per-window RMS, normalised to the window peak, as ints 0-100."""
    edges = np.linspace(0, len(x), n + 1).astype(int)
    e = np.array([np.sqrt((x[a:b] ** 2).mean()) if b > a else 0.0
                  for a, b in zip(edges[:-1], edges[1:])])
    m = e.max()
    return [int(round(v)) for v in (e / m * 100 if m > 0 else e)]


def wrap_view(x, ms=WRAP_MS, n=WRAP_POINTS):
    """The join, laid out as it actually plays: tail then head.

    A seamless loop shows one continuous waveform across the centre line; a
    broken one shows a visible step there.
    """
    k = int(ms * SR / 1000)
    seg = np.concatenate([x[-k:], x[:k]])
    idx = np.linspace(0, len(seg) - 1, n * 2).astype(int)
    s = seg[idx]
    m = np.abs(s).max()
    return [round(float(v / m if m > 0 else v), 4) for v in s]


rows = []
for r in json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8")):
    key = "%s__%s" % (r["target"][:-4], r["variant"])
    y = read_wav(os.path.join(OUT, key + ".wav"))
    with open(os.path.join(OUT, r["ogg"]), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    r["env"] = envelope(y)
    r["wrap"] = wrap_view(y)
    r["audio"] = "data:audio/ogg;base64," + b64
    rows.append(r)

html = open(os.path.join(OUT, "page.html"), encoding="utf-8").read()
html = html.replace("/*__DATA__*/", json.dumps(rows, ensure_ascii=False))
path = os.path.join(OUT, "audition.html")
with open(path, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote %s  (%.2f MB)" % (path, os.path.getsize(path) / 1e6))
