import { Bot, Mic, Monitor, Sparkles, Waves } from "lucide-react";

/** 登录页中部装饰 — 与灵枢主题色协调的三层视觉 */
export function AuthDecor() {
  return (
    <div className="auth-decor-root" aria-hidden>
      <div className="auth-decor-glow auth-decor-glow-a" />
      <div className="auth-decor-glow auth-decor-glow-b" />

      <div className="auth-decor-stack">
        <div className="auth-decor-card auth-decor-card-back">
          <Waves size={36} className="text-primary/30" strokeWidth={1.5} />
        </div>
        <div className="auth-decor-card auth-decor-card-mid">
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15">
              <Sparkles className="text-primary" size={28} />
            </div>
            <p className="text-sm font-semibold text-text-primary">灵枢 Agent</p>
            <p className="text-xs text-text-secondary">多脑 · 多模态 · 本地执行</p>
          </div>
        </div>
        <div className="auth-decor-card auth-decor-card-front">
          <div className="grid grid-cols-3 gap-3 text-center">
            {[
              { Icon: Mic, label: "语音" },
              { Icon: Monitor, label: "视觉" },
              { Icon: Bot, label: "Agent" },
            ].map(({ Icon, label }) => (
              <div key={label} className="flex flex-col items-center gap-1.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                  <Icon size={18} className="text-primary" />
                </div>
                <span className="text-[10px] font-medium text-text-secondary">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="auth-decor-orbit auth-decor-orbit-1" />
      <div className="auth-decor-orbit auth-decor-orbit-2" />
    </div>
  );
}

/** 左侧下方小卡片装饰（大屏时与中部呼应） */
export function AuthHeroCard() {
  return (
    <div className="auth-hero-card mt-10 hidden max-w-xs sm:block" aria-hidden>
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-primary">Multi-Brain Pipeline</p>
      <div className="space-y-2">
        {["意图脑 → 规划脑", "安全审查 → 工具执行", "程序化优先 · VLM 兜底"].map((line) => (
          <div
            key={line}
            className="rounded-xl border border-border/80 bg-surface/80 px-3 py-2 text-xs text-text-secondary backdrop-blur-sm"
          >
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}
