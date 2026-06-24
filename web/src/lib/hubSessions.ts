import type { ThinkingStep } from "@/lib/thinkingTrace";
import type { Task } from "@/lib/api";

export type HubLogItem = {
  id: string;
  role: "user" | "system";
  text: string;
  thinking?: ThinkingStep[];
  thinkingOpen?: boolean;
  status?: "thinking" | "done" | "error";
  taskId?: string;
  confirmTask?: Task;
  taskSnapshot?: Task;
};

export type HubSession = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  logs: HubLogItem[];
};

const STORAGE_KEY = "sensehub_hub_sessions";
const MAX_SESSIONS = 40;

export function sessionTitleFromLogs(logs: HubLogItem[]): string {
  const first = logs.find((l) => l.role === "user" && l.text.trim())?.text.trim();
  if (!first) return "新对话";
  return first.length > 28 ? `${first.slice(0, 28)}…` : first;
}

export function loadHubSessions(): HubSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data
      .filter((s) => s && typeof s.id === "string" && Array.isArray(s.logs))
      .map((s) => ({
        id: String(s.id),
        title: String(s.title || "新对话"),
        createdAt: Number(s.createdAt) || Date.now(),
        updatedAt: Number(s.updatedAt) || Date.now(),
        logs: s.logs as HubLogItem[],
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export function saveHubSessions(sessions: HubSession[]): void {
  const trimmed = sessions
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_SESSIONS);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

export function upsertHubSession(sessions: HubSession[], session: HubSession): HubSession[] {
  const rest = sessions.filter((s) => s.id !== session.id);
  return [session, ...rest].sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_SESSIONS);
}

export function createHubSession(id?: string): HubSession {
  const now = Date.now();
  return { id: id || crypto.randomUUID(), title: "新对话", createdAt: now, updatedAt: now, logs: [] };
}

export function serverSessionToHub(s: { session_id: string; title: string; updated_at?: string; created_at?: string }): HubSession {
  const updated = s.updated_at ? Date.parse(s.updated_at) : Date.now();
  const created = s.created_at ? Date.parse(s.created_at) : updated;
  return { id: s.session_id, title: s.title || "新对话", createdAt: created, updatedAt: updated, logs: [] };
}

export function messagesToLogs(messages: Array<{ role: string; content: string }>): HubLogItem[] {
  return messages.map((m, i) => ({
    id: `srv-${i}-${Date.now()}`,
    role: m.role === "user" ? "user" : "system",
    text: m.content,
    status: "done" as const,
  }));
}
