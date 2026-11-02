"""WebSocket session management for audio recording, STT, and LLM responses."""

import asyncio
import logging
from typing import Any

import numpy as np
from audio import UtteranceRecorder
from config import (
    MSG_ANSWER_DONE,
    MSG_ANSWER_TOKEN,
    MSG_ERROR,
    MSG_STATUS,
    MSG_TRANSCRIPT,
)
from fastapi import WebSocket
from llm import LLMError, stream_answer
from stt import Transcriber

logger = logging.getLogger(__name__)


class Session:
    """Manages one WebSocket client session."""

    def __init__(self, websocket: WebSocket, transcriber: Transcriber) -> None:
        """Initialize session with WebSocket and shared Transcriber.

        Args:
            websocket: Connected client WebSocket instance.
            transcriber: Shared Transcriber instance.
        """
        self._ws = websocket
        self._transcriber = transcriber
        self._recorder: UtteranceRecorder | None = None
        self._audio_queue: asyncio.Queue[np.ndarray | None] | None = None
        self._transcribe_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._is_listening = False
        self._is_suggesting = False

    async def start(self) -> None:
        """Start listening to microphone and transcribing speech."""
        if self._is_listening:
            return

        self._is_listening = True
        self._loop = asyncio.get_running_loop()
        self._audio_queue = asyncio.Queue()

        def on_utterance(audio: np.ndarray) -> None:
            if self._loop and self._audio_queue:
                self._loop.call_soon_threadsafe(self._audio_queue.put_nowait, audio)

        self._recorder = UtteranceRecorder(on_utterance=on_utterance)
        self._transcribe_task = asyncio.create_task(self._transcribe_loop())
        self._recorder.start()
        await self._send_json({"type": MSG_STATUS, "listening": True})

    async def stop(self) -> None:
        """Stop listening to microphone and let pending audio finish."""
        if not self._is_listening:
            return

        self._is_listening = False
        if self._recorder:
            self._recorder.stop()
            self._recorder = None

        if self._audio_queue:
            await self._audio_queue.put(None)

        await self._send_json({"type": MSG_STATUS, "listening": False})

    async def suggest(self, question: str) -> None:
        """Stream LLM answer for given transcribed question."""
        cleaned = question.strip()
        if not cleaned:
            await self._send_json(
                {
                    "type": MSG_ERROR,
                    "message": "Transcript is empty. Speak or type a question.",
                }
            )
            return

        if self._is_suggesting:
            return

        self._is_suggesting = True
        try:
            async for token in stream_answer(cleaned):
                await self._send_json({"type": MSG_ANSWER_TOKEN, "text": token})
            await self._send_json({"type": MSG_ANSWER_DONE})
        except LLMError as err:
            logger.warning("LLM error during suggest: %s", err)
            await self._send_json({"type": MSG_ERROR, "message": str(err)})
        except Exception:
            logger.exception("Unexpected error during suggest")
            await self._send_json(
                {
                    "type": MSG_ERROR,
                    "message": "Failed to generate answer. Please try again.",
                }
            )
        finally:
            self._is_suggesting = False

    async def close(self) -> None:
        """Clean up audio recorder and background tasks on disconnect."""
        self._is_listening = False
        self._is_suggesting = False

        if self._recorder:
            try:
                self._recorder.stop()
            except (RuntimeError, OSError) as exc:
                logger.warning("Error stopping recorder on close: %s", exc)
            self._recorder = None

        if self._transcribe_task and not self._transcribe_task.done():
            self._transcribe_task.cancel()
            try:
                await self._transcribe_task
            except asyncio.CancelledError:
                pass
            self._transcribe_task = None

    async def _transcribe_loop(self) -> None:
        """Consume audio from queue, transcribe in thread, and send text."""
        while True:
            try:
                assert self._audio_queue is not None
                audio = await self._audio_queue.get()
                if audio is None:
                    self._audio_queue.task_done()
                    break

                text = await asyncio.to_thread(self._transcriber.transcribe, audio)
                if text:
                    await self._send_json({"type": MSG_TRANSCRIPT, "text": text})
                self._audio_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in transcribe loop")

    async def _send_json(self, data: dict[str, Any]) -> None:
        """Send JSON message to WebSocket client safely."""
        try:
            await self._ws.send_json(data)
        except (RuntimeError, OSError) as exc:
            logger.warning("Failed to send WebSocket message: %s", exc)
