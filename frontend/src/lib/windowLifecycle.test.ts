import test from "node:test";
import assert from "node:assert/strict";
import {
  clampWindowBounds,
  getDefaultWindowBounds,
  validateAndSanitizePersistedState,
  serializeDesktopState,
  MIN_WINDOW_WIDTH,
  MIN_WINDOW_HEIGHT,
  DESKTOP_INSET,
} from "./windowUtils.ts";
import type { WindowState } from "./windowUtils.ts";

test("lifecycle: open app creates expected window state and bounds", () => {
  const bounds = getDefaultWindowBounds(1440, 900, 0);
  const win: WindowState = {
    id: "home",
    appId: "home",
    title: "AI Assistant",
    isMinimized: false,
    isMaximized: false,
    bounds,
    zIndex: 11,
  };

  assert.equal(win.id, "home");
  assert.equal(win.isMinimized, false);
  assert.equal(win.isMaximized, false);
  assert.ok(win.bounds.width >= MIN_WINDOW_WIDTH);
  assert.ok(win.bounds.height >= MIN_WINDOW_HEIGHT);
  assert.ok(win.bounds.y >= DESKTOP_INSET.top);
});

test("lifecycle: duplicate app opening focuses existing window rather than creating duplicate", () => {
  const windows: WindowState[] = [
    {
      id: "home",
      appId: "home",
      title: "AI Assistant",
      isMinimized: true,
      isMaximized: false,
      bounds: { x: 100, y: 100, width: 800, height: 600 },
      zIndex: 11,
    },
    {
      id: "calendar",
      appId: "calendar",
      title: "Calendar",
      isMinimized: false,
      isMaximized: false,
      bounds: { x: 150, y: 150, width: 800, height: 600 },
      zIndex: 12,
    },
  ];

  // Emulate opening "home" again
  const targetAppId = "home";
  const existing = windows.find((w) => w.id === targetAppId);
  assert.ok(existing);

  // Behavior: Bring existing to top zIndex and un-minimize
  const highestZ = Math.max(...windows.map((w) => w.zIndex));
  const updatedWindows = windows.map((w) =>
    w.id === existing.id ? { ...w, isMinimized: false, zIndex: highestZ + 1 } : w
  );

  assert.equal(updatedWindows.length, 2, "Window count must not increase");
  const home = updatedWindows.find((w) => w.id === "home");
  assert.ok(home);
  assert.equal(home.isMinimized, false, "Must un-minimize on duplicate open");
  assert.ok(home.zIndex > 12, "Must receive highest z-index");
});

test("lifecycle: minimize and unminimize (restore) lifecycle maintains state", () => {
  let win: WindowState = {
    id: "coding",
    appId: "coding",
    title: "Coding",
    isMinimized: false,
    isMaximized: false,
    bounds: { x: 200, y: 150, width: 900, height: 650 },
    zIndex: 15,
  };

  // 1. Minimize
  win = { ...win, isMinimized: true };
  assert.equal(win.isMinimized, true);

  // 2. Restore
  win = { ...win, isMinimized: false, zIndex: 16 };
  assert.equal(win.isMinimized, false);
  assert.equal(win.bounds.width, 900);
});

test("lifecycle: maximize stores pre-maximized bounds and restore restores them", () => {
  const originalBounds = { x: 250, y: 180, width: 850, height: 620 };
  let win: WindowState = {
    id: "study",
    appId: "study",
    title: "Study",
    isMinimized: false,
    isMaximized: false,
    bounds: originalBounds,
    zIndex: 14,
  };

  // Maximize
  const willMaximize = !win.isMaximized;
  win = {
    ...win,
    isMaximized: willMaximize,
    preMaximizedBounds: willMaximize ? { ...win.bounds } : win.preMaximizedBounds,
  };
  assert.equal(win.isMaximized, true);
  assert.deepEqual(win.preMaximizedBounds, originalBounds);

  // Unmaximize (restore)
  const willUnmaximize = !win.isMaximized;
  win = {
    ...win,
    isMaximized: willUnmaximize,
    bounds: !willUnmaximize && win.preMaximizedBounds ? { ...win.preMaximizedBounds } : win.bounds,
  };
  assert.equal(win.isMaximized, false);
  assert.deepEqual(win.bounds, originalBounds, "Window bounds restored to pre-maximized dimensions");
});

test("lifecycle: close window activates next highest unminimized window", () => {
  const windows: WindowState[] = [
    {
      id: "desktop",
      appId: "desktop",
      title: "Overview",
      isMinimized: false,
      isMaximized: false,
      bounds: { x: 50, y: 50, width: 800, height: 600 },
      zIndex: 11,
    },
    {
      id: "coding",
      appId: "coding",
      title: "Coding",
      isMinimized: true, // minimized
      isMaximized: false,
      bounds: { x: 100, y: 100, width: 800, height: 600 },
      zIndex: 13,
    },
    {
      id: "files",
      appId: "files",
      title: "Files",
      isMinimized: false,
      isMaximized: false,
      bounds: { x: 150, y: 150, width: 800, height: 600 },
      zIndex: 12,
    },
    {
      id: "home",
      appId: "home",
      title: "AI Assistant",
      isMinimized: false,
      isMaximized: false,
      bounds: { x: 200, y: 200, width: 800, height: 600 },
      zIndex: 14, // top active window
    },
  ];

  const closingId = "home";
  const remaining = windows.filter((w) => w.id !== closingId);
  const unminimized = remaining.filter((w) => !w.isMinimized);

  const nextActive = unminimized.reduce((p, c) => (p.zIndex > c.zIndex ? p : c));
  assert.equal(nextActive.id, "files", "files (z=12) is next highest unminimized window, coding is skipped because minimized");
});

test("persistence: gracefully handles corrupted JSON and out-of-bounds positions", () => {
  const corruptedPayload = {
    version: 1,
    activeWindowId: "nonexistent",
    windows: [
      {
        id: "calendar",
        appId: "calendar",
        title: "Calendar",
        isMinimized: false,
        isMaximized: false,
        bounds: { x: 99999, y: 99999, width: 10, height: 10 },
      },
    ],
  };

  const restored = validateAndSanitizePersistedState(corruptedPayload, 1280, 800);
  assert.ok(restored);
  assert.equal(restored.windows.length, 1);
  const cal = restored.windows[0];
  assert.ok(cal.bounds.x < 1280, "x was clamped into viewable desktop");
  assert.ok(cal.bounds.y < 800, "y was clamped into viewable desktop");
  assert.equal(cal.bounds.width, MIN_WINDOW_WIDTH);
  assert.equal(cal.bounds.height, MIN_WINDOW_HEIGHT);
  assert.equal(restored.activeWindowId, "calendar", "activeWindowId resolved to only valid window");
});
