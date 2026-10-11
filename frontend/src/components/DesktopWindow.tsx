import React, { useRef, useEffect, useState, useCallback } from "react";
import { motion, useDragControls } from "framer-motion";
import { X, Minus, Maximize2, Minimize2 } from "lucide-react";
import { useWindowManager, WindowState } from "../lib/WindowContext";
import {
  clampWindowBounds,
  getUsableArea,
  MIN_WINDOW_WIDTH,
  MIN_WINDOW_HEIGHT,
} from "../lib/windowUtils";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: any[]) {
  return twMerge(clsx(inputs));
}

interface DesktopWindowProps {
  windowState: WindowState;
  children: React.ReactNode;
}

export const DesktopWindow: React.FC<DesktopWindowProps> = ({ windowState, children }) => {
  const { id, title, isMinimized, isMaximized, bounds, zIndex } = windowState;
  const {
    closeWindow,
    minimizeWindow,
    maximizeWindow,
    focusWindow,
    updateWindowBounds,
    activeWindowId,
  } = useWindowManager();

  const windowRef = useRef<HTMLDivElement>(null);
  const dragControls = useDragControls();
  const isActive = activeWindowId === id;

  const [viewportSize, setViewportSize] = useState({
    width: typeof window !== "undefined" ? window.innerWidth : 1920,
    height: typeof window !== "undefined" ? window.innerHeight : 1080,
  });

  const [isInteracting, setIsInteracting] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setViewportSize({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const usableArea = getUsableArea(viewportSize.width, viewportSize.height);

  // Drag end with boundary clamping
  const handleDragEnd = useCallback(
    (_: any, info: { offset: { x: number; y: number } }) => {
      setIsInteracting(false);
      if (!isMaximized) {
        const rawNewX = bounds.x + info.offset.x;
        const rawNewY = bounds.y + info.offset.y;
        const clamped = clampWindowBounds(
          { ...bounds, x: rawNewX, y: rawNewY },
          viewportSize.width,
          viewportSize.height
        );
        updateWindowBounds(id, { x: clamped.x, y: clamped.y });
      }
    },
    [bounds, id, isMaximized, updateWindowBounds, viewportSize]
  );

  // Resize handler for edges/corners
  const startResize = useCallback(
    (e: React.PointerEvent, direction: "se" | "e" | "s" | "w" | "sw") => {
      e.stopPropagation();
      e.preventDefault();
      focusWindow(id);
      setIsInteracting(true);

      const startX = e.clientX;
      const startY = e.clientY;
      const startBounds = { ...bounds };

      const onPointerMove = (moveEvent: PointerEvent) => {
        const deltaX = moveEvent.clientX - startX;
        const deltaY = moveEvent.clientY - startY;

        let nextWidth = startBounds.width;
        let nextHeight = startBounds.height;
        let nextX = startBounds.x;
        let nextY = startBounds.y;

        if (direction === "se" || direction === "e") {
          nextWidth = Math.max(MIN_WINDOW_WIDTH, startBounds.width + deltaX);
        }
        if (direction === "se" || direction === "s" || direction === "sw") {
          nextHeight = Math.max(MIN_WINDOW_HEIGHT, startBounds.height + deltaY);
        }
        if (direction === "w" || direction === "sw") {
          const proposedWidth = startBounds.width - deltaX;
          if (proposedWidth >= MIN_WINDOW_WIDTH) {
            nextWidth = proposedWidth;
            nextX = startBounds.x + deltaX;
          } else {
            nextWidth = MIN_WINDOW_WIDTH;
            nextX = startBounds.x + (startBounds.width - MIN_WINDOW_WIDTH);
          }
        }

        const clamped = clampWindowBounds(
          { x: nextX, y: nextY, width: nextWidth, height: nextHeight },
          viewportSize.width,
          viewportSize.height
        );
        updateWindowBounds(id, clamped);
      };

      const onPointerUp = () => {
        setIsInteracting(false);
        document.removeEventListener("pointermove", onPointerMove);
        document.removeEventListener("pointerup", onPointerUp);
      };

      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", onPointerUp);
    },
    [bounds, focusWindow, id, updateWindowBounds, viewportSize]
  );

  if (isMinimized) return null;

  return (
    <motion.div
      ref={windowRef}
      drag={!isMaximized}
      dragControls={dragControls}
      dragListener={false}
      dragMomentum={false}
      dragElastic={0}
      onPointerDown={() => focusWindow(id)}
      onDragStart={() => setIsInteracting(true)}
      onDragEnd={handleDragEnd}
      initial={false}
      animate={{
        x: isMaximized ? usableArea.minX : bounds.x,
        y: isMaximized ? usableArea.minY : bounds.y,
        width: isMaximized ? usableArea.width : bounds.width,
        height: isMaximized ? usableArea.height : bounds.height,
        opacity: 1,
        scale: 1,
      }}
      transition={{ type: "spring", bounce: 0, duration: 0.18 }}
      style={{
        zIndex,
        position: "absolute",
        top: 0,
        left: 0,
      }}
      className={cn(
        "flex flex-col bg-surface/90 backdrop-blur-xl border-white/10 shadow-2xl overflow-hidden select-none",
        isMaximized ? "rounded-lg border border-white/10" : "rounded-xl border",
        isActive
          ? "ring-1 ring-brand-500/50 shadow-brand-950/40"
          : "opacity-95 grayscale-[8%] border-white/5"
      )}
    >
      {/* Title Bar */}
      <div
        className={cn(
          "h-11 shrink-0 flex items-center justify-between px-4 border-b transition-colors cursor-move",
          isActive ? "bg-slate-900/70 border-brand-500/20" : "bg-slate-900/40 border-white/5",
          isMaximized && "cursor-default"
        )}
        onPointerDown={(e) => {
          focusWindow(id);
          if (!isMaximized) {
            dragControls.start(e);
          }
        }}
        onDoubleClick={() => maximizeWindow(id)}
      >
        <div className="flex items-center gap-2.5 truncate">
          <div
            className={cn(
              "w-2 h-2 rounded-full transition-colors",
              isActive ? "bg-brand-400 shadow-[0_0_6px_rgba(96,165,250,0.6)]" : "bg-slate-600"
            )}
          />
          <span
            className={cn(
              "font-medium text-xs tracking-wide truncate",
              isActive ? "text-slate-100 font-semibold" : "text-slate-400"
            )}
          >
            {title}
          </span>
        </div>

        {/* Window Controls */}
        <div className="flex items-center gap-1.5" onPointerDown={(e) => e.stopPropagation()}>
          <button
            title="Minimize"
            onClick={(e) => {
              e.stopPropagation();
              minimizeWindow(id);
            }}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            title={isMaximized ? "Restore Window" : "Maximize Window"}
            onClick={(e) => {
              e.stopPropagation();
              maximizeWindow(id);
            }}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            {isMaximized ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            title="Close"
            onClick={(e) => {
              e.stopPropagation();
              closeWindow(id);
            }}
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 relative overflow-hidden bg-slate-950/30 select-text">
        {/* Transparent overlay during drag/resize prevents iframe/content pointer event capturing */}
        {isInteracting && <div className="absolute inset-0 z-50 pointer-events-auto bg-transparent" />}
        <div className="absolute inset-0 overflow-auto">{children}</div>
      </div>

      {/* Resize Handles (Only when not maximized) */}
      {!isMaximized && (
        <>
          {/* Right edge */}
          <div
            className="absolute top-11 right-0 w-2 bottom-2 cursor-e-resize z-40"
            onPointerDown={(e) => startResize(e, "e")}
          />
          {/* Bottom edge */}
          <div
            className="absolute bottom-0 left-2 right-2 h-2 cursor-s-resize z-40"
            onPointerDown={(e) => startResize(e, "s")}
          />
          {/* Left edge */}
          <div
            className="absolute top-11 left-0 w-2 bottom-2 cursor-w-resize z-40"
            onPointerDown={(e) => startResize(e, "w")}
          />
          {/* Bottom-left corner */}
          <div
            className="absolute bottom-0 left-0 w-3 h-3 cursor-sw-resize z-50"
            onPointerDown={(e) => startResize(e, "sw")}
          />
          {/* Bottom-right corner (primary diagonal grip) */}
          <div
            className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-50 flex items-end justify-end p-0.5 group"
            onPointerDown={(e) => startResize(e, "se")}
          >
            <div className="w-2 h-2 border-r border-b border-white/20 group-hover:border-white/50 transition-colors" />
          </div>
        </>
      )}
    </motion.div>
  );
};
