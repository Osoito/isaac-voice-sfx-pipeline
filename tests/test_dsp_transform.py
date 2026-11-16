import numpy as np
from build import dsp

SR = 44100


def tone(f, dur, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2 * np.pi * f * t)


def test_pitch_shift_up_an_octave_halves_length_and_doubles_pitch():
    y = dsp.pitch_shift(tone(200, 0.5), 12)
    assert abs(len(y) - SR // 4) < 200
    assert abs(dsp.f0(y, SR) - 400) < 15


def test_pitch_shift_zero_is_identity():
    x = tone(200, 0.2)
    assert np.allclose(dsp.pitch_shift(x, 0), x)


def test_take_attack_returns_requested_length_with_a_fade_out():
    x = np.ones(SR // 2)
    y = dsp.take_attack(x, SR, 80)
    assert abs(len(y) - int(0.080 * SR)) <= 1
    assert y[-1] < 0.05


def test_fade_zeroes_both_ends():
    y = dsp.fade(np.ones(SR // 10), SR, 5, 5)
    assert y[0] < 0.05 and y[-1] < 0.05
    assert y[len(y) // 2] > 0.95


def test_chain_length_accounts_for_crossfades():
    a, b, c = np.ones(4410), np.ones(4410), np.ones(4410)
    y = dsp.chain([a, b, c], SR, xfade_ms=10)
    x = int(0.010 * SR)
    assert len(y) == 3 * 4410 - 2 * x


def test_chain_of_one_is_that_one():
    a = np.ones(1000)
    assert np.allclose(dsp.chain([a], SR), a)


def test_layer_sums_to_the_longest_length():
    y = dsp.layer([np.ones(100), np.ones(250)])
    assert len(y) == 250
    assert y[0] == 2.0 and y[-1] == 1.0


def test_limit_holds_the_ceiling():
    rng = np.random.default_rng(3)
    y = dsp.limit(rng.normal(0, 1.5, SR), ceiling=0.5)
    assert np.abs(y).max() <= 0.51


def test_match_rms_reaches_an_easy_target_without_limiting():
    x = tone(200, 1.0) * 0.05
    y, drive, short = dsp.match_rms(x, 0.1)
    assert abs(np.sqrt((y ** 2).mean()) - 0.1) < 0.005
    assert drive == 0.0
    assert abs(short) < 0.5


def test_match_rms_reports_a_shortfall_it_cannot_close():
    # A single spike has a huge crest factor; RMS 0.4 is unreachable under budget.
    x = np.zeros(SR)
    x[0] = 1.0
    y, drive, short = dsp.match_rms(x, 0.4, budget_db=6.0)
    assert np.abs(y).max() <= 0.9
    assert short < -3.0


def test_fit_duration_truncates_with_a_fade_and_never_pads():
    x = np.ones(SR)
    y = dsp.fit_duration(x, SR, 0.5)
    assert abs(len(y) - SR // 2) <= 1
    assert y[-1] < 0.05
    assert len(dsp.fit_duration(np.ones(100), SR, 10.0)) == 100
