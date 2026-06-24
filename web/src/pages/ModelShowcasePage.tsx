import { Link } from "react-router-dom";
import { FLAGSHIP_API_MODELS } from "@/lib/siteContent";
import { ScrollCarousel } from "@/components/marketing/ScrollCarousel";
import { FlagshipModelCard } from "@/components/marketing/FlagshipModelCard";
import { useLocale } from "@/context/LocaleContext";

export function ModelShowcasePage() {
  const { t } = useLocale();
  const m = t.modelsPage;

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container">
          <p className="text-sm text-mimo-muted">{m.tag}</p>
          <h1 className="mimo-page-title mt-2">{m.title}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-mimo-muted md:text-base">{m.desc}</p>
        </div>
      </section>

      <section className="mimo-section pt-0">
        <div className="mimo-container">
          <ScrollCarousel controlsBottom>
            {FLAGSHIP_API_MODELS.map((model) => (
              <FlagshipModelCard key={model.id} model={model} />
            ))}
          </ScrollCarousel>
        </div>
      </section>

      <section className="mimo-section border-t" style={{ borderColor: "var(--mimo-border)" }}>
        <div className="mimo-container flex flex-col items-center gap-4 text-center">
          <h2 className="text-lg font-semibold">{m.bottomTitle}</h2>
          <p className="max-w-xl text-sm text-mimo-muted">{m.bottomDesc}</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/token-plan" className="mimo-btn-primary mimo-btn-sm">
              {m.ctaPlans}
            </Link>
            <Link to="/console/api-keys" className="mimo-btn-outline mimo-btn-sm">
              {m.ctaKeys}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
