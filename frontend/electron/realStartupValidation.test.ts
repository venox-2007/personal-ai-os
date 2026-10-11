import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import http from "node:http";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendDir, "..");

function isProcessAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function killProcessTree(pid: number): void {
  try {
    if (process.platform === "win32") {
      spawn("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      process.kill(pid, "SIGKILL");
    }
  } catch {}
}

async function getPortPid(port: number): Promise<number | null> {
  return new Promise((resolve) => {
    if (process.platform !== "win32") return resolve(null);
    const proc = spawn("netstat", ["-ano", "-p", "tcp"], { stdio: ["ignore", "pipe", "ignore"] });
    let out = "";
    proc.stdout.on("data", (d) => (out += d.toString()));
    proc.on("close", () => {
      const lines = out.split("\n");
      for (const line of lines) {
        if (line.includes(`127.0.0.1:${port}`) && line.includes("LISTENING")) {
          const parts = line.trim().split(/\s+/);
          const pid = parseInt(parts[parts.length - 1], 10);
          if (!isNaN(pid)) return resolve(pid);
        }
      }
      resolve(null);
    });
  });
}

async function httpGet(urlStr: string, timeoutMs = 5000): Promise<{ status: number; body: string }> {
  return new Promise((resolve, reject) => {
    const url = new URL(urlStr);
    const req = http.get(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname + url.search,
        timeout: timeoutMs,
      },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve({ status: res.statusCode || 0, body: data }));
      }
    );
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Timeout"));
    });
    req.on("error", reject);
  });
}

