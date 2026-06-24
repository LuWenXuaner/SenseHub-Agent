export type BillingCycle = "monthly" | "yearly";

export type TokenPlanTier = "lite" | "standard" | "pro" | "max";

export type TokenPlanSpec = {
  id: TokenPlanTier;
  effectiveTier: "lite" | "pro" | "max";
  tierRank: number;
  monthlyCost: number;
  yearlyCost: number;
  yearlySave: number;
  monthlyItemId: string;
  yearlyItemId: string;
  creditsLabelKey: string;
  multiplierKey?: string;
  featured?: boolean;
};

export const PLAN_FEATURE_KEYS: Record<TokenPlanTier, string[]> = {
  lite: ["featLite1", "featLite2", "featLite3", "featLite4"],
  standard: ["featStd1", "featStd2", "featStd3", "featStd4"],
  pro: ["featPro1", "featPro2", "featPro3", "featPro4", "featPro5"],
  max: ["featMax1", "featMax2", "featMax3", "featMax4", "featMax5"],
};

/** 默认档位（与后端 list_subscription_plans 一致，API 失败时回退） */
export const TOKEN_PLAN_SPECS: TokenPlanSpec[] = [
  {
    id: "lite",
    effectiveTier: "lite",
    tierRank: 0,
    monthlyCost: 800,
    yearlyCost: 8448,
    yearlySave: 1152,
    monthlyItemId: "sub-lite-month",
    yearlyItemId: "sub-lite-year",
    creditsLabelKey: "creditsLite",
  },
  {
    id: "standard",
    effectiveTier: "pro",
    tierRank: 1,
    monthlyCost: 2500,
    yearlyCost: 26400,
    yearlySave: 3600,
    monthlyItemId: "sub-standard-month",
    yearlyItemId: "sub-standard-year",
    creditsLabelKey: "creditsStandard",
    multiplierKey: "multStandard",
  },
  {
    id: "pro",
    effectiveTier: "pro",
    tierRank: 1,
    monthlyCost: 5000,
    yearlyCost: 52800,
    yearlySave: 7200,
    monthlyItemId: "sub-pro-month",
    yearlyItemId: "sub-pro-year",
    creditsLabelKey: "creditsPro",
    multiplierKey: "multPro",
  },
  {
    id: "max",
    effectiveTier: "max",
    tierRank: 2,
    monthlyCost: 20000,
    yearlyCost: 211200,
    yearlySave: 28800,
    monthlyItemId: "sub-max-month",
    yearlyItemId: "sub-max-year",
    creditsLabelKey: "creditsMax",
    multiplierKey: "multMax",
    featured: true,
  },
];

export function planSubscribeKey(id: TokenPlanTier, billing: BillingCycle): string {
  return `${id}-${billing === "monthly" ? "monthly" : "yearly"}`;
}

export type SubscribeButtonState = "subscribe" | "renew" | "upgrade" | "current" | "blocked" | "login";

export function resolveSubscribeState(
  plan: TokenPlanSpec,
  userTierRank: number,
  subscriptionActive: boolean,
  loggedIn: boolean,
): SubscribeButtonState {
  if (!loggedIn) return "login";
  if (!subscriptionActive) return "subscribe";
  if (plan.tierRank < userTierRank) return "blocked";
  if (plan.tierRank === userTierRank) return "renew";
  if (plan.tierRank > userTierRank) return "upgrade";
  return "subscribe";
}
