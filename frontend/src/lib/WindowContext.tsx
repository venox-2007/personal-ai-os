import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  ReactNode,
} from "react";
import { NavItem } from "../components/Sidebar";
import {
  WindowBounds,
  WindowState,
  DESKTOP_STATE_STORAGE_KEY,
  clampWindowBounds,
  getDefaultWindowBounds,
  validateAndSanitizePersistedState,
  serializeDesktopState,
} from "./windowUtils";

export type { WindowBounds, WindowState };

interface WindowContextType {
  windows: WindowState[];
  activeWindowId: string | null;
  openWindow: (appId: NavItem, title: string) => void;
  closeWindow: (id: string) => void;
  minimizeWindow: (id: string) => void;
  maximizeWindow: (id: string) => void;
  restoreWindow: (id: string) => void;
  focusWindow: (id: string) => void;
  updateWindowBounds: (id: string, bounds: Partial<WindowBounds>) => void;
}

const WindowContext = createContext<WindowContextType | null>(null);

function getViewportDimensions(): { width: number; height: number } {
  if (typeof window === "undefined") return { width: 1920, height: 1080 };
  const width = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
  const height = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
  return {
    width: Math.max(320, width),
    height: Math.max(320, height),
  };
}

export const WindowProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Initialize state once from localStorage (if valid) or fallback safely
  const [windows, setWindows] = useState<WindowState[]>(() => {
    try {
      const stored = localStorage.getItem(DESKTOP_STATE_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        const { width, height } = getViewportDimensions();
        const sanitized = validateAndSanitizePersistedState(parsed, width, height);
        if (sanitized && sanitized.windows.length > 0) {
          return sanitized.windows;
        }
      }
    } catch (e) {
      console.warn("Failed to read persisted desktop state:", e);
    }
    return [];
  });

  const [activeWindowId, setActiveWindowId] = useState<string | null>(() => {
    try {
      const stored = localStorage.getItem(DESKTOP_STATE_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        const { width, height } = getViewportDimensions();
        const sanitized = validateAndSanitizePersistedState(parsed, width, height);
        if (sanitized) {
          return sanitized.activeWindowId;
        }
      }
    } catch {
      // ignore
    }
    return null;
  });

  const [, setHighestZIndex] = useState<number>(() => {
    try {
      const stored = localStorage.getItem(DESKTOP_STATE_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        const { width, height } = getViewportDimensions();
        const sanitized = validateAndSanitizePersistedState(parsed, width, height);
        if (sanitized) {
          return sanitized.highestZIndex;
        }
      }
    } catch {
      // ignore
    }
    return 10;
  });

  // Track viewport changes to keep windows constrained
  const isInitialMount = useRef(true);

  // Focus window brings to foreground, clears minimized status, and updates active window ID
  const focusWindow = useCallback((id: string) => {
    setHighestZIndex((prevZ) => {
      const nextZ = prevZ + 1;
      setWindows((prevWindows) =>
        prevWindows.map((w) => {
          if (w.id === id) {
            return { ...w, zIndex: nextZ, isMinimized: false };
          }
          return w;
        })
      );
      return nextZ;
    });
    setActiveWindowId(id);
  }, []);

  // Open window: if already open, restore and focus it immediately
  const openWindow = useCallback(
    (appId: NavItem, title: string) => {
      setHighestZIndex((prevZ) => {
        const nextZ = prevZ + 1;
        setWindows((prev) => {
          const existing = prev.find((w) => w.id === appId);
          if (existing) {
            return prev.map((w) =>
              w.id === existing.id ? { ...w, zIndex: nextZ, isMinimized: false } : w
            );
          }

          const { width: vw, height: vh } = getViewportDimensions();
          const newBounds = getDefaultWindowBounds(vw, vh, prev.length);

          const newWin: WindowState = {
            id: appId,
            appId,
            title,
            isMinimized: false,
            isMaximized: false,
            bounds: newBounds,
            zIndex: nextZ,
          };
          return [...prev, newWin];
        });
        setActiveWindowId(appId);
        return nextZ;
      });
    },
    []
  );

  // Close window: removes window and activates highest non-minimized window
  const closeWindow = useCallback(
    (id: string) => {
      setWindows((prev) => {
        const remaining = prev.filter((w) => w.id !== id);
        if (activeWindowId === id) {
          const unminimized = remaining.filter((w) => !w.isMinimized);
          if (unminimized.length > 0) {
            const topWindow = unminimized.reduce((p, c) => (p.zIndex > c.zIndex ? p : c));
            setActiveWindowId(topWindow.id);
          } else {
            setActiveWindowId(null);
          }
        }
        return remaining;
      });
    },
    [activeWindowId]
  );

  // Minimize window: marks minimized, moves focus to next highest window
  const minimizeWindow = useCallback(
    (id: string) => {
      setWindows((prev) => {
        const updated = prev.map((w) => (w.id === id ? { ...w, isMinimized: true } : w));
        if (activeWindowId === id) {
          const unminimized = updated.filter((w) => !w.isMinimized && w.id !== id);
          if (unminimized.length > 0) {
            const topWindow = unminimized.reduce((p, c) => (p.zIndex > c.zIndex ? p : c));
            setActiveWindowId(topWindow.id);
          } else {
            setActiveWindowId(null);
          }
        }
        return updated;
      });
    },
    [activeWindowId]
  );

  // Maximize / unmaximize window toggling with preserved pre-maximized bounds
  const maximizeWindow = useCallback(
    (id: string) => {
      setWindows((prev) =>
        prev.map((w) => {
          if (w.id === id) {
            const willMaximize = !w.isMaximized;
            return {
              ...w,
              isMaximized: willMaximize,
              preMaximizedBounds: willMaximize ? { ...w.bounds } : w.preMaximizedBounds,
              bounds: !willMaximize && w.preMaximizedBounds ? { ...w.preMaximizedBounds } : w.bounds,
            };
          }
          return w;
        })
      );
      focusWindow(id);
    },
    [focusWindow]
  );

  // Restore window: un-minimize and focus
  const restoreWindow = useCallback(
    (id: string) => {
      focusWindow(id);
    },
    [focusWindow]
  );

  // Update window bounds with automated clamping
  const updateWindowBounds = useCallback((id: string, partialBounds: Partial<WindowBounds>) => {
    const { width: vw, height: vh } = getViewportDimensions();
    setWindows((prev) =>
      prev.map((w) => {
        if (w.id === id) {
          const merged = { ...w.bounds, ...partialBounds };
          const clamped = clampWindowBounds(merged, vw, vh);
          return {
            ...w,
            bounds: clamped,
            // If dragging/resizing, update preMaximizedBounds if not maximized
            preMaximizedBounds: !w.isMaximized ? clamped : w.preMaximizedBounds,
          };
        }
        return w;
      })
    );
  }, []);

  // Viewport resize listener: ensure all open windows remain within usable area
  useEffect(() => {
    const handleResize = () => {
      const { width: vw, height: vh } = getViewportDimensions();
      setWindows((prev) =>
        prev.map((w) => {
          const clampedBounds = clampWindowBounds(w.bounds, vw, vh);
          const clampedPreMax = w.preMaximizedBounds
            ? clampWindowBounds(w.preMaximizedBounds, vw, vh)
            : undefined;
          return {
            ...w,
            bounds: clampedBounds,
            preMaximizedBounds: clampedPreMax,
          };
        })
      );
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Persist state safely to localStorage on change
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    try {
      const stateToPersist = serializeDesktopState(windows, activeWindowId);
      localStorage.setItem(DESKTOP_STATE_STORAGE_KEY, JSON.stringify(stateToPersist));
    } catch (e) {
      console.warn("Failed to persist desktop state:", e);
    }
  }, [windows, activeWindowId]);

  return (
    <WindowContext.Provider
      value={{
        windows,
        activeWindowId,
        openWindow,
        closeWindow,
        minimizeWindow,
        maximizeWindow,
        restoreWindow,
        focusWindow,
        updateWindowBounds,
      }}
    >
      {children}
    </WindowContext.Provider>
  );
};

export const useWindowManager = () => {
  const context = useContext(WindowContext);
  if (!context) {
    throw new Error("useWindowManager must be used within WindowProvider");
  }
  return context;
};
