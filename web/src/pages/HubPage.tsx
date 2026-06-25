import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { Ear, Mic, Monitor, Send, Square, Waves } from "lucide-react";
import { api, getToken, HubCommandResult, Task, VoiceCommandResult } from "@/lib/api";
import {
  buildChatHistory,
  formatUserFacingError,
  isTerminalTask,
  logPatchFromTask,
  mergeThinkingSteps,
  resolveDisplayText,
  taskFromResponse,
  applyAgentStreamEvent,
  streamLogPatchFromAgentEvent,
  renumberThinkingSteps,
} from "@/lib/thinkingTrace";
import { clearJpegCanvas, drawJpegToCanvas } from "@/lib/jpegPreview";
import { drawPerceptionOverlay } from "@/lib/perceptionOverlay";
import { useAuth } from "@/context/AuthContext";
import { useClawSessionBridge } from "@/context/ClawSessionContext";
import { useLocale } from "@/context/LocaleContext";
import { useBackendWakeListen } from "@/hooks/useBackendWakeListen";
import { useCameraStream } from "@/hooks/useCameraStream";
import { openMicStream, startHoldRecording } from "@/lib/wakeWord";
import { speakExecutionAck, speakReply } from "@/lib/speakFeedback";
import { releaseWebFocus } from "@/lib/releaseWebFocus";

const IM_DESKTOP_TOOLS = new Set(["wechat_send_message"]);
import { ConsoleBrainRouting } from "@/components/console/ConsoleBrainRouting";
import { ConsoleSavePathPicker } from "@/components/hub/ConsoleSavePathPicker";
import { HubChatLog } from "@/components/hub/HubChatLog";
import { HubVirtualScreenMenu } from "@/components/hub/HubVirtualScreenMenu";
import { HubVirtualScreenCalibModal } from "@/components/hub/HubVirtualScreenCalibModal";
import {
  createHubSession,
  loadHubSessions,
  loadDeletedSessionIds,
  markSessionDeleted,
  messagesToLogs,
  replaceSessionId,
  saveHubSessions,
  serverSessionToHub,
  sessionTitleFromLogs,
  upsertHubSession,
  type HubLogItem,
  type HubSession,
} from "@/lib/hubSessions";
import { userStorageScope } from "@/lib/userScope";

type LogItem = HubLogItem;

function shouldOpenVirtualScreenPage(res: HubCommandResult): boolean {
  const steps = Array.isArray(res.plan?.steps) ? res.plan.steps : [];
  return steps.some((s) => {
    if (typeof s !== "object" || !s) return false;
    return String((s as Record<string, unknown>).tool || "") === "virtual_screen_start";
  });
}

function StatusPill({ active, children }: { active?: boolean; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 transition ${
        active
          ? "bg-primary/25 font-medium text-primary ring-1 ring-primary/45 shadow-sm"
          : "text-text-secondary"
      }`}
    >
      {children}
    </span>
  );
}

function ToggleButton({
  active,
  children,
  onClick,
  disabled,
  title,
}: {
  active?: boolean;
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-lg border px-2 py-1 text-xs transition ${
        active
          ? "border-primary bg-primary/20 font-medium text-primary shadow-sm ring-1 ring-primary/35"
          : "border-border bg-surface text-text-secondary hover:border-primary/30 hover:text-text-primary"
      } disabled:cursor-not-allowed disabled:opacity-50`}
    >
      {children}
    </button>
  );
}

