import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandDock } from "./CommandDock";
import { useLayout } from "@/context/LayoutContext";

const NO_SCROLL = new Set(["/console", "/studio", "/system/models", "/system/security", "/system/settings"]);

export function WorkspaceShell() {
  const path = useLocation().pathname;
  const isConsole = path === "/console";
  const { sidebarOpen, toggleSidebar, setSidebarOpen } = useLayout();

  return (
    <div className="flex h-screen flex-col bg-background">
      <TopBar onToggleSidebar={toggleSidebar} sidebarOpen={sidebarOpen} workspaceMode />
      <div className="flex min-h-0 flex-1">
        {sidebarOpen && <Sidebar onCollapse={() => setSidebarOpen(false)} />}
        <main className="flex min-h-0 flex-1 flex-col">
          <div className={`flex-1 p-4 md:p-5 ${NO_SCROLL.has(path) ? "overflow-hidden" : "overflow-y-auto"}`}>
            <Outlet />
          </div>
          {!isConsole && <CommandDock />}
        </main>
      </div>
    </div>
  );
}
