import json
import numpy as np
from conftest import VANILLA_SFX, requires_vanilla
from build import vanilla


def test_band_boundaries():
    assert vanilla.band(0.10) == "<0.15"
    assert vanilla.band(0.15) == "0.15-0.4"
    assert vanilla.band(0.5) == "0.4-0.8"
    assert vanilla.band(1.0) == "0.8-1.5"
    assert vanilla.band(2.0) == "1.5-3"
    assert vanilla.band(4.0) == "3-6"
    assert vanilla.band(9.0) == ">6"


def test_group_strips_numbered_variants():
    assert vanilla.group("player/hurt grunt 1.wav") == "player/hurt grunt"
    assert vanilla.group("player/hurt grunt .wav") == "player/hurt grunt"
    assert vanilla.group("monster roar 10.wav") == "monster roar"
    assert vanilla.group("v2/bone_death_5a.wav") == "v2/bone_death"
    assert vanilla.group("player/derp 0.wav") == "player/derp"


@requires_vanilla
def test_measure_one_real_file():
    row = vanilla.measure(VANILLA_SFX, "player/hurt grunt .wav")
    assert row["path"] == "player/hurt grunt .wav"
    assert 0.3 < row["dur"] < 0.5
    assert row["sr"] in (22050, 44100, 48000)
    assert 0 < row["rms"] < 1
    assert row["env_class"] in ("impact", "sustain", "crescendo", "composite")
    assert row["band"] == "0.15-0.4"
    assert row["group"] == "player/hurt grunt"


@requires_vanilla
def test_build_spec_covers_every_scope_path(tmp_path):
    paths = ["player/hurt grunt .wav", "player/derp 0.wav"]
    out = tmp_path / "spec.json"
    rows = vanilla.build_spec(VANILLA_SFX, paths, out)
    assert len(rows) == 2
    assert {r["path"] for r in rows} == set(paths)
    assert json.loads(out.read_text(encoding="utf-8"))[0]["path"] in paths
