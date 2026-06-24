import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { STUDIO_MODELS } from "@/lib/siteContent";
import {
  createStudioSession,
  loadStudioSessions,
  saveStudioSessions,
  studioTitleFromMessages,
  upsertStudioSession,
  type StudioMessage,
  type StudioSession,
} from "@/lib/studioSessions";
import { api } from "@/lib/api";

type StudioCtx = {
  modelId: string;
  setModelId: (id: string) => void;
  selectedModel: (typeof STUDIO_MODELS)[number];
  sessions: StudioSession[];
  sessionId: string;
  messages: StudioMessage[];
  setMessages: (msgs: StudioMessage[]) => void;
  newChat: () => void;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  persistMessages: (msgs: StudioMessage[]) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
};

const StudioContext = createContext<StudioCtx | null>(null);

export function StudioProvider({ children }: { children: ReactNode }) {
  const [modelId, setModelId] = useState<string>(STUDIO_MODELS[0]?.id ?? "qwen3-8b");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const initial = loadStudioSessions();
  const bootstrap = initial[0] ?? createStudioSession();
  const [sessions, setSessions] = useState<StudioSession[]>(initial.length ? initial : [bootstrap]);
  const [sessionId, setSessionId] = useState(bootstrap.id);
  const [messages, setMessages] = useState<StudioMessage[]>(bootstrap.messages);

  const selectedModel = STUDIO_MODELS.find((m) => m.id === modelId) ?? STUDIO_MODELS[0];

  const persist = useCallback((nextSessions: StudioSession[]) => {
    setSessions(nextSessions);
    saveStudioSessions(nextSessions);
  }, []);

  const persistMessages = useCallback(
    (msgs: StudioMessage[]) => {
      setMessages(msgs);
      setSessions((prev) => {
        const current = prev.find((s) => s.id === sessionId) ?? createStudioSession(sessionId);
        const updated: StudioSession = {
          ...current,
          messages: msgs,
          title: studioTitleFromMessages(msgs),
          updatedAt: Date.now(),
        };
        const next = upsertStudioSession(prev, updated);
        saveStudioSessions(next);
        return next;
      });
    },
    [sessionId]
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.listSessions("studio");
        if (cancelled || !res.sessions?.length) return;
        const mapped = res.sessions.map((s) => {
          const local = loadStudioSessions().find((x) => x.serverId === s.session_id);
          return (
            local ?? {
              ...createStudioSession(),
              serverId: s.session_id,
              title: s.title || "新对话",
            }
          );
        });
        persist(mapped);
        setSessionId(mapped[0].id);
        setMessages(mapped[0].messages);
      } catch {
        /* offline */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [persist]);

  const newChat = useCallback(() => {
    const s = createStudioSession();
    persist(upsertStudioSession(sessions, s));
    setSessionId(s.id);
    setMessages([]);
    void api.createSession("", "studio").then((r) => {
      setSessions((prev) => {
        const next = prev.map((x) => (x.id === s.id ? { ...x, serverId: r.session_id } : x));
        saveStudioSessions(next);
        return next;
      });
    }).catch(() => {});
  }, [persist, sessions]);

  const switchSession = useCallback(
    (id: string) => {
      const s = sessions.find((x) => x.id === id);
      if (!s) return;
      setSessionId(id);
      setMessages(s.messages);
      const sid = s.serverId;
      if (!sid) return;
      void api.getSession(sid).then((detail) => {
        const msgs: StudioMessage[] = detail.messages.map((m) => ({
          role: m.role === "user" ? "user" : "assistant",
          content: m.content,
        }));
        setMessages(msgs);
        persist(upsertStudioSession(sessions, { ...s, messages: msgs, updatedAt: Date.now() }));
      }).catch(() => {});
    },
    [persist, sessions]
  );

  const deleteSession = useCallback(
    (id: string) => {
      const target = sessions.find((s) => s.id === id);
      if (target?.serverId) void api.deleteSession(target.serverId).catch(() => {});
      const next = sessions.filter((s) => s.id !== id);
      const fallback = next[0] ?? createStudioSession();
      const list = next.length ? next : [fallback];
      persist(list);
      setSessionId(fallback.id);
      setMessages(fallback.messages);
    },
    [persist, sessions]
  );

  return (
    <StudioContext.Provider
      value={{
        modelId,
        setModelId,
        selectedModel,
        sessions,
        sessionId,
        messages,
        setMessages,
        newChat,
        switchSession,
        deleteSession,
        persistMessages,
        sidebarOpen,
        setSidebarOpen,
      }}
    >
      {children}
    </StudioContext.Provider>
  );
}

export function useStudio() {
  const ctx = useContext(StudioContext);
  if (!ctx) throw new Error("useStudio must be used within StudioProvider");
  return ctx;
}
