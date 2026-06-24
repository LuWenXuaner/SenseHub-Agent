import { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Lock, Mic } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

type Tier = "lite" | "pro" | "max";
const rank: Record<Tier, number> = { lite: 0, pro: 1, max: 2 };

export function TierGate({
  requiredTier,
  children,
  mode = "block",
}: {
  requiredTier: Tier;
  children?: ReactNode;
  mode?: "block" | "nav" | "inline";
}) {
  const { license } = useAuth();
  const current = license?.tier ?? "lite";
  const allowed = rank[current] >= rank[requiredTier];

  if (allowed) return <>{children}</>;

  if (mode === "inline") {
    return (
      <button
        type="button"
        className="btn-ghost shrink-0 opacity-50"
        disabled
        title={`语音输入需要 ${requiredTier.toUpperCase()} 档位，前往档位页升级`}
        aria-label={`语音输入需要 ${requiredTier.toUpperCase()} 档位`}
      >
        <Mic size={18} aria-hidden />
      </button>
    );
  }

  if (mode === "nav") {
    return (
      <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary">
        <Lock size={16} className="shrink-0" aria-hidden />
        <span className="flex-1 truncate">{requiredTier.toUpperCase()} 功能</span>
        <Link to="/console/points" className="shrink-0 text-xs text-primary hover:underline">
          升级
        </Link>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-dashed border-border p-6">
      <div className="flex flex-col items-center justify-center gap-2 text-center">
        <Lock className="text-primary" size={24} aria-hidden />
        <p className="text-sm text-text-secondary">
          此功能需要 {requiredTier.toUpperCase()} 档位
        </p>
        <Link to="/console/points" className="btn-primary text-xs">
          查看升级
        </Link>
      </div>
    </div>
  );
}

export function UsageMeter() {
  const { license } = useAuth();
  if (!license) return null;
  const { text_commands_used, text_commands_limit, tier } = license;
  if (text_commands_limit == null) {
    return (
      <p className="text-sm text-text-secondary">
        {tier.toUpperCase()} 档位：文本指令无限制
      </p>
    );
  }
  const pct = Math.min(100, (text_commands_used / text_commands_limit) * 100);
  const over = text_commands_used >= text_commands_limit;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span>今日文本指令</span>
        <span className={over ? "text-danger" : "text-text-secondary"}>
          {text_commands_used} / {text_commands_limit}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-border">
        <div
          className={`h-full transition-all ${over ? "bg-danger" : "bg-primary"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
