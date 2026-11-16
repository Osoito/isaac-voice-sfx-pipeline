"""Fill in the categories chosen for auto-assignment, by acoustic fit.

Hand-picking 177 sounds one at a time is not something a person should have to
do, but a pure duration match throws away everything that makes the mod funny.
So each category carries a hint: which source clips suit it, and which end of
the pitch range. The matcher scores atoms on that plus duration, envelope class
and brightness.

Anything in build/semantic.py wins over what this produces.

  python build/auto.py
"""

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build import semantic

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "data" / "vanilla_spec.json"
ATOMS = ROOT / "data" / "atoms.json"
OUT = ROOT / "data" / "auto_map.json"

# Categories the user asked for: D1 through F.
SELECTED = {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "E1", "E2", "F",
            "G1", "G2", "B1", "B2", "B3", "C"}

# Announcements and boss lines may use the recognisable spoken clips: they fire
# once per pill, per card, per boss entrance. The exception is a sound that
# repeats in quick succession, where a word would turn into a stuck record --
# see RAPID below.
SPEECH_OK = {"B1", "B2", "B3", "C"}

# A group with several numbered variants is one the engine cycles through while
# the fight is happening, and these names are repeated actions in their own
# right. Either way the sound comes back within seconds, so no words here.
RAPID_MIN_VARIANTS = 3
RAPID_NAMES = re.compile(
    r"growl|flap|bounce|jump|dash|chase|shoot|spit|tick|loop|barf|puke|"
    r"attack|charge|step|swipe|thrash|grumble", re.I)
PICKUP_LIST = ROOT / "data" / "scope_pickup.txt"
REPORT = ROOT / "data" / "build_report.json"

# Pickups and machines draw only from atoms no creature or player sound is
# already using, and never chain: a coin landing is one event, not a phrase.
FRESH_ONLY = {"G1", "G2"}
NO_CHAIN = {"G1", "G2"}

MACHINE = {
    "feedback/slotspawn 0.wav", "feedback/slotspawn1.wav",
    "feedback/slotspawn 2.wav", "feedback/blood bank spawn.wav",
    "feedback/blood bank touched.wav", "feedback/castleportcullis.wav",
    "feedback/door heavy open.wav", "feedback/door heavy close.wav",
    "feedback/power up1.wav", "feedback/power up 3.wav",
    "feedback/power up 4.wav", "feedback/power up 7.wav",
    "feedback/power up spewer.wav", "feedback/thumbs up.wav",
    "feedback/thumbs down.wav", "feedback/beep.wav",
    "feedback/summonsound.wav", "feedback/death card mix.wav",
    "feedback/book page turn.wav", "shell game 0.wav", "shell game 1.wav",
    "spin_to_win.wav", "portableslot_coin.wav", "portableslot_prize.wav",
    "the_d6_roll.wav", "fortunecookie.wav", "button press.wav",
    "converter.wav", "smelter_swallow.wav", "bagofcrafting.wav",
    "moms_box.wav", "urnopen.wav", "urnclose.wav", "jar_of_flies.wav",
    "movingbox_pack.wav", "movingbox_unpack.wav", "shovel dig.wav",
    "shovel drop.wav", "brokenshovel.wav", "ladder.wav",
    "trapdoor_jump.wav", "godeeper_crawlspace_dig.wav",
    "godeeper_crawlspace_open.wav",
}
PICKUP = {l.strip() for l in PICKUP_LIST.read_text(encoding="utf-8").splitlines()
          if l.strip()} - MACHINE if PICKUP_LIST.exists() else set()

