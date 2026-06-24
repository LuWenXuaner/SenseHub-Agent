import { useState } from "react";
import type { FlagshipApiModel } from "@/lib/siteContent";
import { useLocale } from "@/context/LocaleContext";

function mapPricingLabel(label: string, locale: "zh" | "en", fp: { input: string; output: string; billing: string }) {
  if (locale === "zh") return label;
  if (label.includes("输入")) return fp.input;
  if (label.includes("输出")) return fp.output;
  if (label.includes("计费")) return fp.billing;
  return label;
}

export function FlagshipModelCard({ model }: { model: FlagshipApiModel }) {
  const { locale, t } = useLocale();
  const [imgFailed, setImgFailed] = useState(false);

  return (
    <article className="mimo-flagship-card mimo-card-static">
      <div className="mimo-flagship-art">
        {imgFailed ? (
          <div className="flex h-full items-center justify-center text-2xl font-semibold text-mimo-muted">
            {model.name.slice(0, 2)}
          </div>
        ) : (
          <img
            src={model.imageUrl}
            alt=""
            className="h-full w-full object-contain p-6"
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        )}
      </div>
      <div className="mimo-flagship-body">
        <div className="flex items-center gap-2">
          <h3 className="mimo-flagship-name">{model.name}</h3>
          {model.badge && <span className="mimo-api-badge">{model.badge}</span>}
        </div>
        <p className="mimo-flagship-desc">{model.description}</p>
      </div>
      <dl className="mimo-flagship-pricing">
        {model.pricing.map((row, i) => (
          <div key={row.label} className="mimo-price-row">
            <dt>{mapPricingLabel(row.label, locale, t.flagshipPricing)}</dt>
            <dd className={i < 2 ? "mimo-price-accent" : ""}>{row.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
