import numpy as np
from build import dsp

SR = 44100


def test_trim_silence_strips_both_ends():
    x = np.concatenate([np.zeros(1000), np.ones(500) * 0.5, np.zeros(1000)])
    y = dsp.trim_silence(x)
    assert len(y) == 500
    assert np.all(np.abs(y) > 0.4)


def test_trim_silence_leaves_a_signal_with_no_silence_alone():
    x = np.ones(300) * 0.3
    assert len(dsp.trim_silence(x)) == 300


def test_frame_shape():
    x = np.arange(5000, dtype=float)
    F = dsp.frame(x, 1024, 256)
    assert F.shape == (1 + (5000 - 1024) // 256, 1024)
    assert F[0, 0] == 0.0
    assert F[1, 0] == 256.0


def test_rms_envelope_tracks_a_step():
    x = np.concatenate([np.ones(22050) * 0.1, np.ones(22050) * 0.8])
    e = dsp.rms_envelope(x)
    assert e[5] < 0.2
    assert e[-5] > 0.6


def test_rms_envelope_of_silence_is_zero():
    assert np.allclose(dsp.rms_envelope(np.zeros(10000)), 0.0)