# Per category:
#   prefer   source clips to bias towards. A bonus, not a filter, because most
#            categories have more targets than those clips have atoms.
#   pitch    "high", "low" or None
#   only     hard restriction to these source clips; overrides `prefer`
#   exclude  source clips banned from this category
HINTS = {
    "D1": dict(prefer=["short-17", "short-18", "short-19", "long-2"],
               pitch="low", label="monster roar / grunt / yell"),
    "D2": dict(prefer=["long-5", "short-19", "long-2", "belly"],
               pitch="low", label="boss roar"),
    "D3": dict(prefer=["long-5", "short-11", "short-18"],
               pitch="high", label="scream"),
    "D4": dict(prefer=["laugh", "chuckle"], pitch=None, label="laughter"),
    "D5": dict(prefer=["long-3", "long-5", "cough"], pitch=None,
               label="death cry"),
    "D6": dict(prefer=["short-12", "short-15", "short-9"], pitch="high",
               label="hurt / whimper"),
    "D7": dict(prefer=["short-18", "long-2", "belly"], pitch="low",
               label="growl / hiss"),
    "E1": dict(prefer=["cough"], pitch=None,
               only=["cough", "belly", "gulp"], label="fart / burp"),
    "E2": dict(prefer=["gulp", "cough", "belly"], pitch=None,
               label="mouth sounds"),
    "F": dict(prefer=[], pitch=None, label="misc creature"),
    "G1": dict(prefer=[], pitch="high", label="pickup / drop"),
    "G2": dict(prefer=[], pitch=None, label="machine / device"),
    "B1": dict(prefer=[], pitch=None, label="pill / card announcement"),
    "B2": dict(prefer=[], pitch=None, label="reversed tarot"),
    "B3": dict(prefer=[], pitch=None, label="mega announcement"),
    "C": dict(prefer=[], pitch=None, label="named boss"),
}

_VARIANT = re.compile(r"[ _\-]?\d+[a-d]?$")

# Pitch offsets used to tell variants apart when a group outnumbers its pool.
PITCH_LADDER = (-4.0, 4.0, -7.0, 7.0, -2.0, 2.0)

# Clips that are recognisably words. A monster saying "baka" reads as a person
# talking, not as a creature, so these are barred from every auto-assigned
# category. Hand-written entries in semantic.py are not affected.
# Source clips that are too recognisable to hear often. Barred from the ordinary
# assignment entirely, then placed by hand afterwards into at most `budget`
# targets picked for fit -- so a distinctive line lands somewhere it earns its
# keep instead of being spread thin by whatever the scorer happened to like.
SOURCE_BUDGET = {"onceuponatimeinamerica": 2}

# Categories a budgeted clip may appear in. It is a speech clip, so this has to
# be a subset of SPEECH_OK; rapid groups inside those categories are skipped
# too, in place_budgeted.
BUDGET_OK_CATS = {"B1", "B2", "B3", "C"}

SPEECH_CLIPS = {
    "baga", "wusodaro", "yayamero", "nanda", "iya", "sukisuki",
    "miyamo", "miyamoto", "otsuki", "otsuki-2", "otsuki-3",
    "onceuponatimeinamerica", "梅干",
}


def category(path):
    if path in MACHINE:
        return "G2"
    if path in PICKUP:
        return "G1"
    top = path.split("/")[0] if "/" in path else ""
    if top == "player":
        return "A"
    if top == "voiceover":
        if path.startswith("voiceover/mega/"):
            return "B3"
        if path.startswith("voiceover/reversed/"):
            return "B2"
        return "B1"
    if top:
        return "C"
    s = path[:-4].lower()
    if re.search(r"monster (roar|grunt|yell)|cave monster", s):
        return "D1"
    if re.search(r"^boss ", s):
        return "D2"
    if re.search(r"scream|shriek|screech", s):
        return "D3"
    if re.search(r"laugh|giggle|chuckle", s):
        return "D4"
    if re.search(r"death|dies|dying|deaths", s):
        return "D5"
    if re.search(r"hurt|whimper|cry", s):
        return "D6"
    if re.search(r"fart|burp|belch", s):
        return "E1"
    if re.search(r"barf|puke|vomit|spit|gurg|gulp|swallow|chew|cough|inhale|"
                 r"exhale|breath|slurp|hatch|mouth", s):
        return "E2"
    if re.search(r"growl|hiss|snarl|bark|howl|squeal|moan|wail|sob", s):
        return "D7"
    return "F"


def group_of(path):
    d, _, f = path.rpartition("/")
    stem = _VARIANT.sub("", f[:-4]).strip()
    return f"{d}/{stem}" if d else stem


def score(atom, target, hint_srcs, pitch_pref, f0_lo, f0_hi, want_dur):
    """Lower is better."""
    s = 0.0
    s += 2.0 * abs(math.log((atom["dur"] + 0.02) / (want_dur + 0.02)))
    if atom["env_class"] != target["env_class"]:
        s += 0.5
    if atom["centroid"] > 0 and target["centroid"] > 0:
        s += 0.6 * abs(math.log(atom["centroid"] / target["centroid"]))
    if atom["src"] in hint_srcs:
        s -= 1.6 - 0.1 * hint_srcs.index(atom["src"])
    if pitch_pref and atom["f0"]:
        span = max(f0_hi - f0_lo, 1.0)
        pos = (atom["f0"] - f0_lo) / span
        s += 1.2 * (pos if pitch_pref == "low" else 1.0 - pos)
    elif pitch_pref and not atom["f0"]:
        s += 0.3
    return s


