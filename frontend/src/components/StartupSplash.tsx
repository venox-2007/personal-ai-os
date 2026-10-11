import React, { useEffect, useState } from "react";
import { Loader2, AlertCircle, CheckCircle2, RefreshCw, Cpu, Server, Sparkles, Copy, Check, ExternalLink } from "lucide-react";

export interface ServiceDetail {
  status: "pending" | "running" | "ready" | "error";
  message?: string;
  error?: string;
  recoveryHint?: string;
  copyCommand?: string;
  externalUrl?: string;
}

export interface StartupProgressState {
  step:
    | "checking_ollama"
    | "starting_ollama"
    | "verifying_model"
    | "checking_backend"
    | "starting_backend"
    | "waiting_backend"
    | "ready"
    | "failed";
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

export const StartupSplash: React.FC = () => {
  const [startupState, setStartupState] = useState<StartupProgressState | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [copied, setCopied] = useState(false);
  const isDesktop = typeof window !== "undefined" && Boolean(window.desktopApi?.isElectron);

  useEffect(() => {
    if (!isDesktop || !window.desktopApi) return;

    // Fetch initial state
    window.desktopApi.getStartupStatus?.().then((status) => {
      if (status) setStartupState(status);
    });

    // Listen for real-time progress updates
    const unsubscribe = window.desktopApi.onStartupProgress?.((status) => {
      setStartupState(status);
    });

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [isDesktop]);

  // If not running in Electron, dismissed, or services are already completely ready, do not display splash
  if (!isDesktop || !startupState || startupState.isComplete || isDismissed) {
    return null;
  }

  const handleRetry = async () => {
    if (!window.desktopApi?.retryStartup) return;
    setIsRetrying(true);
    try {
      await window.desktopApi.retryStartup();
    } catch (err) {
      console.error("Retry failed:", err);
    } finally {
      setIsRetrying(false);
    }
  };

  const activeCopyCommand =
    startupState.copyCommand ||
    startupState.model.copyCommand ||
    startupState.ollama.copyCommand ||
    startupState.backend.copyCommand;

  const activeExternalUrl =
    startupState.externalUrl ||
    startupState.ollama.externalUrl ||
    startupState.model.externalUrl ||
    startupState.backend.externalUrl;

  const handleCopyCommand = async () => {
    if (!activeCopyCommand) return;
    try {
      await navigator.clipboard.writeText(activeCopyCommand);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy command:", err);
    }
  };

  const handleOpenExternal = async (url: string) => {
    if (window.desktopApi?.openExternalUrl) {
      await window.desktopApi.openExternalUrl(url);
    } else {
      window.open(url, "_blank");
    }
  };

  const renderServiceRow = (
    title: string,
    detail: ServiceDetail,
    Icon: React.ElementType
  ) => {
    let statusIcon = <div className="w-4 h-4 rounded-full border border-gray-600 bg-gray-800" />;
    let statusColor = "text-gray-400";

    if (detail.status === "ready") {
      statusIcon = <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
      statusColor = "text-emerald-300";
    } else if (detail.status === "running") {
      statusIcon = <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />;
      statusColor = "text-cyan-300";
    } else if (detail.status === "error") {
      statusIcon = <AlertCircle className="w-5 h-5 text-rose-400" />;
      statusColor = "text-rose-300";
    }

    return (
      <div className="flex items-center justify-between p-3.5 bg-gray-900/60 border border-gray-800/80 rounded-xl transition-all">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gray-800/80 border border-gray-700/50 text-gray-300">
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              {title}
            </div>
            <div className={`text-sm font-medium ${statusColor}`}>
              {detail.message || "Pending..."}
            </div>
          </div>
        </div>
        <div>{statusIcon}</div>
      </div>
    );
  };

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="startup-splash"
      onClick={(e) => {
        if (e.target === e.currentTarget) setIsDismissed(true);
      }}
      className="fixed inset-0 z-40 flex items-center justify-center bg-gray-950/80 backdrop-blur-md px-4"
    >
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl p-6 flex flex-col gap-5 text-gray-100">
        <div className="flex items-center justify-between pb-2 border-b border-gray-800/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold tracking-tight text-white">Personal AI OS</h2>
              <p className="text-xs text-gray-400">Coordinating local intelligence services</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2.5">
          {renderServiceRow("Local LLM Server", startupState.ollama, Cpu)}
          {renderServiceRow("Model Engine", startupState.model, Sparkles)}
          {renderServiceRow("FastAPI Core", startupState.backend, Server)}
        </div>

        {startupState.hasError && (
          <div className="p-3.5 bg-rose-950/40 border border-rose-800/60 rounded-xl flex flex-col gap-2.5">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="text-xs text-rose-200">
                <p className="font-semibold">{startupState.errorMessage || "Service failed to start"}</p>
                {startupState.recoveryHint && (
                  <p className="mt-1 text-gray-300 font-mono text-[11px] bg-black/40 p-2 rounded border border-rose-900/40">
                    💡 {startupState.recoveryHint}
                  </p>
                )}
              </div>
            </div>

            {/* Quick Action Helpers */}
            {(activeCopyCommand || activeExternalUrl) && (
              <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-rose-900/30">
                {activeCopyCommand && (
                  <button
                    type="button"
                    onClick={handleCopyCommand}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 text-[11px] font-medium rounded-lg border border-gray-700/60 transition-colors shadow-sm"
                    title={`Copy command: ${activeCopyCommand}`}
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-300">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-gray-400" />
                        <span>Copy Install Command</span>
                      </>
                    )}
                  </button>
                )}
                {activeExternalUrl && (
                  <button
                    type="button"
                    onClick={() => handleOpenExternal(activeExternalUrl)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-200 text-[11px] font-medium rounded-lg border border-cyan-800/50 transition-colors shadow-sm"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Open Official Website</span>
                  </button>
                )}
              </div>
            )}

            <div className="mt-1 flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => setIsDismissed(true)}
                className="text-xs text-gray-400 hover:text-gray-200 underline underline-offset-2 transition-colors"
              >
                Continue to Desktop (Offline)
              </button>
              <button
                type="button"
                onClick={handleRetry}
                disabled={isRetrying}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? "animate-spin" : ""}`} />
                {isRetrying ? "Retrying..." : "Retry Startup"}
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-[11px] text-gray-500 pt-1">
          <span>Automated one-click startup · 100% local</span>
          <button
            type="button"
            onClick={() => setIsDismissed(true)}
            className="hover:text-gray-400 transition-colors"
          >
            Hide
          </button>
        </div>
      </div>
    </div>
  );
};
