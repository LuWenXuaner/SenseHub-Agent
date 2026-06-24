import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AgentChatAvatar, UserChatAvatar } from "@/components/chat/ChatAvatar";
import { ChatMessageContent } from "@/components/chat/ChatMessageContent";
import { Check, ChevronDown, ChevronRight, Ear, Loader2, MessageSquarePlus, Mic, Monitor, Pause, Send, Square, Waves, X } from "lucide-react";
import { api, getToken, HubCommandResult, Task, VoiceCommandResult } from "@/lib/api";
import {
  buildChatHistory,
  formatUserFacingError,
  isTerminalTask,
  logPatchFromTask,
  mergeThinkingSteps,
  resolveDisplayText,
  taskFromResponse,
  type ThinkingStep,
} from "@/lib/thinkingTrace";
import { clearJpegCanvas, drawJpegToCanvas } from "@/lib/jpegPreview";
import { useAuth } from "@/context/AuthContext";
import { useClawSessionBridge } from "@/context/ClawSessionContext";
import { useLocale } from "@/context/LocaleContext";
import { useBackendWakeListen } from "@/hooks/useBackendWakeListen";
import { useCameraStream } from "@/hooks/useCameraStream";
import { openMicStream, startHoldRecording } from "@/lib/wakeWord";
import { speakExecutionAck, speakReply } from "@/lib/speakFeedback";
import { ConfirmPanel } from "@/components/tasks/ConfirmPanel";
import {
  createHubSession,
  loadHubSessions,
  messagesToLogs,
  saveHubSessions,
  serverSessionToHub,
  sessionTitleFromLogs,
  upsertHubSession,
  type HubLogItem,
  type HubSession,
} from "@/lib/hubSessions";

type StepStatus = ThinkingStep["status"];
type LogItem = HubLogItem;

function shouldOpenVirtualScreenPage(res: HubCommandResult): boolean {
  const steps = Array.isArray(res.plan?.steps) ? res.plan.steps : [];
  return steps.some((s) => {
    if (typeof s !== "object" || !s) return false;
    return String((s as Record<string, unknown>).tool || "") === "virtual_screen_start";
  });
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "running") return <Loader2 size={12} className="animate-spin text-primary" aria-hidden />;
  if (status === "error") return <X size={12} className="text-danger" aria-hidden />;
  return <Check size={12} className="text-success" aria-hidden />;
}

