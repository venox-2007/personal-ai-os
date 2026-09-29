import { useState, useEffect } from "react";
import { AppLayout } from "./layouts/AppLayout";
import { HomePage } from "./pages/HomePage";
import { PlaceholderView } from "./pages/PlaceholderView";
import { NavItem } from "./components/Sidebar";
import { ChatMessage, AgentActivityEvent, HealthCheckData } from "./types";
import { checkHealth, sendChatMessage } from "./api/client";

export function App() {
  const [activeTab, setActiveTab] = useState<NavItem>("home");
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
      };

      setMessages((prev) => [...prev, assistantMsg]);
      // Update global activity feed
      setActivities((prev) => [...res.activities, ...prev]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        role: "assistant",
        content: `⚠️ Failed to contact Orchestrator: ${err.message || "Unknown error"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectMessageActivities = (msg: ChatMessage) => {
    if (msg.activities && msg.activities.length > 0) {
      setActivities(msg.activities);
    }
  };

  return (
    <AppLayout activeTab={activeTab} onSelectTab={setActiveTab} health={health}>
      {activeTab === "home" ? (
        <HomePage
          messages={messages}
          activities={activities}
          isLoading={isLoading}
          onSendMessage={handleSendMessage}
          onSelectMessageActivities={handleSelectMessageActivities}
        />
      ) : (
        <PlaceholderView tab={activeTab} />
      )}
    </AppLayout>
  );
}

export default App;
