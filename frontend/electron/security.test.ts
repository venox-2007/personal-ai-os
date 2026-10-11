import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("electron security: main process configuration enforces secure defaults", () => {
  const mainTs = fs.readFileSync(path.join(__dirname, "main.ts"), "utf8");

  // contextIsolation must be true
  assert.match(mainTs, /contextIsolation:\s*true/, "contextIsolation must be enabled");

  // nodeIntegration must be false
  assert.match(mainTs, /nodeIntegration:\s*false/, "nodeIntegration must be disabled");

  // sandbox must be true
  assert.match(mainTs, /sandbox:\s*true/, "Chromium sandbox must be enabled");

  // webSecurity must be true
  assert.match(mainTs, /webSecurity:\s*true/, "webSecurity must be enabled");

  // allowRunningInsecureContent must be false
  assert.match(mainTs, /allowRunningInsecureContent:\s*false/, "allowRunningInsecureContent must be false");

  // Navigation restriction must intercept will-navigate
  assert.match(mainTs, /will-navigate/, "will-navigate must be restricted");

  // External link handling must route through setWindowOpenHandler
  assert.match(mainTs, /setWindowOpenHandler/, "setWindowOpenHandler must guard external windows");
});

test("electron identity: reverse-domain App ID and Name are configured", () => {
  const mainTs = fs.readFileSync(path.join(__dirname, "main.ts"), "utf8");
  assert.match(mainTs, /APP_ID\s*=\s*["']com\.personalaios\.desktop["']/, "APP_ID must match com.personalaios.desktop");
  assert.match(mainTs, /APP_NAME\s*=\s*["']Personal AI OS["']/, "APP_NAME must match Personal AI OS");
  assert.match(mainTs, /setAppUserModelId/, "Windows AppUserModelId must be configured");
});

test("electron preload: strictly scopes exposed API without Node leaks", () => {
  const preloadTs = fs.readFileSync(path.join(__dirname, "preload.ts"), "utf8");

  // Must use contextBridge.exposeInMainWorld
  assert.match(preloadTs, /contextBridge\.exposeInMainWorld/, "Must expose through contextBridge");

  // Must NOT expose fs, child_process, or arbitrary ipcRenderer.send
  assert.doesNotMatch(preloadTs, /require\(["']fs["']\)/, "Preload must not expose fs");
  assert.doesNotMatch(preloadTs, /require\(["']child_process["']\)/, "Preload must not expose child_process");
  assert.doesNotMatch(preloadTs, /ipcRenderer\.send\(/, "Preload must not expose arbitrary send channels");
});

test("electron artifacts: compiled main, preload and application icon exist in dist-electron", () => {
  const distElectron = path.join(__dirname, "..", "dist-electron");
  assert.ok(fs.existsSync(path.join(distElectron, "main.js")), "dist-electron/main.js must exist");
  assert.ok(fs.existsSync(path.join(distElectron, "preload.js")), "dist-electron/preload.js must exist");
  assert.ok(fs.existsSync(path.join(distElectron, "resources", "icon.ico")), "Application icon.ico must exist in resources");
  assert.ok(fs.existsSync(path.join(distElectron, "resources", "placeholder_icon.ico")), "Placeholder icon must exist in resources");
});
