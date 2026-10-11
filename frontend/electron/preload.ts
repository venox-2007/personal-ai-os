import { contextBridge, ipcRenderer } from "electron";

/**
 * Preload script exposing a strictly scoped, context-isolated API.
 * Node integration is disabled; arbitrary IPC, filesystem, and shell APIs are forbidden.
 */
const desktopApi = {
  platform: process.platform,
  isElectron: true,
  getAppInfo: async () => {
    return await ipcRenderer.invoke("app:get-info");
  },
  openExternalUrl: async (url: string) => {
    if (typeof url !== "string") {
      return { success: false, error: "Invalid URL string provided" };
    }
    return await ipcRenderer.invoke("system:open-external", url);
  },
};

// Safely bridge desktop API into the isolated window object
contextBridge.exposeInMainWorld("desktopApi", desktopApi);
