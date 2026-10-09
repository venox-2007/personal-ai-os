import React from "react";
import { useWindowManager } from "../lib/WindowContext";
import { DesktopWindow } from "./DesktopWindow";
import { NavItem } from "./Sidebar";
import { DesktopOverview } from "../pages/DesktopOverview";
import { HomePage } from "../pages/HomePage";
import { FilesView } from "../pages/FilesView";
import { StudyView } from "../pages/StudyView";
import { CodingView } from "../pages/CodingView";
import { ResearchView } from "../pages/ResearchView";
import { CalendarView } from "../pages/CalendarView";
import { MemoryView } from "../pages/MemoryView";
import { ChatMessage, AgentActivityEvent } from "../types";
import { PlaceholderView } from "../pages/PlaceholderView";

interface WindowManagerProps {
  messages: ChatMessage[];
  activities: AgentActivityEvent[];
  isLoading: boolean;
  onSendMessage: (text: string) => Promise<void>;
  onSelectMessageActivities: (msg: ChatMessage) => void;
  onApproveAction: (id: string, reason?: string) => Promise<void>;
  onRejectAction: (id: string, reason?: string) => Promise<void>;
}

export const WindowManager: React.FC<WindowManagerProps> = (props) => {
  const { windows, openWindow } = useWindowManager();

  const renderAppContent = (appId: NavItem) => {
    switch (appId) {
      case "desktop":
        return <DesktopOverview onSelectTab={(id) => openWindow(id, "App")} recentActivities={props.activities} />;
      case "home":
        return (
          <HomePage
            messages={props.messages}
            activities={props.activities}
            isLoading={props.isLoading}
            onSendMessage={props.onSendMessage}
            onSelectMessageActivities={props.onSelectMessageActivities}
            onApproveAction={props.onApproveAction}
            onRejectAction={props.onRejectAction}
          />
        );
      case "files":
        return <FilesView />;
      case "study":
        return <StudyView />;
      case "coding":
        return <CodingView />;
      case "research":
        return <ResearchView />;
      case "calendar":
        return <CalendarView onSendMessage={props.onSendMessage} onSelectTab={(id) => openWindow(id, "App")} />;
      case "memory":
        return <MemoryView />;
      default:
        return <PlaceholderView tab={appId as any} />;
    }
  };

  return (
    <>
      {windows.map((win) => (
        <DesktopWindow key={win.id} windowState={win}>
          {renderAppContent(win.appId)}
        </DesktopWindow>
      ))}
    </>
  );
};
