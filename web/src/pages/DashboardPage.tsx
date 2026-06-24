import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Task } from "@/lib/api";
import { UsageMeter } from "@/components/tier/TierGate";
import { ConfirmPanel } from "@/components/tasks/ConfirmPanel";

export function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    api.listTasks().then(setTasks).catch(() => {});
  }, []);

  const pending = tasks.filter((t) => t.status === "wait_confirm");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">总览</h1>

      {pending.map((t) => (
        <ConfirmPanel
          key={t.task_id}
          task={t}
          onUpdate={(updated) => setTasks((prev) => prev.map((x) => (x.task_id === updated.task_id ? updated : x)))}
        />
      ))}

      <div className="card space-y-3">
        <UsageMeter />
        <div className="flex flex-wrap gap-3 text-sm">
          <Link to="/command" className="text-primary hover:underline">
            指令中心
          </Link>
          <Link to="/perception/camera" className="text-primary hover:underline">
            摄像头
          </Link>
          <Link to="/perception/voice" className="text-primary hover:underline">
            语音
          </Link>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-3 font-semibold">最近任务</h2>
        {tasks.length === 0 ? (
          <p className="text-sm text-text-secondary">暂无任务</p>
        ) : (
          <ul className="space-y-1">
            {tasks.slice(0, 8).map((t) => (
              <li key={t.task_id}>
                <Link
                  to={`/tasks/${t.task_id}`}
                  className="flex justify-between rounded px-1 py-1.5 hover:bg-surface-elevated"
                >
                  <span className="truncate text-sm">{t.intent_text}</span>
                  <span className="ml-2 shrink-0 text-xs text-text-secondary">{t.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
