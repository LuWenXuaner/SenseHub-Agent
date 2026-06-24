import { useEffect, useState } from "react";
import { useTheme, ThemeMode } from "@/hooks/useTheme";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { StatusLine, SystemCard, SystemPageLayout } from "@/components/layout/SystemPageLayout";

type ProviderRow = {
  id: string;
  label: string;
  base_url: string;
  api_key: string;
  configured: boolean;
  source: string;
  roles: string[];
  default_base_url: string;
};

export function SettingsPage() {
  const { mode, setMode } = useTheme();
  const { user, license } = useAuth();
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [draft, setDraft] = useState<Record<string, { base_url: string; api_key: string }>>({});
  const [oldPwd, setOldPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () =>
    api.getApiConfig().then((c) => {
      const list = (c as { providers?: ProviderRow[] }).providers || [];
      setProviders(list);
      const init: Record<string, { base_url: string; api_key: string }> = {};
      for (const p of list) {
        init[p.id] = { base_url: p.base_url || p.default_base_url || "", api_key: "" };
      }
      setDraft(init);
    });

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const saveProviders = async () => {
    setErr("");
    try {
      const payload: Record<string, { base_url: string; api_key: string }> = {};
      for (const [id, row] of Object.entries(draft)) {
        if (row.base_url.trim() || row.api_key.trim()) {
          payload[id] = { base_url: row.base_url.trim(), api_key: row.api_key.trim() };
        }
      }
      await api.saveApiConfig({ providers: payload });
      setMsg("提供商配置已保存（OpenAI 兼容）");
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "保存失败");
    }
  };

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    setErr("");
    if (newPwd !== confirmPwd) {
      setErr("两次新密码不一致");
      return;
    }
    try {
      await api.changePassword(oldPwd, newPwd);
      setMsg("密码已更新");
      setOldPwd("");
      setNewPwd("");
      setConfirmPwd("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "修改失败");
    }
  };

  const configured = providers.filter((p) => p.configured).length;

  return (
    <SystemPageLayout
      title="设置"
      description={`账号与主题 · OpenAI 兼容 API（已配置 ${configured}/${providers.length} 个提供商）`}
      footer={
        <>
          {msg && <StatusLine ok>{msg}</StatusLine>}
          {err && <StatusLine>{err}</StatusLine>}
        </>
      }
    >
      <div className="grid h-full min-h-0 grid-rows-[auto_1fr] gap-2">
        <div className="grid shrink-0 grid-cols-1 gap-2 md:grid-cols-3">
          <SystemCard>
            <p className="text-xs text-text-primary">
              {user?.display_name || user?.username}
              <span className="text-text-secondary"> · {license?.tier.toUpperCase()}</span>
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {(["light", "dark", "system"] as ThemeMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`rounded-md border px-2 py-0.5 text-[11px] ${
                    mode === m ? "border-primary bg-primary/15 text-primary" : "border-border text-text-secondary"
                  }`}
                  onClick={() => setMode(m)}
                >
                  {m === "light" ? "浅色" : m === "dark" ? "深色" : "系统"}
                </button>
              ))}
            </div>
          </SystemCard>

          <form className="card flex items-end gap-1.5 p-3 md:col-span-2" onSubmit={changePassword}>
            <input type="password" className="input min-w-0 flex-1 py-1 text-xs" placeholder="当前密码" value={oldPwd} onChange={(e) => setOldPwd(e.target.value)} />
            <input type="password" className="input min-w-0 flex-1 py-1 text-xs" placeholder="新密码" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} />
            <input type="password" className="input min-w-0 flex-1 py-1 text-xs" placeholder="确认" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)} />
            <button type="submit" className="btn-primary shrink-0 text-xs">
              改密
            </button>
          </form>
        </div>

        <SystemCard title="LLM 提供商（OpenAI 兼容 · 任选其一或多项）" className="min-h-0">
          <p className="mb-2 shrink-0 text-[11px] text-text-secondary">
            支持 OpenAI、DeepSeek、小米 MiMo、硅基流动、火山方舟等；角色用哪个提供商由 models.yaml 的 roles 决定。
            Key 也可写在 local.env（OPENAI_API_KEY、DEEPSEEK_API_KEY、MIMO_API_KEY 等）。
          </p>
          <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 overflow-hidden md:grid-cols-2 xl:grid-cols-3">
            {providers.map((p) => (
              <div
                key={p.id}
                className={`rounded-lg border p-2 ${
                  p.configured ? "border-success/30 bg-success/5" : "border-border bg-surface-elevated/30"
                }`}
              >
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold">{p.label}</span>
                  <span className="text-[10px] text-text-secondary">
                    {p.configured ? p.source : "未配置"}
                    {p.roles.length > 0 && ` · ${p.roles.join(",")}`}
                  </span>
                </div>
                <input
                  className="input mb-1 w-full py-1 font-mono text-[11px]"
                  placeholder={p.default_base_url || "Base URL"}
                  value={draft[p.id]?.base_url ?? ""}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, [p.id]: { ...d[p.id], base_url: e.target.value } }))
                  }
                />
                <input
                  className="input w-full py-1 font-mono text-[11px]"
                  type="password"
                  placeholder={p.api_key ? `已配置 ${p.api_key}` : "API Key"}
                  value={draft[p.id]?.api_key ?? ""}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, [p.id]: { ...d[p.id], api_key: e.target.value } }))
                  }
                />
              </div>
            ))}
          </div>
          <div className="mt-2 flex shrink-0 gap-2">
            <button type="button" className="btn-primary text-xs" onClick={() => void saveProviders()}>
              保存全部提供商
            </button>
            <button
              type="button"
              className="btn-ghost border border-border text-xs"
              onClick={async () => {
                await api.resetApiConfig();
                setMsg("已恢复 env 默认");
                await load();
              }}
            >
              清除 Web 覆盖
            </button>
          </div>
        </SystemCard>
      </div>
    </SystemPageLayout>
  );
}