def n_parts(dur):
    """How many atoms to chain -- at most two, and one wherever it will do.

    Every join is a seam, and a seam is the thing that makes a replacement sound
    assembled rather than uttered. Chaining more pieces would let the short atoms
    earn their keep, but it buys variety with exactly the defect worth avoiding.
    A single atom that runs shorter than the file it replaces is fine: Isaac's
    sfx are fire-and-forget, so a short one simply ends sooner.
    """
    return 1 if dur < CHAIN_ABOVE else 2


# A target has to be at least this long before it is worth a seam at all.
CHAIN_ABOVE = 1.3

# How hard to push work away from an atom already used a lot. Grows with the
# square root of the count, so the first few reuses barely register and the
# hundredth is expensive.
REUSE_WEIGHT = 0.35

# When an atom has to be reused anyway, shift its pitch instead of leaving it
# identical. Different pitch, same clip, no extra seam.
VARIETY_LADDER = (0.0, -3.0, 3.0, -5.0, 5.0, -7.0, 7.0)
VARIETY_AFTER = 6


def build():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    atoms = json.loads(ATOMS.read_text(encoding="utf-8"))
    f0s = [a["f0"] for a in atoms if a["f0"]]
    f0_lo, f0_hi = min(f0s), max(f0s)

    # Atoms already spoken for by creature and player sounds. Read from the last
    # build, so this reflects hand-written picks as well as auto-assigned ones.
    claimed = set()
    if REPORT.exists():
        for r in json.loads(REPORT.read_text(encoding="utf-8")):
            if r.get("cat") not in FRESH_ONLY:
                claimed.update(r["atoms"])

    targets = [r for r in spec
               if category(r["path"]) in SELECTED
               and r["path"] not in semantic.TABLE]

    by_group = defaultdict(list)
    for r in targets:
        by_group[group_of(r["path"])].append(r)

    out, stats = {}, defaultdict(int)
    usage = Counter()   # how often each atom has been placed so far
    for gname in sorted(by_group):
        rows = sorted(by_group[gname], key=lambda r: r["path"])
        cat = category(rows[0]["path"])
        h = HINTS[cat]
        hint_srcs, pitch_pref = h["prefer"], h["pitch"]
        pool = atoms
        if h.get("only"):
            pool = [a for a in atoms if a["src"] in h["only"]]
            if not pool:
                raise SystemExit(f"{cat}: only={h['only']} matches no atoms")
        if h.get("exclude"):
            pool = [a for a in pool if a["src"] not in h["exclude"]]
        rapid = (len(rows) >= RAPID_MIN_VARIANTS
                 or bool(RAPID_NAMES.search(gname)))
        speech_ok = cat in SPEECH_OK and not rapid

        pool = [a for a in pool if a["src"] not in SOURCE_BUDGET]
        if not speech_ok:
            pool = [a for a in pool if a["src"] not in SPEECH_CLIPS]
        if not pool:
            raise SystemExit(f"{cat}: nothing left after filtering")
        # Pickups and machines should not sound like the monster just killed, so
        # atoms already spoken for elsewhere are penalised. Not excluded: barring
        # speech clips leaves only twelve unclaimed atoms, none longer than a
        # quarter second, which is worse repetition than the sharing it avoids.
        prefer_fresh = cat in FRESH_ONLY
        # Members of a numbered group must not share a lead atom. The engine
        # picks randomly among `monster roar 1..10`, so a repeat there throws
        # away variety that costs nothing. Excluded outright rather than
        # penalised: a penalty large enough to always win is just an exclusion
        # with extra steps, and a small one silently loses.
        group_leads = set()

        for row in rows:
            n = 1 if cat in NO_CHAIN else n_parts(row["dur"])
            want = row["dur"] / n
            ranked = sorted(
                pool,
                key=lambda a: score(a, row, hint_srcs, pitch_pref,
                                    f0_lo, f0_hi, want)
                + (1.5 if prefer_fresh and a["id"] in claimed else 0.0)
                + REUSE_WEIGHT * math.sqrt(usage[a["id"]]))
            # A group can be larger than its pool -- `only=["cough"]` gives three
            # atoms for a five-member fart group. When the pool runs out,
            # differentiate by pitch instead, so the variants still differ.
            semis = 0.0
            lead = next((a for a in ranked if (a["id"], 0.0) not in group_leads),
                        None)
            if lead is None:
                lead = ranked[0]
                for cand in PITCH_LADDER:
                    if (lead["id"], cand) not in group_leads:
                        semis = cand
                        break
            # Once an atom is well used, vary its pitch rather than repeat it
            # verbatim. The ladder is indexed by how often it has been used, so
            # the choice is deterministic and spread out.
            if semis == 0.0 and usage[lead["id"]] >= VARIETY_AFTER:
                step = usage[lead["id"]] // VARIETY_AFTER
                cand = VARIETY_LADDER[step % len(VARIETY_LADDER)]
                if (lead["id"], cand) not in group_leads:
                    semis = cand
            group_leads.add((lead["id"], semis))

            picked, seen = [lead["id"]], {lead["src"]}
            usage[lead["id"]] += 1
            if n > 1:
                # The second piece is support, not the identity of the sound, so
                # its own length barely matters. Rank it almost entirely on how
                # little it has been used, which is what finally puts the short
                # atoms to work instead of leaving a third of the library idle.
                tail = sorted(
                    (a for a in pool if a["src"] not in seen),
                    key=lambda a: (usage[a["id"]],
                                   score(a, row, hint_srcs, pitch_pref,
                                         f0_lo, f0_hi, want)))
                for a in tail:
                    if len(picked) >= n:
                        break
                    seen.add(a["src"])
                    picked.append(a["id"])
                    usage[a["id"]] += 1
            out[row["path"]] = {
                "atoms": picked, "semitones": semis, "cap": False,
                "fade_in": 3.0, "fade_out": 12.0, "same_ok": False,
                "cat": cat,
            }
            stats[cat] += 1

    place_budgeted(out, spec, atoms, f0_lo, f0_hi)

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out, stats


