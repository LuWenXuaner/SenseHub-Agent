export type StudioMessage = { role: "user" | "assistant"; content: string };

export type StudioSession = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: StudioMessage[];
  serverId?: string;
};

const STORAGE_KEY = "sensehub_studio_sessions";
const MAX = 40;

export function studioTitleFromMessages(messages: StudioMessage[]): string {
  const first = messages.find((m) => m.role === "user" && m.content.trim())?.content.trim();
  if (!first) return "新对话";
  return first.length > 28 ? `${first.slice(0, 28)}…` : first;
}

export function loadStudioSessions(): StudioSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data
      .filter((s) => s && typeof s.id === "string" && Array.isArray(s.messages))
      .map((s) => ({
        id: String(s.id),
        title: String(s.title || "新对话"),
        createdAt: Number(s.createdAt) || Date.now(),
        updatedAt: Number(s.updatedAt) || Date.now(),
        messages: s.messages as StudioMessage[],
        serverId: s.serverId ? String(s.serverId) : undefined,
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export function saveStudioSessions(sessions: StudioSession[]): void {
  const trimmed = sessions.sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

export function createStudioSession(id?: string): StudioSession {
  const now = Date.now();
  return { id: id || crypto.randomUUID(), title: "新对话", createdAt: now, updatedAt: now, messages: [] };
}

export function upsertStudioSession(sessions: StudioSession[], session: StudioSession): StudioSession[] {
  return [session, ...sessions.filter((s) => s.id !== session.id)].slice(0, MAX);
}
