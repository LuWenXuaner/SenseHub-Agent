import { Link } from "react-router-dom";
import { useLocale } from "@/context/LocaleContext";
import { OfficialQrCode } from "@/components/marketing/OfficialQrCode";

export function ContactPage() {
  const { t } = useLocale();
  const c = t.contact;

  const channels = [
    { title: c.phone, desc: c.phoneDesc, value: c.phoneValue, href: `tel:${c.phoneValue}` },
    { title: c.email, desc: c.emailDesc, value: c.emailValue, href: `mailto:${c.emailValue}` },
  ];

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container">
          <p className="text-sm text-mimo-muted">{t.nav.contact}</p>
          <h1 className="mimo-page-title mt-2">{c.title}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-mimo-muted">{c.subtitle}</p>
        </div>
      </section>

      <section className="mimo-section pt-0">
        <div className="mimo-container grid gap-4 md:grid-cols-2">
          {channels.map((item) => (
            <article key={item.title} className="mimo-news-card mimo-card-static">
              <h2 className="text-lg font-semibold text-mimo-text">{item.title}</h2>
              <p className="mt-2 text-sm text-mimo-muted">{item.desc}</p>
              <a href={item.href} className="mt-4 inline-block text-sm font-medium text-mimo-text hover:underline">
                {item.value}
              </a>
            </article>
          ))}
        </div>
      </section>

      <section className="mimo-section border-t border-mimo-border">
        <div className="mimo-container flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl">
            <h2 className="mimo-section-title-left text-lg">{c.securityTitle}</h2>
            <p className="mt-3 text-sm leading-6 text-mimo-muted">{c.securityDesc}</p>
            <Link to="/console/security" className="mimo-btn-outline mimo-btn-sm mt-6 inline-flex">
              {c.securityCta}
            </Link>
          </div>
          <OfficialQrCode label={c.qrLabel} />
        </div>
      </section>
    </div>
  );
}
