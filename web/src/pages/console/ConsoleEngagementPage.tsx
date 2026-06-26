import { useEffect, useMemo, useState } from "react";
import {
  Crown,
  Lock,
  Medal,
  Palette,
  Share2,
  Sparkles,
  Star,
  Trophy,
  Zap,
} from "lucide-react";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { AchievementShareModal } from "@/components/mimo/AchievementShareModal";
import { useLocale } from "@/context/LocaleContext";
import { useGamification } from "@/hooks/useGamification";
import { useWallet } from "@/hooks/useWallet";
import { ACHIEVEMENT_ICONS, BG_STYLES, RATING_COLORS } from "@/lib/gamificationCatalog";
import { formatPoints } from "@/lib/pointsCatalog";
import type { AchievementRow, GamificationSummary, LeaderboardRow } from "@/lib/api";

const WHEEL_COLORS = ["#ffd666", "#ff9c6e", "#ffc53d", "#ffa940", "#ff7a45", "#ff4d4f", "#d4b106"];

function LevelRing({ pct, color, level }: { pct: number; color: string; level: number }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <svg viewBox="0 0 120 120" className="mimo-engage-level-ring" aria-hidden>
      <defs>
        <filter id="engage-glow">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="7" />
      <circle
        cx="60"
        cy="60"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={offset}
        transform="rotate(-90 60 60)"
        filter="url(#engage-glow)"
        className="mimo-engage-ring-progress"
      />
      <text x="60" y="58" textAnchor="middle" className="mimo-engage-ring-lv">
        {level}
      </text>
      <text x="60" y="74" textAnchor="middle" className="mimo-engage-ring-label">
        LV
      </text>
    </svg>
  );
}

