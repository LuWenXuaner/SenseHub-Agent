import { NavLink } from "react-router-dom";
import {
  Workflow,
  Brain,
  Shield,
  Settings,
  CreditCard,
  Sparkles,
  Command,
  Shapes,
  PanelLeftClose,
} from "lucide-react";
import { TierGate } from "@/components/tier/TierGate";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
    isActive
      ? "bg-primary/15 text-primary font-medium"
      : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
  }`;

function NavItem({
  to,
  icon: Icon,
  label,
  tier,
}: {
  to: string;
  icon: typeof Sparkles;
  label: string;
  tier?: "pro" | "max";
}) {
  const inner = (
    <NavLink to={to} className={linkClass}>
      <Icon size={18} aria-hidden />
      {label}
    </NavLink>
  );
  if (tier) {
    return (
      <TierGate requiredTier={tier} mode="nav">
        {inner}
      </TierGate>
    );
  }
  return inner;
}

export function Sidebar({ onCollapse }: { onCollapse?: () => void }) {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-surface p-3">
      <div className="mb-3 flex items-center justify-between gap-2 px-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-text-secondary">导航</span>
        {onCollapse && (
          <button
            type="button"
            className="rounded-lg p-1.5 text-text-secondary transition hover:bg-surface-elevated hover:text-primary"
            onClick={onCollapse}
            aria-label="收起侧边栏"
            title="收起侧边栏"
          >
            <PanelLeftClose size={16} aria-hidden />
          </button>
        )}
      </div>
      <nav className="flex flex-1 flex-col gap-4 overflow-hidden text-sm">
        <div>
          <p className="mb-2 px-3 text-xs font-semibold uppercase text-text-secondary">产品</p>
          <div className="flex flex-col gap-1">
            <NavItem to="/" icon={Sparkles} label="首页" />
            <NavItem to="/claw" icon={Command} label="Claw" />
            <NavItem to="/studio" icon={Shapes} label="Studio" />
          </div>
        </div>
        <div>
          <p className="mb-2 px-3 text-xs font-semibold uppercase text-text-secondary">自动化</p>
          <div className="flex flex-col gap-1">
            <NavItem to="/console/plugins" icon={Workflow} label="规则" />
          </div>
        </div>
        <div>
          <p className="mb-2 px-3 text-xs font-semibold uppercase text-text-secondary">系统</p>
          <div className="flex flex-col gap-1">
            <NavItem to="/models" icon={Brain} label="模型服务" />
            <NavItem to="/console/security" icon={Shield} label="安全中心" tier="pro" />
            <NavItem to="/console/api-keys" icon={Settings} label="设置" />
            <NavItem to="/console/token-plan" icon={CreditCard} label="档位与用量" />
          </div>
        </div>
      </nav>
    </aside>
  );
}
