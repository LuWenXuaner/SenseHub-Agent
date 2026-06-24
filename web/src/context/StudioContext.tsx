import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { STUDIO_MODELS, type StudioModelItem } from "@/lib/siteContent";
import {
  createStudioSession,
  loadStudioSessions,
  saveStudioSessions,
  studioTitleFromMessages,
  upsertStudioSession,
  type StudioMessage,
  type StudioSession,
} from "@/lib/studioSessions";
import { userStorageScope } from "@/lib/userScope";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

type StudioCtx = {
  modelId: string;
  setModelId: (id: string) => void;
  selectedModel: StudioModelItem;
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
  const { user } = useAuth();
  const scope = userStorageScope(user?.username);
  const [modelId, setModelId] = useState<string>(STUDIO_MODELS[0]?.id ?? "qwen3-8b");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState<StudioSession[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<StudioMessage[]>([]);

  const selectedModel = STUDIO_MODELS.find((m) => m.id === modelId) ?? STUDIO_MODELS[0];

  const persist = useCallback(
    (nextSessions: StudioSession[]) => {
      setSessions(nextSessions);
      saveStudioSessions(nextSessions, scope);
    },
    [scope]
  );

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
        saveStudioSessions(next, scope);
        return next;
      });
    },
    [sessionId, scope]
  );

  useEffect(() => {
    let cancelled = false;
    const initial = loadStudioSessions(scope);
    const bootstrap = initial[0] ?? createStudioSession();
    const list = initial.length ? initial : [bootstrap];
    setSessions(list);
    setSessionId(bootstrap.id);
    setMessages(bootstrap.messages);

    void (async () => {
      try {
        const res = await api.listSessions("studio");
        if (cancelled || !res.sessions?.length) return;
        const mapped = res.sessions.map((s) => {
          const local = list.find((x) => x.serverId === s.session_id);
          return (
            local ?? {
              ...createStudioSession(),
              serverId: s.session_id,
              title: s.title || "新对话",
            }
          );
        });
        setSessions(mapped);
        saveStudioSessions(mapped, scope);
        setSessionId(mapped[0].id);
        setMessages(mapped[0].messages);
      } catch {
        /* offline */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [scope]);

  const newChat = useCallback(() => {
    const s = createStudioSession();
    persist(upsertStudioSession(sessions, s));
    setSessionId(s.id);
    setMessages([]);
    void api
      .createSession("", "studio")
      .then((r) => {
        setSessions((prev) => {
          const next = prev.map((x) => (x.id === s.id ? { ...x, serverId: r.session_id } : x));
          saveStudioSessions(next, scope);
          return next;
        });
      })
      .catch(() => {});
  }, [persist, sessions, scope]);

  const switchSession = useCallback(
    (id: string) => {
      const s = sessions.find((x) => x.id === id);
      if (!s) return;
      setSessionId(id);
      setMessages(s.messages);
      const sid = s.serverId;
      if (!sid) return;
      void api
        .getSession(sid)
        .then((detail) => {
          const msgs: StudioMessage[] = detail.messages.map((m) => ({
            role: m.role === "user" ? "user" : "assistant",
            content: m.content,
          }));
          setMessages(msgs);
          setSessions((prev) => {
            const next = upsertStudioSession(prev, { ...s, messages: msgs, updatedAt: Date.now() });
            saveStudioSessions(next, scope);
            return next;
          });
        })
        .catch(() => {});
    },
    [sessions, scope]
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
