import { Link } from "react-router-dom";
import { useLocale } from "@/context/LocaleContext";

export function UpdatesPage() {
  const { t } = useLocale();

  const newsCtaTo: Record<string, string> = {
    "api-key-reseller": "/models",
    "console-launch": "/claw",
    "studio-multimodal": "/studio",
    "token-plan": "/token-plan",
  };

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container">
          <p className="text-sm text-mimo-muted">{t.updates.tag}</p>
          <h1 className="mimo-page-title mt-2">{t.updates.title}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-mimo-muted">{t.updates.subtitle}</p>
        </div>
      </section>

      <section className="mimo-section pt-0">
        <div className="mimo-container">
          <div className="mimo-news-grid">
            {t.news.map((item) => (
              <article key={item.slug} className="mimo-news-card mimo-card-static">
                <h2 className="text-base font-semibold leading-snug">{item.title}</h2>
                <p className="mt-3 flex-1 text-sm leading-7 text-mimo-muted">{item.summary}</p>
                <Link
                  to={newsCtaTo[item.slug] ?? `/updates/${item.slug}`}
                  className="mimo-btn-text mt-auto inline-flex text-sm"
                >
                  {t.updates.viewDetail} →
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mimo-section border-t border-mimo-border">
        <div className="mimo-container">
          <h2 className="mimo-section-title-left text-lg">{t.updates.tryLatest}</h2>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link to="/claw" className="mimo-btn-primary mimo-btn-sm">
              {t.home.goConsole}
            </Link>
            <Link to="/studio" className="mimo-btn-outline mimo-btn-sm">
              {t.home.goStudio}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
