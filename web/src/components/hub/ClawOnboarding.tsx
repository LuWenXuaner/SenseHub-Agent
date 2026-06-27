import { useEffect, useState } from "react";
import { useLocale } from "@/context/LocaleContext";

const STORAGE_KEY = "sensehub:onboarding:claw:v1";

export function isClawOnboardingDone(): boolean {
  const v = localStorage.getItem(STORAGE_KEY);
  return v === "done" || v === "skipped";
}

export function resetClawOnboarding(): void {
  localStorage.removeItem(STORAGE_KEY);
}

type Props = {
  open: boolean;
  onClose: () => void;
  onFillSample?: (text: string) => void;
};

export function ClawOnboarding({ open, onClose, onFillSample }: Props) {
  const { t } = useLocale();
  const o = t.claw;
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  if (!open) return null;

  const finish = (mode: "done" | "skipped") => {
    localStorage.setItem(STORAGE_KEY, mode);
    onClose();
  };

  const steps = [
    {
      title: o.onboardingStep1Title,
      body: o.onboardingStep1Body,
      target: "claw-onboard-input",
      sample: o.onboardingSampleCommand,
    },
    {
      title: o.onboardingStep2Title,
      body: o.onboardingStep2Body,
      target: "claw-onboard-chat",
    },
    {
      title: o.onboardingStep3Title,
      body: o.onboardingStep3Body,
      target: "claw-onboard-send",
    },
  ];
  const current = steps[step];
  const rect =
    typeof document !== "undefined"
      ? document.getElementById(current.target)?.getBoundingClientRect()
      : null;

  return (
    <div className="fixed inset-0 z-[80]">
      <div className="absolute inset-0 bg-black/55" />
      {rect && (
        <div
          className="pointer-events-none absolute rounded-lg ring-2 ring-primary ring-offset-2 ring-offset-background"
          style={{
            top: rect.top - 4,
            left: rect.left - 4,
            width: rect.width + 8,
            height: rect.height + 8,
          }}
        />
      )}
      <div className="absolute bottom-6 left-1/2 w-[min(24rem,calc(100vw-2rem))] -translate-x-1/2 rounded-xl border border-border bg-surface p-4 shadow-xl">
        <p className="text-xs text-text-secondary">
          {o.onboardingProgress.replace("{n}", String(step + 1)).replace("{total}", String(steps.length))}
        </p>
        <h3 className="mt-1 text-base font-semibold text-text-primary">{current.title}</h3>
        <p className="mt-2 text-sm text-text-secondary">{current.body}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" className="btn-ghost border border-border text-sm" onClick={() => finish("skipped")}>
            {o.onboardingSkip}
          </button>
          {step > 0 && (
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
            >
              {o.onboardingBack}
            </button>
          )}
          {step === 0 && current.sample && onFillSample && (
            <button type="button" className="btn-secondary text-sm" onClick={() => onFillSample(current.sample!)}>
              {o.onboardingFillSample}
            </button>
          )}
          {step < steps.length - 1 ? (
            <button type="button" className="btn-primary text-sm" onClick={() => setStep((s) => s + 1)}>
              {o.onboardingNext}
            </button>
          ) : (
            <button type="button" className="btn-primary text-sm" onClick={() => finish("done")}>
              {o.onboardingDone}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
