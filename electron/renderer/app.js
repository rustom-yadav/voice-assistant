const WS_URL = "ws://127.0.0.1:8765/ws";
const RECONNECT_DELAY_MS = 1000;

const MSG = {
  START: "start",
  STOP: "stop",
  SUGGEST: "suggest",
  STATUS: "status",
  TRANSCRIPT: "transcript",
  ANSWER_TOKEN: "answer_token",
  ANSWER_DONE: "answer_done",
  ERROR: "error",
};

const state = {
  connected: false,
  listening: false,
  generating: false,
  errorMessage: "",
};

let socket = null;
let reconnectTimer = null;

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const btnSuggest = document.getElementById("btn-suggest");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const transcriptInput = document.getElementById("transcript-input");
const answerOutput = document.getElementById("answer-output");
const errorMessage = document.getElementById("error-message");

function connect() {
  if (
    socket &&
    (socket.readyState === WebSocket.CONNECTING ||
      socket.readyState === WebSocket.OPEN)
  ) {
    return;
  }

  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    state.connected = true;
    state.errorMessage = "";
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    render();
  };

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleMessage(msg);
    } catch (err) {
      console.error("Failed to parse incoming WebSocket message:", err);
    }
  };

  socket.onclose = () => {
    state.connected = false;
    state.listening = false;
    state.generating = false;
    render();
    scheduleReconnect();
  };

  socket.onerror = (err) => {
    console.warn("WebSocket connection error:", err);
    socket.close();
  };
}

function scheduleReconnect() {
  if (reconnectTimer) {
    return;
  }
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_DELAY_MS);
}

function handleMessage(msg) {
  switch (msg.type) {
    case MSG.STATUS:
      state.listening = Boolean(msg.listening);
      break;

    case MSG.TRANSCRIPT:
      appendTranscript(msg.text);
      break;

    case MSG.ANSWER_TOKEN:
      state.errorMessage = "";
      answerOutput.textContent += msg.text || "";
      break;

    case MSG.ANSWER_DONE:
      state.generating = false;
      break;

    case MSG.ERROR:
      state.generating = false;
      state.errorMessage = msg.message || "An error occurred.";
      break;

    default:
      console.warn("Unknown message received:", msg);
      break;
  }
  render();
}

function appendTranscript(text) {
  if (!text) {
    return;
  }
  const current = transcriptInput.value.trim();
  transcriptInput.value = current ? `${current}\n${text}` : text;
  transcriptInput.scrollTop = transcriptInput.scrollHeight;
}

function render() {
  const hasTranscript = transcriptInput.value.trim().length > 0;

  btnStart.disabled = !state.connected || state.listening;
  btnStop.disabled = !state.connected || !state.listening;
  btnSuggest.disabled = !state.connected || state.generating || !hasTranscript;

  statusDot.className = "dot";
  if (!state.connected) {
    statusDot.classList.add("dot-disconnected");
    statusText.textContent = "Starting backend... (loading models)";
  } else if (state.listening) {
    statusDot.classList.add("dot-listening");
    statusText.textContent = "Listening...";
  } else {
    statusDot.classList.add("dot-connected");
    statusText.textContent = "Connected";
  }

  if (state.errorMessage) {
    errorMessage.textContent = state.errorMessage;
    errorMessage.classList.add("visible");
  } else {
    errorMessage.textContent = "";
    errorMessage.classList.remove("visible");
  }
}

function onStart() {
  if (!state.connected || state.listening) {
    return;
  }
  state.errorMessage = "";
  sendJson({ type: MSG.START });
}

function onStop() {
  if (!state.connected || !state.listening) {
    return;
  }
  sendJson({ type: MSG.STOP });
}

function onSuggest() {
  const question = transcriptInput.value.trim();
  if (!state.connected || state.generating || !question) {
    return;
  }

  answerOutput.textContent = "";
  state.generating = true;
  state.errorMessage = "";
  render();

  sendJson({ type: MSG.SUGGEST, question });
}

function sendJson(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

btnStart.addEventListener("click", onStart);
btnStop.addEventListener("click", onStop);
btnSuggest.addEventListener("click", onSuggest);
transcriptInput.addEventListener("input", () => {
  render();
});

render();
connect();