export function HubPage() {
  const { license, refreshLicense, user } = useAuth();
  const scope = userStorageScope(user?.username);
  const { t } = useLocale();
  const { setApi: setClawSessionApi } = useClawSessionBridge();
  const c = t.claw;
  const [searchParams, setSearchParams] = useSearchParams();
  const [sessions, setSessions] = useState<HubSession[]>([]);
  const [sessionsReady, setSessionsReady] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [stoppingLogId, setStoppingLogId] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [virtual, setVirtual] = useState({
    active: false,
    calibrated: false,
    show_keyboard: false,
    automation_suspended: false,
  });
  const [virtualCalibOpen, setVirtualCalibOpen] = useState(false);
  const [wakeListening, setWakeListening] = useState(false);
  const [wakeHint, setWakeHint] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const logsScrollRef = useRef<HTMLDivElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const virtualWsRef = useRef<WebSocket | null>(null);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const holdRecRef = useRef<{ stop: () => Promise<Blob> } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const pollAbortRef = useRef(false);
  const activeRunRef = useRef<{ logId: string; taskId?: string; sessionId: string } | null>(null);
  const agentWsRef = useRef<WebSocket | null>(null);
  const stoppedRunsRef = useRef<Set<string>>(new Set());
  const userTouchedSessionRef = useRef(false);
  const sessionIdRef = useRef(sessionId);
  const busySessionIdRef = useRef<string | null>(null);
  const [busySessionId, setBusySessionId] = useState<string | null>(null);
  const virtualScreenEnabled = Boolean(license?.features?.virtual_screen);
  const ttsEnabled = Boolean(license?.features?.tts_feedback);
  const isCurrentSessionBusy = busySessionId === sessionId;

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const setBusySession = useCallback((sid: string | null) => {
    busySessionIdRef.current = sid;
    setBusySessionId(sid);
    setLoading(sid === sessionIdRef.current);
  }, []);

  const persistSession = useCallback((nextLogs: LogItem[], sid: string) => {
    const deleted = loadDeletedSessionIds(scope);
    if (deleted.has(sid)) return;
    setSessions((prev) => {
      const existing = prev.find((s) => s.id === sid);
      const updated: HubSession = {
        id: sid,
        title: sessionTitleFromLogs(nextLogs),
        createdAt: existing?.createdAt ?? Date.now(),
        updatedAt: Date.now(),
        logs: nextLogs,
      };
      const next = upsertHubSession(
        prev.filter((s) => !deleted.has(s.id)),
        updated
      );
      saveHubSessions(next, scope);
      return next;
    });
  }, [scope]);

  useEffect(() => {
    let cancelled = false;
    const token = getToken();
    if (token && !user) {
      setSessionsReady(false);
      return;
    }

    const deleted = loadDeletedSessionIds(scope);
    const local = loadHubSessions(scope);
    const bootstrap = local[0] ?? createHubSession();
    const initialList = local.length ? local : [bootstrap];
    setSessions(initialList);
    setSessionId(bootstrap.id);
    setLogs(bootstrap.logs);
    setSessionsReady(true);

    if (!token) return;

    void (async () => {
      try {
        const res = await api.listSessions("hub");
        if (cancelled || !res.sessions?.length) return;
        const deletedNow = loadDeletedSessionIds(scope);
        setSessions((prev) => {
          const mapped = res.sessions
            .filter((s) => !deletedNow.has(s.session_id))
            .map((s) => {
              const localMatch = prev.find((l) => l.id === s.session_id);
              return localMatch ?? serverSessionToHub(s);
            });
          const serverIds = new Set(mapped.map((s) => s.id));
          const localOnly = prev.filter((l) => !serverIds.has(l.id) && !deletedNow.has(l.id));
          const merged = [...mapped, ...localOnly].sort((a, b) => b.updatedAt - a.updatedAt);
          saveHubSessions(merged, scope);
          return merged;
        });
        if (userTouchedSessionRef.current || cancelled) return;
        const mapped = res.sessions
          .filter((s) => !deletedNow.has(s.session_id))
          .map((s) => serverSessionToHub(s));
        const active = mapped.sort((a, b) => b.updatedAt - a.updatedAt)[0];
        if (!active) return;
        setSessionId(active.id);
        try {
          const detail = await api.getSession(active.id);
          if (!cancelled && detail.messages?.length) {
            setLogs(messagesToLogs(detail.messages));
          } else {
            setLogs([]);
          }
        } catch {
          if (!cancelled) setLogs([]);
        }
      } catch {
        // 离线或未登录时沿用 localStorage
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [scope, user]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      persistSession(logs, sessionId);
    }, 400);
    return () => window.clearTimeout(timer);
  }, [logs, sessionId, persistSession]);

  const patchLogsForSession = useCallback(
    (sid: string, mutator: (logs: LogItem[]) => LogItem[]) => {
      if (sid === sessionIdRef.current) {
        setLogs((prev) => mutator(prev));
        return;
      }
      setSessions((prev) => {
        const target = prev.find((s) => s.id === sid);
        if (!target) return prev;
        const nextLogs = mutator(target.logs);
        const updated: HubSession = {
          ...target,
          logs: nextLogs,
          title: sessionTitleFromLogs(nextLogs),
          updatedAt: Date.now(),
        };
        const next = upsertHubSession(prev, updated);
        saveHubSessions(next, scope);
        return next;
      });
    },
    [scope]
  );

  const patchLog = useCallback((id: string, patch: Partial<LogItem> | ((prev: LogItem) => Partial<LogItem>)) => {
    setLogs((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        const nextPatch = typeof patch === "function" ? patch(l) : patch;
        return { ...l, ...nextPatch };
      })
    );
  }, []);

  const patchActiveRunLog = useCallback(
    (patch: Partial<LogItem> | ((prev: LogItem) => Partial<LogItem>)) => {
      const active = activeRunRef.current;
      if (!active?.logId) return;
      patchLogsForSession(active.sessionId, (prev) =>
        prev.map((l) => {
          if (l.id !== active.logId) return l;
          const nextPatch = typeof patch === "function" ? patch(l) : patch;
          return { ...l, ...nextPatch };
        })
      );
    },
    [patchLogsForSession]
  );

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${proto}://${window.location.host}/ws/agent?token=${encodeURIComponent(token)}`
    );
    agentWsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as Record<string, unknown>;
        const active = activeRunRef.current;
        if (!active?.logId) return;
        const eventSid = String(data.session_id || "");
        if (eventSid && active.sessionId && eventSid !== active.sessionId) {
          activeRunRef.current = { ...active, sessionId: eventSid };
        }
        const evType = String(data.type || "");
        const evTool = String(data.tool || "");
        if (evType === "tool_start" && IM_DESKTOP_TOOLS.has(evTool)) {
          releaseWebFocus();
        }
        patchActiveRunLog((log) => {
          const stream = streamLogPatchFromAgentEvent(data, log);
          if (stream.status === "done") {
            if (busySessionIdRef.current) setBusySession(null);
            activeRunRef.current = null;
          }
          return stream;
        });
      } catch {
        // ignore
      }
    };
    return () => {
      agentWsRef.current = null;
      ws.close();
    };
  }, [patchActiveRunLog]);

  const applyTaskToLog = useCallback((task: Task, logId?: string) => {
    if (stoppedRunsRef.current.has(task.task_id)) return;
    const ownerSid = activeRunRef.current?.sessionId ?? sessionIdRef.current;
    const mutator = (prev: LogItem[]) =>
      prev.map((l) => {
        if (logId && stoppedRunsRef.current.has(logId)) return l;
        if (l.taskId && stoppedRunsRef.current.has(l.taskId)) return l;
        if (logId ? l.id === logId : l.taskId === task.task_id) {
          const patch = logPatchFromTask(task, l);
          return {
            ...l,
            ...patch,
            confirmTask: task.status === "wait_confirm" ? task : undefined,
            taskSnapshot: isTerminalTask(task) ? task : l.taskSnapshot,
          };
        }
        return l;
      });
    patchLogsForSession(ownerSid, mutator);
  }, [patchLogsForSession]);

  const pollTaskUntilSettled = useCallback(
    async (taskId: string, logId: string, ownerSessionId: string) => {
      pollAbortRef.current = false;
      for (let i = 0; i < 40; i += 1) {
        if (pollAbortRef.current) return;
        await new Promise((r) => window.setTimeout(r, 800));
        if (pollAbortRef.current) return;
        try {
          const task = await api.getTask(taskId);
          if (pollAbortRef.current || stoppedRunsRef.current.has(taskId) || stoppedRunsRef.current.has(logId)) {
            return;
          }
          applyTaskToLog(task, logId);
          if (isTerminalTask(task) || task.status === "wait_confirm") {
            if (busySessionIdRef.current === ownerSessionId) {
              setBusySession(null);
            }
            activeRunRef.current = null;
            abortRef.current = null;
            releaseWebFocus();
            return;
          }
        } catch {
          if (busySessionIdRef.current === ownerSessionId) {
            setBusySession(null);
          }
          activeRunRef.current = null;
          abortRef.current = null;
          return;
        }
      }
      if (busySessionIdRef.current === ownerSessionId) {
        setBusySession(null);
      }
      activeRunRef.current = null;
      abortRef.current = null;
    },
    [applyTaskToLog, setBusySession]
  );

  const stopActiveRun = useCallback(() => {
    pollAbortRef.current = true;
    abortRef.current?.abort();
    const active = activeRunRef.current;
    const ownerSid = active?.sessionId ?? busySessionIdRef.current ?? sessionIdRef.current;
    if (active?.logId) stoppedRunsRef.current.add(active.logId);
    if (active?.taskId) stoppedRunsRef.current.add(active.taskId);

    setStopping(false);
    setStoppingLogId(null);
    setBusySession(null);
    activeRunRef.current = null;
    abortRef.current = null;

    if (active?.logId) {
      patchLogsForSession(ownerSid, (prev) =>
        prev.map((l) => {
          if (l.id !== active.logId) return l;
          return {
            ...l,
            text: c.stopped,
            status: "error" as const,
            thinkingOpen: false,
            thinking: l.thinking?.map((s) =>
              s.status === "running" || s.status === "pending"
                ? { ...s, status: "error" as const, detail: c.stopped }
                : s
            ),
          };
        })
      );
    }

    void Promise.all([
      api.killSwitch().catch(() => {}),
      active?.taskId ? api.cancelTask(active.taskId).catch(() => {}) : Promise.resolve(),
    ]);
  }, [c.stopped, patchLogsForSession, setBusySession]);

  const startNewSession = useCallback(async () => {
    userTouchedSessionRef.current = true;
    if (busySessionIdRef.current) {
      const ok = window.confirm("当前有任务正在执行，开启新会话将停止该任务。继续？");
      if (!ok) return;
      stopActiveRun();
    }
    persistSession(logs, sessionId);
    let fresh = createHubSession();
    try {
      const created = await api.createSession(t.studio.newChat, "hub");
      fresh = createHubSession(created.session_id);
      fresh.title = created.title;
    } catch {
      // 服务端不可用时仅本地会话
    }
    setSessions((prev) => {
      const next = upsertHubSession(prev, fresh);
      saveHubSessions(next, scope);
      return next;
    });
    setSessionId(fresh.id);
    sessionIdRef.current = fresh.id;
    setLogs([]);
    setText("");
    setStopping(false);
    setStoppingLogId(null);
    pollAbortRef.current = true;
    abortRef.current?.abort();
    activeRunRef.current = null;
    if (busySessionIdRef.current) {
      setBusySession(null);
    }
  }, [logs, sessionId, persistSession, stopActiveRun, t.studio.newChat, scope, setBusySession]);

  useEffect(() => {
    const onNew = () => void startNewSession();
    window.addEventListener("claw:new-session", onNew);
    return () => window.removeEventListener("claw:new-session", onNew);
  }, [startNewSession]);

  const switchSession = useCallback(
    async (targetId: string) => {
      if (targetId === sessionId) return;
      userTouchedSessionRef.current = true;
      if (busySessionIdRef.current) {
        const ok = window.confirm("切换会话将停止当前正在执行的任务。继续？");
        if (!ok) return;
        stopActiveRun();
      }
      persistSession(logs, sessionId);
      const target = sessions.find((s) => s.id === targetId);
      if (!target) return;
      setSessionId(target.id);
      sessionIdRef.current = target.id;
      setLoading(busySessionIdRef.current === target.id);
      try {
        const detail = await api.getSession(targetId);
        setLogs(detail.messages?.length ? messagesToLogs(detail.messages) : target.logs);
      } catch {
        setLogs(target.logs);
      }
      setText("");
    },
    [logs, sessionId, sessions, persistSession, stopActiveRun]
  );

  const remapSessionId = useCallback(
    (oldId: string, newId: string) => {
      if (!oldId || !newId || oldId === newId) return;
      setSessions((prev) => {
        const next = replaceSessionId(prev, oldId, newId);
        saveHubSessions(next, scope);
        return next;
      });
      if (sessionIdRef.current === oldId) {
        sessionIdRef.current = newId;
        setSessionId(newId);
      }
    },
    [scope]
  );

  const deleteSession = useCallback(
    async (targetId: string) => {
      const target = sessions.find((s) => s.id === targetId);
      if (!target) return;
      const ok = window.confirm(`删除会话「${target.title}」？此操作不可恢复。`);
      if (!ok) return;
      markSessionDeleted(targetId, scope);
      try {
        await api.deleteSession(targetId);
      } catch {
        // 本地墓碑已写入；服务端可能已是 404（临时 UUID 未入库）
      }
      const remaining = sessions.filter((s) => s.id !== targetId);
      if (targetId === sessionId) {
        const next = remaining[0] ?? createHubSession();
        const list = remaining.length ? remaining : [next];
        saveHubSessions(list, scope);
        setSessions(list);
        setSessionId(next.id);
        sessionIdRef.current = next.id;
        setLogs(next.logs);
        setText("");
      } else {
        saveHubSessions(remaining, scope);
        setSessions(remaining);
      }
    },
    [sessionId, sessions, scope]
  );

  useEffect(() => {
    setClawSessionApi({
      sessions: sessionsReady ? sessions : [],
      sessionId,
      switchSession,
      deleteSession,
      newSession: () => void startNewSession(),
    });
    return () => setClawSessionApi(null);
  }, [sessions, sessionsReady, sessionId, switchSession, deleteSession, startNewSession, setClawSessionApi]);

  const pushLog = (role: LogItem["role"], textValue: string, extra?: Partial<LogItem>) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    const item: LogItem = { id, role, text: textValue, status: "done", ...extra };
    setLogs((prev) => [...prev, item].slice(-60));
    return id;
  };

  useEffect(() => {
    const el = logsScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    if (document.activeElement === el) {
      releaseWebFocus();
    }
  }, [logs]);

  const onFrame = useCallback(
    (payload: {
      image: string;
      detections?: { x1: number; y1: number; x2: number; y2: number; confidence: number; label?: string }[];
      gesture?: Record<string, unknown>;
      person_count?: number;
      hands?: {
        hand_box?: { x1: number; y1: number; x2: number; y2: number };
        index_tip?: { x: number; y: number };
        tracking?: boolean;
        pinch?: boolean;
      }[];
    }) => {
      drawPerceptionOverlay(canvasRef.current, payload.image, {
        detections: payload.detections,
        gesture: payload.gesture as { type?: string; description?: string },
        personCount: payload.person_count,
        hands: payload.hands,
      });
    },
    []
  );

  const { streaming, loading: camLoading, error: camError, start: startCam, stop: stopCam } = useCameraStream(onFrame);

  useEffect(() => {
    if (!streaming) clearJpegCanvas(canvasRef.current);
  }, [streaming]);

  const handleStopCam = () => {
    clearJpegCanvas(canvasRef.current);
    void stopCam();
    if (virtual.active) {
      pushLog("system", c.camPreviewOffVirtualOn);
    }
  };

  const refreshVirtual = useCallback(() => {
    api.virtualSessionStatus().then(setVirtual).catch(() => {});
  }, []);

  useEffect(() => {
    void refreshLicense();
    refreshVirtual();
    const timer = window.setInterval(refreshVirtual, 3000);
    return () => {
      window.clearInterval(timer);
      virtualWsRef.current?.close();
    };
  }, [refreshVirtual, refreshLicense]);

  useEffect(() => {
    if (searchParams.get("calibrate") !== "virtual") return;
    setVirtualCalibOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete("calibrate");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    let cancelled = false;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/tasks?token=${encodeURIComponent(token)}`);
    ws.onopen = () => {
      if (cancelled) ws.close();
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type !== "task_update" || !data.task?.task_id) return;
        const task = data.task as Task;
        if (stoppedRunsRef.current.has(task.task_id)) return;
        applyTaskToLog(task);
        if (isTerminalTask(task)) {
          if (busySessionIdRef.current) {
            setBusySession(null);
          }
          activeRunRef.current = null;
          abortRef.current = null;
        }
      } catch {
        // ignore
      }
    };
    return () => {
      cancelled = true;
      if (ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [applyTaskToLog]);

  useEffect(() => {
    if (!virtual.active || !virtualScreenEnabled) {
      virtualWsRef.current?.close();
      virtualWsRef.current = null;
      return;
    }
    const token = getToken();
    if (!token) return;
    let cancelled = false;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/virtual-screen/live?token=${encodeURIComponent(token)}`);
    virtualWsRef.current = ws;
    ws.onopen = () => {
      if (cancelled) ws.close();
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "pointer") {
          if (data.clicked) pushLog("system", "空中点击");
          if (data.suspended) {
            setVirtual((v) => ({ ...v, automation_suspended: true }));
          } else if (data.tracking || data.screen_x != null) {
            setVirtual((v) => ({ ...v, automation_suspended: false }));
          }
        }
        if (data.type === "status") setVirtual((v) => ({ ...v, ...data }));
      } catch {
        // ignore
      }
    };
    return () => {
      cancelled = true;
      if (ws.readyState === WebSocket.OPEN) ws.close();
      if (virtualWsRef.current === ws) virtualWsRef.current = null;
    };
  }, [virtualScreenEnabled, virtual.active]);

  const submit = async (autonomous = false, explicitText?: string, fromVoice = false) => {
    const cmd = (explicitText ?? text).trim();
    if (!cmd || isCurrentSessionBusy || stopping) return;

    setStopping(false);
    setStoppingLogId(null);

    try {
      await fetch("/api/kill-switch/reset", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken() || ""}` },
      });
    } catch {
      // ignore
    }

    const runSessionId = sessionId;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 120_000);
    abortRef.current = controller;
    pollAbortRef.current = false;
    setBusySession(runSessionId);
    const history = buildChatHistory(logs);
    pushLog("user", cmd);
    if (!explicitText) setText("");
    inputRef.current?.blur();
    releaseWebFocus();
    const pendingId = pushLog("system", "", {
      status: "thinking",
      thinking: [],
      thinkingOpen: false,
    });
    activeRunRef.current = { logId: pendingId, sessionId: runSessionId };

    try {
      const res: HubCommandResult | VoiceCommandResult = autonomous
        ? await api.hubAutonomous(cmd)
        : fromVoice || explicitText
          ? await api.voiceRunText(cmd, controller.signal, history, sessionId)
          : await api.hubCommand(cmd, controller.signal, history, sessionId);

      if (controller.signal.aborted) return;

      if (res.session_id && res.session_id !== runSessionId) {
        remapSessionId(runSessionId, res.session_id);
      } else if (res.session_id && res.session_id !== sessionId) {
        setSessionId(res.session_id);
        sessionIdRef.current = res.session_id;
      }

      const task = taskFromResponse(res);
      const isWaitConfirm = task?.status === "wait_confirm";
      const terminal = isTerminalTask(task);
      const isPendingTask =
        Boolean(res.task_id) && !terminal && !isWaitConfirm && !(res.reply || "").trim();
      const display = isWaitConfirm
        ? "该操作需你确认后才会继续执行"
        : resolveDisplayText(res, task, isPendingTask);

      if (res.task_id) activeRunRef.current = { logId: pendingId, taskId: res.task_id, sessionId: runSessionId };

      patchLog(pendingId, (log) => {
        const alreadyDone = log.status === "done" && Boolean(log.text?.trim());
        const serverThinking = renumberThinkingSteps(mergeThinkingSteps(res, task));
        return {
          text: alreadyDone ? log.text : display,
          thinking: alreadyDone ? renumberThinkingSteps(log.thinking || serverThinking) : serverThinking,
          thinkingOpen: false,
          status: isWaitConfirm
            ? "done"
            : isPendingTask
              ? "thinking"
              : alreadyDone
                ? "done"
                : task?.status === "failed" || task?.status === "cancelled"
                  ? "error"
                  : "done",
          taskId: res.task_id || undefined,
          confirmTask: isWaitConfirm ? task : undefined,
          taskSnapshot: task && isTerminalTask(task) ? task : undefined,
        };
      });

      const action =
        res.action || (res.task_id ? "execute" : "matched" in res && res.matched === false ? "error" : "answer");
      const isDesktopExecute = action === "execute" || action === "task" || action === "autonomous";
      if (isDesktopExecute && !isPendingTask) {
        requestAnimationFrame(() => releaseWebFocus());
      }

      if (isWaitConfirm) {
        setBusySession(null);
        activeRunRef.current = null;
        abortRef.current = null;
      } else if (isPendingTask && res.task_id) {
        void pollTaskUntilSettled(res.task_id, pendingId, runSessionId);
      } else {
        activeRunRef.current = null;
        abortRef.current = null;
        setBusySession(null);
        if (!isDesktopExecute && res.reply && ttsEnabled) await speakReply(display, { enabled: ttsEnabled });
      }

      if (!isPendingTask && !isDesktopExecute) {
        if (action === "answer" || action === "status" || action === "cancel") {
          await speakReply(display, { enabled: ttsEnabled });
        } else if (res.reply) {
          await speakReply(display, { enabled: ttsEnabled });
        }
      }

      if ("status" in res && res.status) setVirtual((v) => ({ ...v, ...res.status! }));
      if (res.task_id) await refreshLicense();

      if (shouldOpenVirtualScreenPage(res as HubCommandResult)) {
        pushLog("system", "请完成虚拟屏校准。");
        setVirtualCalibOpen(true);
      }
    } catch (e) {
      if (controller.signal.aborted || stoppedRunsRef.current.has(pendingId)) {
        if (controller.signal.aborted && !stoppedRunsRef.current.has(pendingId)) {
          patchLog(pendingId, {
            text: "请求超时或已中断，请重试或点击停止。",
            status: "error",
            thinkingOpen: false,
          });
        }
        return;
      }
      patchLog(pendingId, {
        text: formatUserFacingError(e instanceof Error ? e.message : "失败"),
        status: "error",
        thinkingOpen: false,
      });
      activeRunRef.current = null;
      abortRef.current = null;
      setBusySession(null);
    } finally {
      window.clearTimeout(timeoutId);
      if (!activeRunRef.current?.taskId && busySessionIdRef.current === runSessionId) {
        setBusySession(null);
        abortRef.current = null;
      }
      refreshVirtual();
    }
  };

  const { listening: wakeActive, lastHeard } = useBackendWakeListen({
    enabled: wakeListening && !isCurrentSessionBusy,
    onUtterance: (raw) => {
      if (!isCurrentSessionBusy) void submit(false, raw, true);
    },
    onStatus: setWakeHint,
    onError: (msg) => pushLog("system", msg),
  });

  const startVoice = async () => {
    try {
      const stream = voiceStreamRef.current ?? (await openMicStream());
      voiceStreamRef.current = stream;
      holdRecRef.current = startHoldRecording(stream);
      setRecording(true);
    } catch {
      pushLog("system", "无法访问麦克风");
    }
  };

  const stopVoice = async () => {
    if (!holdRecRef.current) return;
    setRecording(false);
    try {
      const blob = await holdRecRef.current.stop();
      holdRecRef.current = null;
      const tr = await api.transcribeVoice(blob);
      const heard = (tr.text || "").trim();
      if (!heard) {
        pushLog("system", "未识别到语音");
        return;
      }
      await submit(false, heard, true);
    } catch (e) {
      pushLog("system", e instanceof Error ? e.message : "语音识别失败");
    } finally {
      voiceStreamRef.current?.getTracks().forEach((t) => t.stop());
      voiceStreamRef.current = null;
    }
  };

  const showCamera = streaming || camLoading;

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden bg-mimo-surface p-3 md:p-4">
      <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-border bg-surface px-3 py-2 text-xs">
        <StatusPill active={streaming || camLoading}>
          <Monitor size={12} aria-hidden />
          {c.vision}{streaming ? c.visionOn : c.visionOff}
        </StatusPill>
        <StatusPill active={wakeListening || wakeActive}>
          <Waves size={12} aria-hidden />
          {c.wake}{wakeActive ? c.wakeOn : c.wakeOff}
        </StatusPill>
        <HubVirtualScreenMenu
          featureEnabled={virtualScreenEnabled}
          virtual={virtual}
          onRefresh={refreshVirtual}
          onCalibrate={() => setVirtualCalibOpen(true)}
          onStartCamera={async () => {
            if (!streaming) await startCam();
          }}
          onStopCamera={() => {
            if (streaming) void handleStopCam();
          }}
        />
        <span className="hidden text-text-secondary sm:inline">
          {c.wakeWord} <code className="text-text-primary">灵枢</code>
          {wakeListening && lastHeard ? ` · ${lastHeard}` : ""}
          {wakeListening && wakeHint ? ` · ${wakeHint}` : ""}
        </span>
        <span className="ml-auto flex flex-wrap items-center gap-2">
          <ConsoleSavePathPicker scope={scope} />
          <ConsoleBrainRouting variant="compact" />
          <ToggleButton active={wakeListening} onClick={() => setWakeListening((v) => !v)}>
            <Ear size={12} className="mr-1 inline" aria-hidden />
            {wakeListening ? c.closeWake : c.openWake}
          </ToggleButton>
          {!streaming ? (
            <ToggleButton active={false} disabled={camLoading} onClick={() => startCam().catch(() => {})}>
              {camLoading ? c.starting : c.openCam}
            </ToggleButton>
          ) : (
            <ToggleButton active onClick={handleStopCam}>
              {c.closeCam}
            </ToggleButton>
          )}
        </span>
      </div>

      <div className={`grid min-h-0 flex-1 gap-3 ${showCamera ? "lg:grid-cols-2" : ""}`}>
        {showCamera && (
          <section className="card flex min-h-0 flex-col overflow-hidden p-3">
            <div className="relative min-h-0 flex-1 overflow-hidden rounded-lg bg-black">
              <canvas ref={canvasRef} className="h-full w-full object-contain" />
            </div>
            {camError && <p className="mt-2 text-xs text-danger">{camError}</p>}
          </section>
        )}

        <section className={`card flex min-h-0 flex-col overflow-hidden p-3 ${showCamera ? "" : "min-h-0 flex-1"}`}>
          <div ref={logsScrollRef} className="min-h-0 flex-1 overflow-y-auto text-sm">
            <div className="hub-chat-area flex min-h-full flex-col justify-end">
              {logs.length === 0 && (
                <p className="py-8 text-center text-xs text-text-secondary">{c.emptyHint}</p>
              )}
              {logs.map((l) => (
                <HubChatLog
                  key={l.id}
                  log={l}
                  stopping={stopping && stoppingLogId === l.id}
                  labels={{
                    you: c.you,
                    agent: c.agent,
                    thinking: c.thinking,
                    stopping: c.stopping,
                    busy: c.executing,
                    process: (done, total) =>
                      c.processProgress.replace("{done}", String(done)).replace("{total}", String(total)),
                  }}
                  onPatch={(patch) => patchLog(l.id, patch)}
                  onApplyTask={applyTaskToLog}
                  onPollTask={(taskId, logId) => void pollTaskUntilSettled(taskId, logId, sessionId)}
                />
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>

          <div className="mt-3 flex shrink-0 gap-2 border-t border-border pt-3">
            <textarea
              ref={inputRef}
              className="input min-h-[2.5rem] min-w-0 flex-1 resize-none py-2 leading-relaxed"
              placeholder="输入指令或问题（Enter 发送，Shift+Enter 换行）"
              rows={2}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!isCurrentSessionBusy) void submit(false);
                }
              }}
            />
            {!recording ? (
              <button type="button" className="btn-secondary shrink-0" onClick={startVoice} title="语音" aria-label="语音输入">
                <Mic size={18} aria-hidden />
              </button>
            ) : (
              <button type="button" className="btn-danger shrink-0" onClick={stopVoice} aria-label="停止录音">
                <Square size={18} aria-hidden />
              </button>
            )}
            <button
              type="button"
              className={isCurrentSessionBusy ? "btn-danger shrink-0" : "btn-primary shrink-0"}
              onClick={() => (isCurrentSessionBusy ? stopActiveRun() : void submit(false))}
              aria-label={isCurrentSessionBusy ? c.stopRun : c.send}
              title={isCurrentSessionBusy ? c.stopRun : c.send}
            >
              {isCurrentSessionBusy ? <Square size={16} aria-hidden /> : <Send size={16} aria-hidden />}
            </button>
          </div>
        </section>
      </div>
      <HubVirtualScreenCalibModal
        open={virtualCalibOpen}
        onClose={() => setVirtualCalibOpen(false)}
        onSaved={refreshVirtual}
        onStartCamera={() => {
          if (!streaming) void startCam();
        }}
      />
    </div>
  );
}
