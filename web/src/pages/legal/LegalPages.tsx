import { Link } from "react-router-dom";
import { useLocale } from "@/context/LocaleContext";

function LegalPage({ kind }: { kind: "privacy" | "terms" | "cookie" }) {
  const { t } = useLocale();
  const title =
    kind === "privacy" ? t.legal.privacyTitle : kind === "terms" ? t.legal.termsTitle : t.legal.cookieTitle;

  const paragraphs =
    kind === "privacy"
      ? [t.legal.privacyIntro, t.legal.privacyData, t.legal.privacyStorage, t.legal.privacyRights]
      : kind === "terms"
        ? [t.legal.termsIntro, t.legal.termsService, t.legal.termsAccount, t.legal.termsPoints]
        : [t.legal.cookieIntro];

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container max-w-3xl">
          <p className="text-sm text-mimo-muted">{t.legal.lastUpdated}</p>
          <h1 className="mimo-page-title mt-2">{title}</h1>
        </div>
      </section>
      <section className="mimo-section pt-0">
        <div className="mimo-container max-w-3xl space-y-6">
          {paragraphs.map((p, i) => (
            <p key={i} className="text-sm leading-8 text-mimo-muted">
              {p}
            </p>
          ))}
          <div className="flex flex-wrap gap-4 border-t border-mimo-border pt-8 text-sm">
            <Link to="/legal/privacy" className="text-[#1677ff] hover:underline">
              {t.legal.privacyTitle}
            </Link>
            <Link to="/legal/terms" className="text-[#1677ff] hover:underline">
              {t.legal.termsTitle}
            </Link>
            <Link to="/legal/cookies" className="text-[#1677ff] hover:underline">
              {t.legal.cookieTitle}
            </Link>
            <Link to="/contact" className="text-[#1677ff] hover:underline">
              {t.nav.contact}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

export function PrivacyPolicyPage() {
  return <LegalPage kind="privacy" />;
}

export function TermsPage() {
  return <LegalPage kind="terms" />;
}

export function CookiePolicyPage() {
  return <LegalPage kind="cookie" />;
}
