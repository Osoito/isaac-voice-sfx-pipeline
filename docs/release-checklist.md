# Release checklist

Order matters. Steps 1-3 are mechanical, 4-8 happen in the uploader and on the
Steam page.

## Before anything

- [ ] **Close the game and ModUploader.** Two programs writing `metadata.xml`
      fight over id, version and line endings.
- [ ] `python build/bake.py` — must print PASS.
- [ ] Play a run. The in-game check is the only place a mistyped path shows up:
      a wrong path **fails silently**, the game falls back to its own asset, and
      nothing in the build can see that.

## 1. Preview image

`mod/previewpic.png` does not exist yet, and `deploy.py --release` warns about
it. The Workshop page works without one but looks abandoned. Needs to be
supplied by hand — nothing in this project can generate it.

## 2. Upload straight from the repo

The uploader takes a `metadata.xml` and treats its parent folder as the mod, so
the mod does **not** have to be installed in the game to be published. Upload
from `mod/` in this repo:

```
D:\DeerWorkshop\modding\IssacMiyamoVoices\mod\metadata.xml
```

`mod/` is already release-clean — the build writes only `wav` and `xml` there,
and the `.miyamo-build` ownership marker only ever goes into the *installed*
copy, never into `mod/`.

Verify before uploading:

```
find mod -type f | sed 's/.*\.//' | sort | uniq -c
```

Expect only `wav` and `xml`, plus `png` once the preview image exists. Currently
673 wav + 1 xml, about 56 MB.

If the uploader turns out to insist on a folder under `<install>\mods\`, install
a release copy first and upload from there instead:

```
python build/deploy.py --release
```

That writes no marker file, because Steam only accepts `lua`, `ogg`, `wav`,
`png` and `xml`. Ownership is recorded in `data/deploy_state.json` instead, so
the "do not clobber someone else's mod" guard keeps working.

## 3. Local install is separate from publishing

```
python build/deploy.py             # install for testing
python build/deploy.py --uninstall # remove it; the game stops loading it
```

Uninstall deletes the installed folder rather than dropping a `disable.it`
marker, because that extension is not one Steam accepts and a stray one in a
folder the uploader might read is a trap. `mod/` is untouched either way.

**The mod is currently uninstalled.** The game loads nothing from this project.

## 4. Upload

Run `<Isaac install>\tools\ModUploader\ModUploader.exe`.

**Choose Mod opens a file picker; select the `metadata.xml`.** Status goes from
"Please choose a mod to upload..." to "Ready to upload mod 'Miyamo Voice SFX'" —
it shows the `<name>` field, not the folder name.

Change notes are for existing subscribers, describing what changed for them. A
first release has nothing to say there; leave it empty.

## 5. Visibility

`metadata.xml` currently says `Private`. Upload private first, open the page,
check the description renders and the preview image looks right, then change
`<visibility>` to `Public` and upload again.

## 6. Accept the Workshop EULA on the item page

Without it the item stays invisible to everyone else even when set to Public.
Easy to miss and looks exactly like a failed upload.

## 7. Pull the uploader's fields back

The uploader owns `<id>` and `<version>`: it assigns the id on first publish and
bumps the version on every upload. **Copy both back into `mod/metadata.xml`
before the next release build**, or the next upload creates a second unrelated
Workshop item and the published version number goes backwards. Convention puts
`<id>` directly after `<directory>`.

The uploader writes mixed CRLF and LF. Edit the file in binary or with
`newline=""`, or text mode silently rewrites every line ending.

## Two things to decide before going public

**Preview image.** See step 1.

**The audio is a copyrighted performance.** The clips are one anime character's
voice. Publishing to the Workshop distributes that audio to anyone who
subscribes. That is a judgement call, not a technical blocker, and it is worth
making deliberately rather than by default — plenty of voice mods exist and get
left alone, and some get taken down. Keeping the item Private sidesteps it
entirely and the mod still works locally.
