export interface DesktopAppInfo {
  name: string;
  version: string;
  appId: string;
  isPackaged: boolean;
  platform: string;
}

export interface ElectronDesktopApi {
  platform: string;
  isElectron: boolean;
  getAppInfo: () => Promise<DesktopAppInfo>;
  openExternalUrl: (url: string) => Promise<{ success: boolean; error?: string }>;
}

declare global {
  interface Window {
    desktopApi?: ElectronDesktopApi;
  }
}
