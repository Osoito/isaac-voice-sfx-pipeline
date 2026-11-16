"""Pure data: which atom goes into which vanilla file.

Chosen by the user by listening, 2026-09-09. No logic here; this is the file
that gets edited most.

Per-entry keys:
  atom        atom id from data/atoms.json
  semitones   pitch shift; resampling changes length by the same factor
  cap         enforce the 1.05x duration bound. Off everywhere by choice:
              length does not have to match the file being replaced. The build
              still reports anything longer than vanilla, because a sound that
              retriggers before it finishes overlaps itself.
  fade_in     ms
  fade_out    ms
  same_ok     this atom is deliberately reused inside its numbered group, so
              the engine's free randomisation between variants is knowingly
              given up. Without this the build fails on the duplicate.
  trim_to     seconds; keep only this much from the start. Several atoms hold
              more than one utterance.
  skip        leave the game's own sound in place. The file is removed from the
              mod so the vanilla asset is used.
"""

HURT = ["short-13.00", "short-11.00", "short-15.00"]

DEATH = "long-3.00"

_D = {"semitones": 0.0, "cap": False, "fade_in": 2.0, "fade_out": 8.0,
      "same_ok": False, "trim_to": None, "skip": False}


def _e(**kw):
    return {**_D, **kw}


TABLE = {
    # Fires many times a minute. Three distinct atoms, so the engine's random
    # pick between the numbered variants gives three different grunts for free.
    "player/hurt grunt .wav": _e(atom=HURT[0]),
    "player/hurt grunt 1.wav": _e(atom=HURT[1]),
    "player/hurt grunt 2.wav": _e(atom=HURT[2]),

    # Baby characters: the same hurt atoms pitched up. Resampling shortens them
    # by the same factor, which lands close to the baby files' own lengths.
    "player/baby hurt 1.wav": _e(atom=HURT[0], semitones=5.0),
    "player/baby hurt 2.wav": _e(atom=HURT[1], semitones=5.0),
    "player/baby hurt 3.wav": _e(atom=HURT[2], semitones=5.0),

    "player/derp 0.wav": _e(atom="long-4.01"),
    "player/derp 1.wav": _e(atom="yayamero.01"),

    # One clip for all three variants, by choice: no pitch versions wanted.
    "player/isaac dies new.wav": _e(atom=DEATH, fade_in=10.0, fade_out=40.0,
                                    same_ok=True),
    "player/isaac dies new 1.wav": _e(atom=DEATH, fade_in=10.0, fade_out=40.0,
                                      same_ok=True),
    "player/isaac dies new 2.wav": _e(atom=DEATH, fade_in=10.0, fade_out=40.0,
                                      same_ok=True),

    # --- F, misc creature: fixes from the 2026-09-09 listening pass ---------
    # baga.00 holds three utterances, with energy dips at 0.20 s and 0.38 s.
    # Only the first one is the "baka".
    "child angry roar 1.wav": _e(atom="baga.00", trim_to=0.22),

    "mr_me.wav": _e(atoms=["miyamo.00", "miyamoto.00"]),
    "necromancer.wav": _e(atom="short-18.00"),
    "unholy!.wav": _e(atom="laugh.00"),
    "zombie walker kid 2.wav": _e(atom="laugh.00"),
    "zombie walker kid.wav": _e(atom="cough.02"),

    # All three heartbeats stay vanilla. They are one escalating low-health
    # warning, so replacing part of the ladder would break the signal it carries.
    "heartbeat.wav": _e(atom="cough.00", skip=True),
    "heartbeat faster.wav": _e(atom="cough.00", skip=True),
    "heartbeat fastest.wav": _e(atom="cough.00", skip=True),

    # Howl: resampling down lengthens as it lowers, which turns a spoken phrase
    # into a drawn-out glide. Fades match the audition page so the deployed
    # sound is the one that was actually listened to.
    "dog howell.wav": _e(atom="long-5.00", semitones=-5.0,
                         fade_in=20.0, fade_out=60.0),

    # One numbered group, so the engine picks between these two at random:
    # same clip to sound like one creature, different atoms to keep the variety.
    "fat grunt 1.wav": _e(atom="long-4.01", semitones=-3.0,
                          fade_in=20.0, fade_out=60.0),
    "fat grunt 2.wav": _e(atom="long-4.00", semitones=-3.0,
                          fade_in=20.0, fade_out=60.0),

    # --- D2, generic boss vocalisations -------------------------------------
    # `boss 2 bubbles` and `boss 2 bubbles 1` are one numbered group, so the
    # engine picks between them; the same clip in both is deliberate here.
    "boss 2 bubbles 1.wav": _e(atom="short-7.00", same_ok=True),
    "boss 2 bubbles.wav": _e(atom="short-7.00", same_ok=True),

    "boss bug hiss.wav": _e(atom="short-19.00"),
    "boss gurgle roar.wav": _e(atom="short-21.00"),

    # A bark is a short punch, not a held note. Two impact atoms end to end give
    # the two-bark shape of the original at nearly its exact length.
    "dog bark.wav": _e(atoms=["long-3.00", "cough.00"]),

    # --- G1 / G2, pickups and machines --------------------------------------
    # Both were "wusodaro", the same spoken line, in two unrelated places.
    # Pickups and machines take no speech clips at all, so these are the closest
    # wordless fits: a bright impact for the till, a longer body for the bag.
    "cash_register.wav": _e(atom="cough.00"),
    "bagofcrafting.wav": _e(atom="long-2.01"),

    # Chosen purely on acoustic fit to the vanilla file: duration, envelope
    # class and spectral centroid, with no preference for any particular clip.
    "boo mad.wav": _e(atom="belly.00"),                    # crescendo, matches
    "floaty baby roar 2.wav": _e(atoms=["gulp.00", "sukisuki.01"]),
    "gello.wav": _e(atoms=["short-16.00", "short-14.00", "short-5.00"]),
    "ghost roar.wav": _e(atom="long-5.00"),
    # `child happy roar short 2` is left to the auto matcher: short-18.00 already
    # scores 0.06 against it, the closest fit anywhere in the library.
}
