export type ServiceStep =
  | "checking_ollama"
  | "starting_ollama"
  | "verifying_model"
  | "checking_backend"
  | "starting_backend"
  | "waiting_backend"
  | "ready"
  | "failed";

export interface ServiceDetail {
  status: "pending" | "running" | "ready" | "error";
  message?: string;
  error?: string;
  recoveryHint?: string;
  copyCommand?: string;
  externalUrl?: string;
}

export interface StartupProgressState {
  step: ServiceStep;
  ollama: ServiceDetail;
  model: ServiceDetail;
  backend: ServiceDetail;
  isComplete: boolean;
  hasError: boolean;
  errorMessage?: string;
  recoveryHint?: string;
  copyCommand?: string;
  externalUrl?: string;
}

export interface StartupConfig {
  ollamaEndpoint: string;
  requiredModel: string;
  backendHealthEndpoint: string;
  backendHost: string;
  backendPort: number;
  ollamaExecutablePath?: string;
  standaloneExecutablePath?: string;
  pythonExecutablePath?: string;
  backendWorkingDir?: string;
  readinessTimeoutMs: number;
  pollIntervalMs: number;
}

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
  getStartupStatus: () => Promise<StartupProgressState>;
  onStartupProgress: (callback: (status: StartupProgressState) => void) => () => void;
  retryStartup: () => Promise<{ success: boolean; error?: string }>;
}

declare global {
  interface Window {
    desktopApi?: ElectronDesktopApi;
  }
}
