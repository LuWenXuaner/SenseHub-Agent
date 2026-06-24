import { Link } from "react-router-dom";
import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { InviteFriendsModal } from "@/components/mimo/InviteFriendsModal";
import {
  RedeemConfirmDialog,
  RedeemSuccessDialog,
  type RedeemConfirmItem,
} from "@/components/mimo/RedeemConfirmDialog";
import { useLocale } from "@/context/LocaleContext";
import { useWallet } from "@/hooks/useWallet";
import { EXCHANGE_CATALOG, formatPoints } from "@/lib/pointsCatalog";

const CATEGORIES = ["tier", "api", "product"] as const;

export function ConsolePointsPage() {
  const { t, locale, fmt } = useLocale();
  const { balance, totalEarned, canCheckIn, checkIn, redeem } = useWallet();
  const [msg, setMsg] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [pending, setPending] = useState<RedeemConfirmItem | null>(null);
  const [redeeming, setRedeeming] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [successOpen, setSuccessOpen] = useState(false);

  const onCheckIn = async () => {
    try {
      const res = await checkIn();
      if (res.ok) {
        const extra = "weekend_double" in res && res.weekend_double ? ` · ${t.gamification.weekendDouble}` : "";
        setMsg(fmt(t.console.checkInReward, { n: res.earned }) + extra);
      } else setMsg(t.console.checkInDone);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : t.common.noData);
    }
  };

  const openRedeem = (item: (typeof EXCHANGE_CATALOG)[number]) => {
    const label = t.points[item.labelKey];
    const desc = locale === "zh" ? item.descZh : item.descEn;
    setPending({ id: item.id, label, cost: item.cost, desc });
  };

  const confirmRedeem = async () => {
    if (!pending) return;
    setRedeeming(true);
    try {
      const res = await redeem(pending.id);
      setPending(null);
      let msg = `${pending.label} · ${t.points.cost} ${formatPoints(res.cost, locale)} · ${t.redeemDialog.after} ${formatPoints(res.balance, locale)}`;
      if (res.tier) {
        msg += ` · ${t.console.currentTier} ${res.tier.toUpperCase()}`;
        if (res.tier_expires_at) msg += ` (${res.tier_expires_at})`;
      }
      setSuccessMsg(msg);
      setSuccessOpen(true);
      setMsg("");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : t.points.insufficient);
      setPending(null);
    } finally {
      setRedeeming(false);
    }
  };

  const categoryTitle = (cat: (typeof CATEGORIES)[number]) => {
    if (cat === "tier") return t.points.categoryTier;
    if (cat === "api") return t.points.categoryApi;
    return t.points.categoryProduct;
  };

  return (
    <>
      <ConsolePageFrame
        title={t.console.pointsCenter}
        subtitle={t.points.signInDesc}
        actions={
          <button type="button" className="mimo-btn-cta mimo-btn-sm" onClick={() => setInviteOpen(true)}>
            {t.console.invite}
          </button>
        }
      >
        {msg && <p className="mb-4 text-sm text-mimo-accent">{msg}</p>}

        <Link to="/console/engagement" className="mimo-engage-teaser mb-6 block">
          <Sparkles size={18} className="shrink-0 text-[#c9a96e]" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{t.gamification.hubLink}</p>
            <p className="text-xs text-mimo-muted">{t.gamification.hubTeaser}</p>
          </div>
          <ArrowRight size={16} className="shrink-0 opacity-50" aria-hidden />
        </Link>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="mimo-balance-summary-card">
            <p className="text-sm text-mimo-muted">{t.points.balance}</p>
            <p className="mt-2 text-3xl font-semibold">{formatPoints(balance, locale)}</p>
          </div>
          <div className="mimo-balance-summary-card">
            <p className="text-sm text-mimo-muted">{t.points.totalEarned}</p>
            <p className="mt-2 text-3xl font-semibold">{formatPoints(totalEarned, locale)}</p>
          </div>
          <div className="mimo-balance-summary-card">
            <p className="text-sm text-mimo-muted">{t.points.warningThreshold}</p>
            <p className="mt-2 text-3xl font-semibold">500</p>
            <p className="mt-2 text-xs text-mimo-muted">{t.points.warningOff}</p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <button
            type="button"
            className="mimo-btn-cta mimo-btn-sm"
            disabled={!canCheckIn}
            onClick={() => void onCheckIn()}
          >
            {canCheckIn ? t.console.checkIn : t.console.checkInDone}
          </button>
          <button type="button" className="mimo-btn-outline mimo-btn-sm" onClick={() => setInviteOpen(true)}>
            {t.points.invite}
          </button>
        </div>

        <h3 className="mt-10 text-lg font-semibold">{t.points.exchangeTitle}</h3>
        {CATEGORIES.map((cat) => {
          const items = EXCHANGE_CATALOG.filter((x) => x.category === cat);
          if (!items.length) return null;
          return (
            <div key={cat} className="mt-6">
              <h4 className="mb-3 text-sm font-medium text-mimo-muted">{categoryTitle(cat)}</h4>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {items.map((item) => {
                  const label = t.points[item.labelKey];
                  const desc = locale === "zh" ? item.descZh : item.descEn;
                  return (
                    <div key={item.id} className="mimo-console-panel flex flex-col gap-3">
                      <div>
                        <p className="font-medium">{label}</p>
                        <p className="mt-1 text-xs leading-5 text-mimo-muted">{desc}</p>
                      </div>
                      <div className="mt-auto flex items-center justify-between gap-2">
                        <span className="text-sm text-mimo-accent">
                          {t.points.cost} {formatPoints(item.cost, locale)}
                        </span>
                        <button
                          type="button"
                          className="mimo-btn-cta mimo-btn-sm"
                          disabled={balance < item.cost}
                          onClick={() => openRedeem(item)}
                        >
                          {t.points.redeem}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        <div className="mimo-console-panel mt-8">
          <h3 className="font-medium">{t.points.rulesTitle}</h3>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-7 text-mimo-muted">
            <li>{t.points.rule1}</li>
            <li>{fmt(t.points.rule2, { n: 100, max: 30 })}</li>
            <li>{t.points.rule3}</li>
            <li>{t.points.rule4}</li>
          </ol>
        </div>
      </ConsolePageFrame>

      <InviteFriendsModal open={inviteOpen} onClose={() => setInviteOpen(false)} />
      <RedeemConfirmDialog
        open={!!pending}
        item={pending}
        balance={balance}
        loading={redeeming}
        onClose={() => setPending(null)}
        onConfirm={() => void confirmRedeem()}
      />
      <RedeemSuccessDialog open={successOpen} message={successMsg} onClose={() => setSuccessOpen(false)} />
    </>
  );
}
