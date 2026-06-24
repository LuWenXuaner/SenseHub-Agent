import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Task } from "@/lib/api";
import { ConfirmPanel } from "@/components/tasks/ConfirmPanel";

const statusColor: Record<string, string> = {
  done: "text-success",
  running: "text-primary",
  failed: "text-danger",
  wait_confirm: "text-warning",
  pending: "text-text-secondary",
  cancelled: "text-text-secondary",
};

const statusLabel: Record<string, string> = {
  wait_confirm: "待确认",
  done: "已完成",
  running: "执行中",
  failed: "失败",
  pending: "排队中",
  cancelled: "已取消",
};

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .listTasks()
      .then(setTasks)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const pending = tasks.filter((t) => t.status === "wait_confirm");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">任务</h1>
        <button type="button" className="btn-ghost text-sm" onClick={load}>
          刷新
        </button>
      </div>

      {pending.length > 0 && (
        <div className="space-y-2">
          {pending.map((t) => (
            <ConfirmPanel
              key={t.task_id}
              task={t}
              compact
              onUpdate={(updated) => setTasks((prev) => prev.map((x) => (x.task_id === updated.task_id ? updated : x)))}
            />
          ))}
        </div>
      )}

      {loading ? (
        <p className="text-text-secondary">加载中…</p>
      ) : tasks.length === 0 ? (
        <p className="text-text-secondary">暂无任务</p>
      ) : (
        <div className="space-y-2">
          {tasks.map((t) => (
            <Link
              key={t.task_id}
              to={`/tasks/${t.task_id}`}
              className="card block hover:border-primary/40"
            >
              <div className="flex justify-between gap-4">
                <span className="font-medium">{t.intent_text}</span>
                <span className={`text-sm ${statusColor[t.status] || ""}`}>
                  {statusLabel[t.status] || t.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
