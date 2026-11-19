"""ffmpeg discovery and audio file I/O. The only module that knows where ffmpeg is."""

import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100

_WINGET_FF = (
    Path.home()
    / "AppData/Local/Microsoft/WinGet/Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-7.1-full_build/bin"
)


_RESOLVED = {}


def _locate(name):
    found = shutil.which(name)
    if found:
        return found
    candidate = _WINGET_FF / f"{name}.exe"
    return str(candidate) if candidate.exists() else None


def have(name):
    """True when the tool can be found. For deciding whether to skip a test."""
    if name not in _RESOLVED:
        _RESOLVED[name] = _locate(name)
    return _RESOLVED[name] is not None


def tool(name):
    """Path to ffmpeg or ffprobe, resolved on first use and never at import.

    Importing this module has to work without ffmpeg installed. Most of the
    tests exercise pure-numpy DSP and the stdlib wave reader, so a missing
    ffmpeg should skip the few tests that decode audio instead of killing the
    whole run at collection time.
    """
    if not have(name):
        sys.exit(f"error: {name} not found on PATH or at {_WINGET_FF}")
    return _RESOLVED[name]


def run(args, **kw):
    proc = subprocess.run(args, capture_output=True, **kw)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace")[-2000:]
        raise RuntimeError(f"command failed ({proc.returncode}): {args[0]}\n{tail}")
    return proc


def decode(path):
    """Any audio file -> mono float64 at SR."""
    proc = run([tool("ffmpeg"), "-hide_banner", "-v", "error", "-i", str(path),
                "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(proc.stdout, dtype="<f4").astype(np.float64)


def read_wav(path):
    """Read a wav at its own rate, downmixed to mono float64.

    Vanilla sfx are a mix of 22.05/44.1/48 kHz and mono/stereo, so callers that
    need a specific rate use decode() instead.
    """
    with wave.open(str(path), "rb") as w:
        n, ch = w.getnframes(), w.getnchannels()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    return a.reshape(-1, ch).mean(1) if ch > 1 else a


def wav_info(path):
    with wave.open(str(path), "rb") as w:
        return {"dur": w.getnframes() / w.getframerate(),
                "sr": w.getframerate(), "ch": w.getnchannels()}


def write_wav(path, x, sr=SR):
    """Write mono 16-bit. Output format is uniform regardless of the source."""
    pcm = (np.clip(x, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def to_ogg(wav_path, ogg_path, bitrate="128k"):
    run([tool("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-i", str(wav_path),
         "-c:a", "libvorbis", "-b:a", bitrate, str(ogg_path)])
    return ogg_path


def probe(path):
    proc = run([tool("ffprobe"), "-v", "error", "-select_streams", "a:0",
                "-show_entries",
                "stream=codec_name,sample_rate,channels:format=duration,size",
                "-of", "json", str(path)])
    return json.loads(proc.stdout.decode("utf-8"))
