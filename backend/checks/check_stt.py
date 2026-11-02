"""Check script for STT module (faster-whisper)."""

import sys
import urllib.request
import wave
from pathlib import Path

import numpy as np

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SAMPLE_RATE
from stt import Transcriber

SAMPLE_WAV_URL = (
    "https://raw.githubusercontent.com/ggerganov/whisper.cpp/master/samples/jfk.wav"
)


def ensure_sample_wav(file_path: Path) -> Path:
    """Ensure a test audio file exists; download a sample if not present."""
    if not file_path.exists():
        print(f"Sample audio not found at '{file_path}'. Downloading sample WAV...")
        urllib.request.urlretrieve(SAMPLE_WAV_URL, file_path)
        print("Downloaded sample WAV successfully.")
    return file_path


def load_wav(file_path: Path) -> np.ndarray:
    """Load audio from WAV file and return as float32 1-D numpy array."""
    with wave.open(str(file_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if sampwidth == 2:
        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        data = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    if n_channels > 1:
        data = data.reshape(-1, n_channels).mean(axis=1)

    if framerate != SAMPLE_RATE:
        duration = len(data) / framerate
        target_length = int(duration * SAMPLE_RATE)
        data = np.interp(
            np.linspace(0, len(data), target_length, endpoint=False),
            np.arange(len(data)),
            data,
        ).astype(np.float32)

    return data


def main() -> None:
    """Run transcription on sample audio."""
    checks_dir = Path(__file__).resolve().parent
    wav_path = checks_dir / "sample.wav"

    if len(sys.argv) > 1:
        wav_path = Path(sys.argv[1])
    else:
        ensure_sample_wav(wav_path)

    print(f"Loading audio file: {wav_path}")
    audio = load_wav(wav_path)
    duration_sec = len(audio) / SAMPLE_RATE
    print(
        f"Audio loaded: {len(audio)} samples ({duration_sec:.2f} seconds at {SAMPLE_RATE} Hz)"
    )

    print("Initializing Transcriber (Whisper model)...")
    transcriber = Transcriber()

    print("Transcribing audio...")
    text = transcriber.transcribe(audio)

    print("-" * 50)
    print(f"Result:\n{text}")
    print("-" * 50)


if __name__ == "__main__":
    main()
