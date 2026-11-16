# Handoff: Isaac audio modding

Written at the end of `D:\DeerWorkshop\IssacChiikawaMusicMod` (Chiikawa music mod,
published as Workshop item 3787641648) for the next Isaac audio mod. Everything in
section 1 and 2 was verified by looking at the files, not recalled or assumed. Anything
stated as uncertain is marked as such.

---

## 1. Verified environment

| Item | Value |
|---|---|
| Game install | `D:\softwares\Steam\steamapps\common\The Binding of Isaac Rebirth` |
| Mods dir | `<install>\mods\` (Rep+ uses this, **not** Documents) |
| User data, log, options | `%USERPROFILE%\Documents\My Games\Binding of Isaac Repentance+\` |
| Steam root (registry) | `HKCU\Software\Valve\Steam` → `SteamPath` |
| ffmpeg / ffprobe | `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_...\bin\` |
| Python | `%LOCALAPPDATA%\Programs\Python\Python313\python.exe` (numpy, PIL available) |
| Mod uploader | `<install>\tools\ModUploader\ModUploader.exe` |
| Lua API docs | `<install>\tools\LuaDocs\annotated.html` |
| Resource extractor | `<install>\tools\ResourceExtractor\` |
| Vanilla file list | `<install>\tools\ResourceExtractor\filelist.txt` (1633 sfx entries) |
| REPENTOGON | **not installed** |

### options.ini traps

Keys live under an `[Options]` header, so a parser must not assume top level.

| Key | Value at time of writing | Why it matters |
|---|---|---|
| `EnableMods` | 1 | |
| `EnableDebugConsole` | 1 | Needed for an in-game test harness |
| `MusicEnabled` | was 0 | Music switched off entirely, not just quiet |
| `MusicVolume` | was 0.0 | |
| `SFXVolume` | 0.5 | |

Two separate switches silenced music: `MusicEnabled=0` **and** `MusicVolume=0`. A build
verified as correct was inaudible in game for that reason alone. Check both before any
listening test, and read them from the actual `[Options]` section rather than defaulting
when a key is not found. A check that silently falls back to a default is worse than no
check: it reports OK for the exact condition it exists to catch.

**Repentance+ routes jingles through the SFX volume channel while music uses the music
channel.** Plain Repentance uses music volume for both. So the on-file loudness relation
between a jingle and a loop is not what the player hears; the two sliders scale it.

---

## 2. Isaac mod mechanics

### metadata.xml

```xml
<metadata>
    <name>Display Name</name>
    <directory>folder name</directory>   <!-- must equal the mod folder name -->
    <id>3787641648</id>                  <!-- absent until first upload -->
    <description>BBCode</description>
    <version>1.2</version>
    <visibility>Public</visibility>
    <tag id="Sound Effects"/>
</metadata>
```

- `<id>` and `<version>` are **owned by the uploader**. It assigns the id on first
  publish and bumps the version on every upload. A deploy script that copies the repo
  copy over the installed one must pull both back first, or the next upload creates a
  second unrelated Workshop item and the published version number goes backwards.
- The uploader writes mixed CRLF and LF. Patch the file in binary or with `newline=""`,
  or text mode silently rewrites every line ending and leaves a permanent diff.
- Convention puts `<id>` directly after `<directory>`.

### Load order and callbacks

Mods load **alphabetically by folder name**. A mod that depends on another mod's global
function cannot call it at load time if it sorts earlier. The workaround used by every
Soundtrack Menu compatible mod is to register from `MC_POST_GAME_STARTED`.

**Without REPENTOGON there is no callback that runs at the main menu.** `MC_POST_RENDER`
does not fire there, and `MC_MAIN_MENU_RENDER` is REPENTOGON only (confirmed: Soundtrack
Menu registers it inside `if usingRepentogon then` at `soundtrackmenu.lua:4722`). So
anything a mod registers with another mod only appears after a run has started. That is
a real limitation to document for users, not a bug to fix.

### Other

- A `disable.it` file inside a mod folder means disabled. Absent means enabled.
- Allowed upload file types include `lua`, `ogg`, `wav`, `png`, `xml`. The uploader
  rejects a folder containing anything else with "Mod folder contains one or more files
  that are not allowed to be uploaded to Steam Workshop", so build artifacts and dev
  files must be stripped from a release build.
- `previewpic.png` in the mod folder is the common preview image name.

---

## 3. Sound effects differ from music

This is the part that does **not** carry over from the music mod.

### Two separate mechanisms

**A. Same-path override, no XML.** Put a file at the same relative path as the vanilla
asset and it replaces it. Confirmed across four installed mods, for both art and sound:

| Mod | Overrides |
|---|---|
| `yumenikkihurt_2802234645` | `resources/sfx/player/hurt grunt .wav` and 5 more |
| `less subtle indicator for tinted rocks_3361211771` | one file under `resources/sfx/` |
| `little horn resprited_2522187640` | `resources/gfx/bosses/afterbirth/littlehorn.png` |
| `aqepo's graphical tweaks_2515779552` | several under `resources/gfx/` |

