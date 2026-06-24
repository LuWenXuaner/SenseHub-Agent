import { useAuth } from "@/context/AuthContext";
import { TIER_PLANS, type TierId } from "@/lib/tierCatalog";
import { CapabilityMatrixTable, TierPlanCard } from "@/components/billing/TierPlanCard";
import { Link } from "react-router-dom";

function UsageStrip() {
  const { license } = useAuth();
  if (!license) return null;
  const { text_commands_used, text_commands_limit, tier } = license;
  if (text_commands_limit == null) {
    return (
      <p className="text-sm text-mimo-muted">
        {tier.toUpperCase()} · 今日文本指令 <span className="font-medium text-mimo-text">无限制</span>
      </p>
    );
  }
  const pct = Math.min(100, (text_commands_used / text_commands_limit) * 100);
  const over = text_commands_used >= text_commands_limit;
  return (
    <div className="mx-auto max-w-md space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-mimo-muted">今日文本指令</span>
        <span className={over ? "text-danger" : "text-mimo-text"}>
          {text_commands_used} / {text_commands_limit}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-mimo-border">
        <div
          className={`h-full transition-all ${over ? "bg-danger" : "bg-mimo-cta"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function BillingPage() {
  const { license, refreshLicense } = useAuth();
  const tier = (license?.tier ?? "lite") as TierId;

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container">
          <p className="text-sm text-mimo-muted">Token Plan</p>
          <h1 className="mimo-page-title mt-2">简单、透明的档位计划</h1>
          <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-mimo-muted">
            三档方案满足不同场景：从个人体验到企业级多模态智能体，价格清晰、无隐藏费用。
          </p>
          <div className="mt-6">
            <p className="text-sm text-mimo-muted">当前方案</p>
            <p className="mt-1 text-2xl font-semibold text-mimo-text">{tier.toUpperCase()}</p>
          </div>
          <div className="mt-6">
            <UsageStrip />
          </div>
          <button
            type="button"
            className="mimo-link-more mt-4 text-sm"
            onClick={() => void refreshLicense()}
          >
            刷新状态
          </button>
        </div>
      </section>

      <section className="mimo-section pt-0">
        <div className="mimo-container">
          <div className="grid gap-4 md:grid-cols-3">
            {TIER_PLANS.map((plan) => (
              <TierPlanCard key={plan.id} plan={plan} active={plan.id === tier} mimoStyle />
            ))}
          </div>
        </div>
      </section>

      <section className="mimo-section border-t border-mimo-border bg-mimo-surface">
        <div className="mimo-container">
          <h2 className="mimo-section-title text-xl">能力矩阵</h2>
          <div className="mt-8 overflow-x-auto rounded-2xl border border-mimo-border bg-mimo-bg">
            <CapabilityMatrixTable mimoStyle />
          </div>
        </div>
      </section>

      <section className="mimo-section border-t border-mimo-border">
        <div className="mimo-container text-center">
          <p className="text-sm text-mimo-muted">配置 API Key 后即可在 Console 使用所选模型</p>
          <Link to="/system/settings" className="mimo-btn-primary mt-4 inline-flex">
            前往接口配置
          </Link>
        </div>
      </section>
    </div>
  );
}
