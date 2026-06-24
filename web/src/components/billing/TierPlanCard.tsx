import { Check } from "lucide-react";
import type { TierPlan } from "@/lib/tierCatalog";
import { CAPABILITY_MATRIX } from "@/lib/tierCatalog";

export function TierPlanCard({
  plan,
  active,
  onSelect,
  mimoStyle,
}: {
  plan: TierPlan;
  active: boolean;
  onSelect?: () => void;
  mimoStyle?: boolean;
}) {
  if (mimoStyle) {
    return (
      <article
        className={`relative flex flex-col rounded-2xl border p-6 transition ${
          active
            ? "border-mimo-text bg-mimo-surface ring-1 ring-mimo-border"
            : "border-mimo-border bg-mimo-bg hover:border-mimo-text"
        }`}
      >
        {active && (
          <span className="absolute right-4 top-4 rounded-full bg-mimo-cta px-2.5 py-0.5 text-[10px] font-medium text-white dark:text-[#1d1d1f]">
            当前
          </span>
        )}
        <p className="text-xs font-medium uppercase tracking-wider text-mimo-muted">{plan.name}</p>
        <h3 className="mt-1 text-sm font-semibold text-mimo-text">{plan.tagline}</h3>
        <div className="mt-4 flex items-baseline gap-2">
          <span className="text-3xl font-semibold text-mimo-text">{plan.price}</span>
          <span className="text-xs text-mimo-muted">{plan.priceNote}</span>
        </div>
        <ul className="mt-4 flex-1 space-y-2 text-sm text-mimo-muted">
          {plan.highlights.map((h) => (
            <li key={h} className="flex items-start gap-2">
              <Check size={14} className="mt-0.5 shrink-0 text-mimo-accent" aria-hidden />
              <span>{h}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 border-t border-mimo-border pt-3 text-xs leading-snug text-mimo-muted">
          {plan.limits}
        </p>
        {!active && onSelect && (
          <button type="button" className="mimo-btn-outline mt-4 w-full text-xs" onClick={onSelect}>
            了解 {plan.name}
          </button>
        )}
      </article>
    );
  }

  return (
    <article
      className={`relative flex flex-col rounded-2xl border p-4 transition ${
        active
          ? "border-primary/50 bg-gradient-to-b from-primary/10 to-surface shadow-md ring-1 ring-primary/30"
          : "border-border bg-surface hover:border-primary/25"
      }`}
    >
      {active && (
        <span className="absolute right-3 top-3 rounded-full bg-primary px-2 py-0.5 text-[10px] font-medium text-white">
          当前
        </span>
      )}
      <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">{plan.name}</p>
      <h3 className="mt-1 text-sm font-semibold text-text-primary">{plan.tagline}</h3>
      <div className="mt-3 flex items-baseline gap-1">
        <span className="text-2xl font-bold text-primary">{plan.price}</span>
        <span className="text-xs text-text-secondary">{plan.priceNote}</span>
      </div>
      <ul className="mt-3 flex-1 space-y-1.5 text-xs text-text-secondary">
        {plan.highlights.map((h) => (
          <li key={h} className="flex items-start gap-1.5">
            <Check size={12} className="mt-0.5 shrink-0 text-primary" aria-hidden />
            <span>{h}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 border-t border-border/60 pt-2 text-[11px] leading-snug text-text-secondary">
        {plan.limits}
      </p>
      {!active && onSelect && (
        <button type="button" className="btn-secondary mt-3 w-full text-xs" onClick={onSelect}>
          了解 {plan.name}
        </button>
      )}
    </article>
  );
}

export function CapabilityMatrixTable({ mimoStyle }: { mimoStyle?: boolean }) {
  const head = mimoStyle ? "bg-mimo-surface text-mimo-muted" : "bg-surface-elevated/80 text-text-secondary";
  const border = mimoStyle ? "border-mimo-border" : "border-border/50";
  const cellPrimary = mimoStyle ? "text-mimo-text" : "text-text-primary";
  const cellSecondary = mimoStyle ? "text-mimo-muted" : "text-text-secondary";

  return (
    <table className="w-full text-sm">
      <thead className={head}>
        <tr>
          <th className="px-4 py-3 text-left font-medium">能力</th>
          <th className="px-3 py-3 text-center">Lite</th>
          <th className="px-3 py-3 text-center">Pro</th>
          <th className="px-3 py-3 text-center">Max</th>
        </tr>
      </thead>
      <tbody>
        {CAPABILITY_MATRIX.map((row) => (
          <tr key={row.name} className={`border-t ${border}`}>
            <td className={`px-4 py-2.5 ${cellPrimary}`}>{row.name}</td>
            <td className={`px-3 py-2.5 text-center ${cellSecondary}`}>{row.lite}</td>
            <td className={`px-3 py-2.5 text-center ${cellSecondary}`}>{row.pro}</td>
            <td className={`px-3 py-2.5 text-center ${cellSecondary}`}>{row.max}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
