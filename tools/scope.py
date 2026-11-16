"""Build the in-scope file list and report what it actually demands."""
import os, re, sys, wave
from collections import Counter, defaultdict

SFX, ADDS = sys.argv[1], sys.argv[2]

ENTITY_DIRS = {
    "beast", "dogma", "finalmother", "war", "fistula", "bighorn", "mom", "famine",
    "pestilence", "bumbino", "carrionqueen", "satan", "fallen", "death", "littlehorn",
    "siren", "haunt", "teratoma", "mothershadow", "pin", "blastocyst", "steven",
    "ragmega", "larryjr", "hollow", "maskinfamy", "loki", "gish", "megafatty",
    "gurdy", "forsaken", "gurglings", "stain", "sistersvis", "clog", "backwards",
}
VOCAL = re.compile(r"roar|grunt|scream|yell|growl|hiss|laugh|giggle|whimper|moan|wail|"
                   r"shriek|sob|cry|snarl|bark|howl|squeal|sing|vox|vocal|voice|taunt|"
                   r"preacher|chatter|whisper|mumble|speak|screech|weep|chant", re.I)
MOUTH = re.compile(r"cough|gulp|barf|puke|spit|gurgle|burp|fart|chew|swallow|inhale|"
                   r"exhale|breath|gasp|slurp|lick|kiss|bite|drool|sniff|vomit|belch|"
                   r"hatch|snort", re.I)

added = set()
for line in open(ADDS, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or line.endswith("?"):
        continue
    added.add(line)

scope = []
for dp, _, fns in os.walk(SFX):
    for fn in sorted(fns):
        if not fn.lower().endswith(".wav"):
            continue
        rel = os.path.relpath(os.path.join(dp, fn), SFX).replace(os.sep, "/")
        top = rel.split("/")[0] if "/" in rel else ""
        stem = rel[:-4]
        keep = (top in ("player", "voiceover")
                or VOCAL.search(stem) or MOUTH.search(stem)
                or rel in added)
        if keep:
            with wave.open(os.path.join(SFX, rel), "rb") as w:
                scope.append((rel, w.getnframes() / w.getframerate()))

print("in scope: %d files, %.1f s" % (len(scope), sum(d for _, d in scope)))
print("source material: 39.9 s  ->  reuse %.0f:1" % (sum(d for _, d in scope) / 39.9))
print()

# How many decisions, once numbered variant groups collapse to one choice?
def stem_of(p):
    d, _, f = p.rpartition("/")
    f = f[:-4]
    s = re.sub(r"[ _\-]?\d+[a-d]?$", "", f)
    return (d + "/" + (s or f)).strip("/")

groups = defaultdict(list)
for rel, dur in scope:
    groups[stem_of(rel)].append(rel)
print("distinct variant groups: %d" % len(groups))
sizes = Counter(len(v) for v in groups.values())
print("group sizes:", dict(sorted(sizes.items())))
print()

vo = [g for g in groups if g.startswith("voiceover")]
print("voiceover groups: %d (of %d files)"
      % (len(vo), sum(1 for r, _ in scope if r.startswith("voiceover/"))))
print("  base %d / mega %d / reversed %d"
      % (sum(1 for g in vo if g.count("/") == 1),
         sum(1 for g in vo if g.startswith("voiceover/mega")),
         sum(1 for g in vo if g.startswith("voiceover/reversed"))))
print()

d = sorted(x for _, x in scope)
def pct(q): return d[int(q * (len(d) - 1))]
print("duration  min=%.3f p25=%.3f median=%.3f p75=%.3f p95=%.3f max=%.3f"
      % (d[0], pct(.25), pct(.5), pct(.75), pct(.95), d[-1]))
for lo, hi, lab in [(0, .15, "<0.15s"), (.15, .4, "0.15-0.4"), (.4, .8, "0.4-0.8"),
                    (.8, 1.5, "0.8-1.5"), (1.5, 3, "1.5-3"), (3, 6, "3-6"),
                    (6, 9999, ">6s")]:
    n = sum(1 for x in d if lo <= x < hi)
    print("  %-10s %4d  %5.1f%%  %s" % (lab, n, n / len(d) * 100, "#" * int(n / len(d) * 50)))

print()
print("longest in scope:")
for rel, dur in sorted(scope, key=lambda x: -x[1])[:8]:
    print("  %6.2fs  %s" % (dur, rel))

with open(os.path.join(os.path.dirname(ADDS), "scope_list.txt"), "w", encoding="utf-8") as f:
    for rel, dur in sorted(scope):
        f.write("%s\n" % rel)
