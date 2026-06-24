import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, getToken, screenshotUrl, Task } from "@/lib/api";
import { ConfirmPanel } from "@/components/tasks/ConfirmPanel";

const statusLabel: Record<string, string> = {
  pending: "排队中",
  running: "执行中",
  wait_confirm: "待确认",
  done: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    if (!id) return;
    api.getTask(id).then(setTask).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    if (!id) return;
    const token = getToken();
    if (!token) return;
    const ws = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/tasks?token=${encodeURIComponent(token)}`
    );
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "task_update" && data.task?.task_id === id) {
        setTask(data.task);
      }
    };
    return () => ws.close();
  }, [id]);

  const cancel = async () => {
    if (!id || !confirm("确定取消此任务？")) return;
    const updated = await api.cancelTask(id);
    setTask(updated);
  };

  if (loading) return <p className="text-text-secondary">加载中…</p>;
  if (!task) return <p className="text-danger">任务不存在</p>;

  const canCancel = !["done", "failed", "cancelled"].includes(task.status);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">任务</h1>
          <p className="text-text-secondary">{task.intent_text}</p>
          <p className="mt-1 text-sm">
            {statusLabel[task.status] || task.status}
            {task.current_step > 0 && task.plan_steps.length > 0 && (
              <span className="ml-2 text-text-secondary">
                · 步骤 {task.current_step}/{task.plan_steps.length}
              </span>
            )}
          </p>
          {task.error && <p className="text-sm text-danger">{task.error}</p>}
        </div>
        {canCancel && (
          <button type="button" className="btn-ghost border border-border text-sm" onClick={cancel}>
            取消任务
          </button>
        )}
      </div>

      <ConfirmPanel task={task} onUpdate={setTask} />

      {task.plan_steps.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-semibold">执行计划</h2>
          <ol className="space-y-2">
            {task.plan_steps.map((step, i) => (
              <li key={step.step_id} className="flex gap-3 text-sm">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
                    task.current_step > i ? "bg-success/20 text-success" : "bg-border"
                  }`}
                >
                  {step.step_id}
                </span>
                <span>{step.description || step.tool}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {task.step_results.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-semibold">结果</h2>
          <ul className="space-y-3">
            {task.step_results.map((r) => {
              const url = screenshotUrl(r.screenshot_path);
              return (
                <li key={r.step_id} className="text-sm">
                  <p className={r.success ? "text-success" : "text-danger"}>
                    步骤 {r.step_id}: {r.success ? "成功" : r.error}
                  </p>
                  {url && (
                    <a href={url} target="_blank" rel="noreferrer">
                      <img src={url} alt="截图" className="mt-2 max-h-48 rounded border border-border" />
                    </a>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
