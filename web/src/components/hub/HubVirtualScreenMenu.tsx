import { useEffect, useRef, useState } from "react";
import { ChevronDown, Crosshair, Monitor, Power, PowerOff } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "@/context/LocaleContext";

type VirtualState = {
  active: boolean;
  calibrated: boolean;
  mapping_mode?: "direct" | "homography";
  homography_calibrated?: boolean;
  show_keyboard?: boolean;
  automation_suspended?: boolean;
};

export function HubVirtualScreenMenu({
  virtual,
  onRefresh,
  onStartCamera,
  onStopCamera,
  onCalibrate,
  featureEnabled,
}: {
  virtual: VirtualState;
  onRefresh: () => void;
  onStartCamera?: () => void | Promise<void>;
  onStopCamera?: () => void;
  onCalibrate?: () => void;
  featureEnabled: boolean;
}) {
  const { t } = useLocale();
  const c = t.claw;
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const openVirtual = async () => {
    if (!featureEnabled) {
      window.alert(c.virtualMaxRequired);
      return;
    }
    setBusy(true);
    try {
      await onStartCamera?.();
      await api.virtualSessionStart();
      onRefresh();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "无法打开虚拟屏");
    } finally {
      setBusy(false);
      setOpen(false);
    }
  };

  const closeVirtual = async () => {
    setBusy(true);
    try {
      await api.virtualSessionStop();
      onRefresh();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "无法关闭虚拟屏");
    } finally {
      setBusy(false);
      setOpen(false);
    }
  };

  const goCalibrate = () => {
    if (!featureEnabled) {
      window.alert(c.virtualMaxRequired);
      return;
    }
    setOpen(false);
    onCalibrate?.();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        disabled={busy}
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs transition ${
          virtual.active
            ? "bg-primary/25 font-medium text-primary ring-1 ring-primary/45 shadow-sm"
            : featureEnabled
              ? "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
              : "text-text-secondary/60 hover:bg-surface-elevated"
        }`}
      >
        <Monitor size={12} aria-hidden />
        {c.virtual}
        {virtual.active ? c.virtualOn : c.virtualOff}
        {virtual.active && virtual.automation_suspended && (
          <span className="rounded bg-warning/20 px-1 text-[10px] text-warning">{c.virtualPaused}</span>
        )}
        {!virtual.calibrated && virtual.mapping_mode === "homography" && (
          <span className="rounded bg-warning/20 px-1 text-[10px] text-warning">{c.virtualUncalibrated}</span>
        )}
        <ChevronDown size={12} className={open ? "rotate-180" : ""} aria-hidden />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[10.5rem] rounded-lg border border-border bg-surface py-1 shadow-lg">
          {!virtual.active ? (
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-surface-elevated"
              onClick={() => void openVirtual()}
            >
              <Power size={14} aria-hidden />
              {c.virtualOpen}
            </button>
          ) : (
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-surface-elevated"
              onClick={() => void closeVirtual()}
            >
              <PowerOff size={14} aria-hidden />
              {c.virtualClose}
            </button>
          )}
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-surface-elevated"
            onClick={goCalibrate}
          >
            <Crosshair size={14} aria-hidden />
            {c.virtualCalibrate}
          </button>
        </div>
      )}
    </div>
  );
}
