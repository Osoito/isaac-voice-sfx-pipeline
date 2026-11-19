import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build import game

# Both of these can be absent on a fresh checkout. The vanilla sfx tree has to be
# extracted from the game once, and the voice clips are not mine to redistribute,
# so the tests that read them skip instead of failing.
VANILLA_SFX = game.vanilla_sfx_dir()
VOICES = ROOT / "Voices"

requires_vanilla = pytest.mark.skipif(
    VANILLA_SFX is None,
    reason="needs the game's extracted vanilla sfx. Set ISAAC_DIR, and run the "
           "game's own tools/ResourceExtractor once.",
)

requires_voices = pytest.mark.skipif(
    not (VOICES / "iya.mp3").exists(),
    reason="needs the source voice clips in Voices/, which are not in this repository.",
)
