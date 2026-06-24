import { X } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { formatPoints } from "@/lib/pointsCatalog";

export type RedeemConfirmItem = {
  id: string;
  label: string;
  cost: number;
  desc?: string;
};

type Props = {
  open: boolean;
  item: RedeemConfirmItem | null;
  balance: number;
  loading?: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export function RedeemConfirmDialog({ open, item, balance, loading, onClose, onConfirm }: Props) {
  const { t, locale } = useLocale();
  const rc = t.redeemDialog;

  if (!open || !item) return null;

  const after = balance - item.cost;
  const insufficient = balance < item.cost;

  return (
    <div className="mimo-modal-overlay" onClick={onClose} role="presentation">
      <div
        className="mimo-redeem-dialog"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="redeem-dialog-title"
      >
        <button type="button" className="mimo-modal-close" onClick={onClose} aria-label={t.common.cancel}>
          <X size={18} />
        </button>
        <h2 id="redeem-dialog-title" className="text-lg font-semibold">
          {rc.title}
        </h2>
        <p className="mt-2 text-sm text-mimo-muted">{rc.subtitle}</p>

        <div className="mimo-redeem-dialog-body">
          <p className="font-medium">{item.label}</p>
          {item.desc && <p className="mt-1 text-xs leading-5 text-mimo-muted">{item.desc}</p>}
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-mimo-muted">{rc.cost}</dt>
              <dd className="font-medium text-mimo-accent">{formatPoints(item.cost, locale)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-mimo-muted">{rc.balance}</dt>
              <dd>{formatPoints(balance, locale)}</dd>
            </div>
            <div className="flex justify-between gap-4 border-t border-mimo-border pt-2">
              <dt className="text-mimo-muted">{rc.after}</dt>
              <dd className={insufficient ? "text-danger font-medium" : "font-medium"}>
                {formatPoints(Math.max(0, after), locale)}
              </dd>
            </div>
          </dl>
          {insufficient && <p className="mt-3 text-sm text-danger">{t.points.insufficient}</p>}
        </div>

        <div className="mt-6 flex gap-2">
          <button type="button" className="mimo-console-outline-btn mimo-btn-block" onClick={onClose}>
            {t.common.cancel}
          </button>
          <button
            type="button"
            className="mimo-console-primary-btn mimo-btn-block"
            disabled={insufficient || loading}
            onClick={onConfirm}
          >
            {loading ? rc.processing : rc.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}

export function RedeemSuccessDialog({
  open,
  message,
  onClose,
}: {
  open: boolean;
  message: string;
  onClose: () => void;
}) {
  const { t } = useLocale();
  const rc = t.redeemDialog;

  if (!open) return null;

  return (
    <div className="mimo-modal-overlay" onClick={onClose} role="presentation">
      <div className="mimo-redeem-dialog mimo-redeem-dialog-success" onClick={(e) => e.stopPropagation()} role="dialog">
        <h2 className="text-lg font-semibold text-mimo-accent">{rc.successTitle}</h2>
        <p className="mt-3 text-sm leading-6 text-mimo-muted">{message}</p>
        <button type="button" className="mimo-console-primary-btn mimo-btn-block mt-6" onClick={onClose}>
          {rc.done}
        </button>
      </div>
    </div>
  );
}
