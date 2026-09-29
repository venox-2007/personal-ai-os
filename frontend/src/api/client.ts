import { AgentActivityEvent, HealthCheckData } from "../types";

export interface ChatResponsePayload {
  conversation_id: string;
  response: string;
  activities: AgentActivityEvent[];
  tool_calls?: any[];
  status?: string;
  metadata: Record<string, any>;
}

export async function checkHealth(): Promise<HealthCheckData | null> {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("Health check failed");
    return await res.json();
  } catch (error) {
    console.warn("Backend not yet reachable on /health:", error);
    return null;
  }
}

export async function sendChatMessage(
  message: string,
  conversationId?: string
): Promise<ChatResponsePayload> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId || undefined,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to communicate with orchestrator");
  }

  return await res.json();
}

export async function fetchAgents(): Promise<any[]> {
  try {
    const res = await fetch("/api/agents");
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchTools(): Promise<any[]> {
  try {
    const res = await fetch("/api/tools");
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchMemoryStats(): Promise<Record<string, any>> {
  try {
    const res = await fetch("/api/memory/stats");
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}
