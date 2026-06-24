import { Moon, Sun, OctagonAlert, Sparkles, PanelLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
const tierLabel: Record<string, string> = {
  lite: "Lite",
  pro: "Pro",
  max: "Max",
};

export function TopBar({
  onToggleSidebar,
  sidebarOpen,
  workspaceMode,
}: {
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
  workspaceMode?: boolean;
}) {
  const { toggle, mode } = useTheme();
  const { license, logout, user } = useAuth();

  const onKill = async () => {
    if (!confirm("确定激活紧急停止？将立即停止所有键鼠自动化。")) return;
    await api.killSwitch();
    alert("Kill Switch 已激活");
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface px-4 lg:px-6">
      <div className="flex items-center gap-2 lg:gap-3">
        {onToggleSidebar && (
          <button
            type="button"
            className="btn-ghost p-2"
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? "收起侧边栏" : "展开侧边栏"}
            title={sidebarOpen ? "收起侧边栏" : "展开侧边栏"}
          >
            <PanelLeft size={18} aria-hidden />
          </button>
        )}
        <Sparkles className="text-primary" size={22} aria-hidden />
        <Link to="/" className="font-semibold tracking-tight">
          灵枢 Agent
        </Link>
      </div>

      <div className="flex items-center gap-1.5 lg:gap-2">
        {user && (
          <span className="hidden text-sm text-text-secondary xl:inline">
            {user.display_name || user.username}
          </span>
        )}
        {license && (
          <Link
            to="/console/points"
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              license.tier === "max"
                ? "border border-primary text-primary"
                : license.tier === "pro"
                  ? "bg-primary/15 text-primary"
                  : "bg-surface-elevated text-text-secondary"
            }`}
          >
            {tierLabel[license.tier]}
          </Link>
        )}
        <button
          type="button"
          className="btn-ghost"
          onClick={toggle}
          aria-label="切换主题"
        >
          {mode === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        {workspaceMode && (
          <button type="button" className="btn-danger" onClick={onKill} aria-label="紧急停止">
            <OctagonAlert size={16} className="mr-1" />
            停止
          </button>
        )}
        <button type="button" className="btn-ghost" onClick={logout}>
          退出
        </button>
      </div>
    </header>
  );
}