All six paths in `yumenikkihurt` were checked against `filelist.txt` and every one
matches a real vanilla path, including the trailing space in `hurt grunt .wav`. Vanilla
names contain spaces and inconsistent numbering; copy them exactly from `filelist.txt`
rather than typing them.

**B. Named sounds in `content/sounds.xml`**, for sounds a mod defines and plays itself,
or when weighted random variants are wanted:

```xml
<sounds root="sfx/">
	<sound name="Some Name">
		<sample weight="1" path="folder/file.wav" />
		<sample weight="1" path="folder/file2.wav" />
	</sound>
</sounds>
```

Multiple `<sample>` entries under one `<sound>` give **free weighted random selection**.
For a voice mod with many clips this is the mechanism to reach for: one player hurt sound
backed by a dozen voice takes, picked at random, with no Lua at all.

### Practical notes

- Vanilla sfx are `.wav`; vanilla music is `.ogg`. Match the format of what is replaced.
- `filelist.txt` is the authoritative list of every replaceable path. Player voices:
  `sfx/player/baby hurt 1-3.wav`, `derp 0-1.wav`, `hurt grunt .wav`, `hurt grunt 1-2.wav`,
  `isaac dies new.wav`, `isaac dies new 1-2.wav`.
- Run `ResourceExtractor.exe` first to extract the vanilla sounds and listen to what is
  being replaced. Length, attack and loudness of the original are the spec the
  replacement has to meet, especially for a sound that fires many times a minute.
- Isaac's `SoundEffect` enum in `tools/LuaDocs` maps names to ids for Lua-side work.

### Source material already present

`Voices/` holds 43 mp3 clips: named ones (`baga`, `belly`, `chuckle`, `cough`, `gulp`,
`iya`, `laugh`, `miyamo`, `miyamoto`, `nanda`, `onceuponatimeinamerica`, `otsuki` x3)
plus `long-1..5` and `short-1..18+`. Convert to wav for sfx use. Expect the same loudness
problem described in section 5: clips cut from video will not be level-matched.

---

## 4. Pipeline shape that worked

```
audio_master/          lossless masters, hand managed, source of truth
_source_mp4/           archived originals, never deleted
build/
  tracks.py            PURE DATA: slot -> source mapping, plus validate(). No I/O.
  ffio.py              the only module that knows where ffmpeg is
  build_audio.py       masters -> shipped audio
  build_xml.py         mapping -> content xml (+ generated Lua data)
  verify.py            machine checks, non-zero exit on FAIL
  audition.py          HTML page for listening
  deploy.py            install into the game, dev vs release
mod/                   the shippable mod; every generated file says so in its header
```

Two properties did most of the work:

1. **Data separated from process.** `tracks.py` has no I/O, so the mapping can be
   validated and reasoned about in isolation, and every script imports the same truth.
2. **Cheap steps separated from expensive ones.** Changing which source plays where
   regenerates an XML in under a second. Re-encoding audio takes minutes. Because the two
   are separate scripts, mapping changes were free and got iterated on freely.

`deploy.py` earned its keep. Worth carrying over:

