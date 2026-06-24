import { History, Trash2, X } from "lucide-react";
import type { HubSession } from "@/lib/hubSessions";

export function SessionDrawer({
  open,
  sessions,
  activeId,
  onClose,
  onSelect,
  onDelete,
}: {
  open: boolean;
  sessions: HubSession[];
  activeId: string;
  onClose: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  if (!open) return null;

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px]"
        aria-label="关闭会话列表"
        onClick={onClose}
      />
      <aside
        className="fixed inset-y-0 left-0 z-50 flex w-[min(100%,20rem)] flex-col border-r border-border bg-surface shadow-xl"
        role="dialog"
        aria-label="历史会话"
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <History size={16} aria-hidden />
            历史会话
            <span className="font-normal text-text-secondary">({sessions.length})</span>
          </div>
          <button type="button" className="btn-ghost p-1" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <ul className="flex-1 space-y-1 overflow-y-auto p-2">
          {sessions.map((s) => (
            <li key={s.id}>
              <div
                className={`group flex items-start gap-2 rounded-lg px-2 py-2 ${
                  s.id === activeId ? "bg-primary/12 ring-1 ring-primary/30" : "hover:bg-surface-elevated"
                }`}
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() => onSelect(s.id)}
                >
                  <p className="truncate text-sm font-medium text-text-primary">{s.title}</p>
                  <p className="mt-0.5 text-[11px] text-text-secondary">
                    {new Date(s.updatedAt).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    {s.logs.length > 0 ? ` · ${s.logs.length} 条` : ""}
                  </p>
                </button>
                <button
                  type="button"
                  className="shrink-0 rounded p-1 text-text-secondary opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                  title="删除会话"
                  aria-label="删除会话"
                  onClick={() => onDelete(s.id)}
                >
                  <Trash2 size={14} aria-hidden />
                </button>
              </div>
            </li>
          ))}
          {sessions.length === 0 && (
            <li className="px-3 py-8 text-center text-xs text-text-secondary">暂无历史会话</li>
          )}
        </ul>
      </aside>
    </>
  );
}
