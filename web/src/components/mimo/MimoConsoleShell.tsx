import { Link, NavLink, Outlet } from "react-router-dom";
import {
  BarChart3,
  ChevronDown,
  CreditCard,
  ExternalLink,
  FileText,
  Gift,
  Key,
  Puzzle,
  Receipt,
  Shield,
  ShieldCheck,
  User,
  Users,
  Wallet,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { InviteFriendsModal } from "@/components/mimo/InviteFriendsModal";

type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  external?: boolean;
};

function ConsoleTopBar() {
  const { t } = useLocale();

  return (
    <header className="mimo-console-header">
      <div className="flex min-w-0 items-center gap-3">
        <Link to="/" className="mimo-console-logo shrink-0">
          灵枢 <span className="font-normal opacity-70">SenseHub</span>
        </Link>
        <span className="mimo-console-divider" aria-hidden />
        <span className="text-sm font-medium">{t.console.title}</span>
      </div>
      <nav className="hidden items-center gap-6 text-sm text-mimo-muted lg:flex">
        <Link to="/research" className="hover:text-mimo-text">{t.nav.research}</Link>
        <Link to="/models" className="hover:text-mimo-text">{t.nav.models}</Link>
        <Link to="/updates" className="hover:text-mimo-text">{t.nav.updates}</Link>
        <Link to="/contact" className="hover:text-mimo-text">{t.nav.contact}</Link>
        <Link to="/product/api" className="hover:text-mimo-text">{t.nav.docs}</Link>
        <Link to="/console/points" className="hover:text-mimo-text">{t.nav.pricing}</Link>
        <LanguageSwitcher />
        <Link
          to="/console/account"
          className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-mimo-warm"
        >
          <User size={16} />
        </Link>
      </nav>
    </header>
  );
}

function ConsoleSidebar({ onInvite }: { onInvite: () => void }) {
  const { user } = useAuth();
  const { t } = useLocale();

  const sections: { title: string; items: NavItem[] }[] = [
    {
      title: t.console.account,
      items: [
        { to: "/console/account", label: t.console.personalCenter, icon: User, end: true },
        { to: "/console/api-keys", label: t.console.apiKeys, icon: Key },
        { to: "/console/security", label: t.console.security, icon: Shield },
      ],
    },
    {
      title: t.console.finance,
      items: [
        { to: "/console/points", label: t.console.pointsCenter, icon: Wallet },
        { to: "/console/token-plan", label: t.console.tokenPlan, icon: CreditCard },
        { to: "/console/bills", label: t.console.bills, icon: BarChart3 },
        { to: "/console/points-history", label: t.console.pointsHistory, icon: Receipt },
        { to: "/console/exchange", label: t.console.exchange, icon: FileText },
      ],
    },
    {
      title: t.console.referral,
      items: [{ to: "/console/invite", label: t.console.inviteMgmt, icon: Users }],
    },
    {
      title: t.console.plugins,
      items: [{ to: "/console/plugins", label: t.console.pluginMgmt, icon: Puzzle }],
    },
    ...(user?.username === "admin"
      ? [
          {
            title: t.adminPage.section,
            items: [{ to: "/console/admin/users", label: t.adminPage.title, icon: ShieldCheck }],
          },
        ]
      : []),
    {
      title: t.console.learnMore,
      items: [
        { to: "/claw", label: t.console.claw, icon: ExternalLink, external: true },
        { to: "/studio", label: t.console.chatWith, icon: ExternalLink, external: true },
        { to: "/code", label: t.menu.code, icon: ExternalLink, external: true },
      ],
    },
  ];

  return (
    <aside className="mimo-console-sidebar">
      <nav className="flex-1 space-y-5 overflow-y-auto p-3">
        {sections.map((section) => (
          <div key={section.title}>
            <p className="mimo-console-nav-heading">{section.title}</p>
            <ul className="mt-1 space-y-0.5">
              {section.items.map((item) => (
                <li key={`${section.title}-${item.label}`}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `mimo-console-nav-item ${isActive ? "mimo-console-nav-item-active" : ""}`
                    }
                  >
                    <item.icon size={15} className="shrink-0 opacity-55" />
                    <span>{item.label}</span>
                    {item.external && <ExternalLink size={12} className="ml-auto opacity-40" />}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="shrink-0 space-y-2 border-t border-mimo-border p-3">
        <button
          type="button"
          className="mimo-console-promo flex w-full flex-col items-center justify-center py-4"
          onClick={onInvite}
          aria-label={t.console.invite}
        >
          <Gift size={44} strokeWidth={1.25} className="text-mimo-accent" />
        </button>
        <button type="button" className="mimo-console-invite-btn mimo-btn-sm" onClick={onInvite}>
          {t.console.invite}
        </button>
        {user?.display_name || user?.username ? (
          <p className="truncate text-center text-xs text-mimo-muted">
            {user.display_name || user.username}
          </p>
        ) : null}
      </div>
    </aside>
  );
}

export function MimoConsoleShell() {
  const { t } = useLocale();
  const [inviteOpen, setInviteOpen] = useState(false);

  return (
    <div className="mimo-product-app flex h-screen flex-col bg-[#f7f7f7]">
      <div className="mimo-console-announce">{t.console.announce}</div>
      <ConsoleTopBar />
      <div className="flex min-h-0 flex-1">
        <ConsoleSidebar onInvite={() => setInviteOpen(true)} />
        <main className="mimo-console-main min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
      <InviteFriendsModal open={inviteOpen} onClose={() => setInviteOpen(false)} />
    </div>
  );
}
