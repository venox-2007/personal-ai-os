export type NavItem =
  | "desktop"
  | "home"
  | "calendar"
  | "tasks"
  | "study"
  | "research"
  | "coding"
  | "files"
  | "memory"
  | "workflows"
  | "settings";

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
  preMaximizedBounds?: WindowBounds;
}

export interface PersistedWindowState {
  id: string;
  appId: NavItem;
  title: string;
  isMinimized: boolean;
  isMaximized: boolean;
  bounds: WindowBounds;
  preMaximizedBounds?: WindowBounds;
  zIndexOrder: number; // relative ordering
}

export interface PersistedDesktopState {
  version: number;
  activeWindowId: string | null;
  windows: PersistedWindowState[];
}

export const DESKTOP_STATE_STORAGE_KEY = "personal_ai_desktop_state_v1";

export const MIN_WINDOW_WIDTH = 420;
export const MIN_WINDOW_HEIGHT = 280;

// Top bar is ~32px, Dock is ~72px, margins ~16px
export const DESKTOP_INSET = {
  top: 36,
  bottom: 80,
  left: 8,
  right: 8,
};

export const VALID_NAV_ITEMS: readonly NavItem[] = [
  "desktop",
  "home",
  "files",
  "study",
  "coding",
  "research",
  "calendar",
  "memory",
  "workflows",
] as const;

export function isValidNavItem(val: unknown): val is NavItem {
  return typeof val === "string" && (VALID_NAV_ITEMS as readonly string[]).includes(val);
}

export interface UsableArea {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}

export function getUsableArea(viewportWidth: number, viewportHeight: number): UsableArea {
  const minX = DESKTOP_INSET.left;
  const minY = DESKTOP_INSET.top;
  const maxX = Math.max(minX, viewportWidth - DESKTOP_INSET.right);
  const maxY = Math.max(minY, viewportHeight - DESKTOP_INSET.bottom);
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(0, maxX - minX),
    height: Math.max(0, maxY - minY),
  };
}

export function clampWindowBounds(
  bounds: WindowBounds,
  viewportWidth: number,
  viewportHeight: number
): WindowBounds {
  const area = getUsableArea(viewportWidth, viewportHeight);

  // 1. Constrain size
  const maxAllowedWidth = Math.max(MIN_WINDOW_WIDTH, area.width);
  const maxAllowedHeight = Math.max(MIN_WINDOW_HEIGHT, area.height);

  const width = Math.min(Math.max(MIN_WINDOW_WIDTH, Math.round(bounds.width || MIN_WINDOW_WIDTH)), maxAllowedWidth);
  const height = Math.min(Math.max(MIN_WINDOW_HEIGHT, Math.round(bounds.height || MIN_WINDOW_HEIGHT)), maxAllowedHeight);

  // 2. Constrain position: title bar must remain accessible inside usable area
  // We keep at least 120px of window width visible or the full width if smaller
  const minVisibleWidth = Math.min(120, width);
  const minX = area.minX - width + minVisibleWidth;
  const maxX = area.maxX - minVisibleWidth;
  const minY = area.minY; // Never hide title bar above top bar
  const maxY = Math.max(area.minY, area.maxY - 40); // Keep at least 40px of title bar visible vertically

  const x = Math.min(Math.max(minX, Math.round(bounds.x)), maxX);
  const y = Math.min(Math.max(minY, Math.round(bounds.y)), maxY);

  return { x, y, width, height };
}

export function getDefaultWindowBounds(
  viewportWidth: number,
  viewportHeight: number,
  cascadeIndex: number = 0,
  defaultWidth: number = 1000,
  defaultHeight: number = 700
): WindowBounds {
  const area = getUsableArea(viewportWidth, viewportHeight);
  const targetWidth = Math.min(defaultWidth, Math.max(MIN_WINDOW_WIDTH, area.width - 40));
  const targetHeight = Math.min(defaultHeight, Math.max(MIN_WINDOW_HEIGHT, area.height - 40));

  const offset = (cascadeIndex % 5) * 32;
  const initialX = area.minX + Math.max(0, (area.width - targetWidth) / 2) + offset;
  const initialY = area.minY + Math.max(0, (area.height - targetHeight) / 2) + offset;

  return clampWindowBounds(
    {
      x: initialX,
      y: initialY,
      width: targetWidth,
      height: targetHeight,
    },
    viewportWidth,
    viewportHeight
  );
}

