import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { TierGate } from "@/components/tier/TierGate";

export function CommandDock() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { refreshLicense } = useAuth();

  const submit = async () => {
    const cmd = text.trim();
    if (!cmd || loading) return;
    setLoading(true);
    try {
      const task = await api.createTask(cmd);
      setText("");
      await refreshLicense();
      navigate(`/tasks/${task.task_id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "发送失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="shrink-0 border-t border-border bg-surface p-3">
      <div className="mx-auto flex max-w-4xl items-center gap-2">
        <input
          id="command-input"
          name="command"
          className="input min-w-0 flex-1"
          placeholder="输入指令，例如：截个图 / 看屏幕打开记事本"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          aria-label="指令输入"
        />
        <TierGate requiredTier="pro" mode="inline" />
        <button
          type="button"
          className="btn-primary shrink-0 whitespace-nowrap"
          onClick={submit}
          disabled={loading}
          aria-label="发送指令"
        >
          <Send size={16} className="mr-1" />
          {loading ? "发送中…" : "发送"}
        </button>
      </div>
    </div>
  );
}
