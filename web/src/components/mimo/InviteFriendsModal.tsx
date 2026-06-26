import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Download, ExternalLink, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { fetchAuthedBlobUrl, siteOrigin } from "@/lib/authedAsset";
import { InviteProgressPanel, InviteRulesPanel } from "@/components/mimo/InvitePanels";

type Tab = "invite" | "progress" | "rules";

export function InviteFriendsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useLocale();
  const { token, user } = useAuth();
  const ref = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<Tab>("invite");
  const [copied, setCopied] = useState(false);
  const [qrUrl, setQrUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const code = user?.invite_code || "";
  const link = `${window.location.origin}/login?invite=${code}`;

  useEffect(() => {
    if (!open || !token || !code) {
      setQrUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    fetchAuthedBlobUrl(`/api/invites/qrcode.png?origin=${encodeURIComponent(siteOrigin())}`)
      .then((url) => {
        objectUrl = url;
        if (!cancelled) setQrUrl(url);
        else URL.revokeObjectURL(url);
      })
      .catch(() => {
        if (!cancelled) setQrUrl(null);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [open, token, code]);

  if (!open) return null;

  const copyLink = async () => {
    if (!code) return;
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadQr = () => {
    if (!qrUrl) return;
    const a = document.createElement("a");
    a.href = qrUrl;
    a.download = `sensehub-invite-${code}.png`;
    a.rel = "noopener";
    a.click();
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "invite", label: t.invite.tabInvite },
    { id: "progress", label: t.invite.tabProgress },
    { id: "rules", label: t.invite.tabRules },
  ];

  return (
    <div className="mimo-modal-overlay" onClick={onClose} role="presentation">
      <div
        ref={ref}
        className="mimo-invite-modal max-h-[min(90vh,720px)] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="invite-title"
      >
        <button type="button" className="mimo-modal-close" onClick={onClose} aria-label="关闭">
          <X size={18} />
        </button>

        <p className="text-sm font-semibold">
          灵枢 <span className="font-normal text-mimo-muted">SenseHub</span>
        </p>
        <h2 id="invite-title" className="mt-4 text-2xl font-semibold tracking-tight">
          {t.invite.modalTitle}
        </h2>
        <p className="mt-2 text-sm text-mimo-muted">{t.invite.modalSubtitle}</p>

        <div className="mt-6 flex gap-1 border-b border-mimo-border">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mimo-console-tab ${tab === item.id ? "mimo-console-tab-active" : ""}`}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {tab === "invite" && (
            <>
              <div className="space-y-2">
                <span className="mimo-invite-badge mimo-invite-badge-dark">{t.invite.badgePrimary}</span>
                <span className="mimo-invite-badge mimo-invite-badge-light">{t.invite.badgeSecondary}</span>
              </div>
              <ul className="mt-6 space-y-2 text-xs leading-6 text-mimo-muted">
                <li>{t.invite.rule1}</li>
                <li>{t.invite.rule2}</li>
              </ul>
              <Link
                to="/console/invite"
                className="mt-4 inline-flex items-center gap-1 text-sm text-[#1677ff] hover:underline"
                onClick={onClose}
              >
                {t.invite.progress}
                <ExternalLink size={13} />
              </Link>
              {token && code ? (
                <div className="mt-8">
                  <p className="text-xs text-mimo-muted">{t.invite.yourCode}</p>
                  <p className="mt-1 font-mono text-lg font-semibold">{code}</p>

                  <div className="mt-6 flex flex-col items-center gap-3 rounded-xl border border-mimo-border bg-surface p-4">
                    <p className="text-xs font-medium text-mimo-muted">{t.invite.qrTitle}</p>
                    {qrUrl ? (
                      <img
                        src={qrUrl}
                        alt={t.invite.qrTitle}
                        className="h-44 w-44 rounded-lg border border-mimo-border bg-white p-2"
                      />
                    ) : (
                      <div className="flex h-44 w-44 items-center justify-center rounded-lg border border-dashed border-mimo-border text-xs text-mimo-muted">
                        {t.invite.qrLoading}
                      </div>
                    )}
                    <p className="text-center text-[11px] text-mimo-muted">{t.invite.qrHint}</p>
                    <button
                      type="button"
                      className="mimo-btn-ghost mimo-btn-sm border border-mimo-border"
                      disabled={!qrUrl}
                      onClick={downloadQr}
                    >
                      <Download size={14} className="mr-1 inline" aria-hidden />
                      {t.invite.qrDownload}
                    </button>
                  </div>

                  <p className="mt-4 break-all font-mono text-[11px] text-mimo-muted">{link}</p>
                  <button type="button" className="mimo-btn-cta mimo-btn-sm mt-4 w-full" onClick={() => void copyLink()}>
                    {copied ? t.invite.copied : `${t.invite.copyLink} →`}
                  </button>
                </div>
              ) : (
                <Link to="/login" className="mimo-btn-cta mimo-btn-sm mt-8 block w-full text-center" onClick={onClose}>
                  {t.invite.ctaLogin}
                </Link>
              )}
            </>
          )}
          {tab === "progress" && <InviteProgressPanel compact />}
          {tab === "rules" && <InviteRulesPanel compact />}
        </div>
      </div>
    </div>
  );
}