async function ensurePortsClean(): Promise<void> {
  for (const port of [11434, 8000]) {
    const pid = await getPortPid(port);
    if (pid) {
      console.log(`[Cleanup] Releasing lingering PID ${pid} on port ${port}...`);
      killProcessTree(pid);
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
}

// Master sequential test runner
test("Real Windows Startup & Lifecycle Scenarios", async (t) => {
  await ensurePortsClean();

  // SCENARIO 1, 9, 10
  await t.test("Scenario 1, 9, 10: Real Electron cold start, process ownership, shutdown, and relaunch", async () => {
    const playwright = await import("playwright");
    const electron = (playwright as any)._electron;

    console.log("\n--- Scenario 1: Cold Start ---");
    const electronApp = await electron.launch({
      args: ["."],
      cwd: frontendDir,
      env: { ...process.env, NODE_ENV: "production" },
    });

    const electronPid = electronApp.process().pid;
    console.log(`[Scenario 1] Electron PID: ${electronPid}`);

    let ollamaPid: number | null = null;
    let backendPid: number | null = null;

    try {
      const window = await electronApp.firstWindow();
      await window.waitForSelector("header", { timeout: 15000 });

      // Poll until Electron reports complete readiness
      let isReady = false;
      let lastStatus: any = null;
      for (let i = 0; i < 40; i++) {
        lastStatus = await window.evaluate(async () => {
          return await (window as any).desktopApi?.getStartupStatus?.();
        });
        if (lastStatus?.isComplete === true) {
          isReady = true;
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }

      console.log(`[Scenario 1] Startup completed with status:`, lastStatus);
      assert.ok(isReady, "All services must reach ready status");

      // Verify HTTP responses
      const ollamaRes = await httpGet("http://127.0.0.1:11434/");
      assert.equal(ollamaRes.status, 200);

      const backendRes = await httpGet("http://127.0.0.1:8000/api/health");
      assert.equal(backendRes.status, 200);

      ollamaPid = await getPortPid(11434);
      backendPid = await getPortPid(8000);
      console.log(`[Scenario 1] Active PIDs -> Ollama: ${ollamaPid}, FastAPI: ${backendPid}`);
      assert.ok(ollamaPid && ollamaPid > 0);
      assert.ok(backendPid && backendPid > 0);

      console.log("\n--- Scenario 9: Application Shutdown & Process Cleanup ---");
      await electronApp.close();
      await new Promise((r) => setTimeout(r, 3000));

      const ollamaAlive = ollamaPid ? isProcessAlive(ollamaPid) : false;
      const backendAlive = backendPid ? isProcessAlive(backendPid) : false;
      console.log(`[Scenario 9] Process status after exit -> Ollama alive: ${ollamaAlive}, Backend alive: ${backendAlive}`);
      assert.equal(ollamaAlive, false, "App-owned Ollama must be killed on exit");
      assert.equal(backendAlive, false, "App-owned FastAPI backend must be killed on exit");
    } catch (err) {
      await electronApp.close();
      throw err;
    }

    console.log("\n--- Scenario 10: Relaunch Electron & Repeated Startup ---");
    const electronApp2 = await electron.launch({
      args: ["."],
      cwd: frontendDir,
      env: { ...process.env, NODE_ENV: "production" },
    });

    try {
      const window2 = await electronApp2.firstWindow();
      await window2.waitForSelector("header", { timeout: 15000 });

      let isReady2 = false;
      for (let i = 0; i < 40; i++) {
        const s = await window2.evaluate(async () => {
          return await (window as any).desktopApi?.getStartupStatus?.();
        });
        if (s?.isComplete === true) {
          isReady2 = true;
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
      assert.ok(isReady2, "Relaunch must succeed without stale lock errors");
    } finally {
      await electronApp2.close();
      await new Promise((r) => setTimeout(r, 3000));
    }
  });

  // SCENARIO 2: External Ollama adoption
  await t.test("Scenario 2: External Ollama adoption without termination", async () => {
    await ensurePortsClean();

    const ollamaExe = path.join(process.env.LOCALAPPDATA || "", "Programs", "Ollama", "ollama.exe");
    const externalOllama = spawn(ollamaExe, ["serve"], {
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    });
    const externalOllamaPid = externalOllama.pid;
    console.log(`\n--- Scenario 2: Started external Ollama PID: ${externalOllamaPid} ---`);

    // Wait for Ollama to become responsive
    let ready = false;
    for (let i = 0; i < 30; i++) {
      try {
        const res = await httpGet("http://127.0.0.1:11434/");
        if (res.status === 200) { ready = true; break; }
      } catch {}
      await new Promise((r) => setTimeout(r, 300));
    }
    assert.ok(ready, "External Ollama must respond on port 11434");

    const playwright = await import("playwright");
    const electron = (playwright as any)._electron;

    try {
      const electronApp = await electron.launch({
        args: ["."],
        cwd: frontendDir,
        env: { ...process.env, NODE_ENV: "production" },
      });

      try {
        const window = await electronApp.firstWindow();
        await window.waitForSelector("header", { timeout: 15000 });

        let adopted = false;
        for (let i = 0; i < 20; i++) {
          const s = await window.evaluate(async () => {
            return await (window as any).desktopApi?.getStartupStatus?.();
          });
          if (s?.ollama?.status === "ready") {
            console.log(`[Scenario 2] Ollama status:`, s.ollama);
            assert.ok(s.ollama.message?.includes("external"));
            adopted = true;
            break;
          }
          await new Promise((r) => setTimeout(r, 500));
        }
        assert.ok(adopted, "Ollama must be detected as externally running");
      } finally {
        await electronApp.close();
        await new Promise((r) => setTimeout(r, 3000));
      }

      // External Ollama MUST still be alive!
      const stillAlive = externalOllamaPid ? isProcessAlive(externalOllamaPid) : false;
      console.log(`[Scenario 2] External Ollama PID ${externalOllamaPid} alive after Electron exit: ${stillAlive}`);
      assert.equal(stillAlive, true, "Externally spawned Ollama must NOT be terminated by Electron");
    } finally {
      if (externalOllamaPid) killProcessTree(externalOllamaPid);
      await new Promise((r) => setTimeout(r, 1000));
    }
  });

  // SCENARIO 3: External FastAPI adoption
  await t.test("Scenario 3: External FastAPI adoption without duplicate process", async () => {
    await ensurePortsClean();

    const pythonExe = path.join(repoRoot, "backend", ".venv", "Scripts", "python.exe");
    const externalBackend = spawn(pythonExe, ["-m", "uvicorn", "app.main:app", "--port", "8000"], {
      cwd: path.join(repoRoot, "backend"),
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    });
    const externalBackendPid = externalBackend.pid;
    console.log(`\n--- Scenario 3: Started external FastAPI PID: ${externalBackendPid} ---`);

    let ready = false;
    for (let i = 0; i < 40; i++) {
      try {
        const res = await httpGet("http://127.0.0.1:8000/api/health");
        if (res.status === 200) { ready = true; break; }
      } catch {}
      await new Promise((r) => setTimeout(r, 300));
    }
    assert.ok(ready, "External FastAPI must respond on port 8000");

    const playwright = await import("playwright");
    const electron = (playwright as any)._electron;

    try {
      const electronApp = await electron.launch({
        args: ["."],
        cwd: frontendDir,
        env: { ...process.env, NODE_ENV: "production" },
      });

      try {
        const window = await electronApp.firstWindow();
        await window.waitForSelector("header", { timeout: 15000 });

        let adopted = false;
        for (let i = 0; i < 30; i++) {
          const s = await window.evaluate(async () => {
            return await (window as any).desktopApi?.getStartupStatus?.();
          });
          if (s?.backend?.status === "ready") {
            console.log(`[Scenario 3] Backend status:`, s.backend);
            assert.ok(s.backend.message?.includes("external"));
            adopted = true;
            break;
          }
          await new Promise((r) => setTimeout(r, 500));
        }
        assert.ok(adopted, "Backend must be detected as externally running");
      } finally {
        await electronApp.close();
        await new Promise((r) => setTimeout(r, 3000));
      }

      // External backend MUST still be alive!
      const stillAlive = externalBackendPid ? isProcessAlive(externalBackendPid) : false;
      console.log(`[Scenario 3] External Backend PID ${externalBackendPid} alive after Electron exit: ${stillAlive}`);
      assert.equal(stillAlive, true, "Externally spawned Backend must NOT be terminated by Electron");
    } finally {
      if (externalBackendPid) killProcessTree(externalBackendPid);
      await new Promise((r) => setTimeout(r, 1000));
    }
  });

  // SCENARIO 5: Port conflict with unrelated foreign service
  await t.test("Scenario 5: Port 8000 occupied by foreign service is not killed", async () => {
    await ensurePortsClean();

    const foreignServer = http.createServer((req, res) => {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Unrelated foreign app");
    });

    await new Promise<void>((resolve) => foreignServer.listen(8000, "127.0.0.1", () => resolve()));
    console.log("\n--- Scenario 5: Foreign service listening on port 8000 ---");

    const playwright = await import("playwright");
    const electron = (playwright as any)._electron;

    try {
      const electronApp = await electron.launch({
        args: ["."],
        cwd: frontendDir,
        env: { ...process.env, NODE_ENV: "production" },
      });

      try {
        const window = await electronApp.firstWindow();
        await window.waitForSelector("div[role='status']", { timeout: 15000 });

        let errorReported = false;
        for (let i = 0; i < 20; i++) {
          const s = await window.evaluate(async () => {
            return await (window as any).desktopApi?.getStartupStatus?.();
          });
          if (s?.hasError === true) {
            console.log(`[Scenario 5] Error reported correctly:`, s.errorMessage);
            assert.match(s.errorMessage || "", /Port 8000 is already occupied/i);
            errorReported = true;
            break;
          }
          await new Promise((r) => setTimeout(r, 500));
        }
        assert.ok(errorReported, "Error must be reported for port conflict");

        // Foreign service must still be alive and responding!
        const res = await httpGet("http://127.0.0.1:8000/");
        assert.equal(res.status, 404);
        assert.equal(res.body, "Unrelated foreign app");
        console.log(`[Scenario 5] Foreign service was safely preserved.`);
      } finally {
        await electronApp.close();
      }
    } finally {
      await new Promise<void>((resolve) => foreignServer.close(() => resolve()));
    }
  });

  // SCENARIO 4: Missing model reports issue and recovery instructions
  await t.test("Scenario 4: Missing qwen3:4b reports error and recovery instructions", async () => {
    await ensurePortsClean();

    // Start a mock Ollama server that returns tags WITHOUT qwen3:4b
    const mockOllama = http.createServer((req, res) => {
      if (req.url === "/") {
        res.writeHead(200);
        res.end("Ollama is running");
      } else if (req.url === "/api/tags") {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ models: [{ name: "llama3:latest" }] }));
      } else {
        res.writeHead(404);
        res.end();
      }
    });

    await new Promise<void>((resolve) => mockOllama.listen(11434, "127.0.0.1", () => resolve()));
    console.log("\n--- Scenario 4: Mock Ollama running without qwen3:4b ---");

    const playwright = await import("playwright");
    const electron = (playwright as any)._electron;

    try {
      const electronApp = await electron.launch({
        args: ["."],
        cwd: frontendDir,
        env: { ...process.env, NODE_ENV: "production" },
      });

      try {
        const window = await electronApp.firstWindow();
        await window.waitForSelector("div[role='status']", { timeout: 15000 });

        let reported = false;
        for (let i = 0; i < 20; i++) {
          const s = await window.evaluate(async () => {
            return await (window as any).desktopApi?.getStartupStatus?.();
          });
          if (s?.hasError === true && s?.step === "failed") {
            console.log(`[Scenario 4] Missing model reported:`, s.errorMessage);
            console.log(`[Scenario 4] Recovery hint provided:`, s.recoveryHint);
            assert.match(s.errorMessage || "", /Required.*model.*missing/i);
            assert.match(s.recoveryHint || "", /ollama pull qwen3:4b/i);
            reported = true;
            break;
          }
          await new Promise((r) => setTimeout(r, 500));
        }
        assert.ok(reported, "Missing model must trigger recoverable failure state");
      } finally {
        await electronApp.close();
      }
    } finally {
      await new Promise<void>((resolve) => mockOllama.close(() => resolve()));
    }
  });

  // SCENARIO 6, 7 & 8: Service failure, bounded timeout, no orphan, and retry recovery
  await t.test("Scenario 6, 7 & 8: Recoverable failures, no orphan process, and retry startup", async () => {
    await ensurePortsClean();

    // Test coordinator retry directly through coordinator instance
    const { StartupCoordinator } = await import("../dist-electron/startupCoordinator.js");
    
    // Simulate FastAPI failing to start by pointing to invalid python binary
    console.log("\n--- Scenario 7: FastAPI failure handling ---");
    const coordinator = new StartupCoordinator({
      pythonExecutablePath: path.join(repoRoot, "nonexistent", "python.exe"),
      readinessTimeoutMs: 15000,
      pollIntervalMs: 200,
    });

    const success = await coordinator.orchestrate();
    assert.equal(success, false, "Orchestration must fail safely when python binary is invalid");

    const state = coordinator.getState();
    assert.equal(state.hasError, true);
    assert.equal(state.backend.status, "error");
    assert.equal(coordinator.hasOwnedBackendProcess(), false, "Must not hold orphan process reference");
    console.log(`[Scenario 7] Failure cleanly recorded without indefinite hang:`, state.errorMessage);

    // Scenario 8: Correcting the configuration and retrying
    console.log("\n--- Scenario 8: Retry startup after correcting failure ---");
    // Point python path back to valid python
    (coordinator as any).config.pythonExecutablePath = path.join(repoRoot, "backend", ".venv", "Scripts", "python.exe");
    const retrySuccess = await coordinator.orchestrate();
    assert.equal(retrySuccess, true, "Startup retry must succeed once failure condition is resolved");

    const recoveredState = coordinator.getState();
    assert.equal(recoveredState.isComplete, true);
    assert.equal(recoveredState.hasError, false);
    console.log(`[Scenario 8] Startup retry successfully recovered:`, recoveredState.step);

    await coordinator.shutdown();
  });

  await ensurePortsClean();
});

