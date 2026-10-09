import { useState, useEffect } from "react";
import { AppLayout } from "./layouts/AppLayout";
import { WindowProvider } from "./lib/WindowContext";
import { WindowManager } from "./components/WindowManager";
import { ChatMessage, AgentActivityEvent, HealthCheckData } from "./types";
import { checkHealth, sendChatMessage, approveAction, rejectAction } from "./api/client";

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activities, setActivities] = useState<AgentActivityEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [health, setHealth] = useState<HealthCheckData | null>(null);

  // Poll backend health status
  useEffect(() => {
    let isMounted = true;
    const updateHealth = async () => {
      const data = await checkHealth();
      if (isMounted) setHealth(data);
    };

    updateHealth();
    const interval = setInterval(updateHealth, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSendMessage = async (text: string) => {
    const userMsgId = `user_${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await sendChatMessage(text, conversationId);
      setConversationId(res.conversation_id);

      const assistantMsg: ChatMessage = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: res.response,
        timestamp: new Date().toISOString(),
        activities: res.activities,
        tool_calls: res.tool_calls,
        status: res.status,
        approval: res.approval,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (res.activities && res.activities.length > 0) {
        setActivities((prev) => [...res.activities, ...prev]);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `❌ Failed to contact Orchestrator: ${err.message || "Unknown error"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveAction = async (approvalId: string, reason?: string) => {
    try {
      const res = await approveAction(approvalId, reason);

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.approval && msg.approval.id === approvalId) {
            return {
              ...msg,
              approval: {
                ...msg.approval,
                status: "approved",
                resolved_at: new Date().toISOString(),
              },
            };
          }
          return msg;
        })
      );

      const resumeMsg: ChatMessage = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: res.response,
        timestamp: new Date().toISOString(),
        activities: res.activities,
        tool_calls: res.tool_calls,
        status: "completed",
      };
      setMessages((prev) => [...prev, resumeMsg]);

      if (res.activities && res.activities.length > 0) {
        setActivities((prev) => [...res.activities, ...prev]);
      }
    } catch (err: any) {
      console.error("Failed to approve action:", err);
      throw err;
    }
  };

  const handleRejectAction = async (approvalId: string, reason?: string) => {
    try {
      const res = await rejectAction(approvalId, reason);

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.approval && msg.approval.id === approvalId) {
            return {
              ...msg,
              approval: {
                ...msg.approval,
                status: "rejected",
                resolved_at: new Date().toISOString(),
              },
            };
          }
          return msg;
        })
      );

      const rejectMsg: ChatMessage = {
        id: `asst_${Date.now()}`,
        role: "assistant",
        content: res.response,
        timestamp: new Date().toISOString(),
        activities: res.activities,
        tool_calls: res.tool_calls,
        status: "rejected",
      };
      setMessages((prev) => [...prev, rejectMsg]);

      if (res.activities && res.activities.length > 0) {
        setActivities((prev) => [...res.activities, ...prev]);
      }
    } catch (err: any) {
      console.error("Failed to reject action:", err);
      throw err;
    }
  };

  const handleSelectMessageActivities = (msg: ChatMessage) => {
    if (msg.activities && msg.activities.length > 0) {
      setActivities(msg.activities);
    }
  };

  return (
    <WindowProvider>
      <AppLayout
        health={health}
        activities={activities}
        isLoading={isLoading}
      >
        <WindowManager
          messages={messages}
          activities={activities}
          isLoading={isLoading}
          onSendMessage={handleSendMessage}
          onSelectMessageActivities={handleSelectMessageActivities}
          onApproveAction={handleApproveAction}
          onRejectAction={handleRejectAction}
        />
      </AppLayout>
    </WindowProvider>
  );
}
