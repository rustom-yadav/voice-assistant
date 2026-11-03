import { execSync, spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { app, BrowserWindow, dialog } from "electron";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

let mainWindow = null;
let backendProcess = null;

function startBackend() {
  if (backendProcess) {
    return;
  }
  const backendDir = path.join(__dirname, "..", "backend");
  const isWindows = process.platform === "win32";
  const pythonPath = path.join(
    backendDir,
    ".venv",
    isWindows ? "Scripts/python.exe" : "bin/python"
  );
  const args = ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765"];

  console.log(`Starting backend: ${pythonPath}`);
  backendProcess = spawn(pythonPath, args, { cwd: backendDir });

  backendProcess.stdout.on("data", (data) => {
    console.log(`[Python]: ${data}`.trim());
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[Python]: ${data}`.trim());
  });

  backendProcess.on("exit", (code, signal) => {
    console.log(`Python backend exited (code: ${code}, signal: ${signal})`);
    backendProcess = null;
  });

  
  backendProcess.on("error", (err) => {
    dialog.showErrorBox(
      "Backend could not start",
      `${err.message}\n\nRun "uv sync" inside the backend folder first.`,
    );
    backendProcess = null;
  });
}

function stopBackend() {
  if (!backendProcess) {
    return;
  }

  console.log(`Stopping Python backend (PID: ${backendProcess.pid})...`);
  try {
    if (process.platform === "win32") {
      execSync(`taskkill /pid ${backendProcess.pid} /T /F`, { stdio: "ignore" });
    } else {
      backendProcess.kill();
    }
  } catch {
    // Process already terminated
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
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopBackend();
});
