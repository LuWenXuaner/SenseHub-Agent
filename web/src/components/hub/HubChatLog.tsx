import { AlertCircle, Bot, Loader2, UserRound } from "lucide-react";
import { ChatMessageContent } from "@/components/chat/ChatMessageContent";
import { ConfirmPanel } from "@/components/tasks/ConfirmPanel";
import type { Task } from "@/lib/api";
import type { ThinkingStep } from "@/lib/thinkingTrace";
import type { HubLogItem } from "@/lib/hubSessions";

type StepStatus = ThinkingStep["status"];

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "running") return <Loader2 size={12} className="animate-spin text-primary" aria-hidden />;
  if (status === "error") return <AlertCircle size={12} className="text-danger" aria-hidden />;
  return (
    <span className="inline-flex h-3 w-3 items-center justify-center rounded-full bg-success/20 text-success" aria-hidden>
      ✓
    </span>
  );
}

function ThinkingPanel({
  steps,
  open,
  onToggle,
  busy,
  labels,
}: {
  steps: ThinkingStep[];
  open: boolean;
  onToggle: () => void;
  busy?: boolean;
  labels: { busy: string; process: (done: number, total: number) => string };
}) {
  if (!steps.length) return null;
  const done = busy
    ? steps.filter((s) => s.status === "done").length
    : steps.filter((s) => s.status !== "error" && s.status !== "running").length;
  return (
    <div className="hub-chat-thinking">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs font-medium text-text-secondary transition hover:text-text-primary"
      >
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-primary/10 text-primary">
          {busy ? <Loader2 size={12} className="animate-spin" /> : "⚙"}
        </span>
        {busy ? labels.busy : labels.process(done, steps.length)}
      </button>
      {open && (
        <div className="mt-2 space-y-2 rounded-lg border border-border/60 bg-surface/50 p-2.5">
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

type Props = {
  log: HubLogItem;
  stopping?: boolean;
  labels: {
    you: string;
    agent: string;
    thinking: string;
    stopping: string;
    busy: string;
    process: (done: number, total: number) => string;
  };
  onPatch: (patch: Partial<HubLogItem>) => void;
  onApplyTask: (task: Task, logId: string) => void;
  onPollTask: (taskId: string, logId: string) => void;
};

export function HubChatLog({ log, stopping, labels, onPatch, onApplyTask, onPollTask }: Props) {
  if (log.role === "user") {
    return (
      <article className="hub-chat-row hub-chat-row-user">
        <div className="hub-chat-avatar hub-chat-avatar-user" aria-hidden>
          <UserRound size={16} strokeWidth={2} />
        </div>
        <div className="hub-chat-main">
          <span className="hub-chat-name">{labels.you}</span>
          <div className="hub-chat-bubble hub-chat-bubble-user">{log.text}</div>
        </div>
      </article>
    );
  }

  const isError = log.status === "error";
  const hasProgress = Boolean(log.thinking && log.thinking.length > 0);
  const isThinking = (log.status === "thinking" && !log.text && !hasProgress) || Boolean(stopping);
  const showBusyBubble = isThinking;

  return (
    <article className={`hub-chat-row ${isError ? "hub-chat-row-error" : ""}`}>
      <div className="hub-chat-avatar hub-chat-avatar-agent" aria-hidden>
        <Bot size={16} strokeWidth={2} />
      </div>
      <div className="hub-chat-main">
        <span className="hub-chat-name">{labels.agent}</span>
        {showBusyBubble ? (
          <div className={`hub-chat-bubble hub-chat-bubble-agent hub-chat-bubble-busy ${stopping ? "hub-chat-bubble-stopping" : ""}`}>
            <Loader2 size={14} className="animate-spin text-primary" aria-hidden />
            <span>{stopping ? labels.stopping : labels.thinking}</span>
          </div>
        ) : log.text || log.status !== "thinking" ? (
          <div
            className={`hub-chat-bubble hub-chat-bubble-agent ${
              isError ? "hub-chat-bubble-error" : ""
            }`}
          >
            <ChatMessageContent text={log.text} variant="studio" />
          </div>
        ) : null}
        {log.confirmTask && (
          <ConfirmPanel
            compact
            task={log.confirmTask}
            onUpdate={(updated) => {
              onApplyTask(updated, log.id);
              if (updated.status === "running") {
                onPollTask(updated.task_id, log.id);
              }
            }}
          />
        )}
        {log.thinking && log.thinking.length > 0 && (
          <ThinkingPanel
            steps={log.thinking}
            open={Boolean(log.thinkingOpen)}
            busy={log.status === "thinking"}
            labels={{ busy: labels.busy, process: labels.process }}
            onToggle={() => onPatch({ thinkingOpen: !log.thinkingOpen })}
          />
        )}
      </div>
    </article>
  );
}
