import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import net from "node:net";
import { StartupCoordinator } from "../dist-electron/startupCoordinator.js";

test("startup coordinator: initial state reflects pending services", () => {
  const coordinator = new StartupCoordinator();
  const state = coordinator.getState();

  assert.equal(state.step, "checking_ollama");
  assert.equal(state.isComplete, false);
  assert.equal(state.hasError, false);
  assert.equal(state.ollama.status, "pending");
  assert.equal(state.model.status, "pending");
  assert.equal(state.backend.status, "pending");
});

test("startup coordinator: listeners receive progress updates", () => {
  const coordinator = new StartupCoordinator();
  const updates: string[] = [];

  const unsubscribe = coordinator.onProgress((state) => {
    updates.push(state.step);
  });

  assert.ok(updates.length >= 1, "Initial state should be received immediately upon subscribing");
  unsubscribe();
});

test("startup coordinator: detects missing model and sets recovery hint without silent download", async () => {
  // Create a mock Ollama server that returns tags without qwen3:4b
  const mockServer = http.createServer((req, res) => {
    if (req.url === "/") {
      res.writeHead(200, { "Content-Type": "text/plain" });
      res.end("Ollama is running");
    } else if (req.url === "/api/tags") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ models: [{ name: "llama3:latest" }, { name: "mistral:latest" }] }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  await new Promise<void>((resolve) => mockServer.listen(0, "127.0.0.1", () => resolve()));
  const port = (mockServer.address() as net.AddressInfo).port;

  try {
    const coordinator = new StartupCoordinator({
      ollamaEndpoint: `http://127.0.0.1:${port}`,
      requiredModel: "qwen3:4b",
      readinessTimeoutMs: 1000,
      pollIntervalMs: 100,
    });

    const success = await coordinator.orchestrate();
    assert.equal(success, false, "Orchestration must fail when required model is not installed");

    const state = coordinator.getState();
    assert.equal(state.hasError, true);
    assert.equal(state.step, "failed");
    assert.equal(state.model.status, "error");
    assert.match(state.errorMessage || "", /Required.*model.*missing/i);
    assert.match(state.recoveryHint || "", /ollama pull qwen3:4b/i);
  } finally {
    await new Promise<void>((resolve) => mockServer.close(() => resolve()));
  }
});

test("startup coordinator: detects port conflict when port 8000 is occupied by non-backend server", async () => {
  // Mock an existing foreign service running on a port
  const foreignServer = http.createServer((req, res) => {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("foreign service not Personal AI");
  });

  await new Promise<void>((resolve) => foreignServer.listen(0, "127.0.0.1", () => resolve()));
  const port = (foreignServer.address() as net.AddressInfo).port;

  // Mock valid Ollama server with required model
  const ollamaServer = http.createServer((req, res) => {
    if (req.url === "/") {
      res.writeHead(200);
      res.end("Ollama is running");
    } else if (req.url === "/api/tags") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ models: [{ name: "qwen3:4b" }] }));
    }
  });
  await new Promise<void>((resolve) => ollamaServer.listen(0, "127.0.0.1", () => resolve()));
  const ollamaPort = (ollamaServer.address() as net.AddressInfo).port;

  try {
    const coordinator = new StartupCoordinator({
      ollamaEndpoint: `http://127.0.0.1:${ollamaPort}`,
      requiredModel: "qwen3:4b",
      backendPort: port,
      backendHealthEndpoint: `http://127.0.0.1:${port}/api/health`,
      readinessTimeoutMs: 500,
      pollIntervalMs: 100,
    });

    const success = await coordinator.orchestrate();
    assert.equal(success, false, "Must fail if port is occupied by unrelated process");

    const state = coordinator.getState();
    assert.equal(state.hasError, true);
    assert.equal(state.backend.status, "error");
    assert.match(state.errorMessage || "", /Port.*already occupied/i);
    // Crucially, coordinator must NOT have taken ownership of foreign process
    assert.equal(coordinator.hasOwnedBackendProcess(), false);
  } finally {
    await new Promise<void>((resolve) => foreignServer.close(() => resolve()));
    await new Promise<void>((resolve) => ollamaServer.close(() => resolve()));
  }
});

test("startup coordinator: succeeds when Ollama and Backend are already running externally", async () => {
  // Mock external Ollama with model
  const ollamaServer = http.createServer((req, res) => {
    if (req.url === "/") {
      res.writeHead(200);
      res.end("Ollama is running");
    } else if (req.url === "/api/tags") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ models: [{ name: "qwen3:4b" }] }));
    }
  });
  await new Promise<void>((resolve) => ollamaServer.listen(0, "127.0.0.1", () => resolve()));
  const ollamaPort = (ollamaServer.address() as net.AddressInfo).port;

  // Mock external healthy backend
  const backendServer = http.createServer((req, res) => {
    if (req.url === "/api/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", orchestrator: "ready" }));
    }
  });
  await new Promise<void>((resolve) => backendServer.listen(0, "127.0.0.1", () => resolve()));
  const backendPort = (backendServer.address() as net.AddressInfo).port;

  try {
    const coordinator = new StartupCoordinator({
      ollamaEndpoint: `http://127.0.0.1:${ollamaPort}`,
      requiredModel: "qwen3:4b",
      backendPort: backendPort,
      backendHealthEndpoint: `http://127.0.0.1:${backendPort}/api/health`,
      readinessTimeoutMs: 1000,
      pollIntervalMs: 100,
    });

    const success = await coordinator.orchestrate();
    assert.equal(success, true, "Orchestration must succeed when services are ready");

    const state = coordinator.getState();
    assert.equal(state.isComplete, true);
    assert.equal(state.hasError, false);
    assert.equal(state.step, "ready");
    assert.equal(state.ollama.status, "ready");
    assert.equal(state.model.status, "ready");
    assert.equal(state.backend.status, "ready");

    // Since both services were external, coordinator does NOT own them
    assert.equal(coordinator.hasOwnedOllamaProcess(), false);
    assert.equal(coordinator.hasOwnedBackendProcess(), false);

    // Shutdown should run safely without killing external services
    await coordinator.shutdown();
  } finally {
    await new Promise<void>((resolve) => ollamaServer.close(() => resolve()));
    await new Promise<void>((resolve) => backendServer.close(() => resolve()));
  }
});