export function validateAndSanitizePersistedState(
  raw: unknown,
  viewportWidth: number,
  viewportHeight: number
): { windows: WindowState[]; activeWindowId: string | null; highestZIndex: number } | null {
  if (!raw || typeof raw !== "object") return null;

  const data = raw as Partial<PersistedDesktopState>;
  if (!Array.isArray(data.windows)) return null;

  const sanitizedWindows: WindowState[] = [];
  const seenIds = new Set<string>();

  // Sort by zIndexOrder if present
  const sortedRaw = [...data.windows].sort((a, b) => {
    const orderA = typeof a?.zIndexOrder === "number" ? a.zIndexOrder : 0;
    const orderB = typeof b?.zIndexOrder === "number" ? b.zIndexOrder : 0;
    return orderA - orderB;
  });

  let baseZIndex = 10;

  for (const item of sortedRaw) {
    if (!item || typeof item !== "object") continue;
    if (!isValidNavItem(item.appId)) continue;
    const id = typeof item.id === "string" && item.id.trim() ? item.id : item.appId;
    if (seenIds.has(id)) continue;
    seenIds.add(id);

    const title = typeof item.title === "string" && item.title.trim() ? item.title : String(item.appId);
    const isMinimized = Boolean(item.isMinimized);
    const isMaximized = Boolean(item.isMaximized);

    const rawBounds = item.bounds && typeof item.bounds === "object" ? item.bounds : ({} as any);
    const bounds = clampWindowBounds(
      {
        x: Number.isFinite(rawBounds.x) ? rawBounds.x : 50,
        y: Number.isFinite(rawBounds.y) ? rawBounds.y : 50,
        width: Number.isFinite(rawBounds.width) ? rawBounds.width : 900,
        height: Number.isFinite(rawBounds.height) ? rawBounds.height : 600,
      },
      viewportWidth,
      viewportHeight
    );

    let preMaximizedBounds: WindowBounds | undefined = undefined;
    if (item.preMaximizedBounds && typeof item.preMaximizedBounds === "object") {
      preMaximizedBounds = clampWindowBounds(
        {
          x: Number.isFinite(item.preMaximizedBounds.x) ? item.preMaximizedBounds.x : bounds.x,
          y: Number.isFinite(item.preMaximizedBounds.y) ? item.preMaximizedBounds.y : bounds.y,
          width: Number.isFinite(item.preMaximizedBounds.width) ? item.preMaximizedBounds.width : bounds.width,
          height: Number.isFinite(item.preMaximizedBounds.height) ? item.preMaximizedBounds.height : bounds.height,
        },
        viewportWidth,
        viewportHeight
      );
    }

    baseZIndex += 1;
    sanitizedWindows.push({
      id,
      appId: item.appId,
      title,
      isMinimized,
      isMaximized,
      bounds,
      preMaximizedBounds,
      zIndex: baseZIndex,
    });
  }

  // Active window ID validation
  let activeId: string | null = null;
  if (typeof data.activeWindowId === "string" && seenIds.has(data.activeWindowId)) {
    const candidate = sanitizedWindows.find((w) => w.id === data.activeWindowId);
    if (candidate && !candidate.isMinimized) {
      activeId = candidate.id;
    }
  }

  // If active window was not found or was minimized, pick top unminimized window
  if (!activeId) {
    const unminimized = sanitizedWindows.filter((w) => !w.isMinimized);
    if (unminimized.length > 0) {
      const top = unminimized.reduce((p, c) => (p.zIndex > c.zIndex ? p : c));
      activeId = top.id;
    }
  }

  return {
    windows: sanitizedWindows,
    activeWindowId: activeId,
    highestZIndex: baseZIndex,
  };
}

export function serializeDesktopState(
  windows: WindowState[],
  activeWindowId: string | null
): PersistedDesktopState {
  // Sort windows by zIndex to preserve relative stacking order cleanly
  const sorted = [...windows].sort((a, b) => a.zIndex - b.zIndex);

  const persistedWindows: PersistedWindowState[] = sorted.map((w, index) => ({
    id: w.id,
    appId: w.appId,
    title: w.title,
    isMinimized: w.isMinimized,
    isMaximized: w.isMaximized,
    bounds: { ...w.bounds },
    preMaximizedBounds: w.preMaximizedBounds ? { ...w.preMaximizedBounds } : undefined,
    zIndexOrder: index,
  }));

  return {
    version: 1,
    activeWindowId,
    windows: persistedWindows,
  };
}
