import { Link, Outlet } from "react-router-dom";
import { Check, ChevronDown, Link2, PanelLeft, PanelLeftClose, Plus, Trash2, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { STUDIO_MODELS } from "@/lib/siteContent";
import { StudioProvider, useStudio } from "@/context/StudioContext";

function StudioTopBar() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const { modelId, setModelId, selectedModel } = useStudio();
  const { token } = useAuth();
  const { t } = useLocale();

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <header className="mimo-studio-header">
      <div ref={rootRef} className="relative">
        <button
          type="button"
          className="mimo-studio-model-btn"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {selectedModel?.name}
          {selectedModel?.badge && <span className="mimo-studio-badge-new">{selectedModel.badge}</span>}
          <ChevronDown size={14} className={`opacity-50 transition ${open ? "rotate-180" : ""}`} />
        </button>
        {open && (
          <div className="mimo-studio-model-menu">
            {STUDIO_MODELS.map((m) => (
              <button
                key={m.id}
                type="button"
                className={`mimo-studio-model-option ${m.id === modelId ? "mimo-studio-model-option-active" : ""}`}
                onClick={() => {
                  setModelId(m.id);
                  setOpen(false);
                }}
              >
                <div className="min-w-0 flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{m.name}</span>
                    {m.badge && <span className="mimo-studio-badge-new">{m.badge}</span>}
                  </div>
                  <p className="mt-0.5 text-xs text-mimo-muted">{m.description}</p>
                </div>
                {m.id === modelId && <Check size={16} />}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-3">
        <Link to="/console/api-keys" className="mimo-studio-api-link">
          <Link2 size={14} />
          {t.studio.apiService}
        </Link>
        {!token ? (
          <Link to="/login" className="mimo-btn-cta text-sm">
            {t.studio.login}
          </Link>
        ) : (
          <Link
            to="/console/account"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-mimo-warm"
            title={t.console.title}
          >
            <User size={16} />
          </Link>
        )}
      </div>
    </header>
  );
}

function StudioSidebar() {
  const { t, locale } = useLocale();
  const { newChat, sidebarOpen, setSidebarOpen, sessions, sessionId, switchSession, deleteSession } = useStudio();

  const onDelete = (id: string, title: string) => {
    const msg = (t.studio.confirmDelete ?? "删除对话「{title}」？").replace("{title}", title);
    if (!window.confirm(msg)) return;
    deleteSession(id);
  };

  if (!sidebarOpen) {
    return (
      <aside className="mimo-studio-sidebar mimo-studio-sidebar-collapsed">
        <button
          type="button"
          className="mimo-studio-sidebar-toggle"
          onClick={() => setSidebarOpen(true)}
          aria-label="open"
        >
          <PanelLeft size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="mimo-studio-sidebar">
      <div className="flex items-center gap-2 border-b border-mimo-border px-4 py-3">
        <button type="button" className="text-mimo-muted hover:text-mimo-text" onClick={() => setSidebarOpen(false)}>
          <PanelLeftClose size={18} />
        </button>
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">
          {locale === "zh" ? "灵枢" : "SenseHub"}{" "}
          <span className="font-normal text-mimo-muted">Chat</span>
        </span>
        <button
          type="button"
          className="rounded p-1 text-mimo-muted hover:bg-black/5 hover:text-mimo-text"
          aria-label={t.studio.newChat}
          title={t.studio.newChat}
          onClick={newChat}
        >
          <Plus size={16} />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        <p className="px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-mimo-muted">{t.studio.history}</p>
        {sessions.length === 0 ? (
          <p className="px-2 py-2 text-xs text-mimo-muted">{t.studio.noHistory}</p>
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
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded p-1 text-mimo-muted opacity-0 transition hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                    aria-label={t.studio.deleteSession}
                    title={t.studio.deleteSession}
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

function StudioLayout() {
  return (
    <div className="mimo-product-app flex h-screen flex-col bg-white">
      <div className="flex min-h-0 flex-1">
        <StudioSidebar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <StudioTopBar />
          <main className="mimo-studio-main min-h-0 flex-1 overflow-hidden">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

export function MimoStudioShell() {
  return (
    <StudioProvider>
      <StudioLayout />
    </StudioProvider>
  );
}
