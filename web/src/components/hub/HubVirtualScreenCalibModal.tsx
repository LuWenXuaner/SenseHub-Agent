import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { VirtualScreenCalibPanel } from "@/components/hub/VirtualScreenCalibPanel";

export function HubVirtualScreenCalibModal({
  open,
  onClose,
  onSaved,
  onStartCamera,
}: {
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
  onStartCamera?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="mimo-modal-overlay z-[200]" onClick={onClose} role="presentation">
      <div
        ref={ref}
        className="flex max-h-[min(92vh,820px)] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="virtual-calib-title"
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-3">
          <h2 id="virtual-calib-title" className="text-lg font-bold">
            精细校准
          </h2>
          <button
            type="button"
            className="btn-ghost rounded-lg p-2"
            onClick={onClose}
            aria-label="关闭"
          >
            <X size={18} aria-hidden />
          </button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
          <VirtualScreenCalibPanel
            active={open}
            onSaved={onSaved}
            onStartCamera={onStartCamera}
          />
        </div>
      </div>
    </div>
  );
}
