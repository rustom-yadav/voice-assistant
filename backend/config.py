"""Configuration constants for the local voice assistant backend."""

# Server settings
HOST = "127.0.0.1"
PORT = 8765

# Audio capture settings
SAMPLE_RATE = 16000
BLOCK_MS = 30  # Audio block size in milliseconds

# Whisper STT settings
WHISPER_MODEL = "small.en"  # Model size or local directory path
WHISPER_DEVICE = "cpu"  # "cuda" if NVIDIA GPU is available
WHISPER_COMPUTE_TYPE = "int8"

# Ollama LLM settings
OLLAMA_MODEL = "llama3.2:3b"

# Voice Activity Detection (VAD) / Silence settings
SILENCE_RMS_THRESHOLD = 0.01  # Audio RMS below this value is treated as silence
SILENCE_SECONDS = 0.8  # Duration of silence to mark the end of an utterance
MIN_UTTERANCE_SECONDS = 0.3  # Shorter sounds (e.g. coughs, clicks) are discarded
MAX_UTTERANCE_SECONDS = 15.0  # Maximum length before forcing an utterance split
PRE_ROLL_SECONDS = 0.3  # Audio buffer preserved prior to detected speech start

# Assistant prompt
SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the question clearly in simple English, "
    "in a few short sentences. If the text has several lines, answer the last question."
)

# WebSocket message types (UI -> Backend)
MSG_START = "start"
MSG_STOP = "stop"
MSG_SUGGEST = "suggest"

# WebSocket message types (Backend -> UI)
MSG_STATUS = "status"
MSG_TRANSCRIPT = "transcript"
MSG_ANSWER_TOKEN = "answer_token"
MSG_ANSWER_DONE = "answer_done"
MSG_ERROR = "error"
