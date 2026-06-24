import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { DocsLayout, DocsQuickIcon } from "@/components/docs/DocsLayout";
import { DocContentSection } from "@/components/docs/DocContentSection";
import { getDocsHeroSlides, getDocsQuickStart } from "@/lib/docsContent";
import { useLocale } from "@/context/LocaleContext";

const SECTION_META = [
  "start",
  "text",
  "tools",
  "vision",
  "image",
  "audio",
  "voice",
  "asr",
  "tts",
  "faq",
] as const;

function sectionTitle(d: (typeof import("@/lib/i18n/zh").zh.docsPage), id: (typeof SECTION_META)[number]) {
  const map: Record<(typeof SECTION_META)[number], string> = {
    start: d.sectionStartTitle,
    text: d.sectionTextTitle,
    tools: d.sectionToolsTitle,
    vision: d.sectionVisionTitle,
    image: d.navImage,
    audio: d.navAudio,
    voice: d.sectionVoiceTitle,
    asr: d.navAsr,
    tts: d.sectionTtsTitle,
    faq: d.sectionFaqTitle,
  };
  return map[id];
}

export function ProductApiPage() {
  const { t, locale } = useLocale();
  const d = t.docsPage;
  const location = useLocation();
  const heroSlides = getDocsHeroSlides(t);
  const quickStart = getDocsQuickStart(t);
  const [slide, setSlide] = useState(0);
  const hero = heroSlides[slide] ?? heroSlides[0];

  useEffect(() => {
    const hash = location.hash.replace("#", "");
    if (!hash) return;
    const tmr = window.setTimeout(() => {
      document.getElementById(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
    return () => window.clearTimeout(tmr);
  }, [location.hash, location.pathname]);

  return (
    <DocsLayout>
      <div className="mimo-docs-main">
        <p className="text-sm font-medium text-mimo-text">{hero.title}</p>

        <div className="mimo-docs-hero mt-4">
          <div className="mimo-docs-hero-copy">
            <h1 className="text-2xl font-semibold md:text-3xl">{hero.title}</h1>
            <p className="mt-3 max-w-xl text-sm leading-7 text-mimo-muted">{hero.desc}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to={hero.primary.to} className="mimo-btn-cta mimo-btn-sm">
                {hero.primary.label}
              </Link>
              <Link to={hero.secondary.to} className="mimo-btn-outline mimo-btn-sm">
                {hero.secondary.label}
              </Link>
            </div>
          </div>
          <div className="mimo-docs-hero-art" aria-hidden />
          <div className="mimo-docs-hero-dots">
            {heroSlides.map((_, i) => (
              <button
                key={i}
                type="button"
                className={`mimo-docs-dot ${i === slide ? "mimo-docs-dot-active" : ""}`}
                onClick={() => setSlide(i)}
                aria-label={`${d.slideLabel} ${i + 1}`}
              />
            ))}
          </div>
        </div>

        <h2 className="mimo-docs-section-title mt-12">{d.sectionQuickStart}</h2>
        <div className="mimo-docs-quick-grid">
          {quickStart.map((card) => (
            <Link key={card.id} to={card.to} className="mimo-docs-quick-card">
              <DocsQuickIcon name={card.icon} />
              <h3 className="mt-4 font-semibold">{card.title}</h3>
              <p className="mt-2 text-sm leading-6 text-mimo-muted">{card.desc}</p>
            </Link>
          ))}
        </div>

        <div className="mt-12 space-y-0 border-t border-mimo-border pt-10">
          {SECTION_META.map((id) => (
            <DocContentSection key={id} id={id} title={sectionTitle(d, id)} locale={locale} />
          ))}
        </div>

        <div className="mt-10 text-right">
          <a href="#start" className="text-sm text-mimo-muted hover:text-mimo-text">
            {d.sectionFooterLink}
          </a>
        </div>
      </div>
    </DocsLayout>
  );
}
