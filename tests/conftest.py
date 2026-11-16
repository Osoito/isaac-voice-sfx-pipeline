import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VANILLA_SFX = Path(
    "D:/softwares/Steam/steamapps/common/The Binding of Isaac Rebirth"
    "/extracted_resources/resources/sfx"
)
VOICES = ROOT / "Voices"
