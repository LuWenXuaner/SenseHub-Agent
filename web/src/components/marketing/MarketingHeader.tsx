import { Link, NavLink } from "react-router-dom";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { UseLingshuDropdown } from "./UseLingshuDropdown";
import { MarketingNavDropdown } from "./MarketingNavDropdown";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { useLocale } from "@/context/LocaleContext";

export function MarketingHeader() {
  const { toggle, mode } = useTheme();
  const { t, locale } = useLocale();

  const modelsMenu = [
    {
      label: locale === "zh" ? "模型广场" : "Model gallery",
      to: "/models",
      description: locale === "zh" ? "浏览全部代采模型与定价" : "Browse models and pricing",
    },
    {
      label: t.menu.tokenPlan,
      to: "/token-plan",
      description: locale === "zh" ? "档位方案与积分兑换" : "Tiers and point redemption",
    },
    {
      label: locale === "zh" ? "API 文档" : "API docs",
      to: "/product/api",
      description: locale === "zh" ? "接入说明与示例" : "Integration guide",
    },
  ];

  const updatesMenu = [
    {
      label: locale === "zh" ? "全部动态" : "All updates",
      to: "/updates",
      description: locale === "zh" ? "产品更新与能力迭代" : "Product changelog",
    },
    ...t.news.slice(0, 3).map((item) => ({
      label: item.title,
      to: `/updates/${item.slug}`,
      description: item.summary.length > 42 ? `${item.summary.slice(0, 42)}…` : item.summary,
    })),
  ];

  const NAV = [
    { to: "/research", label: t.nav.research },
    { to: "/models", label: t.nav.models, dropdown: true as const, menu: modelsMenu },
    { to: "/updates", label: t.nav.updates, dropdown: true as const, menu: updatesMenu },
    { to: "/token-plan", label: t.menu.tokenPlan },
    { to: "/contact", label: t.nav.contact },
  ];

  return (
    <header className="mimo-header sticky top-0 z-50 bg-white">
      <div className="mimo-container flex h-16 items-center justify-between gap-6">
        <Link to="/" className="mimo-logo shrink-0">
          {locale === "zh" ? "灵枢" : "SenseHub"}{" "}
          <span className="font-normal text-mimo-muted">{locale === "zh" ? "SenseHub" : "Agent"}</span>
        </Link>

        <nav className="hidden items-center gap-7 lg:flex">
          {NAV.map((item) =>
            "dropdown" in item && item.dropdown ? (
              <MarketingNavDropdown key={item.to} label={item.label} to={item.to} items={item.menu} />
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `mimo-nav-link inline-flex items-center gap-0.5 ${isActive ? "mimo-nav-link-active" : ""}`
                }
              >
                {item.label}
              </NavLink>
            )
          )}
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
