"""Install the built mod into the game's mods folder.

  python build/deploy.py             # dev install, drops an ownership marker
  python build/deploy.py --release   # no marker, nothing but uploadable files
  python build/deploy.py --uninstall # remove the installed copy from the game
  python build/deploy.py --dry-run   # show what would happen, change nothing

Refuses to write over a folder this project did not create, so a subscribed mod
of the same name cannot be clobbered by accident. Close the game and the
uploader first: two programs writing the same metadata fight.

Steam Workshop only accepts lua, ogg, wav, png and xml, so a release build must
not carry the marker file. Ownership is then remembered in data/deploy_state.json
instead, which keeps the guard working across release deploys.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD_SRC = ROOT / "mod"
REPORT = ROOT / "data" / "build_report.json"
STATE = ROOT / "data" / "deploy_state.json"
MODS_DIR = Path("D:/softwares/Steam/steamapps/common/The Binding of Isaac Rebirth/mods")
MOD_DIR_NAME = "miyamo voice sfx"
MARKER = ".miyamo-build"

ALLOWED = {".lua", ".ogg", ".wav", ".png", ".xml"}
# Files that exist only for in-game testing. None yet; the console harness would
# go here if it gets written.
DEV_ONLY = set()


def preflight(release):
    """Nothing is copied until the build's own claims check out."""
    rows = json.loads(REPORT.read_text(encoding="utf-8"))
    missing = [r["path"] for r in rows
               if not (MOD_SRC / "resources" / "sfx" / r["path"]).exists()]
    if missing:
        sys.exit("error: build report lists files that do not exist:\n  "
                 + "\n  ".join(missing[:20]))
    if not (MOD_SRC / "metadata.xml").exists():
        sys.exit("error: mod/metadata.xml is missing")

    if release:
        bad = [p for p in MOD_SRC.rglob("*")
               if p.is_file() and p.suffix.lower() not in ALLOWED]
        if bad:
            sys.exit("error: these files are not uploadable to the Workshop:\n  "
                     + "\n  ".join(str(p.relative_to(MOD_SRC)) for p in bad[:20]))
        if not (MOD_SRC / "previewpic.png").exists():
            print("warning: mod/previewpic.png is missing; the Workshop page "
                  "will have no preview image")
    return len(rows)


def owns(dest):
    if (dest / MARKER).exists():
        return True
    if STATE.exists():
        return str(dest) in json.loads(STATE.read_text(encoding="utf-8")).get("installed", [])
    return False


def remember(dest):
    data = {"installed": []}
    if STATE.exists():
        data = json.loads(STATE.read_text(encoding="utf-8"))
    if str(dest) not in data["installed"]:
        data["installed"].append(str(dest))
    STATE.write_text(json.dumps(data, indent=1), encoding="utf-8")


def uninstall(dry):
    """Remove the installed copy so the game stops loading it.

    Deleting rather than dropping a `disable.it` marker: that file is not one of
    the extensions Steam accepts, so leaving one in a folder the uploader might
    read is a trap. The build in `mod/` is untouched either way.
    """
    dest = MODS_DIR / MOD_DIR_NAME
    if not dest.exists():
        print(f"nothing to remove: {dest} does not exist")
        return
    if not owns(dest):
        sys.exit(f"error: {dest} was not created by this project. "
                 f"Refusing to delete it.")
    n = sum(1 for p in dest.rglob("*") if p.is_file())
    if dry:
        print(f"would delete {dest} ({n} files)")
        return
    shutil.rmtree(dest)
    if STATE.exists():
        data = json.loads(STATE.read_text(encoding="utf-8"))
        data["installed"] = [p for p in data["installed"] if p != str(dest)]
        STATE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"removed {dest} ({n} files). The game will no longer load the mod.")


def main():
    dry = "--dry-run" in sys.argv
    release = "--release" in sys.argv
    if "--uninstall" in sys.argv:
        uninstall(dry)
        return
    n = preflight(release)
    dest = MODS_DIR / MOD_DIR_NAME

    if dest.exists() and not owns(dest):
        sys.exit(f"error: {dest} exists but was not created by this project. "
                 f"Refusing to overwrite it.")

    files = sorted(p for p in MOD_SRC.rglob("*")
                   if p.is_file() and p.name not in DEV_ONLY)
    mode = "release" if release else "dev"
    print(f"{len(files)} files -> {dest}  [{mode}]")
    if dry:
        for p in files[:12]:
            print("  ", p.relative_to(MOD_SRC))
        if len(files) > 12:
            print(f"   ... and {len(files) - 12} more")
        print("(dry run, nothing written)")
        return

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for p in files:
        target = dest / p.relative_to(MOD_SRC)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)

    remember(dest)
    if not release:
        (dest / MARKER).write_text("created by IssacMiyamoVoices/build/deploy.py\n",
                                   encoding="utf-8")
    print(f"installed {n} sounds ({mode}). Restart the game to pick it up.")
    if release:
        print("no marker file written; this folder is ready for ModUploader.")


if __name__ == "__main__":
    main()