- `--release` strips dev-only files and the build marker.
- A marker file identifies folders this project created; the script refuses to overwrite
  a folder it did not create, so a subscribed mod of the same name cannot be clobbered.
- Preflight: every path referenced by the XML exists before anything is copied.
- Pulls uploader-owned fields back before overwriting (section 2).

---

## 5. Audio lessons

**Measure the loudness spread before anything else.** The 16 masters ripped from video
spanned **15.4 LU** (-27.9 to -12.5 LUFS). Untreated, the volume changed every time the
player walked onto a new floor. This was the single most audible defect the mod could
have shipped, and it was invisible until measured. Normalisation brought the spread to
0.2 LU.

**Anchor targets on the game's own assets.** Soundtrack Menu bundles the vanilla Rebirth
oggs, so the game's real levels were measurable rather than guessed:

| | vanilla Rebirth | this mod, raw | normalised |
|---|---|---|---|
| loop mean | -11.6 LUFS | -18.9 | -19.1 |
| loop spread | 9.6 LU | 15.4 | **0.2** |
| jingle mean | -14.5 LUFS | -13.7 | -22.1 |
| jingle vs loop | -2.9 LU | +5.2 | **-2.9** |

Two things fell out of that table. Vanilla jingles sit about 3 LU *below* its loops,
while the raw cuts were 5 LU above, because each was cut from the loudest phrase of its
source. And vanilla true peaks reach +2.6 dBTP, so a -1 dBTP ceiling is stricter than the
game itself.

**Derive the target from the material, not from a number you like.** Reaching vanilla's
-11.6 LUFS needed about 10 dB of limiting on the peakiest masters, which audibly squashes
them. Instead the build computes the loudest level *every* source can reach while the
limiter does no more than a 3 dB budget, capped at the vanilla level. That produced
-19.1 LUFS, set by the quietest-headroom track. The mod ends up 7.5 LU below vanilla,
which is reported as a standing warning rather than hidden. For short sfx the same method
applies but the budget can be looser, since a one-shot tolerates limiting far better than
a two-minute loop does.

**Trim leading and trailing digital silence** from every master first, and derive
everything downstream from the trimmed copy, so an offset means the same thing in the
build, the analysis and the audition page.

**Maximising RMS picks the wrong window.** Selecting the highest short-term RMS window
lands in the middle of the loudest phrase, which for vocal music is the middle of a sung
line, so the clip has no beginning and no end. Two attempts failed the same way before
the cause was clear. The fix was to search the opposite way: find energy dips, treat the
rise out of one as a phrase start, end at the next dip. For a voice mod this matters even
more, since every clip is a phrase.

---

## 6. Verification, in three layers

Ordered cheapest first. The point of the ordering is that the loop requiring human ears
must not also require launching the game.

**Layer 1, machine, no game, no ears.** Ran as part of the build. Names match a
checked-in copy of the canonical list; every referenced file exists and decodes; duration
within tolerance; no clipping; onset not silent; tail decays; loudness spread within
tolerance; level against the game's own assets; channel balance against the player's
actual slider settings.

**Layer 2, human ears, still no game.** A self-contained HTML page with every clip
embedded as a data URI, each shown against a waveform of its source with the cut window
marked, plus a padded context clip. Published as an artifact. The user listens, quotes a
number, the value changes in the data module, one rebuild, refresh. Round trip in
seconds. This absorbed three review rounds that would otherwise have been game restarts.

**Layer 3, in game, deterministic.** A dev-only Lua file registering console commands
that trigger each sound directly, since most fire in situations that are tedious to
reproduce. It caught the three failure modes layer 2 cannot see: a typo'd name (which
fails **silently**, falling back to vanilla), a one-shot that loops, and loudness wrong
in the game's real mix. `deploy.py --release` excludes it.

The harness printed a ready line on load, so its absence was the signal that it failed to
load. Cheap and worth repeating.

---

## 7. Process rules that paid off

