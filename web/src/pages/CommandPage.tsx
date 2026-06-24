import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export function CommandPage() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { license, refreshLicense } = useAuth();
  const multiAgent = Boolean(license?.features?.multi_agent);

  const submit = async (multi = false) => {
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      const task = multi
        ? await api.createMultiAgentTask(text.trim())
        : await api.createTask(text.trim());
      await refreshLicense();
      navigate(`/tasks/${task.task_id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "失败");
    } finally {
      setLoading(false);
    }
  };

  const shortcuts = [
    { label: "截个图", cmd: "截个图" },
    { label: "打开记事本", cmd: "打开记事本" },
    { label: "浏览器搜索", cmd: "打开浏览器搜索 灵枢 Agent" },
  ];

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">指令中心</h1>
      <textarea
        className="input min-h-[120px]"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="描述你想完成的任务…"
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary" onClick={() => submit(false)} disabled={loading}>
          {loading ? "执行中…" : "发送"}
        </button>
        {multiAgent && (
          <button type="button" className="btn-secondary" onClick={() => submit(true)} disabled={loading}>
            多 Agent
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {shortcuts.map((s) => (
          <button
            key={s.cmd}
            type="button"
            className="rounded-full border border-border px-3 py-1 text-sm hover:border-primary"
            onClick={() => setText(s.cmd)}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
