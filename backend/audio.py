"""Microphone audio capture with Voice Activity Detection (VAD)."""

import collections
import logging
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd
from config import (
    BLOCK_MS,
    MAX_UTTERANCE_SECONDS,
    MIN_UTTERANCE_SECONDS,
    PRE_ROLL_SECONDS,
    SAMPLE_RATE,
    SILENCE_RMS_THRESHOLD,
    SILENCE_SECONDS,
)

logger = logging.getLogger(__name__)


class UtteranceRecorder:
    """Records microphone audio and detects discrete spoken utterances."""

    def __init__(self, on_utterance: Callable[[np.ndarray], None]) -> None:
        """Initialize recorder with utterance callback.

        Args:
            on_utterance: Function called with float32 16 kHz audio when an utterance ends.
        """
        self._on_utterance = on_utterance
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

        # Compute block counts from config constants
        self._block_size = int(SAMPLE_RATE * BLOCK_MS / 1000)
        block_duration = BLOCK_MS / 1000.0
        self._pre_roll_limit = int(PRE_ROLL_SECONDS / block_duration)
        self._silence_limit = int(SILENCE_SECONDS / block_duration)
        self._min_blocks_limit = int(MIN_UTTERANCE_SECONDS / block_duration)
        self._max_blocks_limit = int(MAX_UTTERANCE_SECONDS / block_duration)

        # Buffers and state
        self._is_speaking = False
        self._silence_block_count = 0
        self._pre_roll_buffer: collections.deque[np.ndarray] = collections.deque(
            maxlen=self._pre_roll_limit
        )
        self._recorded_blocks: list[np.ndarray] = []

    def start(self) -> None:
        """Open and start the microphone audio input stream."""
        with self._lock:
            if self._stream is not None:
                return
            self._reset_state()
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=self._block_size,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("UtteranceRecorder started.")

    def stop(self) -> None:
        """Stop and close the microphone input stream, flushing pending audio."""
        with self._lock:
            if self._stream is None:
                return
            try:
                self._stream.stop()
                self._stream.close()
            except (sd.PortAudioError, OSError) as exc:
                logger.warning("Error stopping audio stream: %s", exc)
            finally:
                self._stream = None
            self._flush_current_utterance()
            logger.info("UtteranceRecorder stopped.")

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Process incoming audio block from sounddevice thread."""
        if status:
            logger.warning("Audio stream callback status: %s", status)

        block = indata[:, 0].copy()
        rms = float(np.sqrt(np.mean(np.square(block))))
        is_speech = rms > SILENCE_RMS_THRESHOLD

        with self._lock:
            if not self._is_speaking:
                self._handle_silence_state(block, is_speech)
            else:
                self._handle_speech_state(block, is_speech)

    def _handle_silence_state(self, block: np.ndarray, is_speech: bool) -> None:
        """Handle incoming block when not currently in speech mode."""
        if is_speech:
            self._is_speaking = True
            self._recorded_blocks = list(self._pre_roll_buffer)
            self._recorded_blocks.append(block)
            self._silence_block_count = 0
        else:
            self._pre_roll_buffer.append(block)

    def _handle_speech_state(self, block: np.ndarray, is_speech: bool) -> None:
        """Handle incoming block when actively recording speech."""
        self._recorded_blocks.append(block)
        if is_speech:
            self._silence_block_count = 0
        else:
            self._silence_block_count += 1

        silence_ended = self._silence_block_count >= self._silence_limit
        max_duration_reached = len(self._recorded_blocks) >= self._max_blocks_limit
        if silence_ended or max_duration_reached:
            self._flush_current_utterance()

    def _flush_current_utterance(self) -> None:
        """Deliver finished speech audio if it meets the minimum duration threshold."""
        if self._is_speaking and len(self._recorded_blocks) >= self._min_blocks_limit:
            audio = np.concatenate(self._recorded_blocks)
            try:
                self._on_utterance(audio)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error in on_utterance callback: %s", exc)
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset internal buffers and detection state."""
        self._is_speaking = False
        self._silence_block_count = 0
        self._pre_roll_buffer.clear()
        self._recorded_blocks.clear()
