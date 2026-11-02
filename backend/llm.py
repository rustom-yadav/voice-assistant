"""Ollama streaming LLM wrapper."""

import logging
from collections.abc import AsyncIterator

import httpx
import ollama
from config import OLLAMA_MODEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception raised for user-friendly LLM errors."""


async def stream_answer(question: str) -> AsyncIterator[str]:
    """Stream answer tokens from local Ollama model for the given question.

    Args:
        question: User prompt or transcribed question text.

    Yields:
        Text chunks (tokens) progressively as received from Ollama.

    Raises:
        LLMError: When Ollama is not running or model is not pulled.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    try:
        client = ollama.AsyncClient()
        response = await client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            content = chunk["message"]["content"]
            if content:
                yield content

    except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionRefusedError) as exc:
        logger.error("Failed to connect to Ollama: %s", exc)
        raise LLMError("Ollama is not running. Start Ollama and try again.") from exc
    except ollama.ResponseError as exc:
        logger.error("Ollama response error: %s", exc)
        if exc.status_code == 404 or "not found" in str(exc).lower():
            raise LLMError(f"Model not found. Run: ollama pull {OLLAMA_MODEL}") from exc
        raise LLMError(f"Ollama error: {exc.error}") from exc
    except Exception as exc:
        logger.error("Unexpected error while calling Ollama: %s", exc)
        if "connect" in str(exc).lower():
            raise LLMError(
                "Ollama is not running. Start Ollama and try again."
            ) from exc
        raise LLMError(f"LLM error: {exc}") from exc
