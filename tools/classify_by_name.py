"""Classify every vanilla sfx by what makes the sound, to draw the mod's scope line."""
import os, re, sys, wave
from collections import Counter, defaultdict

SFX = sys.argv[1]

# Folders that are one creature. Everything inside is made by that creature,
# though not all of it with a voice.
ENTITY_DIRS = {
    "beast", "dogma", "finalmother", "war", "fistula", "bighorn", "mom", "famine",
    "pestilence", "bumbino", "carrionqueen", "satan", "fallen", "death", "littlehorn",
    "siren", "haunt", "teratoma", "mothershadow", "pin", "blastocyst", "steven",
    "ragmega", "larryjr", "hollow", "maskinfamy", "loki", "gish", "megafatty",
    "gurdy", "forsaken", "gurglings", "stain", "sistersvis", "clog", "backwards",
}

VOCAL = r"""roar|grunt|scream|yell|growl|hiss|laugh|giggle|whimper|moan|wail|shriek|
sob|cry|snarl|bark|howl|squeal|sing|vox|vocal|voice|taunt|preacher|chatter|
whisper|mumble|speak|screech|weep|chant"""

MOUTH = r"""cough|gulp|barf|puke|spit|gurgle|burp|fart|chew|swallow|inhale|exhale|
breath|gasp|slurp|lick|kiss|bite|drool|sniff|vomit|belch|hatch|snort"""

# Sounds a living thing makes with its body rather than its throat.
BODY = r"""feet|footstep|walk|step|flap|wing|jump|land|stomp|bounce|wiggle|squish|
crawl|scamper|slither|thrash|dive|heartbeat|pulse"""

WORLD = r"""door|coin|penny|nickel|dime|key|chest|lock|unlock|explos|rocket|bomb|
laser|lightning|thunder|portal|loop|amb_|ambient|water|lava|fire|rock|stone|
glass|wood|metal|chain|machine|slot|menu|button|paper|card|page|beep|click|
tick|bell|whistle_|drip|drop_|splash|steam|wind|rubble|debris|shatter|break|
freeze|electric|zap|charge|spin|swoosh|whoosh|teleport|warp|shoot|shot|fire_|
tear|bullet|blast|impact|hit|punch|slash|whip|sword|knife|axe|razor|blade"""

vocal, mouth, body, world = (re.compile(p, re.I | re.X) for p in (VOCAL, MOUTH, BODY, WORLD))

rows = []
for dp, _, fns in os.walk(SFX):
    for fn in fns:
        if not fn.lower().endswith((".wav", ".ogg")):
            continue
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, SFX).replace(os.sep, "/")
        top = rel.split("/")[0] if "/" in rel else ""
        stem = rel[:-4]
        try:
            with wave.open(p, "rb") as w:
                dur = w.getnframes() / w.getframerate()
        except Exception:
            dur = None

        if top == "player":
            tier = "1-player"
        elif top == "voiceover":
            tier = "1-voiceover"
        elif vocal.search(stem):
            tier = "1-vocal"
        elif mouth.search(stem):
            tier = "2-mouth"
        elif top in ENTITY_DIRS and not world.search(stem):
            tier = "3-entity-other"
        elif body.search(stem) and not world.search(stem):
            tier = "3-entity-other"
        else:
            tier = "4-world"
        rows.append((tier, rel, dur, top))

by = defaultdict(list)
for t, rel, dur, top in rows:
    by[t].append((rel, dur))

print("total files:", len(rows))
print()
order = ["1-player", "1-voiceover", "1-vocal", "2-mouth", "3-entity-other", "4-world"]
run = 0
for t in order:
    n = len(by[t])
    run += n
    secs = sum(d for _, d in by[t] if d)
    print("  %-16s %5d  %5.1f%%   cumulative %5d   %6.1f s of audio"
          % (t, n, n / len(rows) * 100, run, secs))
print()

for t in order[:-1]:
    print("=== %s (%d) — sample ===" % (t, len(by[t])))
    for rel, d in by[t][:14]:
        print("   %-58s %s" % (rel, ("%.2fs" % d) if d else "?"))
    if len(by[t]) > 14:
        print("   ... +%d more" % (len(by[t]) - 14))
    print()

print("=== entity dirs landing in 4-world (check these) ===")
for t, rel, dur, top in rows:
    if t == "4-world" and top in ENTITY_DIRS:
        print("   ", rel)
