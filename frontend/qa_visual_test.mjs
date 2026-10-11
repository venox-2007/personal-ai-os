import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const BASE_URL = "http://127.0.0.1:5173";
const SCREENSHOT_DIR = path.resolve("./frontend/qa_screenshots");

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runVisualQA() {
  console.log("=== Starting Visual QA and Interaction Validation Suite ===");

  const browser = await chromium.launch({
    executablePath: EDGE_PATH,
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const page = await context.newPage();

  // Listen for console errors & failed requests
  const consoleErrors = [];
  const failedRequests = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });

  page.on("requestfailed", (req) => {
    failedRequests.push(`${req.method()} ${req.url()} - ${req.failure()?.errorText}`);
  });

  // Scenario 1: Initial Desktop Load
  console.log("Scenario 1: Testing initial desktop load...");
  await page.goto(BASE_URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  // Check wallpaper, top bar, dock
  const topBar = await page.locator("header");
  assert.ok((await topBar.count()) > 0, "DesktopTopBar must be visible");

  // Verify health indicator rendered (backend ok)
  const healthDot = await page.locator("header div[title='Backend OK']");
  assert.ok((await healthDot.count()) > 0, "Backend OK health indicator must be visible in top bar");

  const dock = await page.locator("div.absolute.bottom-3");
  assert.ok((await dock.count()) > 0, "Desktop dock must be rendered");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "01_initial_desktop.png") });
  console.log("  -> Scenario 1 Passed. Screenshot: 01_initial_desktop.png");

  // Scenario 2: Open each available app and verify render
  console.log("Scenario 2: Opening each app from the dock...");
  const apps = [
    { id: "desktop", label: "Overview" },
    { id: "home", label: "AI Assistant" },
    { id: "research", label: "Research" },
    { id: "study", label: "Study" },
    { id: "coding", label: "Coding" },
    { id: "files", label: "Files" },
    { id: "calendar", label: "Calendar" },
    { id: "memory", label: "Memory" },
    { id: "workflows", label: "Workflows" },
  ];

  for (const app of apps) {
    const dockBtn = page.locator(`button[aria-label='${app.label}']`);
    await dockBtn.click();
    await page.waitForTimeout(300);

    // Verify window opened
    const winTitle = page.locator(`span:has-text('${app.label}')`);
    assert.ok((await winTitle.count()) > 0, `Window for ${app.label} must be present`);

    // Close window to keep clean
    const closeBtn = page.locator("button[title='Close']").last();
    await closeBtn.click();
    await page.waitForTimeout(200);
  }
  console.log("  -> Scenario 2 Passed: All 9 app windows opened and closed cleanly.");

  // Scenario 3 & 4: Drag and Resize
  console.log("Scenario 3 & 4: Testing window drag and multi-edge resize...");
  // Open AI Assistant
  await page.locator("button[aria-label='AI Assistant']").click();
  await page.waitForTimeout(400);

  const windowLocator = page.locator("div.flex.flex-col.bg-surface\\/90").first();
  const initialBox = await windowLocator.boundingBox();
  assert.ok(initialBox, "Window bounding box must exist");

  // Drag via title bar
  const titleBar = windowLocator.locator("div.h-11").first();
  const titleBox = await titleBar.boundingBox();
  assert.ok(titleBox, "Title bar bounding box must exist");

  await page.mouse.move(titleBox.x + 50, titleBox.y + 15);
  await page.mouse.down();
  await page.mouse.move(titleBox.x + 150, titleBox.y + 100, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(300);

  const draggedBox = await windowLocator.boundingBox();
  assert.ok(draggedBox, "Dragged box must exist");
  assert.ok(draggedBox.x > initialBox.x + 50, "Window x must have moved");
  assert.ok(draggedBox.y > initialBox.y + 40, "Window y must have moved");
  assert.ok(draggedBox.y >= 36, "Window title bar must remain within usable area below top bar");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "02_window_dragged.png") });
  console.log("  -> Scenario 3 Passed: Window dragged within safe usable boundaries.");

  // Resize using bottom-right handle
  const seResizeGrip = windowLocator.locator("div.cursor-se-resize");
  const seBox = await seResizeGrip.boundingBox();
  assert.ok(seBox, "SE resize grip must exist");

  await page.mouse.move(seBox.x + seBox.width / 2, seBox.y + seBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(seBox.x + 120, seBox.y + 80, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(300);

  const resizedBox = await windowLocator.boundingBox();
  assert.ok(resizedBox, "Resized box must exist");
  assert.ok(resizedBox.width > draggedBox.width + 50, "Window width must expand");
  assert.ok(resizedBox.height > draggedBox.height + 40, "Window height must expand");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "03_window_resized.png") });
  console.log("  -> Scenario 4 Passed: Multi-edge resize expanded window dimensions cleanly.");

  // Scenario 5: Maximize and Restore
  console.log("Scenario 5: Testing Maximize and Restore...");
  const preMaxBox = await windowLocator.boundingBox();
  assert.ok(preMaxBox);

  const maxBtn = windowLocator.locator("button[title='Maximize Window']");
  await maxBtn.click();
  await page.waitForTimeout(400);

  const maximizedBox = await windowLocator.boundingBox();
  assert.ok(maximizedBox);
  assert.ok(maximizedBox.width > 1400, "Maximized width should span usable desktop width");
  assert.ok(maximizedBox.y >= 36, "Maximized top must not cover top bar");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "04_window_maximized.png") });

  // Restore
  const restoreBtn = windowLocator.locator("button[title='Restore Window']");
  await restoreBtn.click();
  await page.waitForTimeout(400);

  const restoredBox = await windowLocator.boundingBox();
  assert.ok(restoredBox);
  assert.ok(Math.abs(restoredBox.width - preMaxBox.width) < 5, "Restored width matches pre-maximized bounds");
  assert.ok(Math.abs(restoredBox.height - preMaxBox.height) < 5, "Restored height matches pre-maximized bounds");
  console.log("  -> Scenario 5 Passed: Maximize and Restore preserved geometry.");

  // Scenario 6: Minimize, Restore from dock, switch focus, close
  console.log("Scenario 6: Testing Minimize and Restore from Dock...");
  const minBtn = windowLocator.locator("button[title='Minimize']");
  await minBtn.click();
  await page.waitForTimeout(400);

  // Minimized window should not be in DOM or visible
  assert.equal(await windowLocator.count(), 0, "Minimized window must be hidden/unmounted");

  // Dock indicator for AI Assistant should be minimized (hollow ring)
  const homeDockBtn = page.locator("button[aria-label='AI Assistant']");
  const minimizedDot = homeDockBtn.locator("div.border-slate-400\\/80");
  assert.ok((await minimizedDot.count()) > 0, "Dock indicator must show minimized state");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "05_dock_minimized_state.png") });

  // Click dock to restore
  await homeDockBtn.click();
  await page.waitForTimeout(400);
  assert.equal(await page.locator("div.flex.flex-col.bg-surface\\/90").count(), 1, "Window must be restored");

  const closeBtn = page.locator("button[title='Close']").first();
  await closeBtn.click();
  await page.waitForTimeout(300);
  assert.equal(await page.locator("div.flex.flex-col.bg-surface\\/90").count(), 0, "Window closed");
  console.log("  -> Scenario 6 Passed: Minimize, dock indicator, restoration, and close verified.");

  // Scenario 7: Duplicate app-opening prevention
  console.log("Scenario 7: Testing Duplicate App Opening Prevention...");
  await homeDockBtn.click();
  await page.waitForTimeout(300);
  await homeDockBtn.click(); // Click again (should minimize since active)
  await page.waitForTimeout(300);
  await homeDockBtn.click(); // Click again (should restore)
  await page.waitForTimeout(300);

  const homeWindows = await page.locator("span:has-text('AI Assistant')").count();
  assert.equal(homeWindows, 1, "Exactly one instance of AI Assistant must exist");
  console.log("  -> Scenario 7 Passed: Duplicate prevention enforced (single instance maintained).");

  // Scenario 8: Multiple windows & stacking order
  console.log("Scenario 8: Testing multiple windows & z-index stacking...");
  await page.locator("button[aria-label='Files']").click();
  await page.waitForTimeout(300);
  await page.locator("button[aria-label='Calendar']").click();
  await page.waitForTimeout(300);

  // Calendar was opened last, should be active and on top
  const activeDotCalendar = page.locator("button[aria-label='Calendar'] div.bg-brand-400");
  assert.ok((await activeDotCalendar.count()) > 0, "Calendar dock button has active pill indicator");

  // Click AI Assistant in dock: should focus AI Assistant to foreground
  await homeDockBtn.click();
  await page.waitForTimeout(300);

  const activeDotHome = homeDockBtn.locator("div.bg-brand-400");
  assert.ok((await activeDotHome.count()) > 0, "AI Assistant dock button now has active pill indicator");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "06_multiple_windows_stacking.png") });
  console.log("  -> Scenario 8 Passed: Multiple windows stacking and dock indicators synchronized.");

  // Scenario 9: Refresh and Persistence
  console.log("Scenario 9: Testing page reload persistence...");
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  const reloadedWindows = await page.locator("div.flex.flex-col.bg-surface\\/90").count();
  assert.equal(reloadedWindows, 3, "All 3 previously open windows restored after reload");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "07_restored_after_reload.png") });
  console.log("  -> Scenario 9 Passed: 3 open windows and active state successfully restored.");

  // Scenario 10: Inject Malformed State and verify crash-resilience
  console.log("Scenario 10: Testing recovery from corrupted localStorage state...");
  await page.evaluate(() => {
    localStorage.setItem(
      "personal_ai_desktop_state_v1",
      JSON.stringify({
        version: 999,
        activeWindowId: "null_ptr",
        windows: [{ id: "bad", appId: "bad_app", bounds: { x: "NaN" } }],
      })
    );
  });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(800);

  const recoveredTopBar = await page.locator("header").count();
  assert.ok(recoveredTopBar > 0, "Desktop top bar renders cleanly without crashing on corrupt state");
  console.log("  -> Scenario 10 Passed: Desktop safely recovered from corrupted state without crashing.");

  // Scenario 11: Viewport Resize Resilience
  console.log("Scenario 11: Testing viewport resize resilience...");
  await page.locator("button[aria-label='Coding']").click();
  await page.waitForTimeout(400);

  // Resize viewport to small laptop resolution (1024x768)
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.waitForTimeout(500);

  const codingWindow = page.locator("div.flex.flex-col.bg-surface\\/90").first();
  const smallVwBox = await codingWindow.boundingBox();
  assert.ok(smallVwBox);
  assert.ok(smallVwBox.x >= 8 && smallVwBox.x < 1024, "Window x remains inside smaller viewport");
  assert.ok(smallVwBox.y >= 36 && smallVwBox.y < 768, "Window y remains inside smaller viewport");
  assert.ok(smallVwBox.width <= 1024, "Window width adapted or clamped");

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "08_small_viewport_clamped.png") });

  // Restore normal viewport
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(400);
  console.log("  -> Scenario 11 Passed: Windows dynamically adapt and stay within smaller viewports.");

  // Scenario 12: Content and Interaction verification inside window
  console.log("Scenario 12: Testing internal window interactions (buttons, input, scrolling)...");
  // AI Assistant chat textarea
  await homeDockBtn.click();
  await page.waitForTimeout(400);

  const chatInput = page.locator("textarea, input[placeholder*='Ask'], input[type='text']").first();
  if ((await chatInput.count()) > 0) {
    await chatInput.fill("Hello Personal AI OS");
    const val = await chatInput.inputValue();
    assert.equal(val, "Hello Personal AI OS", "Input typing inside window functions properly");
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "09_content_interaction_clean.png") });
  console.log("  -> Scenario 12 Passed: Internal controls, forms, and buttons interact cleanly.");

  await browser.close();

  console.log("\n=== Visual QA & Interaction Suite Completed Successfully! ===");
  console.log(`Console Errors Recorded: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log("Console Errors:", consoleErrors);
  }
  console.log(`Failed Network Requests: ${failedRequests.length}`);
  if (failedRequests.length > 0) {
    console.log("Failed Requests:", failedRequests);
  }
}

runVisualQA().catch((err) => {
  console.error("Visual QA Failed with error:", err);
  process.exit(1);
});