function EngageHero({ data }: { data: GamificationSummary }) {
  const { t } = useLocale();
  const g = t.gamification;
  const p = data.progress;
  const color = RATING_COLORS[p.rating_id] ?? "#c9a96e";
  const unlocked = data.achievements.filter((a) => a.unlocked).length;

  return (
    <section className="mimo-engage-hero" style={{ ["--engage-accent" as string]: color }}>
      <div className="mimo-engage-hero-bg" aria-hidden />
      <div className="mimo-engage-hero-orbs" aria-hidden>
        <span />
        <span />
        <span />
      </div>

      <div className="mimo-engage-hero-grid">
        <div className="mimo-engage-hero-main">
          <span className="mimo-engage-hero-chip">
            <Sparkles size={14} aria-hidden />
            {data.season.name}
          </span>
          <h2 className="mimo-engage-hero-title">
            {p.rating_name}
            <span className="mimo-engage-hero-rating">· {g.rating}</span>
          </h2>
          <p className="mimo-engage-hero-xp">
            XP {p.xp.toLocaleString()}
            <span className="opacity-60"> / {p.next_cap.toLocaleString()}</span>
          </p>
          <div className="mimo-engage-hero-stats">
            <div className="mimo-engage-stat-pill">
              <Medal size={14} aria-hidden />
              <span>
                {unlocked}/{data.achievements.length} {g.achievements}
              </span>
            </div>
            <div className="mimo-engage-stat-pill">
              <Zap size={14} aria-hidden />
              <span>
                {data.wheel.free_spins_left} {g.wheelFreeShort}
              </span>
            </div>
            {data.weekend_double && (
              <div className="mimo-engage-stat-pill mimo-engage-stat-pill-hot">{g.weekendDouble}</div>
            )}
          </div>
        </div>

        <div className="mimo-engage-hero-ring-wrap">
          <LevelRing pct={p.progress_pct} color={color} level={p.level} />
          <p className="mimo-engage-hero-pct">{p.progress_pct}%</p>
        </div>
      </div>

      <div className="mimo-engage-milestone-rail">
        {data.milestones.map((ms) => (
          <div
            key={ms.level}
            className={`mimo-engage-milestone-node ${p.level >= ms.level ? "mimo-engage-milestone-node-done" : ""}`}
          >
            <span className="mimo-engage-milestone-dot" />
            <span className="mimo-engage-milestone-label">Lv.{ms.level}</span>
            <span className="mimo-engage-milestone-reward">+{ms.points}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function WheelPanel() {
  const { t, locale, fmt } = useLocale();
  const g = t.gamification;
  const { data, spinWheel, refresh } = useGamification();
  const { refresh: refreshWallet } = useWallet();
  const [spinning, setSpinning] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [result, setResult] = useState<{ text: string; win: boolean } | null>(null);

  const segments = useMemo(() => data?.wheel.prizes ?? [], [data]);

  const wheelGradient = useMemo(() => {
    if (!segments.length) return "";
    const slice = 360 / segments.length;
    const parts = segments.map((_, i) => {
      const c = WHEEL_COLORS[i % WHEEL_COLORS.length];
      return `${c} ${i * slice}deg ${(i + 1) * slice}deg`;
    });
    return `conic-gradient(from -90deg, ${parts.join(", ")})`;
  }, [segments]);

  const onSpin = async () => {
    if (!data || spinning) return;
    setSpinning(true);
    setResult(null);
    const extraTurns = 5 + Math.floor(Math.random() * 3);
    setRotation((r) => r + extraTurns * 360 + Math.floor(Math.random() * 360));
    try {
      const res = await spinWheel();
      setResult({ text: fmt(g.wheelWin, { prize: res.prize.label }), win: true });
      await refreshWallet();
    } catch (e) {
      setResult({ text: e instanceof Error ? e.message : g.wheelFail, win: false });
    } finally {
      setTimeout(() => setSpinning(false), 1100);
      void refresh();
    }
  };

  if (!data) return null;
  const w = data.wheel;

  return (
    <div className="mimo-engage-panel mimo-engage-panel-glow">
      <div className="mimo-engage-panel-head">
        <div>
          <h3 className="mimo-engage-panel-title">{g.wheelTitle}</h3>
          <p className="mt-0.5 text-xs text-mimo-muted">{g.wheelDesc}</p>
        </div>
        <div className="mimo-engage-panel-icon">
          <Zap size={18} aria-hidden />
        </div>
      </div>

      <div className="mimo-engage-wheel-stage">
        <div className="mimo-engage-wheel-pointer" aria-hidden />
        <div
          className={`mimo-engage-wheel-disc ${spinning ? "mimo-engage-wheel-disc-spin" : ""}`}
          style={{
            background: wheelGradient,
            transform: `rotate(${rotation}deg)`,
          }}
        >
          {segments.map((seg, i) => {
            const slice = 360 / segments.length;
            const angle = slice * i + slice / 2 - 90;
            return (
              <span
                key={seg.id}
                className="mimo-engage-wheel-label"
                style={{ transform: `rotate(${angle}deg) translateY(-68px)` }}
              >
                {seg.points}
              </span>
            );
          })}
        </div>
        <div className="mimo-engage-wheel-hub">
          <Star size={18} className="text-[#c9a96e]" aria-hidden />
        </div>
      </div>

      <p className="mt-4 text-center text-sm text-mimo-muted">
        {w.free_spins_left > 0
          ? fmt(g.wheelFreeLeft, { n: w.free_spins_left })
          : fmt(g.wheelCost, { n: w.spin_cost, balance: formatPoints(w.balance, locale) })}
      </p>
      <button
        type="button"
        className="mimo-engage-spin-btn mimo-btn-block mt-3"
        disabled={spinning || (w.free_spins_left <= 0 && w.balance < w.spin_cost)}
        onClick={() => void onSpin()}
      >
        {spinning ? g.wheelSpinning : g.wheelSpin}
      </button>
      {result && (
        <p className={`mimo-engage-result mt-3 ${result.win ? "mimo-engage-result-win" : ""}`}>{result.text}</p>
      )}
    </div>
  );
}

function AchievementBadge({
  row,
  onShare,
}: {
  row: AchievementRow;
  onShare?: (row: AchievementRow) => void;
}) {
  const { t } = useLocale();
  const g = t.gamification;
  const Icon = ACHIEVEMENT_ICONS[row.icon] ?? Medal;
  const inner = (
    <>
      {row.unlocked && <span className="mimo-engage-badge-shine" aria-hidden />}
      <div className="mimo-engage-badge-icon">
        <Icon size={22} aria-hidden />
      </div>
      <span className="mimo-engage-badge-name">{row.name}</span>
      {row.unlocked ? (
        <Share2 size={12} className="mimo-engage-badge-share" aria-hidden />
      ) : (
        <Lock size={12} className="mimo-engage-badge-lock" aria-hidden />
      )}
    </>
  );

  if (row.unlocked && onShare) {
    return (
      <button
        type="button"
        className="mimo-engage-badge mimo-engage-badge-unlocked mimo-engage-badge-btn"
        title={`${row.desc} · ${g.shareTap}`}
        onClick={() => onShare(row)}
      >
        {inner}
      </button>
    );
  }

  return (
    <div
      className={`mimo-engage-badge ${row.unlocked ? "mimo-engage-badge-unlocked" : "mimo-engage-badge-locked"}`}
      title={row.desc}
    >
      {inner}
    </div>
  );
}

function AchievementGrid({ onShare }: { onShare: (row: AchievementRow) => void }) {
  const { t } = useLocale();
  const g = t.gamification;
  const { data } = useGamification();
  if (!data) return null;
  const unlocked = data.achievements.filter((a) => a.unlocked).length;
  const pct = Math.round((unlocked / data.achievements.length) * 100);

  return (
    <div className="mimo-engage-panel mimo-engage-panel-wide">
      <div className="mimo-engage-panel-head">
        <div>
          <h3 className="mimo-engage-panel-title">{g.achievements}</h3>
          <p className="mt-0.5 text-xs text-mimo-muted">{g.achievementsDesc}</p>
        </div>
        <div className="mimo-engage-ach-progress">
          <span className="text-sm font-semibold">{pct}%</span>
          <span className="text-xs text-mimo-muted">
            {unlocked}/{data.achievements.length}
          </span>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
        {data.achievements.map((a) => (
          <AchievementBadge key={a.id} row={a} onShare={onShare} />
        ))}
      </div>
    </div>
  );
}

function LeaderboardPodium({ rows }: { rows: LeaderboardRow[] }) {
  const top = rows.slice(0, 3);
  const order = [top[1], top[0], top[2]].filter(Boolean);
  const heights = ["h-16", "h-24", "h-12"];
  const medals = ["#c0c0c0", "#ffd666", "#cd7f32"];

  return (
    <div className="mimo-engage-podium">
      {order.map((row, i) => {
        const rank = row.rank;
        const h = heights[i] ?? "h-14";
        return (
          <div key={row.public_id} className="mimo-engage-podium-col">
            <div className="mimo-engage-podium-avatar" style={{ borderColor: medals[rank - 1] ?? "#ddd" }}>
              {rank === 1 ? <Crown size={16} /> : <span>{rank}</span>}
            </div>
            <p className="mimo-engage-podium-name">{row.display_name}</p>
            <div className={`mimo-engage-podium-bar ${h}`} style={{ background: medals[rank - 1] ?? "#e8e8e8" }}>
              <span className="mimo-engage-podium-score">{row.total_earned.toLocaleString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LeaderboardPanel() {
  const { t } = useLocale();
  const g = t.gamification;
  const { data } = useGamification();
  const [rows, setRows] = useState<LeaderboardRow[]>([]);

  useEffect(() => {
    if (data?.leaderboard_preview) setRows(data.leaderboard_preview);
  }, [data]);

  const list = rows.length ? rows : data?.leaderboard_preview ?? [];
  const rest = list.slice(3);

  return (
    <div className="mimo-engage-panel mimo-engage-panel-glow">
      <div className="mimo-engage-panel-head">
        <div className="flex items-center gap-2">
          <Trophy size={18} className="text-[#c9a96e]" aria-hidden />
          <h3 className="mimo-engage-panel-title">{g.leaderboard}</h3>
        </div>
      </div>
      {list.length >= 3 && <LeaderboardPodium rows={list} />}
      <ol className="mt-4 space-y-1.5">
        {(rest.length ? rest : list).map((row) => (
          <li key={row.public_id} className={`mimo-engage-lb-row ${row.rank <= 3 ? "mimo-engage-lb-row-top" : ""}`}>
            <span className={`mimo-engage-lb-rank ${row.rank <= 3 ? "mimo-engage-lb-rank-top" : ""}`}>{row.rank}</span>
            <span className="min-w-0 flex-1 truncate font-medium">{row.display_name}</span>
            <span className="mimo-engage-lb-rating">{row.rating_name}</span>
            <span className="mimo-engage-lb-score">{row.total_earned.toLocaleString()}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ProfileCosmetics() {
  const { t } = useLocale();
  const g = t.gamification;
  const { data, updateProfile } = useGamification();
  const [saving, setSaving] = useState(false);
  if (!data) return null;

  const pick = async (kind: "bg" | "theme", id: string) => {
    setSaving(true);
    try {
      await updateProfile(kind === "bg" ? { profile_bg: id } : { profile_theme: id });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mimo-engage-panel mimo-engage-panel-glow">
      <div className="mimo-engage-panel-head">
        <div>
          <h3 className="mimo-engage-panel-title">{g.customize}</h3>
          <p className="mt-0.5 text-xs text-mimo-muted">{g.customizeDesc}</p>
        </div>
        <div className="mimo-engage-panel-icon">
          <Palette size={18} aria-hidden />
        </div>
      </div>
      <p className="mt-3 text-xs font-medium uppercase tracking-wide text-mimo-muted">{g.backgrounds}</p>
      <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {data.backgrounds.map((bg) => (
          <button
            key={bg.id}
            type="button"
            disabled={!bg.unlocked || saving}
            className={`mimo-engage-cosmetic ${data.profile.profile_bg === bg.id ? "mimo-engage-cosmetic-active" : ""} ${!bg.unlocked ? "mimo-engage-cosmetic-locked" : ""}`}
            style={{ background: BG_STYLES[bg.id] ?? BG_STYLES.default }}
            onClick={() => void pick("bg", bg.id)}
          >
            {!bg.unlocked && <Lock size={14} className="mimo-engage-cosmetic-lock" aria-hidden />}
            <span className="mimo-engage-cosmetic-label">{bg.name}</span>
          </button>
        ))}
      </div>
      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-mimo-muted">{g.themes}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {data.themes.map((th) => (
          <button
            key={th.id}
            type="button"
            disabled={!th.unlocked || saving}
            className={`mimo-engage-theme-chip ${data.profile.profile_theme === th.id ? "mimo-engage-theme-chip-active" : ""} ${!th.unlocked ? "opacity-40" : ""}`}
            style={{ ["--chip-accent" as string]: th.accent ?? "#c9a96e" }}
            onClick={() => void pick("theme", th.id)}
          >
            {!th.unlocked && <Lock size={10} className="mr-1 inline" aria-hidden />}
            {th.name}
          </button>
        ))}
      </div>
    </div>
  );
}

function EngageLoading() {
  return (
    <div className="mimo-engage-loading">
      <div className="mimo-engage-loading-hero mimo-engage-shimmer" />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="mimo-engage-loading-card mimo-engage-shimmer" />
        <div className="mimo-engage-loading-card mimo-engage-shimmer" />
      </div>
    </div>
  );
}

export function ConsoleEngagementPage() {
  const { t } = useLocale();
  const g = t.gamification;
  const { data, loading } = useGamification();
  const [shareTarget, setShareTarget] = useState<AchievementRow | null>(null);

  return (
    <ConsolePageFrame title={g.title} subtitle={g.subtitle}>
      {loading && !data ? (
        <EngageLoading />
      ) : data ? (
        <div className="mimo-engage-hub">
          <EngageHero data={data} />
          <div className="mimo-engage-grid-main">
            <WheelPanel />
            <LeaderboardPanel />
          </div>
          <AchievementGrid onShare={(row) => setShareTarget(row)} />
          <ProfileCosmetics />
        </div>
      ) : (
        <p className="text-sm text-mimo-muted">{t.common.noData}</p>
      )}
      <AchievementShareModal
        open={!!shareTarget}
        achievement={shareTarget}
        onClose={() => setShareTarget(null)}
      />
    </ConsolePageFrame>
  );
}
