import { useEffect, useState } from "react";
import { Download, Link2, Share2, X } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { api, type AchievementRow, type AchievementShareResult } from "@/lib/api";
import { siteOrigin } from "@/lib/authedAsset";
import { ACHIEVEMENT_ICONS } from "@/lib/gamificationCatalog";

export function AchievementShareModal({
  open,
  achievement,
  onClose,
}: {
  open: boolean;
  achievement: AchievementRow | null;
  onClose: () => void;
}) {
  const { t } = useLocale();
  const g = t.gamification;
  const [loading, setLoading] = useState(false);
  const [share, setShare] = useState<AchievementShareResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open || !achievement?.id) {
      setShare(null);
      setError("");
      setCopied(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .achievementShare(achievement.id, siteOrigin())
      .then((res) => {
        if (!cancelled) setShare(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : g.shareFail);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, achievement?.id, g.shareFail]);

  if (!open || !achievement) return null;

  const Icon = ACHIEVEMENT_ICONS[achievement.icon] ?? Share2;
  const cardSrc = share
    ? `${share.card_url}?origin=${encodeURIComponent(siteOrigin())}`
    : "";

  const copyLink = async () => {
    if (!share?.share_url) return;
    await navigator.clipboard.writeText(share.share_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyText = async () => {
    if (!share?.share_text) return;
    await navigator.clipboard.writeText(share.share_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadCard = () => {
    if (!cardSrc) return;
    const a = document.createElement("a");
    a.href = cardSrc;
    a.download = `sensehub-achievement-${achievement.id}.png`;
    a.rel = "noopener";
    a.click();
  };

  const nativeShare = async () => {
    if (!share || !navigator.share) return;
    try {
      await navigator.share({
        title: `${achievement.name} · 灵枢 SenseHub`,
        text: share.share_text,
        url: share.share_url,
      });
    } catch {
      /* user cancelled */
    }
  };

  return (
    <div className="mimo-modal-overlay" onClick={onClose} role="presentation">
      <div
        className="mimo-invite-modal max-h-[min(92vh,780px)] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="ach-share-title"
      >
        <button type="button" className="mimo-modal-close" onClick={onClose} aria-label="关闭">
          <X size={18} />
        </button>

        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <Icon size={24} aria-hidden />
          </div>
          <div>
            <h2 id="ach-share-title" className="text-xl font-semibold">
              {g.shareTitle}
            </h2>
            <p className="text-sm text-mimo-muted">{achievement.name}</p>
          </div>
        </div>

        <p className="mt-3 text-sm text-mimo-muted">{g.shareDesc}</p>

        {loading && <p className="mt-6 text-sm text-mimo-muted">{g.shareLoading}</p>}
        {error && <p className="mt-6 text-sm text-red-500">{error}</p>}

        {share && !loading && (
          <>
            <div className="mt-6 flex justify-center rounded-xl border border-mimo-border bg-surface p-3">
              <img
                src={cardSrc}
                alt={achievement.name}
                className="max-h-[min(52vh,420px)] w-auto rounded-lg shadow-md"
              />
            </div>

            <p className="mt-3 break-all font-mono text-[11px] text-mimo-muted">{share.share_url}</p>

            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <button type="button" className="mimo-btn-cta mimo-btn-sm w-full" onClick={() => void copyLink()}>
                <Link2 size={14} className="mr-1 inline" aria-hidden />
                {copied ? g.shareCopied : g.shareCopyLink}
              </button>
              <button type="button" className="mimo-btn-ghost mimo-btn-sm w-full border border-mimo-border" onClick={() => void copyText()}>
                {g.shareCopyText}
              </button>
              <button type="button" className="mimo-btn-ghost mimo-btn-sm w-full border border-mimo-border" onClick={downloadCard}>
                <Download size={14} className="mr-1 inline" aria-hidden />
                {g.shareDownloadCard}
              </button>
              {typeof navigator !== "undefined" && "share" in navigator && (
                <button type="button" className="mimo-btn-ghost mimo-btn-sm w-full border border-mimo-border" onClick={() => void nativeShare()}>
                  <Share2 size={14} className="mr-1 inline" aria-hidden />
                  {g.shareNative}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
