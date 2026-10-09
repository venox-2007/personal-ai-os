import React, { useRef, useEffect, useState } from "react";
import { motion, useDragControls } from "framer-motion";
import { X, Minus, Maximize2, Minimize2 } from "lucide-react";
import { useWindowManager, WindowState } from "../lib/WindowContext";
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
  const { closeWindow, minimizeWindow, maximizeWindow, focusWindow, updateWindowBounds, activeWindowId } = useWindowManager();
  
  const windowRef = useRef<HTMLDivElement>(null);
  const dragControls = useDragControls();
  const isActive = activeWindowId === id;

  // Handle constraints
  const [windowSize, setWindowSize] = useState({ width: window.innerWidth, height: window.innerHeight });
  useEffect(() => {
    const handleResize = () => setWindowSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

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
      onDragEnd={(_, info) => {
        if (!isMaximized) {
          // Keep it on screen
          let newX = bounds.x + info.offset.x;
          let newY = bounds.y + info.offset.y;
          
          // Basic bounds checking (prevent losing title bar)
          newY = Math.max(0, Math.min(newY, windowSize.height - 40));
          newX = Math.max(-bounds.width + 100, Math.min(newX, windowSize.width - 100));
          
          updateWindowBounds(id, { x: newX, y: newY });
        }
      }}
      initial={false}
      animate={{
        x: isMaximized ? 0 : bounds.x,
        y: isMaximized ? 0 : bounds.y,
        width: isMaximized ? "100%" : bounds.width,
        height: isMaximized ? "100%" : bounds.height,
        opacity: 1,
        scale: 1,
      }}
      transition={{ type: "spring", bounce: 0, duration: 0.2 }}
      style={{
        zIndex,
        position: "absolute",
        top: 0,
        left: 0,
      }}
      className={cn(
        "flex flex-col bg-surface/90 backdrop-blur-xl border-white/10 shadow-2xl overflow-hidden",
        isMaximized ? "rounded-none border-0" : "rounded-xl border",
        isActive ? "ring-1 ring-brand-500/50 shadow-brand-900/20" : "opacity-95 grayscale-[10%]"
      )}
    >
      {/* Title Bar */}
      <div
        className={cn(
          "h-12 shrink-0 flex items-center justify-between px-4 border-b transition-colors select-none",
          isActive ? "bg-slate-900/60 border-brand-500/20" : "bg-slate-900/40 border-white/5"
        )}
        onPointerDown={(e) => {
          focusWindow(id);
          if (!isMaximized) {
            dragControls.start(e);
          }
        }}
        onDoubleClick={() => maximizeWindow(id)}
      >
        <div className="flex items-center gap-3">
          <span className={cn("font-medium text-sm", isActive ? "text-slate-200" : "text-slate-400")}>
            {title}
          </span>
        </div>
        
        <div className="flex items-center gap-2" onPointerDown={(e) => e.stopPropagation()}>
          <button
            onClick={(e) => { e.stopPropagation(); minimizeWindow(id); }}
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            <Minus className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); maximizeWindow(id); }}
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
          >
            {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); closeWindow(id); }}
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 relative overflow-hidden bg-slate-950/20">
        {/* We use pointer-events-none on a glassy overlay when dragging to prevent iframe/content stealing pointer, but framer motion drag handles this well if we use onPointerDown correctly */}
        <div className="absolute inset-0 overflow-auto">
          {children}
        </div>
      </div>
      
      {/* Basic Resizer (Bottom Right) */}
      {!isMaximized && (
        <div
          className="absolute bottom-0 right-0 w-6 h-6 cursor-se-resize z-50"
          onPointerDown={(e) => {
            e.stopPropagation();
            focusWindow(id);
            const startX = e.clientX;
            const startY = e.clientY;
            const startWidth = bounds.width;
            const startHeight = bounds.height;
            
            const handlePointerMove = (moveEvent: PointerEvent) => {
              const newWidth = Math.max(400, startWidth + (moveEvent.clientX - startX));
              const newHeight = Math.max(300, startHeight + (moveEvent.clientY - startY));
              updateWindowBounds(id, { width: newWidth, height: newHeight });
            };
            
            const handlePointerUp = () => {
              document.removeEventListener("pointermove", handlePointerMove);
              document.removeEventListener("pointerup", handlePointerUp);
            };
            
            document.addEventListener("pointermove", handlePointerMove);
            document.addEventListener("pointerup", handlePointerUp);
          }}
        />
      )}
    </motion.div>
  );
};