**Verify against the source instead of guessing.** Reading the dependency's Lua answered
questions that would otherwise have been assumptions: the fallback chain for undefined
tracks, the exact track-name strings, the REPENTOGON-only main menu callback. Extracting
strings from `ModUploader.exe` gave the real button labels instead of a described-from-
memory UI. One guess that was not checked ("Choose Mod opens a folder picker") was wrong
and cost a round trip. It opens a file picker for `metadata.xml`.

**Encode cross-item constraints as automated checks.** A mapping of 63 entries had
exactly one error: a floor sharing its music with the boss fought on that floor, so the
floor's ordinary rooms played boss music. Assigning by eye found it only when the user
hit it in game. The fix was a `FLOOR_BOSS_PAIRS` table checked in `validate()`, tested by
reintroducing the original bug and confirming the check fires. Any rule that must hold
across many items belongs in code, not in attention.

**Pin automatically chosen values once reviewed.** Automatic selection was mutually
exclusive: each clip claimed a window and blocked the others. Editing one unpinned clip
silently relocated every other clip sharing a source. After the first review round all 22
were pinned to their reviewed values, and from then on edits touched only what was asked.

**One owner per file.** The uploader and the deploy script both wrote `metadata.xml` and
fought over id, version, element order and line endings. Resolved by naming the owner of
each field explicitly: id and version belong to the uploader and are pulled back, the
rest belongs to the repo. Do not edit a Workshop description on the Steam page and in the
repo both; make the repo the only source and the page its projection.

**Split taste from fact.** Which cut sounds better is the user's call and asking is
faster than guessing; whether the uploader accepts `.ogg` is a fact and asking wastes
their time. Guessing on the first wasted three rounds on one clip. Not checking the
second would have risked a failed upload.

**Recommendations must follow from the analysis in the same message.** This session
produced a recommendation that contradicted the reasoning written three paragraphs above
it, and the reader caught it rather than the writer.

---

## 8. Workshop publishing

1. `deploy.py --release` first. Dev files and build markers must not ship.
2. Close the game and the uploader before any deploy; two programs writing the same
   metadata fight.
3. Run `ModUploader.exe`. **Choose Mod opens a file picker; select the mod's
   `metadata.xml`.** The uploader treats its parent folder as the mod.
4. Status goes from "Please choose a mod to upload..." to "Ready to upload mod '<name>'",
   showing the `<name>` field, not the folder name.
5. Visibility comes from `<visibility>`. Upload Private first, check the page, then
   Public.
6. Change notes are for existing subscribers, describing what changed for them. An
   initial public release has nothing to say there; leave it empty.
7. **Accept the Workshop EULA on the item page.** Without it the item stays invisible to
   everyone else even when set to Public. Easy to miss and looks like a failed upload.
8. Run `deploy.py --release` once more to pull the id and version back into the repo.

---

## 9. Files worth adapting

From `D:\DeerWorkshop\IssacChiikawaMusicMod\build\`:

| File | Reuse |
|---|---|
| `ffio.py` | Almost verbatim. ffmpeg discovery, ebur128 loudness, RMS envelope. |
| `deploy.py` | Almost verbatim. Change `MOD_DIR_NAME` and the dev file list. |
| `verify.py` | Structure and most checks; thresholds need retuning for short sfx. |
| `audition.py` | Structure and the page; row content is domain specific. |
| `tracks.py` | The *shape* only. Pure data, `validate()`, constraint tables. |
| `build_audio.py` | `phrase_windows()` and the normalisation helpers. |

The design spec in the Chiikawa music mod repository, `docs/design.md`,
records the reasoning behind each decision, including the ones that were revised.

---

## 10. Known warts left in the Chiikawa mod

- The mod sits 7.5 LU below the vanilla soundtrack. Accepted trade-off, reported by
  `verify.py` on every run, adjustable via `LIMIT_BUDGET_DB`.
- Jingle slot 30 ends only 8.3 dB below its own clip level and may click faintly.
- Sixteen pieces of music cover 85 slots, so reuse is heavy. Stated in the Workshop
  description rather than left for a subscriber to notice.
- No loop points are hand authored. `music.xml` supports an `intro=` attribute for a
  separate intro plus looping body; unused, so each track hard loops end to start.
