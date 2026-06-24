import { Link } from "react-router-dom";
import { useLocale } from "@/context/LocaleContext";

export function ProductConsolePage() {
  const { t } = useLocale();
  const p = t.product;

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container">
          <p className="text-sm text-mimo-muted">{p.tag}</p>
          <h1 className="mimo-page-title mt-2">{p.consoleTitle}</h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-mimo-muted md:text-base">{p.consoleDesc}</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/claw" className="mimo-btn-primary">
              {p.consoleCta}
            </Link>
            <Link to="/research" className="mimo-btn-outline">
              {t.common.learnMore}
            </Link>
          </div>
        </div>
      </section>

      <section className="mimo-section">
        <div className="mimo-container grid gap-6 md:grid-cols-3">
          {[
            { title: p.featPlan, desc: p.featPlanDesc },
            { title: p.featSecurity, desc: p.featSecurityDesc },
            { title: p.featDesktop, desc: p.featDesktopDesc },
          ].map((item) => (
            <article key={item.title} className="mimo-model-card">
              <h2 className="text-lg font-semibold text-mimo-text">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-mimo-muted">{item.desc}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
