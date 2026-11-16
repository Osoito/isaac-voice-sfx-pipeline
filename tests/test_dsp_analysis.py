import numpy as np
from build import dsp

SR = 44100


def tone(f, dur, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    # a few harmonics, so autocorrelation has something to lock onto
    return (np.sin(2 * np.pi * f * t)
            + 0.5 * np.sin(4 * np.pi * f * t)
            + 0.25 * np.sin(6 * np.pi * f * t)) / 1.75


def test_f0_finds_a_known_pitch():
    assert abs(dsp.f0(tone(200, 0.4), SR) - 200) < 8


def test_f0_returns_none_for_noise():
    rng = np.random.default_rng(0)
    assert dsp.f0(rng.normal(0, 0.3, SR // 2), SR) is None


def test_voiced_ratio_high_for_tone_low_for_noise():
    rng = np.random.default_rng(1)
    assert dsp.voiced_ratio(tone(150, 0.5), SR) > 0.8
    assert dsp.voiced_ratio(rng.normal(0, 0.3, SR // 2), SR) < 0.3


def test_attack_ms_short_for_a_click():
    x = np.zeros(SR // 2)
    x[100:400] = 1.0
    assert dsp.attack_ms(x, SR) < 15


def test_attack_ms_long_for_a_slow_swell():
    x = np.linspace(0, 1, SR) * tone(200, 1.0)
    assert dsp.attack_ms(x, SR) > 300


def test_centroid_orders_bright_above_dark():
    assert dsp.centroid(tone(150, 0.4), SR) < dsp.centroid(tone(1500, 0.4), SR)


def test_envelope_class_impact():
    x = tone(200, 0.5) * np.exp(-np.linspace(0, 8, int(0.5 * SR)))
    assert dsp.envelope_class(x, SR) == "impact"


def test_envelope_class_crescendo():
    x = tone(200, 1.0) * np.linspace(0.05, 1.0, SR)
    assert dsp.envelope_class(x, SR) == "crescendo"


def test_envelope_class_sustain():
    x = tone(200, 1.0)
    assert dsp.envelope_class(x, SR) == "sustain"
