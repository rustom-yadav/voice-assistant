import { spawn, execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { app, BrowserWindow } from "electron";

const __dirname = import.meta.dirname || path.dirname(fileURLToPath(import.meta.url));

let mainWindow = null;
let backendProcess = null;

function startBackend() {
  const backendDir = path.join(__dirname, "..", "backend");
  const pythonPath = path.join(backendDir, ".venv", "Scripts", "python.exe");
  const args = ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765"];

  console.log(`Starting backend: ${pythonPath} in ${backendDir}`);
  backendProcess = spawn(pythonPath, args, { cwd: backendDir });

  backendProcess.stdout.on("data", (data) => {
    console.log(`[Python]: ${data}`.trim());
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[Python]: ${data}`.trim());
  });

  backendProcess.on("exit", (code, signal) => {
    console.log(`Python backend exited with code ${code}, signal ${signal}`);
    backendProcess = null;
  });
}

function stopBackend() {
  if (!backendProcess) {
    return;
  }

  const pid = backendProcess.pid;
  console.log(`Stopping Python backend (PID: ${pid})...`);

  try {
    if (process.platform === "win32") {
      execSync(`taskkill /pid ${pid} /T /F`);
    } else {
      backendProcess.kill();
    }
  } catch (err) {
    console.warn(`Error during backend termination: ${err.message}`);
    if (backendProcess) {
      backendProcess.kill();
    }
  } finally {
    backendProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 700,
    title: "Local Voice Assistant",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopBackend();
});
