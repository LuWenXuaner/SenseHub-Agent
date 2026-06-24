import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandDock } from "./CommandDock";
import { useLayout } from "@/context/LayoutContext";

const SYSTEM_PATHS = new Set(["/system/models", "/system/security", "/system/settings"]);

function isWorkspacePath(path: string): boolean {
  return (
    path.startsWith("/console") ||
    path.startsWith("/studio") ||
    path.startsWith("/rules") ||
    path.startsWith("/tasks") ||
    path.startsWith("/perception") ||
    path.startsWith("/system")
  );
}

export function AppShell() {
  const location = useLocation();
  const path = location.pathname;
  const isHome = location.pathname === "/";
  const isConsole = path === "/console";
  const workspacePage = isWorkspacePath(path);
  const showDock = workspacePage && !isConsole;
  const { sidebarOpen, toggleSidebar, setSidebarOpen } = useLayout();
  const noPageScroll = path === "/console" || SYSTEM_PATHS.has(path);

  return (
    <div className="flex h-screen flex-col bg-background">
      <TopBar
        onToggleSidebar={workspacePage ? toggleSidebar : undefined}
        sidebarOpen={sidebarOpen}
        workspaceMode={workspacePage}
      />
      <div className="flex min-h-0 flex-1">
        {workspacePage && sidebarOpen && <Sidebar onCollapse={() => setSidebarOpen(false)} />}
        <main className="flex min-h-0 flex-1 flex-col">
          <div
            className={`flex-1 p-4 md:p-5 ${noPageScroll ? "overflow-hidden" : "overflow-y-auto"}`}
          >
            <Outlet />
          </div>
          {showDock && <CommandDock />}
        </main>
      </div>
    </div>
  );
}
