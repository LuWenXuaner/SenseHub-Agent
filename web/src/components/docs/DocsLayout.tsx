import { Link, NavLink } from "react-router-dom";
import { Code2, Coins, Grid3x3, HelpCircle, Tag, Zap } from "lucide-react";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { DocsNavLink } from "@/components/docs/DocsNavLink";
import { getDocsNav } from "@/lib/docsContent";
import { useLocale } from "@/context/LocaleContext";
import type { ReactNode } from "react";

const ICONS = {
  zap: Zap,
  grid: Grid3x3,
  coin: Coins,
  code: Code2,
  tag: Tag,
  help: HelpCircle,
} as const;

export function DocsQuickIcon({ name }: { name: keyof typeof ICONS }) {
  const Icon = ICONS[name] ?? Zap;
  return <Icon size={22} className="text-mimo-text" />;
}

export function DocsLayout({ children }: { children: ReactNode }) {
  const { t, locale } = useLocale();
  const d = t.docs;
  const nav = getDocsNav(t);

  return (
    <div className="mimo-docs-app flex min-h-screen flex-col bg-white">
      <header className="mimo-docs-header">
        <div className="mimo-container flex h-14 items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <Link to="/" className="mimo-docs-logo shrink-0">
              {locale === "zh" ? "灵枢" : "SenseHub"}{" "}
              <span className="font-normal opacity-70">{locale === "zh" ? "SenseHub" : ""}</span>
            </Link>
            <span className="mimo-console-divider" />
            <span className="text-sm font-medium">{d.brand}</span>
          </div>
          <nav className="hidden items-center gap-6 text-sm text-mimo-muted lg:flex">
            <Link to="/research" className="hover:text-mimo-text">
              {t.nav.research}
            </Link>
            <Link to="/models" className="hover:text-mimo-text">
              {t.nav.models}
            </Link>
            <Link to="/updates" className="hover:text-mimo-text">
              {t.nav.updates}
            </Link>
            <Link to="/contact" className="hover:text-mimo-text">
              {t.nav.contact}
            </Link>
            <LanguageSwitcher />
            <Link to="/console/account" className="mimo-btn-cta mimo-btn-sm">
              {t.menu.console}
            </Link>
          </nav>
        </div>
        <div className="mimo-docs-tabs border-t border-mimo-border">
          <div className="mimo-container flex flex-wrap items-center gap-6 py-2 text-sm">
            <NavLink
              to="/product/api"
              end
              className={({ isActive }) => `mimo-docs-tab ${isActive ? "active" : "text-mimo-muted"}`}
            >
              {d.quickStart}
            </NavLink>
            <NavLink to="/product/api#faq" className="mimo-docs-tab-link">
              {d.navFaq}
            </NavLink>
            <span className="mimo-docs-tab text-mimo-muted">{d.apiDoc}</span>
            <Link to="/models" className="mimo-docs-tab-link">
              {d.price}
            </Link>
            <Link to="/console/points" className="mimo-docs-tab-link">
              {t.console.tokenPlan}
            </Link>
            <Link to="/updates" className="mimo-docs-tab-link">
              {d.news}
            </Link>
            <Link to="/updates" className="mimo-docs-tab-link">
              {d.changelog}
            </Link>
            <span className="ml-auto hidden text-xs text-mimo-muted md:inline">
              {t.console.tokenPlan} · {t.claw.title} · {t.studio.chatWith}
            </span>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="mimo-docs-sidebar hidden w-[240px] shrink-0 border-r border-mimo-border lg:block">
          <div className="p-4">
            <div className="mimo-docs-search">
              <input type="search" placeholder={d.search} className="mimo-docs-search-input" />
              <kbd className="mimo-docs-kbd">Ctrl K</kbd>
            </div>
          </div>
          <nav className="space-y-4 overflow-y-auto px-3 pb-6">
            {nav.map((section) => (
              <div key={section.id}>
                <p className="mimo-docs-nav-heading">{section.label}</p>
                <ul className="mt-1 space-y-0.5">
                  {section.children?.map((item) => (
                    <li key={item.id}>
                      <DocsNavLink to={item.to ?? ""} label={item.label} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            <div>
              <p className="mimo-docs-nav-heading">{locale === "zh" ? "法律" : "Legal"}</p>
              <ul className="mt-1 space-y-0.5">
                <li>
                  <Link to="/legal/privacy" className="mimo-docs-nav-item">
                    {d.privacy}
                  </Link>
                </li>
                <li>
                  <Link to="/legal/terms" className="mimo-docs-nav-item">
                    {d.terms}
                  </Link>
                </li>
              </ul>
            </div>
          </nav>
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
