import { HeroNetworkVisual } from "./HeroNetworkVisual";
import { useLocale } from "@/context/LocaleContext";

export function MimoHero() {
  const { t, locale } = useLocale();

  return (
    <section className="mimo-hero-split">
      <div className="mimo-container grid min-h-[min(80vh,720px)] items-center gap-4 py-12 md:grid-cols-2 md:gap-8 md:py-16">
        <div className="mimo-hero-copy">
          <h1 className="mimo-hero-brand">{locale === "zh" ? "灵枢" : "SenseHub"}</h1>
          <p className="mimo-hero-tagline">{t.home.heroTagline}</p>
        </div>
        <div className="mimo-hero-visual-col">
          <HeroNetworkVisual />
        </div>
      </div>
    </section>
  );
}
