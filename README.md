# Local Voice Assistant

A fast, private, desktop voice assistant running entirely **locally and offline**. It captures microphone audio, transcribes speech in real time, allows editing of the transcribed text, and streams answers progressively from a local language model.

No cloud APIs. No data leaves your machine.

> **Platform Note:** This project has been **tested and verified on Windows**. The codebase is written cross-platform (supporting both Windows and POSIX pathing and process lifecycles) and is expected to work on **macOS** and **Linux** as well.

---

## Architecture & Tech Stack

```
┌─────────────────────────────────┐        WebSocket (JSON)        ┌──────────────────────────────────────┐
│       Electron (UI Shell)       │ ◄────────────────────────────► │        Python Backend (FastAPI)      │
│  - Start / Stop commands        │    ws://127.0.0.1:8765/ws      │                                      │
│  - Editable Transcript box      │                                │  - sounddevice (direct mic capture)  │
│  - Suggest Answer button        │  (Sends control commands only, │  - VAD (Voice Activity Detection)    │
│  - Progressive Answer box       │    no audio data over socket)  │  - faster-whisper (small.en, int8)   │
└─────────────────────────────────┘                                │  - Ollama (llama3.2:3b streaming)    │
   main.js manages Python lifecycle                                └──────────────────────────────────────┘
```

> **Important Design Decision: Why the microphone is captured in Python, not Electron**
> - **Electron is UI-only:** The Electron frontend does **not** access the browser microphone or stream audio. It strictly sends lightweight JSON control instructions (`start`, `stop`, `suggest`) to the backend over WebSocket.
> - **Backend directly accesses the microphone:** Because the Python backend runs locally on the user's machine, it captures audio directly at the hardware/OS level using `sounddevice` (16 kHz mono). It detects speech and silence (VAD) and feeds speech directly into `faster-whisper` to generate the transcription.
> - **Benefits:** This eliminates complex browser audio plumbing (AudioWorklets, WebRTC, resampling, and streaming high-bandwidth PCM over WebSockets), keeping the frontend clean and ensuring zero audio latency.

| Layer | Technology | Purpose |
|---|---|---|
| **Desktop Shell** | Electron | Lightweight native desktop window (800x700) |
| **Frontend** | Vanilla HTML, CSS, JavaScript | No React or bundlers; direct, responsive UI |
| **Backend** | Python 3.12 (managed via `uv`) + FastAPI + uvicorn | WebSocket server, asynchronous job queues |
| **Audio Capture** | `sounddevice` + NumPy | Direct 16 kHz mono float32 stream with pre-roll buffer |
| **Speech-to-Text** | `faster-whisper` (`small.en`, `int8` CPU) | High-accuracy local speech recognition |
| **Local LLM** | Ollama (`llama3.2:3b`) | Streaming token-by-token text generation |
| **Communication** | WebSocket (`ws://127.0.0.1:8765/ws`) | Single bidirectional real-time JSON protocol |

---

## Prerequisites

Make sure the following tools are installed on your machine before starting:

### 1. Python & uv
- **Python 3.12** (`3.12.10` recommended): Verify with `python --version`.
- **uv** (ultra-fast Python project & environment manager):
  ```powershell
  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  Verify with `uv --version`.

### 2. Node.js & npm
- **Node.js** (`v20+` or `v24` LTS recommended): Verify with `node -v`.
- **npm** (`v10+` or `v11` latest): Verify with `npm -v`.

### 3. Ollama (Local LLM)
- Download and install the **Ollama Desktop App** from [ollama.com](https://ollama.com).
- Make sure Ollama is running (it runs in the system tray automatically, or you can run `ollama serve`).
- Pull the required model (`llama3.2:3b`):
  ```bash
  ollama pull llama3.2:3b
  ```
- *(Optional)* Verify the model in terminal:
  ```bash
  ollama run llama3.2:3b "Hello, are you running locally?"
  ```

### 4. Microphone
- A working microphone connected and enabled in your OS privacy settings.

---

## Setup & Installation

### 1. Set up the Python Backend
From the project root:
```bash
cd backend
uv sync
```
This automatically creates a local `.venv` and installs all required Python dependencies (`fastapi`, `uvicorn`, `faster-whisper`, `sounddevice`, `numpy`, `ollama`).

> **Note on Whisper model:** The `small.en` model downloads automatically on the first run and caches locally in your user profile (`~/.cache/huggingface/hub`). For completely air-gapped environments, set `WHISPER_MODEL` in `backend/config.py` to a local folder containing the model weights.

### 2. Set up the Electron Frontend
```bash
cd ../electron
npm install
```

---

## Running the Application

To launch the desktop assistant:

```bash
cd electron
npm start
```

Electron automatically spawns the Python backend in the background and shuts it down cleanly when the window is closed.

---

## How to Use

1. **Wait for Connection:**
   The status indicator initially shows gray (`Starting backend... (loading models)`). Once the backend finishes loading Whisper into memory (typically 1–2 seconds), the status dot turns green (`Connected`).

2. **Start Listening:**
   Click **Start**. The indicator turns red (`Listening...`).

3. **Speak:**
   Speak a question or sentence into your microphone. When you pause (0.8s silence), the audio is automatically processed and the text appears in the **Transcript** box.

4. **Edit Transcript (Optional):**
   The transcript box is fully editable. You can edit errors, refine your prompt, or type text manually.

5. **Stop Listening:**
   Click **Stop** to turn off the microphone.

6. **Suggest Answer:**
   Click **Suggest Answer**. The local Ollama model will stream its response token by token into the **Answer** box.

---

## Project Structure

```
voice-assistant/
├── README.md                  # Setup and usage guide
├── .gitignore                 # Configured for Python, Node, models, and audio
├── backend/
│   ├── pyproject.toml         # uv managed project dependencies
│   ├── config.py              # Server, audio, Whisper, and LLM constants
│   ├── audio.py               # Microphone capture and silence detection (VAD)
│   ├── stt.py                 # faster-whisper STT wrapper
│   ├── llm.py                 # Ollama async streaming wrapper
│   ├── session.py             # WebSocket session and async queue pipeline
│   ├── main.py                # FastAPI app, lifespan model loader, /ws endpoint
│   
└── electron/
    ├── package.json           # Electron configuration (ES Module)
    ├── main.js                # Window and backend lifecycle management
    └── renderer/
        ├── index.html         # Single-column desktop layout
        ├── style.css          # Minimal, clean responsive styles
        └── app.js             # WebSocket client and UI state machine
```

---

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| **Ollama is not running** | The Ollama service is stopped. | Start Ollama from your desktop application launcher or run `ollama serve` in a terminal before clicking Suggest Answer. |
| **Model not found** | The `llama3.2:3b` model has not been downloaded yet. | Run `ollama pull llama3.2:3b` in your terminal. |
| **No microphone found** | PortAudio cannot access an audio input device. | Ensure a microphone is connected. Check Windows Privacy Settings: *Settings > Privacy & Security > Microphone* and ensure "Let apps access your microphone" is turned **On**. |
| **Port 8765 already in use** | A previous backend process did not terminate. | Run `netstat -ano \| findstr 8765` to find the process PID, then terminate it using `taskkill /pid <PID> /F`, or restart your terminal. |
| **Backend could not start popup** | Python virtual environment is missing. | Run `cd backend` followed by `uv sync`. |

---

---
## Author 

Rustom Yadav

## License

MIT

