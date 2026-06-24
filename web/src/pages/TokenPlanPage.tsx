import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, ChevronDown } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { useWallet } from "@/hooks/useWallet";
import { api } from "@/lib/api";
import { formatPoints } from "@/lib/pointsCatalog";
import {
  PLAN_FEATURE_KEYS,
  TOKEN_PLAN_SPECS,
  planSubscribeKey,
  resolveSubscribeState,
  type BillingCycle,
  type TokenPlanSpec,
  type TokenPlanTier,
} from "@/lib/tokenPlanCatalog";
import { TOKEN_PLAN_CODING_TOOLS } from "@/lib/siteContent";
import { PartnerIcon } from "@/components/marketing/PartnerIcon";
import "@/styles/token-plan-page.css";

const FAQ_KEYS = ["faq1", "faq2", "faq3", "faq4", "faq5"] as const;

export function TokenPlanPage() {
  const { t, locale, fmt } = useLocale();
  const tp = t.tokenPlanPage;
  const { token, refreshLicense } = useAuth();
  const { balance, summary, subscribe, refresh: refreshWallet } = useWallet();
  const navigate = useNavigate();
  const [billing, setBilling] = useState<BillingCycle>("yearly");
  const [plans, setPlans] = useState<TokenPlanSpec[]>(TOKEN_PLAN_SPECS);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const userTierRank = summary?.tier_rank ?? 0;
  const subscriptionActive = summary?.subscription_active ?? false;

  useEffect(() => {
    api
      .walletPlans()
      .then((r) => {
        if (!r.items?.length) return;
        setPlans(
          r.items.map((row) => ({
            id: row.id as TokenPlanTier,
            effectiveTier: row.effective_tier as TokenPlanSpec["effectiveTier"],
            tierRank: row.tier_rank,
            monthlyCost: row.monthly_cost,
            yearlyCost: row.yearly_cost,
            yearlySave: row.yearly_save,
            monthlyItemId: row.monthly_item_id,
            yearlyItemId: row.yearly_item_id,
            creditsLabelKey:
              row.id === "lite"
                ? "creditsLite"
                : row.id === "standard"
                  ? "creditsStandard"
                  : row.id === "pro"
                    ? "creditsPro"
                    : "creditsMax",
            multiplierKey:
              row.id === "standard"
                ? "multStandard"
                : row.id === "pro"
                  ? "multPro"
                  : row.id === "max"
                    ? "multMax"
                    : undefined,
            featured: row.id === "max",
          })),
        );
      })
      .catch(() => {});
  }, []);

  const planTags = useMemo(
    () =>
      ({
        lite: tp.planTagLite,
        standard: tp.planTagStandard,
        pro: tp.planTagPro,
        max: tp.planTagMax,
      }) as Record<TokenPlanTier, string>,
    [tp],
  );

  const creditsLabel = (key: string) => (tp as Record<string, string>)[key] ?? key;
  const featureLabel = (key: string) => (tp as Record<string, string>)[key] ?? key;

  const btnLabel = (state: ReturnType<typeof resolveSubscribeState>) => {
    if (state === "login") return tp.loginToSubscribe;
    if (state === "renew") return tp.btnRenew;
    if (state === "upgrade") return tp.btnUpgrade;
    if (state === "blocked") return tp.btnBlocked;
    return tp.subscribeNow;
  };

  const onSubscribe = async (plan: TokenPlanSpec) => {
    setErr("");
    setMsg("");
    if (!token) {
      navigate(`/login?redirect=${encodeURIComponent("/token-plan")}`);
      return;
    }
    const state = resolveSubscribeState(plan, userTierRank, subscriptionActive, true);
    if (state === "blocked") {
      setErr(tp.btnBlocked);
      return;
    }
    const planKey = planSubscribeKey(plan.id, billing);
    setLoadingId(plan.id);
    try {
      const res = await subscribe(planKey);
      await refreshWallet();
      await refreshLicense();
      setMsg(fmt(tp.success, { label: res.label, balance: res.balance.toLocaleString() }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : tp.insufficient);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="mimo-tp-page">
      <section className="mimo-tp-hero">
        <div className="mimo-container mimo-tp-hero-inner">
          <h1 className="mimo-tp-hero-title">{tp.heroTitle}</h1>
          <p className="mimo-tp-hero-sub">{tp.heroSubtitle}</p>
          <p className="mimo-tp-hero-note">{tp.heroNote}</p>
          {token && (
            <div className="mimo-tp-hero-meta">
              <span className="mimo-tp-hero-pill">
                <span className="mimo-tp-hero-pill-label">{tp.balanceLabel}</span>
                <strong>{formatPoints(balance, locale)}</strong>
              </span>
              {subscriptionActive && summary?.tier && (
                <span className="mimo-tp-hero-pill mimo-tp-hero-pill-accent">
                  <span className="mimo-tp-hero-pill-label">{summary.tier.toUpperCase()}</span>
                  {summary.tier_expires_at && (
                    <>
                      <span className="mimo-tp-hero-pill-sep" aria-hidden>
                        ·
                      </span>
                      <span>
                        {tp.expiresOn} {summary.tier_expires_at}
                      </span>
                    </>
                  )}
                </span>
              )}
            </div>
          )}
        </div>
      </section>

      <section id="plans" className="mimo-tp-plans">
        <div className="mimo-container">
          <h2 className="mimo-tp-section-title">{tp.choosePlan}</h2>

          <div className="mimo-tp-billing-toggle">
            <button
              type="button"
              className={billing === "monthly" ? "mimo-tp-billing-active" : ""}
              onClick={() => setBilling("monthly")}
            >
              {tp.billingMonthly}
            </button>
            <button
              type="button"
              className={billing === "yearly" ? "mimo-tp-billing-active" : ""}
              onClick={() => setBilling("yearly")}
            >
              {tp.billingYearly}
              <span className="mimo-tp-badge">{tp.yearlyBadge}</span>
            </button>
          </div>

          {(msg || err) && (
            <div className={`mimo-tp-alert ${err ? "mimo-tp-alert-error" : ""}`}>{err || msg}</div>
          )}

          <div className="mimo-tp-grid">
            {plans.map((plan) => {
              const cost = billing === "monthly" ? plan.monthlyCost : plan.yearlyCost;
              const original = billing === "yearly" ? plan.monthlyCost * 12 : undefined;
              const period = billing === "monthly" ? tp.perMonth : tp.perYear;
              const tierName = plan.id.charAt(0).toUpperCase() + plan.id.slice(1);
              const state = resolveSubscribeState(plan, userTierRank, subscriptionActive, !!token);
              const disabled = state === "blocked" || loadingId === plan.id;
              const features = PLAN_FEATURE_KEYS[plan.id].map((k) => featureLabel(k));

              return (
                <article
                  key={plan.id}
                  className={`mimo-tp-card mimo-tp-card--${plan.id} ${plan.featured ? "mimo-tp-card-featured" : ""}`}
                >
                  <div className="mimo-tp-card-head">
                    <div className="mimo-tp-card-head-top">
                      <h3 className="mimo-tp-card-name">{tierName}</h3>
                      {billing === "yearly" && plan.yearlySave > 0 ? (
                        <span className="mimo-tp-save">{fmt(tp.saveLabel, { n: plan.yearlySave })}</span>
                      ) : (
                        <span className="mimo-tp-save mimo-tp-save-placeholder" aria-hidden />
                      )}
                    </div>
                    <p className="mimo-tp-card-tag">{planTags[plan.id]}</p>
                  </div>

                  <div className="mimo-tp-card-pricing">
                    <div className="mimo-tp-price-row">
                      <span className="mimo-tp-price">{cost.toLocaleString()}</span>
                      <span className="mimo-tp-price-unit">
                        {t.common.pointsUnit}
                        {period}
                      </span>
                    </div>
                    <p className={`mimo-tp-original ${original == null ? "mimo-tp-original-empty" : ""}`}>
                      {original != null
                        ? fmt(tp.originalPrice, { n: original.toLocaleString() })
                        : "\u00a0"}
                    </p>
                    <div className="mimo-tp-quota">
                      <p className="mimo-tp-credits">{creditsLabel(plan.creditsLabelKey)}</p>
                      <p className={`mimo-tp-mult ${plan.multiplierKey ? "" : "mimo-tp-mult-empty"}`}>
                        {plan.multiplierKey
                          ? (tp as Record<string, string>)[plan.multiplierKey]
                          : "\u00a0"}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    className={`mimo-tp-subscribe ${state === "blocked" ? "mimo-tp-subscribe-disabled" : ""}`}
                    disabled={disabled}
                    onClick={() => void onSubscribe(plan)}
                  >
                    {loadingId === plan.id ? "…" : btnLabel(state)}
                  </button>

                  <ul className="mimo-tp-features">
                    {features.map((f) => (
                      <li key={f}>
                        <Check size={14} strokeWidth={2.5} aria-hidden />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>

                  <p className="mimo-tp-renew-note">{tp.renewNote}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mimo-tp-tools">
        <div className="mimo-container">
          <h2 className="mimo-tp-section-title">{tp.toolsTitle}</h2>
          <p className="mimo-tp-section-desc">{tp.toolsDesc}</p>
          <div className="mimo-tp-tools-grid">
            {TOKEN_PLAN_CODING_TOOLS.map((tool) => (
              <div key={tool.id} className="mimo-tp-tool-chip">
                <PartnerIcon partner={tool} size={22} />
                <span>{tool.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mimo-tp-steps">
        <div className="mimo-container">
          <h2 className="mimo-tp-section-title">{tp.quickStartTitle}</h2>
          <div className="mimo-tp-steps-grid">
            {[
              { title: tp.step1Title, desc: tp.step1Desc, cta: tp.step1Cta, to: "#plans" },
              { title: tp.step2Title, desc: tp.step2Desc, cta: tp.step2Cta, to: "/product/api" },
              { title: tp.step3Title, desc: tp.step3Desc, cta: tp.step3Cta, to: "/console/token-plan" },
              { title: tp.step4Title, desc: tp.step4Desc, cta: tp.step4Cta, to: "/claw" },
            ].map((step) => (
              <article key={step.title} className="mimo-tp-step-card">
                <h3>{step.title}</h3>
                <p>{step.desc}</p>
                <Link to={step.to} className="mimo-tp-step-link">
                  {step.cta} →
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="mimo-tp-faq">
        <div className="mimo-container mimo-tp-faq-inner">
          <h2 className="mimo-tp-section-title">{tp.faqTitle}</h2>
          <div className="mimo-tp-faq-list">
            {FAQ_KEYS.map((key, idx) => {
              const q = (tp as Record<string, string>)[`${key}Q`];
              const a = (tp as Record<string, string>)[`${key}A`];
              const open = openFaq === idx;
              return (
                <div key={key} className={`mimo-tp-faq-item ${open ? "mimo-tp-faq-open" : ""}`}>
                  <button
                    type="button"
                    className="mimo-tp-faq-q"
                    onClick={() => setOpenFaq(open ? null : idx)}
                  >
                    {q}
                    <ChevronDown size={18} className="mimo-tp-faq-chevron" aria-hidden />
                  </button>
                  {open && <p className="mimo-tp-faq-a">{a}</p>}
                </div>
              );
            })}
          </div>
          {token ? (
            <Link to="/console/token-plan" className="mimo-tp-learn-more">
              {tp.goConsole} →
            </Link>
          ) : (
            <Link to="/login" className="mimo-tp-learn-more">
              {tp.learnMore} →
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}
