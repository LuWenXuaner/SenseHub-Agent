import { Link } from "react-router-dom";
import { OfficialQrCode } from "./OfficialQrCode";
import { useLocale } from "@/context/LocaleContext";

export function MarketingFooter() {
  const { t, locale } = useLocale();
  const f = t.footer;

  const FOOTER_LINKS = {
    product: [
      { label: f.consoleProduct, to: "/product/console" },
      { label: f.studioProduct, to: "/product/studio" },
      { label: f.apiProduct, to: "/product/api" },
      { label: t.console.tokenPlan, to: "/console/points" },
    ],
    platform: [
      { label: f.apiKeys, to: "/console/api-keys" },
      { label: f.models, to: "/models" },
      { label: f.docs, to: "/product/api" },
      { label: f.security, to: "/console/security" },
    ],
    about: [
      { label: f.research, to: "/research" },
      { label: f.updates, to: "/updates" },
      { label: f.contact, to: "/contact" },
      { label: f.aboutUs, to: "/#about" },
    ],
    legal: [
      { label: f.privacy, to: "/legal/privacy" },
      { label: f.terms, to: "/legal/terms" },
      { label: f.cookies, to: "/legal/cookies" },
    ],
  } as const;

  return (
    <footer className="mimo-footer-dark">
      <div className="mimo-container py-14">
        <div className="grid gap-10 lg:grid-cols-[1fr_auto]">
          <div className="grid gap-10 sm:grid-cols-2 md:grid-cols-4">
            <div>
              <p className="mimo-footer-dark-title">{f.product}</p>
              <ul className="mimo-footer-dark-links">
                {FOOTER_LINKS.product.map((item) => (
                  <li key={item.to}>
                    <Link to={item.to}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mimo-footer-dark-title">{f.platform}</p>
              <ul className="mimo-footer-dark-links">
                {FOOTER_LINKS.platform.map((item) => (
                  <li key={item.to}>
                    <Link to={item.to}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mimo-footer-dark-title">{f.about}</p>
              <ul className="mimo-footer-dark-links">
                {FOOTER_LINKS.about.map((item) => (
                  <li key={item.label}>
                    <Link to={item.to}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="mimo-footer-dark-title">{f.legal}</p>
              <ul className="mimo-footer-dark-links">
                {FOOTER_LINKS.legal.map((item) => (
                  <li key={item.label}>
                    <Link to={item.to}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <OfficialQrCode label={f.qrLabel} />
        </div>

        <div className="mimo-footer-dark-brand mt-12">
          <p className="text-lg font-semibold">{locale === "zh" ? "灵枢 SenseHub" : "SenseHub"}</p>
          <p className="mt-2 max-w-xl text-sm leading-6 opacity-70">{f.brandTagline}</p>
        </div>
      </div>

      <div className="mimo-footer-dark-bar">
        <div className="mimo-container flex flex-col items-center justify-between gap-2 py-5 text-xs opacity-60 sm:flex-row">
          <span>{f.copyright}</span>
          <span>{f.icp}</span>
        </div>
      </div>
    </footer>
  );
}
