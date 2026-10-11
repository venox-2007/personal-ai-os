import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("electron e2e: launches packaged window, enforces isolation, and renders desktop", async () => {
  // Use playwright electron launcher
  const playwright = await import("playwright");
  const electron = (playwright as any)._electron;
  assert.ok(electron, "Playwright electron module must be available");

  const electronApp = await electron.launch({
    args: ["."],
    cwd: path.resolve(__dirname, ".."),
    env: {
      ...process.env,
      NODE_ENV: "production",
    },
  });

  try {
    const appInfo = await electronApp.evaluate(async ({ app }: any) => ({
      name: app.getName(),
      version: app.getVersion(),
    }));
    assert.equal(appInfo.name, "Personal AI OS");

    const window = await electronApp.firstWindow();
    await window.waitForSelector("header", { timeout: 10000 });
    await window.waitForSelector("div.absolute.bottom-3", { timeout: 5000 });

    const security = await window.evaluate(() => ({
      hasProcess: typeof (window as any).process !== "undefined",
      hasRequire: typeof (window as any).require !== "undefined",
      hasBuffer: typeof (window as any).Buffer !== "undefined",
      hasDesktopApi: typeof (window as any).desktopApi !== "undefined",
    }));

    assert.equal(security.hasProcess, false, "Node process must NOT be exposed");
    assert.equal(security.hasRequire, false, "Node require must NOT be exposed");
    assert.equal(security.hasBuffer, false, "Node Buffer must NOT be exposed");
    assert.equal(security.hasDesktopApi, true, "desktopApi must be exposed");

    const desktopAppInfo = await window.evaluate(async () => {
      return await (window as any).desktopApi.getAppInfo();
    });
    assert.equal(desktopAppInfo.name, "Personal AI OS");
    assert.equal(desktopAppInfo.appId, "com.personalaios.desktop");
  } finally {
    await electronApp.close();
  }
});