def place_budgeted(out, spec, atoms, f0_lo, f0_hi):
    """Give each budgeted clip its allowance, spent on the targets it fits best.

    Hand-written entries in semantic.py count against the same allowance, so the
    total across the whole mod is what the budget says, not the budget plus
    however many were picked by hand.
    """
    by_path = {r["path"]: r for r in spec}
    for src, budget in SOURCE_BUDGET.items():
        manual = sum(1 for e in semantic.TABLE.values()
                     if any(a.rsplit(".", 1)[0] == src
                            for a in (e.get("atoms") or [e["atom"]])))
        left = budget - manual
        if left <= 0:
            print(f"  budget {src}: {manual} used by hand, none left to place")
            continue

        cands = [a for a in atoms if a["src"] == src]
        scored = []
        for path, e in out.items():
            if e["cat"] not in BUDGET_OK_CATS or len(e["atoms"]) != 1:
                continue
            g = group_of(path)
            if (sum(1 for q in out if group_of(q) == g) >= RAPID_MIN_VARIANTS
                    or RAPID_NAMES.search(g)):
                continue
            row = by_path[path]
            best = min(cands, key=lambda a: score(a, row, [], None,
                                                  f0_lo, f0_hi, row["dur"]))
            scored.append((score(best, row, [], None, f0_lo, f0_hi, row["dur"]),
                           path, best["id"]))
        scored.sort()

        # One per numbered group, so the two placements land on different sounds.
        placed, seen_groups = 0, set()
        for _, path, atom_id in scored:
            if placed >= left:
                break
            g = group_of(path)
            if g in seen_groups:
                continue
            seen_groups.add(g)
            out[path]["atoms"] = [atom_id]
            placed += 1
            print(f"  budget {src}: {path} -> {atom_id}")


if __name__ == "__main__":
    out, stats = build()
    print(f"{len(out)} targets auto-assigned -> {OUT}")
    for cat in sorted(stats):
        h = HINTS[cat]
        limits = []
        if h.get("only"):
            limits.append("only " + "/".join(h["only"]))
        if h.get("exclude"):
            limits.append("no " + "/".join(h["exclude"]))
        print(f"  {cat:<4} {stats[cat]:4d}  {h['label']}"
              + (f"   [{'; '.join(limits)}]" if limits else ""))
    chains = sum(1 for v in out.values() if len(v["atoms"]) > 1)
    print(f"{chains} of them chain more than one atom")
