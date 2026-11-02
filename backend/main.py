"""FastAPI server providing health and WebSocket endpoints."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from config import HOST, MSG_START, MSG_STOP, MSG_SUGGEST, PORT
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from session import Session
from stt import Transcriber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load models once at startup before accepting traffic."""
    logger.info("Loading speech-to-text model on startup...")
    app.state.transcriber = Transcriber()
    logger.info("Server ready to accept WebSocket connections.")
    yield
    logger.info("Server shutdown complete.")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check() -> dict[str, bool]:
    """Health check endpoint to verify server readiness."""
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint managing client commands and streaming events."""
    await websocket.accept()
    logger.info("Client connected to WebSocket.")
    session = Session(websocket, app.state.transcriber)
    try:
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")
            if msg_type == MSG_START:
                await session.start()
            elif msg_type == MSG_STOP:
                await session.stop()
            elif msg_type == MSG_SUGGEST:
                question = msg.get("question", "")
                await session.suggest(question)
            else:
                logger.warning("Unrecognized message type: %s", msg_type)
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("WebSocket connection exception: %s", exc)
    finally:
        await session.close()


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)

