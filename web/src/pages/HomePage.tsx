import { Link } from "react-router-dom";
import {
  ECOSYSTEM_PARTNERS,
  FLAGSHIP_API_MODELS,
  PRODUCT_MATRIX,
} from "@/lib/siteContent";
import { MimoHero } from "@/components/marketing/MimoHero";
import { ScrollCarousel } from "@/components/marketing/ScrollCarousel";
import { FlagshipModelCard } from "@/components/marketing/FlagshipModelCard";
import { ProductMatrixRow } from "@/components/marketing/ProductMatrixRow";
import { EcosystemGrid } from "@/components/marketing/EcosystemGrid";
import { DeveloperVoiceGraph } from "@/components/marketing/DeveloperVoiceGraph";
import { AboutSection } from "@/components/marketing/AboutSection";
import { NEWS_HOME_LIMIT, NewsPager } from "@/components/marketing/NewsPager";
import { useInView } from "@/hooks/useInView";
import { useLocale } from "@/context/LocaleContext";

export function HomePage() {
  const newsView = useInView();
  const modelsView = useInView();
  const productsView = useInView();
  const ecoView = useInView();
  const { t } = useLocale();

  const newsCtaTo: Record<string, string> = {
    "api-key-reseller": "/models",
    "console-launch": "/claw",
    "studio-multimodal": "/studio",
    "token-plan": "/token-plan",
    "model-lineup-2026": "/models",
    "chat-ui-upgrade": "/studio",
    "points-invite": "/console/points",
    "code-agent-beta": "/code",
    "session-privacy": "/product/api",
  };

  return (
    <>
      <MimoHero />

      <section
        ref={newsView.ref}
        className={`mimo-section border-b ${newsView.visible ? "mimo-in-view" : ""}`}
        style={{ borderColor: "var(--mimo-border)" }}
      >
        <div className="mimo-container">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <h2 className="mimo-section-title-left">{t.home.news}</h2>
            <Link to="/updates" className="mimo-link-more text-sm">
              {t.home.viewUpdates}
            </Link>
          </div>
          <div className="mimo-news-grid mimo-reveal-stagger mt-8">
            {t.news.slice(0, NEWS_HOME_LIMIT).map((item) => (
              <article key={item.slug} className="mimo-news-card mimo-card-static mimo-reveal-item">
                <h3 className="text-base font-semibold leading-snug">{item.title}</h3>
                <p className="mt-3 flex-1 text-sm leading-7 text-mimo-muted">{item.summary}</p>
                <Link
                  to={newsCtaTo[item.slug] ?? `/updates/${item.slug}`}
                  className="mimo-btn-text mt-auto inline-flex text-sm"
                >
                  {item.cta} →
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section
        ref={modelsView.ref}
        className={`mimo-section border-b bg-mimo-warm ${modelsView.visible ? "mimo-in-view" : ""}`}
        style={{ borderColor: "var(--mimo-border)" }}
      >
        <div className="mimo-container">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <h2 className="mimo-section-title-left">{t.home.flagship}</h2>
            <Link to="/models" className="mimo-link-more shrink-0">
              {t.home.viewAllModels}
            </Link>
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-mimo-muted">{t.home.flagshipDesc}</p>
          <ScrollCarousel className="mt-10" controlsBottom>
            {FLAGSHIP_API_MODELS.map((model) => (
              <FlagshipModelCard key={model.id} model={model} />
            ))}
          </ScrollCarousel>
        </div>
      </section>

      <section
        ref={productsView.ref}
        className={`mimo-section border-b bg-mimo-warm ${productsView.visible ? "mimo-in-view" : ""}`}
        style={{ borderColor: "var(--mimo-border)" }}
      >
        <div className="mimo-container">
          <h2 className="mimo-section-title-left">{t.home.products}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-mimo-muted">{t.home.productsDesc}</p>
          <ProductMatrixRow items={PRODUCT_MATRIX} />
        </div>
      </section>

      <section
        ref={ecoView.ref}
        className={`mimo-section border-b mimo-reveal-stagger ${ecoView.visible ? "mimo-in-view" : ""}`}
        style={{ borderColor: "var(--mimo-border)" }}
      >
        <div className="mimo-container">
          <h2 className="mimo-section-title-left">{t.home.ecosystem}</h2>
          <EcosystemGrid partners={ECOSYSTEM_PARTNERS} />
        </div>
      </section>

      <DeveloperVoiceGraph />
      <AboutSection />
    </>
  );
}
