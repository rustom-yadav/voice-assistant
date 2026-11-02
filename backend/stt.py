"""Speech-to-text module using faster-whisper."""

import logging

import numpy as np
from config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class Transcriber:
    """Wrapper around faster-whisper WhisperModel for transcribing audio."""

    def __init__(self) -> None:
        """Initialize and load the Whisper model once."""
        logger.info(
            "Loading Whisper model '%s' on %s (%s)...",
            WHISPER_MODEL,
            WHISPER_DEVICE,
            WHISPER_COMPUTE_TYPE,
        )
        try:
            self.model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                local_files_only=True,
            )
        except Exception:  # noqa: BLE001
            self.model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                local_files_only=False,
            )
        logger.info("Whisper model loaded successfully.")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe 16 kHz mono float32 audio array into text.

        Args:
            audio: 1-D numpy array of float32 samples at 16 kHz.

        Returns:
            Recognized English text, or an empty string if nothing detected.
        """
        if audio.size == 0:
            return ""

        segments, _ = self.model.transcribe(
            audio,
            language="en",
            vad_filter=True,
            beam_size=1,
        )
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()
