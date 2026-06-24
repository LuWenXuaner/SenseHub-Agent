import { Link, NavLink } from "react-router-dom";
import { ChevronDown, Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { UseLingshuDropdown } from "./UseLingshuDropdown";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { useLocale } from "@/context/LocaleContext";

export function MarketingHeader() {
  const { toggle, mode } = useTheme();
  const { t, locale } = useLocale();

  const NAV = [
    { to: "/research", label: t.nav.research },
    { to: "/models", label: t.nav.models, dropdown: true },
    { to: "/updates", label: t.nav.updates, dropdown: true },
    { to: "/token-plan", label: t.menu.tokenPlan },
    { to: "/contact", label: t.nav.contact },
  ] as const;

  return (
    <header className="mimo-header sticky top-0 z-50 bg-white">
      <div className="mimo-container flex h-16 items-center justify-between gap-6">
        <Link to="/" className="mimo-logo shrink-0">
          {locale === "zh" ? "灵枢" : "SenseHub"}{" "}
          <span className="font-normal text-mimo-muted">{locale === "zh" ? "SenseHub" : "Agent"}</span>
        </Link>

        <nav className="hidden items-center gap-7 lg:flex">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `mimo-nav-link inline-flex items-center gap-0.5 ${isActive ? "mimo-nav-link-active" : ""}`
              }
            >
              {item.label}
              {"dropdown" in item && item.dropdown && (
                <ChevronDown size={14} className="opacity-50" aria-hidden />
              )}
            </NavLink>
          ))}
          <LanguageSwitcher />
        </nav>

        <div className="flex items-center gap-2">
          <button type="button" className="mimo-icon-btn" onClick={toggle} aria-label="切换主题">
            {mode === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <UseLingshuDropdown />
        </div>
      </div>
    </header>
  );
}
