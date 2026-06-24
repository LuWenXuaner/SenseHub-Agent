import { api, Task } from "@/lib/api";

interface ConfirmPanelProps {
  task: Task;
  onUpdate: (task: Task) => void;
  compact?: boolean;
}

export function ConfirmPanel({ task, onUpdate, compact }: ConfirmPanelProps) {
  if (task.status !== "wait_confirm") return null;

  const approve = async () => {
    const updated = await api.confirmTask(task.task_id);
    onUpdate(updated);
  };

  const reject = async () => {
    const updated = await api.cancelTask(task.task_id);
    onUpdate(updated);
  };

  return (
    <div
      className={`rounded-xl border border-warning bg-warning/10 ${
        compact ? "p-3" : "card"
      }`}
    >
        <p className={`${compact ? "text-sm" : ""} mb-2 font-medium text-warning`}>
        需要你确认
      </p>
      {!compact && (
        <p className="mb-3 text-sm text-text-secondary">
          {task.summary || task.intent_text}
        </p>
      )}
      {compact && task.plan_steps.length > 0 && (
        <ul className="mb-2 space-y-1 text-xs text-text-secondary">
          {task.plan_steps.map((s) => (
            <li key={s.step_id}>
              · {s.description || s.tool}
              {s.risk_level === "L2" ? "（敏感操作）" : ""}
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary" onClick={approve}>
          确认执行
        </button>
        <button type="button" className="btn-ghost border border-border" onClick={reject}>
          取消
        </button>
      </div>
    </div>
  );
}
