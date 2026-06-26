import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Medal } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { api, type AchievementSharePublicView } from "@/lib/api";
import { ACHIEVEMENT_ICONS } from "@/lib/gamificationCatalog";
import { siteOrigin } from "@/lib/authedAsset";

export function ShareAchievementPage() {
  const { token = "" } = useParams();
  const { t } = useLocale();
  const g = t.gamification;
  const [view, setView] = useState<AchievementSharePublicView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setError(g.shareInvalid);
      return;
    }
    api
      .achievementSharePublic(token)
      .then(setView)
      .catch((e) => setError(e instanceof Error ? e.message : g.shareInvalid));
  }, [token, g.shareInvalid]);

  const cardSrc = token
    ? `/api/gamification/share/achievement/${encodeURIComponent(token)}/card.png?origin=${encodeURIComponent(siteOrigin())}`
    : "";

  const Icon = view ? ACHIEVEMENT_ICONS[view.achievement.icon] ?? Medal : Medal;

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-lg flex-col items-center justify-center px-4 py-16">
      {error && (
        <div className="mimo-console-panel w-full p-8 text-center">
          <p className="text-mimo-muted">{error}</p>
          <Link to="/" className="mimo-btn-cta mimo-btn-sm mt-6 inline-block">
            {g.shareBackHome}
          </Link>
        </div>
      )}

      {view && !error && (
        <div className="w-full space-y-6">
          <div className="text-center">
            <p className="text-sm font-semibold text-primary">灵枢 SenseHub</p>
            <h1 className="mt-2 text-2xl font-semibold">{g.sharePublicTitle}</h1>
          </div>

          <div className="flex justify-center">
            <img src={cardSrc} alt={view.achievement.name} className="w-full max-w-md rounded-xl shadow-lg" />
          </div>

          <div className="mimo-console-panel flex items-start gap-4 p-5">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary">
              <Icon size={22} aria-hidden />
            </div>
            <div>
              <p className="font-semibold">{view.achievement.name}</p>
              <p className="mt-1 text-sm text-mimo-muted">{view.achievement.desc}</p>
              <p className="mt-3 text-sm">
                {g.sharePublicUser.replace("{name}", view.user.display_name)}
              </p>
              <p className="text-xs text-mimo-muted">
                Lv.{view.user.level} · {view.user.rating_name}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
            <Link to="/login" className="mimo-btn-cta mimo-btn-sm text-center">
              {g.shareCtaJoin}
            </Link>
            <Link to="/token-plan" className="mimo-btn-ghost mimo-btn-sm border border-mimo-border text-center">
              {g.shareCtaPlan}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