function ThinkingPanel({
  steps,
  open,
  onToggle,
  busy,
}: {
  steps: ThinkingStep[];
  open: boolean;
  onToggle: () => void;
  busy?: boolean;
}) {
  if (!steps.length) return null;
  const done = steps.filter((s) => s.status === "done").length;
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs text-text-secondary transition hover:text-text-primary"
      >
        {open ? <ChevronDown size={14} aria-hidden /> : <ChevronRight size={14} aria-hidden />}
        <span>{busy ? "执行中…" : `执行过程 · ${done}/${steps.length}`}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-2.5 border-l border-border/70 pl-3">
          {steps.map((step) => (
            <div key={step.id} className="text-xs">
              <div className="flex items-center gap-2 text-text-primary">
                <StepIcon status={step.status} />
                <span className="font-medium">{step.label}</span>
              </div>
              {step.detail && <p className="ml-5 mt-0.5 leading-relaxed text-text-secondary">{step.detail}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
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

function NewSessionButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      title={label}
      onClick={onClick}
      className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-text-secondary transition hover:border-primary/40 hover:text-primary"
    >
      <MessageSquarePlus size={12} className="mr-1 inline" aria-hidden />
      {label}
    </button>
  );
}

export function HubPage() {
  const { license, refreshLicense } = useAuth();
  const { t } = useLocale();
  const { setApi: setClawSessionApi } = useClawSessionBridge();
  const c = t.claw;
  const navigate = useNavigate();
  const initialSessions = loadHubSessions();
  const bootstrap = initialSessions[0] ?? createHubSession();
  const [sessions, setSessions] = useState<HubSession[]>(initialSessions.length ? initialSessions : [bootstrap]);
  const [sessionId, setSessionId] = useState(bootstrap.id);
  const [text, setText] = useState("");
  const [logs, setLogs] = useState<LogItem[]>(bootstrap.logs);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [virtual, setVirtual] = useState({ active: false, calibrated: false, show_keyboard: false });
  const [wakeListening, setWakeListening] = useState(false);
  const [wakeHint, setWakeHint] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const virtualWsRef = useRef<WebSocket | null>(null);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const holdRecRef = useRef<{ stop: () => Promise<Blob> } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const pollAbortRef = useRef(false);
  const activeRunRef = useRef<{ logId: string; taskId?: string } | null>(null);
  const maxTier = license?.tier === "max";
  const ttsEnabled = Boolean(license?.features?.tts_feedback);

  const persistSession = useCallback((nextLogs: LogItem[], sid: string) => {
    setSessions((prev) => {
      const existing = prev.find((s) => s.id === sid);
      const updated: HubSession = {
        id: sid,
        title: sessionTitleFromLogs(nextLogs),
        createdAt: existing?.createdAt ?? Date.now(),
        updatedAt: Date.now(),
        logs: nextLogs,
      };
      const next = upsertHubSession(prev, updated);
      saveHubSessions(next);
      return next;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const local = loadHubSessions();
        const res = await api.listSessions("hub");
        if (cancelled || !res.sessions?.length) return;
        const serverIds = new Set(res.sessions.map((s) => s.session_id));
        const mapped = res.sessions.map((s) => {
          const localMatch = local.find((l) => l.id === s.session_id);
          return localMatch ?? serverSessionToHub(s);
        });
        const localOnly = local.filter((l) => !serverIds.has(l.id));
        const merged = [...mapped, ...localOnly].sort((a, b) => b.updatedAt - a.updatedAt);
        setSessions(merged);
        const active = merged[0];
        setSessionId(active.id);
        if (active.logs.length) {
          setLogs(active.logs);
        } else {
          try {
            const detail = await api.getSession(active.id);
            if (!cancelled && detail.messages?.length) {
              setLogs(messagesToLogs(detail.messages));
            }
          } catch {
            /* keep empty */
          }
        }
      } catch {
        // 离线或未登录时沿用 localStorage
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      persistSession(logs, sessionId);
    }, 400);
    return () => window.clearTimeout(timer);
  }, [logs, sessionId, persistSession]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${proto}://${window.location.host}/ws/agent?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(sessionId)}`
    );
    ws.onmessage = () => {
      /* 实时事件由 mergeThinkingSteps / task WS 补充 */
    };
    return () => ws.close();
  }, [sessionId]);

  const patchLog = (id: string, patch: Partial<LogItem>) => {
    setLogs((prev) => prev.map((l) => (l.id === id ? { ...l, ...patch } : l)));
  };

  const applyTaskToLog = useCallback((task: Task, logId?: string) => {
    setLogs((prev) =>
      prev.map((l) => {
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
      })
    );
  }, []);

  const pollTaskUntilSettled = useCallback(
    async (taskId: string, logId: string) => {
      pollAbortRef.current = false;
      for (let i = 0; i < 40; i += 1) {
        if (pollAbortRef.current) return;
        await new Promise((r) => window.setTimeout(r, 1200));
        if (pollAbortRef.current) return;
        try {
          const task = await api.getTask(taskId);
          applyTaskToLog(task, logId);
          if (isTerminalTask(task) || task.status === "wait_confirm") {
            setLoading(false);
            activeRunRef.current = null;
            abortRef.current = null;
            return;
          }
        } catch {
          setLoading(false);
          activeRunRef.current = null;
          abortRef.current = null;
          return;
        }
      }
      setLoading(false);
      activeRunRef.current = null;
      abortRef.current = null;
    },
    [applyTaskToLog]
  );

  const stopActiveRun = useCallback(async () => {
    pollAbortRef.current = true;
    abortRef.current?.abort();
    const active = activeRunRef.current;
    try {
      if (active?.taskId) await api.cancelTask(active.taskId);
      await api.killSwitch();
      await fetch("/api/kill-switch/reset", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken() || ""}` },
      }).catch(() => {});
    } catch {
      // ignore
    }
    if (active?.logId) {
      patchLog(active.logId, {
        text: "已停止执行",
        status: "error",
        thinkingOpen: false,
      });
    }
    activeRunRef.current = null;
    abortRef.current = null;
    setLoading(false);
  }, []);

  const startNewSession = useCallback(async () => {
    if (loading) {
      const ok = window.confirm("当前正在执行，开启新会话将停止任务。继续？");
      if (!ok) return;
      await stopActiveRun();
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
      saveHubSessions(next);
      return next;
    });
    setSessionId(fresh.id);
    setLogs([]);
    setText("");
    setLoading(false);
    pollAbortRef.current = true;
    abortRef.current?.abort();
    activeRunRef.current = null;
  }, [loading, logs, sessionId, persistSession, stopActiveRun, t.studio.newChat]);

  useEffect(() => {
    const onNew = () => void startNewSession();
    window.addEventListener("claw:new-session", onNew);
    return () => window.removeEventListener("claw:new-session", onNew);
  }, [startNewSession]);

  const switchSession = useCallback(
    async (targetId: string) => {
      if (targetId === sessionId) return;
      if (loading) {
        const ok = window.confirm("切换会话将停止当前任务。继续？");
        if (!ok) return;
        await stopActiveRun();
      }
      persistSession(logs, sessionId);
      const target = sessions.find((s) => s.id === targetId);
      if (!target) return;
      setSessionId(target.id);
      try {
        const detail = await api.getSession(targetId);
        setLogs(detail.messages?.length ? messagesToLogs(detail.messages) : target.logs);
      } catch {
        setLogs(target.logs);
      }
      setText("");
    },
    [loading, logs, sessionId, sessions, persistSession, stopActiveRun]
  );

  const deleteSession = useCallback(
    (targetId: string) => {
      const target = sessions.find((s) => s.id === targetId);
      if (!target) return;
      const ok = window.confirm(`删除会话「${target.title}」？此操作不可恢复。`);
      if (!ok) return;
      void api.deleteSession(targetId).catch(() => {});
      const remaining = sessions.filter((s) => s.id !== targetId);
      if (targetId === sessionId) {
        const next = remaining[0] ?? createHubSession();
        const list = remaining.length ? remaining : [next];
        saveHubSessions(list);
        setSessions(list);
        setSessionId(next.id);
        setLogs(next.logs);
        setText("");
      } else {
        saveHubSessions(remaining);
        setSessions(remaining);
      }
    },
    [sessionId, sessions]
  );

  useEffect(() => {
    setClawSessionApi({ sessions, sessionId, switchSession, deleteSession });
    return () => setClawSessionApi(null);
  }, [sessions, sessionId, switchSession, deleteSession, setClawSessionApi]);

  const pushLog = (role: LogItem["role"], textValue: string, extra?: Partial<LogItem>) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
    const item: LogItem = { id, role, text: textValue, status: "done", ...extra };
    setLogs((prev) => [...prev, item].slice(-60));
    return id;
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const onFrame = useCallback((payload: { image: string }) => {
    drawJpegToCanvas(canvasRef.current, payload.image);
  }, []);

  const { streaming, loading: camLoading, error: camError, start: startCam, stop: stopCam } = useCameraStream(onFrame);

  useEffect(() => {
    if (!streaming) clearJpegCanvas(canvasRef.current);
  }, [streaming]);

  const handleStopCam = () => {
    clearJpegCanvas(canvasRef.current);
    void stopCam();
  };

  const refreshVirtual = useCallback(() => {
    api.virtualSessionStatus().then(setVirtual).catch(() => {});
  }, []);

  useEffect(() => {
    refreshVirtual();
    const timer = window.setInterval(refreshVirtual, 3000);
    return () => {
      window.clearInterval(timer);
      stopCam().catch(() => {});
      virtualWsRef.current?.close();
    };
  }, [refreshVirtual, stopCam]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/tasks?token=${encodeURIComponent(token)}`);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type !== "task_update" || !data.task?.task_id) return;
        const task = data.task as Task;
        applyTaskToLog(task);
        if (isTerminalTask(task)) {
          setLoading(false);
          activeRunRef.current = null;
          abortRef.current = null;
        }
      } catch {
        // ignore
      }
    };
    return () => ws.close();
  }, [applyTaskToLog]);

  useEffect(() => {
    if (!virtual.active || !maxTier) {
      virtualWsRef.current?.close();
      virtualWsRef.current = null;
      return;
    }
    const token = getToken();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/virtual-screen/live?token=${encodeURIComponent(token)}`);
    virtualWsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "pointer" && data.clicked) pushLog("system", "空中点击");
        if (data.type === "status") setVirtual((v) => ({ ...v, ...data }));
      } catch {
        // ignore
      }
    };
    return () => ws.close();
  }, [maxTier, virtual.active]);

  const submit = async (autonomous = false, explicitText?: string, fromVoice = false) => {
    const cmd = (explicitText ?? text).trim();
    if (!cmd || loading) return;

    try {
      await fetch("/api/kill-switch/reset", {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken() || ""}` },
      });
    } catch {
      // ignore
    }

    const controller = new AbortController();
    abortRef.current = controller;
    pollAbortRef.current = false;
    setLoading(true);
    const history = buildChatHistory(logs);
    pushLog("user", cmd);
    if (!explicitText) setText("");
    const pendingId = pushLog("system", "", {
      status: "thinking",
      thinking: [],
      thinkingOpen: true,
    });
    activeRunRef.current = { logId: pendingId };

    try {
      const res: HubCommandResult | VoiceCommandResult = autonomous
        ? await api.hubAutonomous(cmd)
        : fromVoice || explicitText
          ? await api.voiceRunText(cmd, controller.signal, history, sessionId)
          : await api.hubCommand(cmd, controller.signal, history, sessionId);

      if (controller.signal.aborted) return;

      if (res.session_id && res.session_id !== sessionId) {
        setSessionId(res.session_id);
      }

      const task = taskFromResponse(res);
      const isWaitConfirm = task?.status === "wait_confirm";
      const terminal = isTerminalTask(task);
      const isPendingTask = Boolean(res.task_id) && !terminal && !res.reply && !isWaitConfirm;
      const display = isWaitConfirm
        ? "该操作需你确认后才会继续执行"
        : resolveDisplayText(res, task, isPendingTask);

      if (res.task_id) activeRunRef.current = { logId: pendingId, taskId: res.task_id };

      patchLog(pendingId, {
        text: display,
        thinking: mergeThinkingSteps(res, task),
        thinkingOpen: isPendingTask || isWaitConfirm,
        status: isWaitConfirm
          ? "done"
          : isPendingTask
            ? "thinking"
            : task?.status === "failed" || task?.status === "cancelled"
              ? "error"
              : "done",
        taskId: res.task_id || undefined,
        confirmTask: isWaitConfirm ? task : undefined,
        taskSnapshot: task && isTerminalTask(task) ? task : undefined,
      });

      if (isWaitConfirm) {
        setLoading(false);
        activeRunRef.current = null;
        abortRef.current = null;
      } else if (isPendingTask && res.task_id) {
        void pollTaskUntilSettled(res.task_id, pendingId);
      } else {
        activeRunRef.current = null;
        abortRef.current = null;
        setLoading(false);
        if (res.reply && ttsEnabled) await speakReply(display, { enabled: ttsEnabled });
      }

      const action =
        res.action || (res.task_id ? "execute" : "matched" in res && res.matched === false ? "error" : "answer");

      if (!isPendingTask) {
        if (action === "answer" || action === "status" || action === "cancel") {
          await speakReply(display, { enabled: ttsEnabled });
        } else if (res.reply) {
          await speakReply(display, { enabled: ttsEnabled });
        }
      } else if (action === "execute" || action === "task" || action === "autonomous") {
        if (fromVoice || explicitText) {
          await speakExecutionAck(cmd, { autonomous, enabled: ttsEnabled });
        }
      }

      if ("status" in res && res.status) setVirtual((v) => ({ ...v, ...res.status! }));
      if (res.task_id) await refreshLicense();

      if (shouldOpenVirtualScreenPage(res as HubCommandResult)) {
        pushLog("system", "已打开虚拟屏设置，完成校准后关闭该页即可返回。");
        const win = window.open("/perception/virtual-screen?from=hub", "_blank", "noopener,noreferrer,width=1180,height=760");
        if (!win) navigate("/perception/virtual-screen?from=hub");
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      patchLog(pendingId, {
        text: formatUserFacingError(e instanceof Error ? e.message : "失败"),
        status: "error",
        thinkingOpen: false,
      });
      activeRunRef.current = null;
      abortRef.current = null;
      setLoading(false);
    } finally {
      if (!activeRunRef.current?.taskId) {
        setLoading(false);
        abortRef.current = null;
      }
      refreshVirtual();
    }
  };

  const { listening: wakeActive, lastHeard } = useBackendWakeListen({
    enabled: wakeListening && !loading,
    onUtterance: (raw) => {
      if (!loading) void submit(false, raw, true);
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
        {maxTier && (
          <StatusPill active={virtual.active}>
            {c.virtual}{virtual.active ? c.virtualOn : c.virtualOff}
          </StatusPill>
        )}
        <span className="hidden text-text-secondary sm:inline">
          {c.wakeWord} <code className="text-text-primary">灵枢</code>
          {wakeListening && lastHeard ? ` · ${lastHeard}` : ""}
          {wakeListening && wakeHint ? ` · ${wakeHint}` : ""}
        </span>
        <span className="ml-auto flex flex-wrap items-center gap-2">
          <NewSessionButton onClick={() => void startNewSession()} label={c.newSession} />
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
          <div className="min-h-0 flex-1 overflow-y-auto text-sm">
            <div className="flex min-h-full flex-col justify-end gap-2">
              {logs.length === 0 && (
                <p className="py-4 text-center text-xs text-text-secondary">{c.emptyHint}</p>
              )}
              {logs.map((l) => (
                <div
                  key={l.id}
                  className={`rounded-lg px-3 py-2 ${
                    l.role === "user" ? "bg-primary/10 text-primary" : "bg-surface-elevated text-text-primary"
                  }`}
                >
                  {l.role === "user" ? (
                    <div className="flex items-start gap-2.5">
                      <UserChatAvatar />
                      <span className="min-w-0 flex-1 pt-1">{l.text}</span>
                    </div>
                  ) : (
                    <>
                      {l.status === "thinking" && !l.text ? (
                        <div className="flex items-start gap-2.5 text-text-secondary">
                          <AgentChatAvatar />
                          <div className="flex items-center gap-2 pt-1">
                            <Loader2 size={14} className="animate-spin" aria-hidden />
                            <span>思考中…</span>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-start gap-2.5">
                          <AgentChatAvatar />
                          <div className="min-w-0 flex-1">
                            <ChatMessageContent text={l.text} />
                          </div>
                        </div>
                      )}
                      {l.confirmTask && (
                        <ConfirmPanel
                          compact
                          task={l.confirmTask}
                          onUpdate={(updated) => {
                            applyTaskToLog(updated, l.id);
                            if (updated.status === "running") {
                              void pollTaskUntilSettled(updated.task_id, l.id);
                            }
                          }}
                        />
                      )}
                      {l.thinking && l.thinking.length > 0 && (
                        <ThinkingPanel
                          steps={l.thinking}
                          open={Boolean(l.thinkingOpen)}
                          busy={l.status === "thinking"}
                          onToggle={() => patchLog(l.id, { thinkingOpen: !l.thinkingOpen })}
                        />
                      )}
                    </>
                  )}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>

          <div className="mt-3 flex shrink-0 gap-2 border-t border-border pt-3">
            <textarea
              className="input min-h-[2.5rem] min-w-0 flex-1 resize-none py-2 leading-relaxed"
              placeholder="输入指令或问题（Enter 发送，Shift+Enter 换行）"
              rows={2}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!loading) void submit(false);
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
              className={loading ? "btn-danger shrink-0" : "btn-primary shrink-0"}
              onClick={() => (loading ? void stopActiveRun() : void submit(false))}
              aria-label={loading ? "停止执行" : "发送"}
              title={loading ? "停止执行" : "发送"}
            >
              {loading ? <Pause size={16} aria-hidden /> : <Send size={16} aria-hidden />}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
