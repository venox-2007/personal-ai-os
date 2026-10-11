import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("electron production shell: packaged local assets load and render without Vite server", async () => {
  const playwright = await import("playwright");
  const electron = (playwright as any)._electron;
  assert.ok(electron, "Playwright electron launcher must be available");

  const electronApp = await electron.launch({
    args: ["."],
    cwd: path.resolve(__dirname, ".."),
    env: {
      ...process.env,
      NODE_ENV: "production",
    },
  });

  try {
    const window = await electronApp.firstWindow();

    // 1. Verify packaged local file protocol URL
    const currentUrl = window.url();
    assert.match(currentUrl, /^file:\/\/\/.*\/dist\/index\.html$/, "App must load compiled dist/index.html via file:// protocol");

    // 2. Verify Desktop top bar and bottom dock mount
    await window.waitForSelector("header", { timeout: 10000 });
    await window.waitForSelector("div.absolute.bottom-3", { timeout: 5000 });

    // 3. Verify backend-disconnected state: top bar indicates Backend Offline cleanly without hanging
    const offlineIndicator = window.locator("header div[title='Backend Offline']");
    await offlineIndicator.waitFor({ timeout: 15000 });
    assert.ok((await offlineIndicator.count()) > 0, "Top bar must display clear 'Backend Offline' indicator");

    // 4. Verify security: Node.js isolation and strict preload scoping
    const security = await window.evaluate(() => ({
      hasProcess: typeof (window as any).process !== "undefined",
      hasRequire: typeof (window as any).require !== "undefined",
      hasBuffer: typeof (window as any).Buffer !== "undefined",
      hasDesktopApi: typeof (window as any).desktopApi !== "undefined",
      desktopApiKeys: (window as any).desktopApi ? Object.keys((window as any).desktopApi) : [],
    }));

    assert.equal(security.hasProcess, false, "Node process must NOT be accessible in renderer");
    assert.equal(security.hasRequire, false, "Node require must NOT be accessible in renderer");
    assert.equal(security.hasBuffer, false, "Node Buffer must NOT be accessible in renderer");
    assert.equal(security.hasDesktopApi, true, "desktopApi must be bridged to window");
    assert.deepEqual(
      security.desktopApiKeys.sort(),
      [
        "getAppInfo",
        "getStartupStatus",
        "isElectron",
        "onStartupProgress",
        "openExternalUrl",
        "platform",
        "retryStartup",
      ].sort(),
      "Preload must only expose strictly approved typed methods"
    );

    // 5. Verify window management: open app window and verify client-side interaction
    const splash = window.locator("div[role='status']");
    try {
      if (await splash.isVisible({ timeout: 2000 })) {
        const hideBtn = splash.locator("button:has-text('Hide'), button:has-text('Continue')").first();
        await hideBtn.click();
        await splash.waitFor({ state: "hidden", timeout: 3000 });
      }
    } catch {
      // Splash already complete or dismissed
    }

    const assistantBtn = window.locator("button[aria-label='AI Assistant']");
    await assistantBtn.click();
    await window.waitForSelector("div.flex.flex-col.bg-surface\\/90", { timeout: 10000 });

    // 6. Test disconnected chat interaction: submit a message and confirm graceful offline error notice
    const chatInput = window.locator("textarea, input[placeholder*='Ask'], input[type='text']").first();
    await chatInput.fill("Hello offline");
    const sendButton = window.locator("button:has-text('Execute'), button:has-text('Send')").first();
    await sendButton.click();

    // Verify error notice appears in assistant message without UI crash
    const errorNotice = window.locator("div:has-text('Failed to contact Orchestrator')").first();
    await errorNotice.waitFor({ timeout: 10000 });
    assert.ok((await errorNotice.count()) > 0, "Graceful offline error notice displayed in chat stream");

    // 7. Verify page reload / refresh behavior with persisted state
    await window.reload();
    await window.waitForSelector("header", { timeout: 10000 });
    const restoredWindows = await window.locator("div.flex.flex-col.bg-surface\\/90").count();
    assert.ok(restoredWindows >= 1, "Open windows persisted and restored after Electron reload");

    // 8. Navigation restriction: verify internal navigation to unauthorized origin is blocked
    const navBlocked = await window.evaluate(() => {
      try {
        window.location.href = "https://malicious-external-site.com";
        return true;
      } catch {
        return false;
      }
    });
    assert.ok(navBlocked, "Attempted navigation executed");
    await window.waitForTimeout(500);
    // URL must still be file:///.../dist/index.html (not navigated away)
    assert.match(window.url(), /^file:\/\/\//, "Window must remain locked to local file protocol");
  } finally {
    await electronApp.close();
  }
});

test("electron process cleanup: closing window terminates electron processes", async () => {
  const playwright = await import("playwright");
  const electron = (playwright as any)._electron;

  const electronApp = await electron.launch({
    args: ["."],
    cwd: path.resolve(__dirname, ".."),
    env: {
      ...process.env,
      NODE_ENV: "production",
    },
  });

  const pid = electronApp.process().pid;
  assert.ok(pid && pid > 0, "Electron main process PID must exist");

  const window = await electronApp.firstWindow();
  await window.waitForSelector("header", { timeout: 10000 });

  // Close the window directly
  await window.close();

  // Wait briefly for app to exit on all windows closed
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // Verify process exited
  let isRunning = true;
  try {
    process.kill(pid, 0); // throws if process does not exist
  } catch {
    isRunning = false;
  }

  assert.equal(isRunning, false, "Electron process must exit cleanly after window is closed");
});
