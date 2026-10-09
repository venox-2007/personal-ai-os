import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { NavItem } from "../components/Sidebar";

export interface WindowBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface WindowState {
  id: string; // Used as the NavItem appId
  appId: NavItem;
  title: string;
  isMinimized: boolean;
  isMaximized: boolean;
  bounds: WindowBounds;
  zIndex: number;
}

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

const DEFAULT_WIDTH = 1000;
const DEFAULT_HEIGHT = 700;

export const WindowProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [activeWindowId, setActiveWindowId] = useState<string | null>(null);
  const [highestZIndex, setHighestZIndex] = useState(10);

  const focusWindow = useCallback((id: string) => {
    setHighestZIndex((prev) => prev + 1);
    setWindows((prev) =>
      prev.map((w) => {
        if (w.id === id) {
          return { ...w, zIndex: highestZIndex + 1, isMinimized: false };
        }
        return w;
      })
    );
    setActiveWindowId(id);
  }, [highestZIndex]);

  const openWindow = useCallback((appId: NavItem, title: string) => {
    setWindows((prev) => {
      const existing = prev.find((w) => w.id === appId);
      if (existing) {
        // If it exists, focus it asynchronously after state render
        setTimeout(() => focusWindow(existing.id), 0);
        return prev;
      }
      
      // Calculate initial position (centered with slight cascade if needed)
      const offset = (prev.length % 5) * 40;
      // Estimate screen size
      const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
      const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
      
      const newWin: WindowState = {
        id: appId, // For now, 1 instance per app
        appId,
        title,
        isMinimized: false,
        isMaximized: false,
        bounds: {
          x: Math.max(10, (vw - DEFAULT_WIDTH) / 2 + offset),
          y: Math.max(10, (vh - DEFAULT_HEIGHT) / 2 + offset - 40), // slightly higher because of dock
          width: DEFAULT_WIDTH,
          height: DEFAULT_HEIGHT,
        },
        zIndex: highestZIndex + 1,
      };
      
      setHighestZIndex((z) => z + 1);
      setActiveWindowId(appId);
      return [...prev, newWin];
    });
  }, [highestZIndex, focusWindow]);

  const closeWindow = useCallback((id: string) => {
    setWindows((prev) => {
      const remaining = prev.filter((w) => w.id !== id);
      if (activeWindowId === id) {
        // Focus the highest z-index window that isn't minimized
        const unminimized = remaining.filter((w) => !w.isMinimized);
        if (unminimized.length > 0) {
          const topWindow = unminimized.reduce((prev, current) => 
            (prev.zIndex > current.zIndex) ? prev : current
          );
          setActiveWindowId(topWindow.id);
        } else {
          setActiveWindowId(null);
        }
      }
      return remaining;
    });
  }, [activeWindowId]);

  const minimizeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.map((w) => w.id === id ? { ...w, isMinimized: true } : w));
    
    // Switch focus
    if (activeWindowId === id) {
       setWindows((prev) => {
         const unminimized = prev.filter((w) => !w.isMinimized && w.id !== id);
         if (unminimized.length > 0) {
           const topWindow = unminimized.reduce((p, c) => (p.zIndex > c.zIndex) ? p : c);
           setActiveWindowId(topWindow.id);
         } else {
           setActiveWindowId(null);
         }
         return prev;
       });
    }
  }, [activeWindowId]);

  const maximizeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.map((w) => w.id === id ? { ...w, isMaximized: !w.isMaximized } : w));
    focusWindow(id);
  }, [focusWindow]);

  const restoreWindow = useCallback((id: string) => {
    focusWindow(id);
  }, [focusWindow]);

  const updateWindowBounds = useCallback((id: string, bounds: Partial<WindowBounds>) => {
    setWindows((prev) => prev.map((w) => w.id === id ? { ...w, bounds: { ...w.bounds, ...bounds } } : w));
  }, []);

  return (
    <WindowContext.Provider value={{
      windows,
      activeWindowId,
      openWindow,
      closeWindow,
      minimizeWindow,
      maximizeWindow,
      restoreWindow,
      focusWindow,
      updateWindowBounds
    }}>
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
