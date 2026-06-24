import { Link, Outlet } from "react-router-dom";
import { PanelLeft, PanelLeftClose, Plus, Trash2, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { CodeProvider, useCode } from "@/context/CodeContext";

function CodeTopBar() {
  const { t } = useLocale();
  const { token } = useAuth();

  return (
    <header className="mimo-claw-header justify-end border-b border-mimo-border">
      <nav className="flex items-center gap-3 text-sm text-mimo-muted">
        <LanguageSwitcher />
        {!token ? (
          <Link to="/login" className="mimo-btn-cta mimo-btn-sm">
            {t.studio.login}
          </Link>
        ) : (
          <Link
            to="/console/account"
            className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-mimo-warm"
            title={t.console.title}
          >
            <User size={16} />
          </Link>
        )}
      </nav>
    </header>
  );
}

function CodeSidebar() {
  const { t } = useLocale();
  const { newSession, sidebarOpen, setSidebarOpen, sessions, sessionId, switchSession, deleteSession } = useCode();

  const onDelete = (id: string, title: string) => {
    const msg = (t.code.confirmDelete ?? "删除任务「{title}」？").replace("{title}", title);
    if (!window.confirm(msg)) return;
    deleteSession(id);
  };

  if (!sidebarOpen) {
    return (
      <aside className="mimo-claw-sidebar mimo-claw-sidebar-collapsed mimo-product-sidebar-full border-r border-mimo-border">
        <button type="button" className="mimo-studio-sidebar-toggle" onClick={() => setSidebarOpen(true)} aria-label="open">
          <PanelLeft size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="mimo-claw-sidebar mimo-product-sidebar-full border-r border-mimo-border">
      <div className="flex items-center gap-2 border-b border-mimo-border px-3 py-2">
        <button type="button" onClick={() => setSidebarOpen(false)} className="text-mimo-muted hover:text-mimo-text">
          <PanelLeftClose size={18} />
        </button>
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">{t.code.title}</span>
        <button
          type="button"
          className="rounded p-1 text-mimo-muted hover:bg-black/5 hover:text-mimo-text"
          aria-label={t.code.newTask}
          title={t.code.newTask}
          onClick={newSession}
        >
          <Plus size={16} />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        <p className="px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-mimo-muted">{t.code.agentHistory}</p>
        {sessions.length === 0 ? (
          <p className="px-2 py-2 text-xs text-mimo-muted">{t.code.noHistory}</p>
        ) : (
          <ul className="space-y-0.5">
            {sessions.map((s) => (
              <li key={s.id}>
                <div
                  className={`group flex items-center gap-1 rounded-lg px-1 ${
                    s.id === sessionId ? "bg-mimo-warm" : "hover:bg-mimo-warm/70"
                  }`}
                >
                  <button
                    type="button"
                    className={`min-w-0 flex-1 truncate px-1 py-1.5 text-left text-xs ${
                      s.id === sessionId ? "font-medium text-mimo-text" : "text-mimo-muted"
                    }`}
                    onClick={() => switchSession(s.id)}
                  >
                    {s.title}
                    {s.projectName ? (
                      <span className="mt-0.5 block truncate text-[10px] font-normal opacity-60">{s.projectName}</span>
                    ) : null}
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded p-1 text-mimo-muted opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                    aria-label={t.code.deleteTask}
                    title={t.code.deleteTask}
                    onClick={() => onDelete(s.id, s.title)}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-mimo-border p-3">
        <Link to="/console/account" className="text-xs text-mimo-muted hover:text-mimo-text">
          ← {t.console.title}
        </Link>
      </div>
    </aside>
  );
}

function CodeLayout() {
  return (
    <div className="mimo-product-app flex h-screen">
      <CodeSidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <CodeTopBar />
        <main className="min-h-0 flex-1 overflow-hidden bg-mimo-warm">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function MimoCodeShell() {
  return (
    <CodeProvider>
      <CodeLayout />
    </CodeProvider>
  );
}
