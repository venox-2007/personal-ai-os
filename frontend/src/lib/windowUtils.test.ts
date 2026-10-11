import test from "node:test";
import assert from "node:assert/strict";
import {
  clampWindowBounds,
  getDefaultWindowBounds,
  getUsableArea,
  validateAndSanitizePersistedState,
  serializeDesktopState,
  MIN_WINDOW_WIDTH,
  MIN_WINDOW_HEIGHT,
  DESKTOP_INSET,
} from "./windowUtils.ts";
import type { WindowState } from "./windowUtils.ts";

test("getUsableArea calculates boundaries respecting insets", () => {
  const area = getUsableArea(1920, 1080);
  assert.equal(area.minX, DESKTOP_INSET.left);
  assert.equal(area.minY, DESKTOP_INSET.top);
  assert.equal(area.maxX, 1920 - DESKTOP_INSET.right);
  assert.equal(area.maxY, 1080 - DESKTOP_INSET.bottom);
  assert.equal(area.width, 1920 - DESKTOP_INSET.left - DESKTOP_INSET.right);
  assert.equal(area.height, 1080 - DESKTOP_INSET.top - DESKTOP_INSET.bottom);
});

test("clampWindowBounds enforces minimum width and height", () => {
  const clamped = clampWindowBounds({ x: 100, y: 100, width: 200, height: 150 }, 1920, 1080);
  assert.equal(clamped.width, MIN_WINDOW_WIDTH);
  assert.equal(clamped.height, MIN_WINDOW_HEIGHT);
});

test("clampWindowBounds keeps title bar reachable and prevents going offscreen", () => {
  // Try placing window way above top bar
  const clampedTop = clampWindowBounds({ x: 100, y: -500, width: 800, height: 600 }, 1920, 1080);
  assert.ok(clampedTop.y >= DESKTOP_INSET.top, "y coordinate must not be above top bar");

  // Try placing window way to the left
  const clampedLeft = clampWindowBounds({ x: -2000, y: 100, width: 800, height: 600 }, 1920, 1080);
  assert.ok(clampedLeft.x + clampedLeft.width >= DESKTOP_INSET.left + 120, "window must remain partially visible horizontally");

  // Try placing window far below dock
  const clampedBottom = clampWindowBounds({ x: 100, y: 3000, width: 800, height: 600 }, 1920, 1080);
  assert.ok(clampedBottom.y <= 1080 - DESKTOP_INSET.bottom - 40, "title bar must remain reachable above dock");
});

test("getDefaultWindowBounds creates valid centered cascade bounds", () => {
  const b0 = getDefaultWindowBounds(1920, 1080, 0);
  const b1 = getDefaultWindowBounds(1920, 1080, 1);
  assert.ok(b0.width >= MIN_WINDOW_WIDTH);
  assert.ok(b0.height >= MIN_WINDOW_HEIGHT);
  assert.notEqual(b0.x, b1.x, "cascading windows should have staggered positions");
  assert.notEqual(b0.y, b1.y);
});

test("validateAndSanitizePersistedState rejects non-objects or invalid payloads", () => {
  assert.equal(validateAndSanitizePersistedState(null, 1920, 1080), null);
  assert.equal(validateAndSanitizePersistedState(undefined, 1920, 1080), null);
  assert.equal(validateAndSanitizePersistedState("invalid", 1920, 1080), null);
  assert.equal(validateAndSanitizePersistedState(12345, 1920, 1080), null);
  assert.equal(validateAndSanitizePersistedState({}, 1920, 1080), null);
  assert.equal(validateAndSanitizePersistedState({ windows: "not-an-array" }, 1920, 1080), null);
});

test("validateAndSanitizePersistedState filters out unknown apps and corrupt bounds", () => {
  const malformedData = {
    version: 1,
    activeWindowId: "malicious_app",
    windows: [
      {
        id: "malicious_app",
        appId: "hacker_app", // invalid appId
        title: "Malicious",
        isMinimized: false,
        isMaximized: false,
        bounds: { x: NaN, y: Infinity, width: "invalid", height: -100 },
      },
      {
        id: "home",
        appId: "home",
        title: "AI Assistant",
        isMinimized: false,
        isMaximized: true,
        bounds: { x: 50, y: 50, width: 800, height: 600 },
        preMaximizedBounds: { x: 80, y: 80, width: 700, height: 500 },
        zIndexOrder: 1,
      },
      {
        id: "coding",
        appId: "coding",
        title: "Coding Workspace",
        isMinimized: true,
        isMaximized: false,
        bounds: { x: -5000, y: -5000, width: 100, height: 50 }, // offscreen / undersized
        zIndexOrder: 0,
      },
    ],
  };

  const sanitized = validateAndSanitizePersistedState(malformedData, 1920, 1080);
  assert.ok(sanitized !== null);
  assert.equal(sanitized.windows.length, 2, "Only valid apps (home, coding) should survive");

  const home = sanitized.windows.find((w) => w.id === "home");
  assert.ok(home);
  assert.equal(home.isMaximized, true);
  assert.equal(home.title, "AI Assistant");
  assert.ok(home.preMaximizedBounds);

  const coding = sanitized.windows.find((w) => w.id === "coding");
  assert.ok(coding);
  assert.equal(coding.isMinimized, true);
  assert.ok(coding.bounds.width >= MIN_WINDOW_WIDTH, "Clamped bounds width");
  assert.ok(coding.bounds.height >= MIN_WINDOW_HEIGHT, "Clamped bounds height");

  assert.equal(sanitized.activeWindowId, "home", "Active window ID resolves to unminimized valid window");
});

test("serializeDesktopState and validate roundtrip preserves relative z-order", () => {
  const windows: WindowState[] = [
    {
      id: "files",
      appId: "files",
      title: "Files",
      isMinimized: false,
      isMaximized: false,
      bounds: { x: 100, y: 100, width: 800, height: 600 },
      zIndex: 25,
    },
    {
      id: "home",
      appId: "home",
      title: "AI Assistant",
      isMinimized: false,
      isMaximized: false,
      bounds: { x: 150, y: 150, width: 850, height: 650 },
      zIndex: 12,
    },
  ];

  const serialized = serializeDesktopState(windows, "files");
  assert.equal(serialized.activeWindowId, "files");
  assert.equal(serialized.windows.length, 2);

  const reloaded = validateAndSanitizePersistedState(serialized, 1920, 1080);
  assert.ok(reloaded);
  assert.equal(reloaded.activeWindowId, "files");

  const filesReloaded = reloaded.windows.find((w) => w.id === "files");
  const homeReloaded = reloaded.windows.find((w) => w.id === "home");
  assert.ok(filesReloaded && homeReloaded);
  assert.ok(filesReloaded.zIndex > homeReloaded.zIndex, "Files was higher z-index than home");
});
