"""Where the game is installed. The only module that answers that question.

Resolution order, first hit wins:

  1. the ISAAC_DIR environment variable, if it points at a real directory
  2. Steam's own install root, read from HKCU\\Software\\Valve\\Steam
  3. the common Steam library locations in FALLBACK_LIBRARIES

Before this module the install path was a literal in nine files, so a checkout
on any machine but the one it was written on failed nine separate times. The
registry lookup is the same one the Chiikawa music mod uses.

Nothing here raises on a missing game. A resolver returns None, and the caller
decides whether that is fatal. `require()` turns it into one clear message for
the scripts that cannot do anything without it.
"""

import os
import sys
from pathlib import Path

GAME_SUBPATH = Path("steamapps/common/The Binding of Isaac Rebirth")

FALLBACK_LIBRARIES = [
    Path("C:/Program Files (x86)/Steam"),
    Path("D:/Steam"),
    Path("D:/SteamLibrary"),
    Path("D:/softwares/Steam"),
]

# Relative to the install directory.
SFX_SUBPATH = Path("extracted_resources/resources/sfx")
MODS_SUBPATH = Path("mods")


def _steam_roots():
    """Candidate Steam install roots, best first."""
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.append(Path(winreg.QueryValueEx(k, "SteamPath")[0]))
    except Exception:
        # Not on Windows, no Steam, or the key is absent. The fallbacks still apply.
        pass
    return roots + FALLBACK_LIBRARIES


def install_dir():
    """The game's install directory, or None if it cannot be found."""
    override = os.environ.get("ISAAC_DIR")
    if override:
        path = Path(override)
        return path if path.is_dir() else None
    for root in _steam_roots():
        candidate = root / GAME_SUBPATH
        if candidate.is_dir():
            return candidate
    return None


def vanilla_sfx_dir():
    """The extracted vanilla sfx tree, or None.

    This is not part of a stock install. It is produced by running the game's
    own ResourceExtractor once, so it can be absent on a machine that has the
    game.
    """
    install = install_dir()
    if install is None:
        return None
    sfx = install / SFX_SUBPATH
    return sfx if sfx.is_dir() else None


def mods_dir():
    """The folder Repentance+ loads mods from, or None."""
    install = install_dir()
    if install is None:
        return None
    mods = install / MODS_SUBPATH
    return mods if mods.is_dir() else None


EXTRACTOR_HINT = ("The sfx tree is not part of a stock install. Run the game's own "
                  "tools/ResourceExtractor once to produce it.")


def require(path, what, hint=None):
    """Return `path`, or exit with a message naming what to do about it.

    For the scripts that have nothing to do without the game. A script that can
    still do useful work should check for None itself instead of calling this.
    """
    if path is not None:
        return path
    lines = [
        f"Could not find {what}.",
        "Set ISAAC_DIR to the game's install directory, for example",
        f'  ISAAC_DIR="C:/Program Files (x86)/Steam/{GAME_SUBPATH.as_posix()}"',
    ]
    if hint:
        lines.append(hint)
    sys.exit("\n".join(lines))
