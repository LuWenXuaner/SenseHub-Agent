import { Link, Outlet } from "react-router-dom";
import { PanelLeft, PanelLeftClose, Plus, Trash2, User } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { ClawSessionProvider, useClawSessions } from "@/context/ClawSessionContext";

function ClawTopBar() {
  const { t } = useLocale();
  const { token } = useAuth();

  return (
    <header className="mimo-claw-header justify-end">
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

function ClawSidebar() {
  const { t } = useLocale();
  const [open, setOpen] = useState(true);
  const sessionApi = useClawSessions();

  const newSession = () => window.dispatchEvent(new CustomEvent("claw:new-session"));

  if (!open) {
    return (
      <aside className="mimo-claw-sidebar mimo-claw-sidebar-collapsed mimo-product-sidebar-full">
        <button type="button" className="mimo-studio-sidebar-toggle" onClick={() => setOpen(true)} aria-label="open">
          <PanelLeft size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="mimo-claw-sidebar mimo-product-sidebar-full">
      <div className="flex items-center gap-2 border-b border-mimo-border px-3 py-2">
        <button type="button" onClick={() => setOpen(false)} className="text-mimo-muted hover:text-mimo-text">
          <PanelLeftClose size={18} />
        </button>
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">{t.claw.title}</span>
        <button
          type="button"
          className="rounded p-1 text-mimo-muted hover:bg-black/5 hover:text-mimo-text"
          aria-label={t.claw.newSession}
          title={t.claw.newSession}
          onClick={newSession}
        >
          <Plus size={16} />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        <p className="px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-mimo-muted">{t.claw.history}</p>
        {!sessionApi || sessionApi.sessions.length === 0 ? (
          <p className="px-2 py-2 text-xs text-mimo-muted">{t.claw.noHistory}</p>
        ) : (
          <ul className="space-y-0.5">
            {sessionApi.sessions.map((s) => (
              <li key={s.id}>
                <div
                  className={`group flex items-center gap-1 rounded-lg px-1 ${
                    s.id === sessionApi.sessionId ? "bg-mimo-warm" : "hover:bg-mimo-warm/70"
                  }`}
                >
                  <button
                    type="button"
                    className={`min-w-0 flex-1 truncate px-1 py-1.5 text-left text-xs ${
                      s.id === sessionApi.sessionId ? "font-medium text-mimo-text" : "text-mimo-muted"
                    }`}
                    onClick={() => sessionApi.switchSession(s.id)}
                  >
                    {s.title}
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded p-1 text-mimo-muted opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                    aria-label={t.claw.deleteSession}
                    title={t.claw.deleteSession}
                    onClick={() => sessionApi.deleteSession(s.id)}
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

export function MimoClawShell() {
  return (
    <ClawSessionProvider>
      <div className="mimo-product-app flex h-screen">
        <ClawSidebar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <ClawTopBar />
          <main className="min-h-0 flex-1 overflow-hidden bg-mimo-warm">
            <Outlet />
          </main>
        </div>
      </div>
    </ClawSessionProvider>
  );
}
