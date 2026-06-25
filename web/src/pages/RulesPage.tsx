import { useEffect, useState } from "react";
import { api, Rule } from "@/lib/api";

type TriggerType = "speech" | "gesture" | "vision";
type ActionType = "notify" | "confirm_pending" | "cancel_pending";

const GESTURE_EVENTS = [
  { id: "wave", label: "挥手" },
  { id: "nod", label: "点头" },
  { id: "shake", label: "摇头" },
  { id: "hand_raised", label: "举手" },
];

const VISION_EVENTS = [{ id: "person_detected", label: "人员出现" }];

export function RulesPage({ embedded = false }: { embedded?: boolean }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState<TriggerType>("speech");
  const [speechMatch, setSpeechMatch] = useState("");
  const [gestureEvent, setGestureEvent] = useState("nod");
  const [visionEvent, setVisionEvent] = useState("person_detected");
  const [confidenceMin, setConfidenceMin] = useState(0.55);
  const [actionType, setActionType] = useState<ActionType>("notify");
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
    if (!name.trim()) return;
    let trigger: Rule["trigger"];
    if (triggerType === "speech") {
      if (!speechMatch.trim()) return;
      trigger = { type: "speech", match: speechMatch.trim(), bypass_llm: false };
    } else if (triggerType === "gesture") {
      trigger = { type: "gesture", event: gestureEvent, confidence_min: confidenceMin };
    } else {
      trigger = { type: "vision", event: visionEvent, confidence_min: confidenceMin };
    }
    const action =
      actionType === "notify"
        ? { type: "notify", message: notifyMsg.trim() || name.trim() }
        : { type: actionType, message: notifyMsg.trim() || name.trim() };
    await api.createRule({
      name: name.trim(),
      enabled: true,
      tier_min: triggerType === "speech" ? "lite" : "pro",
      trigger,
      action,
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
          <select className="input" value={triggerType} onChange={(e) => setTriggerType(e.target.value as TriggerType)}>
            <option value="speech">语音</option>
            <option value="gesture">手势</option>
            <option value="vision">视觉</option>
          </select>
          {triggerType === "speech" && (
            <input
              className="input"
              placeholder="语音匹配词（如：打开记事本）"
              value={speechMatch}
              onChange={(e) => setSpeechMatch(e.target.value)}
              required
            />
          )}
          {triggerType === "gesture" && (
            <select className="input" value={gestureEvent} onChange={(e) => setGestureEvent(e.target.value)}>
              {GESTURE_EVENTS.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          )}
          {triggerType === "vision" && (
            <select className="input" value={visionEvent} onChange={(e) => setVisionEvent(e.target.value)}>
              {VISION_EVENTS.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          )}
          {triggerType !== "speech" && (
            <label className="text-sm">
              置信度阈值
              <input
                type="number"
                step={0.05}
                min={0.3}
                max={0.95}
                className="input mt-1"
                value={confidenceMin}
                onChange={(e) => setConfidenceMin(Number(e.target.value))}
              />
            </label>
          )}
          <select className="input" value={actionType} onChange={(e) => setActionType(e.target.value as ActionType)}>
            <option value="notify">仅通知</option>
            <option value="confirm_pending">点头确认待确认任务</option>
            <option value="cancel_pending">取消待确认任务</option>
          </select>
          <input
            className="input"
            placeholder="触发说明（可选）"
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
                  {r.action.type !== "notify" && ` · 动作 ${r.action.type}`}
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
