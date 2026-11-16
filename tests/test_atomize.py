import numpy as np
from build import atomize, dsp

SR = 44100


def three_bursts():
    """Three 150 ms tone bursts separated by 100 ms of near-silence."""
    def burst(f):
        t = np.arange(int(0.15 * SR)) / SR
        return np.sin(2 * np.pi * f * t) * np.hanning(len(t))
    gap = np.zeros(int(0.10 * SR))
    return np.concatenate([burst(200), gap, burst(250), gap, burst(300)])


def test_split_syllables_finds_three_segments():
    segs = atomize.split_syllables(three_bursts(), SR, min_ms=60)
    assert len(segs) == 3
    for a, b in segs:
        assert 0.10 < (b - a) / SR < 0.22


def test_split_syllables_drops_segments_below_min_ms():
    segs = atomize.split_syllables(three_bursts(), SR, min_ms=400)
    assert segs == []


def test_split_syllables_on_one_continuous_sound_returns_one():
    t = np.arange(int(0.5 * SR)) / SR
    segs = atomize.split_syllables(np.sin(2 * np.pi * 200 * t), SR, min_ms=60)
    assert len(segs) == 1


def test_tag_atom_shape():
    t = np.arange(int(0.3 * SR)) / SR
    x = np.sin(2 * np.pi * 200 * t) * np.hanning(len(t))
    tag = atomize.tag_atom("long-3", 2, x, 0.4, 0.7, SR)
    assert tag["id"] == "long-3.02"
    assert tag["src"] == "long-3"
    assert tag["start"] == 0.4 and tag["end"] == 0.7
    assert abs(tag["dur"] - 0.3) < 1e-9
    assert tag["pinned"] is True
    for k in ("f0", "voiced_ratio", "attack_ms", "centroid", "env_class", "rms"):
        assert k in tag
