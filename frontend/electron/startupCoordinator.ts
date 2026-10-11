import { spawn, ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import net from "node:net";
import http from "node:http";
import { StartupConfig, StartupProgressState, ServiceStep } from "./types";

export type StartupProgressCallback = (state: StartupProgressState) => void;

export class StartupCoordinator {
  private config: StartupConfig;
  private state: StartupProgressState;
  private listeners: Set<StartupProgressCallback> = new Set();
  private ownedOllamaProcess: ChildProcess | null = null;
  private ownedBackendProcess: ChildProcess | null = null;
  private isOrchestrating = false;

  constructor(customConfig?: Partial<StartupConfig>) {
    const rootDir = path.resolve(__dirname, "..", "..");
    const defaultPython =
      process.platform === "win32"
        ? path.join(rootDir, "backend", ".venv", "Scripts", "python.exe")
        : path.join(rootDir, "backend", ".venv", "bin", "python");

    this.config = {
      ollamaEndpoint: "http://127.0.0.1:11434",
      requiredModel: "qwen3:4b",
      backendHealthEndpoint: "http://127.0.0.1:8000/api/health",
      backendHost: "127.0.0.1",
      backendPort: 8000,
      pythonExecutablePath: defaultPython,
      backendWorkingDir: path.join(rootDir, "backend"),
      readinessTimeoutMs: 30000,
      pollIntervalMs: 500,
      ...customConfig,
    };

    this.state = this.getInitialState();
  }

  public getInitialState(): StartupProgressState {
    return {
      step: "checking_ollama",
      ollama: { status: "pending", message: "Checking Ollama status..." },
      model: { status: "pending", message: `Waiting for ${this.config.requiredModel} check...` },
      backend: { status: "pending", message: "Waiting for FastAPI backend check..." },
      isComplete: false,
      hasError: false,
    };
  }

  public getState(): StartupProgressState {
    return { ...this.state };
  }

  public onProgress(callback: StartupProgressCallback): () => void {
    this.listeners.add(callback);
    callback(this.getState());
    return () => {
      this.listeners.delete(callback);
    };
  }

  private updateState(updater: (prev: StartupProgressState) => Partial<StartupProgressState>): void {
    this.state = {
      ...this.state,
      ...updater(this.state),
    };
    for (const listener of this.listeners) {
      try {
        listener(this.getState());
      } catch (err) {
        console.error("Error in startup progress listener:", err);
      }
    }
  }

  public async orchestrate(): Promise<boolean> {
    if (this.isOrchestrating) return false;
    this.isOrchestrating = true;

    try {
      this.state = this.getInitialState();
      this.updateState(() => ({ step: "checking_ollama" }));

      // 1. Check or start Ollama
      const ollamaReady = await this.ensureOllama();
      if (!ollamaReady) {
        return false;
      }

      // 2. Verify model availability
      this.updateState(() => ({
        step: "verifying_model",
        model: { status: "running", message: `Verifying ${this.config.requiredModel}...` },
      }));
      const modelReady = await this.verifyModel();
      if (!modelReady) {
        return false;
      }

      // 3. Check or start FastAPI backend
      this.updateState(() => ({
        step: "checking_backend",
        backend: { status: "running", message: "Checking backend readiness..." },
      }));
      const backendReady = await this.ensureBackend();
      if (!backendReady) {
        return false;
      }

      // 4. All services ready
      this.updateState((prev) => ({
        step: "ready",
        ollama: { ...prev.ollama, status: "ready" },
        model: { ...prev.model, status: "ready" },
        backend: { ...prev.backend, status: "ready" },
        isComplete: true,
        hasError: false,
      }));

      return true;
    } catch (err: any) {
      this.failStep("failed", "Unexpected startup orchestrator failure", err?.message || String(err));
      return false;
    } finally {
      this.isOrchestrating = false;
    }
  }

  // --- Step 1: Ollama ---
  private async ensureOllama(): Promise<boolean> {
    const isRunning = await this.pingOllama();
    if (isRunning) {
      this.updateState(() => ({
        ollama: { status: "ready", message: "Ollama is running (external)" },
      }));
      return true;
    }

    // Try starting Ollama
    this.updateState(() => ({
      step: "starting_ollama",
      ollama: { status: "running", message: "Starting local Ollama server..." },
    }));

    const ollamaExe = this.findOllamaExecutable();
    if (!ollamaExe) {
      this.failStep(
        "checking_ollama",
        "Ollama executable not found on this computer",
        "Please install Ollama from https://ollama.com/download or verify its installation path.",
        "Install Ollama from https://ollama.com/download",
        undefined,
        "https://ollama.com/download"
      );
      return false;
    }

    try {
      this.ownedOllamaProcess = spawn(ollamaExe, ["serve"], {
        detached: false,
        stdio: "ignore",
        windowsHide: true,
      });

      this.ownedOllamaProcess.on("error", (err) => {
        console.error("Owned Ollama process error:", err);
      });

      this.ownedOllamaProcess.on("exit", (code) => {
        console.warn(`Owned Ollama process exited with code ${code}`);
        this.ownedOllamaProcess = null;
      });
    } catch (err: any) {
      this.failStep(
        "starting_ollama",
        "Failed to launch Ollama process",
        err?.message || "Could not execute Ollama executable."
      );
      return false;
    }

    // Wait for Ollama readiness
    const ready = await this.waitForEndpoint(
      () => this.pingOllama(),
      this.config.readinessTimeoutMs,
      this.config.pollIntervalMs
    );

    if (!ready) {
      if (this.ownedOllamaProcess) {
        await this.terminateProcessGracefully(this.ownedOllamaProcess, "Ollama");
        this.ownedOllamaProcess = null;
      }
      this.failStep(
        "starting_ollama",
        "Ollama failed to respond within timeout",
        "Ollama was started but did not respond on port 11434 in time."
      );
      return false;
    }

    this.updateState(() => ({
      ollama: { status: "ready", message: "Ollama started and ready (app-owned)" },
    }));
    return true;
  }

  public async pingOllama(): Promise<boolean> {
    try {
      const url = new URL("/", this.config.ollamaEndpoint);
      const res = await this.fetchSimple(url.toString(), 1500);
      return res.status === 200 && res.body.includes("Ollama is running");
    } catch {
      return false;
    }
  }

  public findOllamaExecutable(): string | null {
    if (this.config.ollamaExecutablePath && fs.existsSync(this.config.ollamaExecutablePath)) {
      return this.config.ollamaExecutablePath;
    }

    const localAppData = process.env.LOCALAPPDATA;
    const candidates: string[] = [];

    if (localAppData) {
      candidates.push(path.join(localAppData, "Programs", "Ollama", "ollama.exe"));
    }
    const programFiles = process.env.ProgramFiles;
    if (programFiles) {
      candidates.push(path.join(programFiles, "Ollama", "ollama.exe"));
    }

    for (const p of candidates) {
      if (fs.existsSync(p)) return p;
    }
    return null;
  }

  // --- Step 2: Model Verification ---
  private async verifyModel(): Promise<boolean> {
    try {
      const url = new URL("/api/tags", this.config.ollamaEndpoint);
      const res = await this.fetchSimple(url.toString(), 3000);
      if (res.status !== 200) {
        this.failStep(
          "verifying_model",
          "Unable to query installed models from Ollama",
          `Ollama returned HTTP status ${res.status} when querying /api/tags.`
        );
        return false;
      }

      const data = JSON.parse(res.body);
      const models: any[] = data.models || [];
      const hasModel = models.some(
        (m: any) =>
          m.name === this.config.requiredModel ||
          m.name === `${this.config.requiredModel}:latest` ||
          m.name?.startsWith(this.config.requiredModel)
      );

      if (!hasModel) {
        this.failStep(
          "verifying_model",
          `Required AI model '${this.config.requiredModel}' is missing`,
          `Please open a terminal and run 'ollama pull ${this.config.requiredModel}' to download the model before starting Personal AI OS.`,
          `Run: ollama pull ${this.config.requiredModel}`,
          `ollama pull ${this.config.requiredModel}`,
          `https://ollama.com/library/${this.config.requiredModel.split(":")[0]}`
        );
        return false;
      }

      this.updateState(() => ({
        model: { status: "ready", message: `Model '${this.config.requiredModel}' verified` },
      }));
      return true;
    } catch (err: any) {
      this.failStep("verifying_model", "Failed to query Ollama model library", err?.message);
      return false;
    }
  }

  public resolveBackendTarget(): { executable: string; args: string[]; cwd?: string; isStandalone: boolean } | null {
    // 1. Explicit standalone executable configuration
    if (this.config.standaloneExecutablePath && fs.existsSync(this.config.standaloneExecutablePath)) {
      return {
        executable: this.config.standaloneExecutablePath,
        args: ["--host", this.config.backendHost, "--port", String(this.config.backendPort)],
        cwd: path.dirname(this.config.standaloneExecutablePath),
        isStandalone: true,
      };
    }

    // 2. Production installed application resources (NSIS / packaged desktop app)
    const resourcesPath = (process as any).resourcesPath;
    if (resourcesPath) {
      const packagedExe = path.join(resourcesPath, "backend", "personal_ai_backend.exe");
      if (fs.existsSync(packagedExe)) {
        const localAppData =
          process.env.LOCALAPPDATA ||
          (process.env.USERPROFILE ? path.join(process.env.USERPROFILE, "AppData", "Local") : "");
        const targetDataDir =
          process.env.PERSONAL_AI_DATA_DIR ||
          (localAppData ? path.join(localAppData, "PersonalAIOS") : undefined);
        const args = ["--host", this.config.backendHost, "--port", String(this.config.backendPort)];
        if (targetDataDir) {
          args.push("--data-dir", targetDataDir);
        }
        return {
          executable: packagedExe,
          args,
          cwd: path.dirname(packagedExe),
          isStandalone: true,
        };
      }
    }

    // 3. Development Python virtual environment
    const pythonExe = this.config.pythonExecutablePath;
    if (pythonExe && fs.existsSync(pythonExe)) {
      return {
        executable: pythonExe,
        args: [
          "-m",
          "uvicorn",
          "app.main:app",
          "--host",
          this.config.backendHost,
          "--port",
          String(this.config.backendPort),
        ],
        isStandalone: false,
      };
    }

    return null;
  }

  // --- Step 3: FastAPI Backend ---
  private async ensureBackend(): Promise<boolean> {
    const isHealthy = await this.pingBackendHealth();
    if (isHealthy) {
      this.updateState(() => ({
        backend: { status: "ready", message: "FastAPI backend already healthy (external)" },
      }));
      return true;
    }

    // Check for conflicting occupied port
    const portOccupied = await this.isPortInUse(this.config.backendPort, this.config.backendHost);
    if (portOccupied) {
      this.failStep(
        "starting_backend",
        `Port ${this.config.backendPort} is already occupied by an unrecognized process`,
        `Port ${this.config.backendPort} is in use, but does not respond to /api/health. Please close the conflicting application. Never terminates unknown processes.`
      );
      return false;
    }

    // Resolve executable target (standalone binary or Python venv)
    const target = this.resolveBackendTarget();
    if (!target) {
      this.failStep(
        "starting_backend",
        "Python virtual environment not found for backend",
        `Could not find backend executable or Python binary at ${this.config.pythonExecutablePath}. Please set up backend/.venv first.`
      );
      return false;
    }

    this.updateState(() => ({
      step: "starting_backend",
      backend: {
        status: "running",
        message: target.isStandalone
          ? "Starting standalone FastAPI backend..."
          : "Starting FastAPI backend process...",
      },
    }));

    try {
      this.ownedBackendProcess = spawn(target.executable, target.args, {
        cwd: (target as any).cwd || this.config.backendWorkingDir,
        detached: false,
        stdio: "ignore",
        windowsHide: true,
      });

      this.ownedBackendProcess.on("error", (err) => {
        console.error("Owned backend process error:", err);
      });

      this.ownedBackendProcess.on("exit", (code) => {
        console.warn(`Owned backend process exited with code ${code}`);
        this.ownedBackendProcess = null;
      });
    } catch (err: any) {
      this.failStep(
        "starting_backend",
        "Failed to launch FastAPI backend process",
        err?.message || "Could not spawn backend process."
      );
      return false;
    }

    this.updateState(() => ({
      step: "waiting_backend",
      backend: { status: "running", message: "Waiting for /api/health readiness..." },
    }));

    const ready = await this.waitForEndpoint(
      () => this.pingBackendHealth(),
      this.config.readinessTimeoutMs,
      this.config.pollIntervalMs
    );

    if (!ready) {
      if (this.ownedBackendProcess) {
        await this.terminateProcessGracefully(this.ownedBackendProcess, "backend");
        this.ownedBackendProcess = null;
      }
      this.failStep(
        "waiting_backend",
        "FastAPI backend failed to report healthy within timeout",
        "The backend process was started, but did not become ready in time."
      );
      return false;
    }

    this.updateState(() => ({
      backend: { status: "ready", message: "FastAPI backend healthy and ready (app-owned)" },
    }));
    return true;
  }

  public async pingBackendHealth(): Promise<boolean> {
    try {
      const res = await this.fetchSimple(this.config.backendHealthEndpoint, 1500);
      if (res.status !== 200) return false;
      const data = JSON.parse(res.body);
      return data.status === "ok";
    } catch {
      return false;
    }
  }

  private isPortInUse(port: number, host: string): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      socket.setTimeout(800);
      socket.once("error", () => {
        socket.destroy();
        resolve(false);
      });
      socket.once("timeout", () => {
        socket.destroy();
        resolve(false);
      });
      socket.connect(port, host, () => {
        socket.end();
        resolve(true);
      });
    });
  }

  private failStep(
    step: ServiceStep,
    errorMessage: string,
    details?: string,
    recoveryHint?: string,
    copyCommand?: string,
    externalUrl?: string
  ): void {
    const errorDetail = details ? `${errorMessage}: ${details}` : errorMessage;
    const targetKey = step === "verifying_model" ? "model" : step.includes("ollama") ? "ollama" : "backend";
    this.updateState(() => ({
      step: "failed",
      hasError: true,
      errorMessage: errorDetail,
      recoveryHint: recoveryHint || details,
      copyCommand,
      externalUrl,
      [targetKey]: {
        status: "error",
        error: errorDetail,
        recoveryHint: recoveryHint || details,
        copyCommand,
        externalUrl,
      },
    }));
  }

  private async waitForEndpoint(
    probe: () => Promise<boolean>,
    timeoutMs: number,
    intervalMs: number
  ): Promise<boolean> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (await probe()) return true;
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    return false;
  }

  private fetchSimple(targetUrl: string, timeoutMs: number): Promise<{ status: number; body: string }> {
    return new Promise((resolve, reject) => {
      const parsed = new URL(targetUrl);
      const req = http.request(
        {
          hostname: parsed.hostname,
          port: parsed.port,
          path: parsed.pathname + parsed.search,
          method: "GET",
          timeout: timeoutMs,
        },
        (res) => {
          let body = "";
          res.on("data", (chunk) => (body += chunk));
          res.on("end", () => resolve({ status: res.statusCode || 500, body }));
        }
      );

      req.on("timeout", () => {
        req.destroy();
        reject(new Error("Request timed out"));
      });
      req.on("error", reject);
      req.end();
    });
  }

  // --- Process Lifecycle and Cleanup ---
  private async terminateProcessGracefully(child: ChildProcess, name: string): Promise<void> {
    const pid = child.pid;
    if (!pid) return;
    console.log(`[StartupCoordinator] Stopping owned ${name} process (PID ${pid})...`);

    if (process.platform === "win32") {
      try {
        // 1. Request graceful termination first
        spawn("taskkill", ["/PID", String(pid), "/T"], { stdio: "ignore" });
      } catch (err) {
        console.warn(`[StartupCoordinator] Graceful taskkill request failed:`, err);
      }

      // 2. Poll up to 1.5s to see if process exited cleanly
      const exited = await new Promise<boolean>((resolve) => {
        let isGone = false;
        const check = setInterval(() => {
          try {
            process.kill(pid, 0);
          } catch {
            isGone = true;
            clearInterval(check);
            resolve(true);
          }
        }, 100);
        setTimeout(() => {
          clearInterval(check);
          resolve(isGone);
        }, 1500);
      });

      // 3. Bounded escalation: force kill only if still alive after timeout
      if (!exited) {
        console.warn(`[StartupCoordinator] PID ${pid} did not exit gracefully within timeout; escalating to force kill...`);
        try {
          spawn("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore" });
        } catch (err) {
          console.error(`[StartupCoordinator] Force kill error:`, err);
        }
      }
    } else {
      try {
        child.kill("SIGTERM");
        setTimeout(() => {
          try {
            if (!child.killed) child.kill("SIGKILL");
          } catch {}
        }, 1500);
      } catch (err) {
        console.error(`Error killing ${name}:`, err);
      }
    }
  }

  public async shutdown(): Promise<void> {
    console.log("[StartupCoordinator] Initiating shutdown for owned processes...");

    // 1. Terminate owned backend process
    if (this.ownedBackendProcess) {
      await this.terminateProcessGracefully(this.ownedBackendProcess, "backend");
      this.ownedBackendProcess = null;
    }

    // 2. Terminate owned Ollama process ONLY if this application spawned it
    if (this.ownedOllamaProcess) {
      await this.terminateProcessGracefully(this.ownedOllamaProcess, "Ollama");
      this.ownedOllamaProcess = null;
    }
  }

  // Getters for testing ownership assertions
  public hasOwnedBackendProcess(): boolean {
    return this.ownedBackendProcess !== null;
  }

  public hasOwnedOllamaProcess(): boolean {
    return this.ownedOllamaProcess !== null;
  }
}
