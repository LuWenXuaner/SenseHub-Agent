import { useEffect, useState } from "react";
import { api, Rule } from "@/lib/api";

export function RulesPage({ embedded = false }: { embedded?: boolean }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [speechMatch, setSpeechMatch] = useState("");
  const [notifyMsg, setNotifyMsg] = useState("");

  const load = () => {
    api
      .listRules()
      .then(setRules)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const toggleEnabled = async (rule: Rule) => {
    await api.updateRule(rule.rule_id, { ...rule, enabled: !rule.enabled });
    load();
  };

  const remove = async (id: string) => {
    if (!confirm("确定删除？")) return;
    await api.deleteRule(id);
    load();
  };

  const addRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !speechMatch.trim()) return;
    await api.createRule({
      name: name.trim(),
      enabled: true,
      tier_min: "lite",
      trigger: { type: "speech", match: speechMatch.trim(), bypass_llm: false },
      action: { type: "notify", message: notifyMsg.trim() || `语音触发：${name}` },
    });
    setName("");
    setSpeechMatch("");
    setNotifyMsg("");
    setShowAdd(false);
    load();
  };

  if (loading) return <p className="text-text-secondary">加载中…</p>;

  return (
    <div className="space-y-4">
      {!embedded && (
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">规则</h1>
          <button type="button" className="btn-secondary text-sm" onClick={() => setShowAdd(!showAdd)}>
            {showAdd ? "取消" : "新建规则"}
          </button>
        </div>
      )}
      {embedded && (
        <div className="flex justify-end">
          <button type="button" className="mimo-console-outline-btn w-auto px-4" onClick={() => setShowAdd(!showAdd)}>
            {showAdd ? "取消" : "新建规则"}
          </button>
        </div>
      )}

      {showAdd && (
        <form className="card space-y-3" onSubmit={addRule}>
          <input
            className="input"
            placeholder="规则名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="input"
            placeholder="语音匹配词（如：打开记事本）"
            value={speechMatch}
            onChange={(e) => setSpeechMatch(e.target.value)}
            required
          />
          <input
            className="input"
            placeholder="触发通知（可选）"
            value={notifyMsg}
            onChange={(e) => setNotifyMsg(e.target.value)}
          />
          <button type="submit" className="btn-primary">
            保存
          </button>
        </form>
      )}

      <div className="space-y-3">
        {rules.map((r) => (
          <div key={r.rule_id} className="card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-medium">{r.name}</p>
                <p className="text-xs text-text-secondary">
                  {r.trigger.type}
                  {r.trigger.event && ` · ${r.trigger.event}`}
                  {r.trigger.match && ` · 「${r.trigger.match}」`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1 text-sm">
                  <input type="checkbox" checked={r.enabled} onChange={() => toggleEnabled(r)} />
                  启用
                </label>
                <button type="button" className="text-xs text-danger" onClick={() => remove(r.rule_id)}>
                  删除
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {rules.length === 0 && <p className="text-text-secondary">暂无规则</p>}
    </div>
  );
}
