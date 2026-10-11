import { app, BrowserWindow, shell, ipcMain, IpcMainInvokeEvent } from "electron";
import path from "node:path";
import fs from "node:fs";
import { StartupCoordinator } from "./startupCoordinator";

// Security & Identity configuration
const APP_ID = "com.personalaios.desktop";
const APP_NAME = "Personal AI OS";

app.setName(APP_NAME);
if (process.platform === "win32") {
  app.setAppUserModelId(APP_ID);
}

// Ensure single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}

let mainWindow: BrowserWindow | null = null;
const startupCoordinator = new StartupCoordinator();

const isDev =
  process.env.ELECTRON_IS_DEV === "true" ||
  (process.env.NODE_ENV !== "production" && !app.isPackaged);
const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL || "http://127.0.0.1:5173";

function resolveIconPath(): string | undefined {
  const customIco = path.join(__dirname, "resources", "icon.ico");
  if (fs.existsSync(customIco)) return customIco;

  const placeholderIco = path.join(__dirname, "resources", "placeholder_icon.ico");
  if (fs.existsSync(placeholderIco)) return placeholderIco;

  return undefined;
}

function createWindow(): void {
  const iconPath = resolveIconPath();

  mainWindow = new BrowserWindow({
    title: APP_NAME,
    width: 1360,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: "#0f1115", // Matches near-black Personal AI OS background
    show: false, // Wait until ready-to-show to prevent white flash
    autoHideMenuBar: true,
    icon: iconPath,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  // Handle window closing
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Navigation Restrictions: prevent renderer from navigating away from the app
  mainWindow.webContents.on("will-navigate", (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    // Allow local dev server or packaged file protocol
    if (isDev && parsedUrl.origin === new URL(VITE_DEV_SERVER_URL).origin) {
      return;
    }
    if (parsedUrl.protocol === "file:") {
      return;
    }

    event.preventDefault();
    console.warn(`[Security] Blocked unauthorized internal navigation to: ${navigationUrl}`);
  });

  // Open external links through default system browser via setWindowOpenHandler
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsedUrl = new URL(url);
      if (parsedUrl.protocol === "https:" || parsedUrl.protocol === "http:") {
        shell.openExternal(url);
      }
    } catch (e) {
      console.warn(`[Security] Failed to open external url: ${url}`, e);
    }
    return { action: "deny" };
  });

  // Load appropriate content
  if (isDev) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL).catch((err) => {
      console.error(`Failed to load dev server at ${VITE_DEV_SERVER_URL}:`, err);
    });
  } else {
    // In production, load the packaged Vite distribution
    const prodPath = path.join(__dirname, "..", "dist", "index.html");
    mainWindow.loadFile(prodPath).catch((err) => {
      console.error(`Failed to load production build at ${prodPath}:`, err);
    });
  }
}

// IPC Handlers
ipcMain.handle("app:get-info", (event: IpcMainInvokeEvent) => {
  // Validate sender
  if (!mainWindow || event.sender !== mainWindow.webContents) {
    throw new Error("Unauthorized IPC invocation");
  }

  return {
    name: APP_NAME,
    version: app.getVersion(),
    appId: APP_ID,
    isPackaged: app.isPackaged,
    platform: process.platform,
  };
});

ipcMain.handle("system:open-external", async (event: IpcMainInvokeEvent, targetUrl: unknown) => {
  if (!mainWindow || event.sender !== mainWindow.webContents) {
    return { success: false, error: "Unauthorized IPC invocation" };
  }

  if (typeof targetUrl !== "string") {
    return { success: false, error: "Invalid target URL" };
  }

  try {
    const parsed = new URL(targetUrl);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      return { success: false, error: "Only HTTP/HTTPS URLs may be opened externally" };
    }
    await shell.openExternal(targetUrl);
    return { success: true };
  } catch (err: any) {
    return { success: false, error: err.message || "Failed to open external URL" };
  }
});

// Startup IPC Handlers
ipcMain.handle("startup:get-status", (event: IpcMainInvokeEvent) => {
  if (!mainWindow || event.sender !== mainWindow.webContents) {
    throw new Error("Unauthorized IPC invocation");
  }
  return startupCoordinator.getState();
});

ipcMain.handle("startup:retry", async (event: IpcMainInvokeEvent) => {
  if (!mainWindow || event.sender !== mainWindow.webContents) {
    throw new Error("Unauthorized IPC invocation");
  }
  const success = await startupCoordinator.orchestrate();
  return { success, error: success ? undefined : startupCoordinator.getState().errorMessage };
});

// App Lifecycle
app.whenReady().then(() => {
  createWindow();

  // Forward progress events to renderer
  startupCoordinator.onProgress((state) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("startup:progress", state);
    }
  });

  // Launch service startup orchestration automatically
  startupCoordinator.orchestrate().catch((err) => {
    console.error("[Main] Startup orchestration unhandled error:", err);
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("second-instance", () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.on("before-quit", async () => {
  try {
    await startupCoordinator.shutdown();
  } catch (err) {
    console.error("[Main] Error during startupCoordinator shutdown:", err);
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
