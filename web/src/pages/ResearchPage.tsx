import { CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useLocale } from "@/context/LocaleContext";

export function ResearchPage() {
  const { t } = useLocale();
  const r = t.research;
  const pillars = r.pillars as { title: string; desc: string }[];
  const deliverables = r.deliverables as string[];

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container">
          <p className="text-sm text-mimo-muted">{r.tag as string}</p>
          <h1 className="mimo-page-title mt-2">{r.title as string}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-mimo-muted md:text-base">
            {r.intro as string}
          </p>
        </div>
      </section>

      <section className="mimo-section pt-0">
        <div className="mimo-container grid gap-4 md:grid-cols-2">
          {pillars.map((item) => (
            <article key={item.title} className="mimo-model-card">
              <h2 className="text-lg font-semibold text-mimo-text">{item.title}</h2>
              <p className="mt-2 text-sm leading-6 text-mimo-muted">{item.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mimo-section border-t border-mimo-border bg-mimo-surface">
        <div className="mimo-container max-w-3xl">
          <h2 className="text-center text-xl font-semibold text-mimo-text">{r.capabilities as string}</h2>
          <ul className="mt-6 grid gap-3 md:grid-cols-2">
            {deliverables.map((row) => (
              <li key={row} className="flex items-start gap-2 text-sm text-mimo-muted">
                <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-mimo-accent" />
                {row}
              </li>
            ))}
          </ul>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/claw" className="mimo-btn-primary">
              {r.tryNow as string}
            </Link>
            <Link to="/models" className="mimo-btn-outline">
              {r.viewModels as string}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
