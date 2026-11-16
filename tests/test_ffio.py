import numpy as np
from conftest import VOICES
from build import ffio


def test_decode_returns_mono_float_at_44100():
    x = ffio.decode(VOICES / "iya.mp3")
    assert x.ndim == 1
    assert x.dtype == np.float64
    # iya.mp3 is 0.536 s; allow codec padding either way
    assert 0.45 < len(x) / ffio.SR < 0.65


def test_read_wav_matches_probe_duration(tmp_path):
    x = np.sin(np.linspace(0, 400, ffio.SR)) * 0.5
    p = tmp_path / "tone.wav"
    ffio.write_wav(p, x)
    y = ffio.read_wav(p)
    assert len(y) == len(x)
    assert np.allclose(y, x, atol=2e-4)
