import { useMemo, useRef, useState } from "react";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";
import {
  getStudioModelBrandLabel,
  groupStudioModels,
  type StudioModelBrand,
  type StudioModelItem,
} from "@/lib/modelCatalog";
import { useLocale } from "@/context/LocaleContext";

type StudioModelPickerProps = {
  open: boolean;
  modelId: string;
  onSelect: (id: string) => void;
  /** 嵌入父级下拉面板时使用，去掉绝对定位与外层边框 */
  embedded?: boolean;
  /** 品牌子菜单展开方向，Code 右侧面板用 left */
  flyoutSide?: "left" | "right";
};

export function StudioModelPicker({
  open,
  modelId,
  onSelect,
  embedded = false,
  flyoutSide = "right",
}: StudioModelPickerProps) {
  const { locale } = useLocale();
  const groups = useMemo(() => groupStudioModels(), []);
  const [hoverBrand, setHoverBrand] = useState<StudioModelBrand | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const scheduleClose = () => {
    closeTimer.current = setTimeout(() => setHoverBrand(null), 130);
  };

  if (!open) return null;

  const FlyoutChevron = flyoutSide === "left" ? ChevronLeft : ChevronRight;
  const flyoutClass =
    flyoutSide === "left" ? "mimo-studio-model-flyout mimo-studio-model-flyout-left" : "mimo-studio-model-flyout";

  const renderModel = (m: StudioModelItem) => (
    <button
      key={m.id}
      type="button"
      className={`mimo-studio-model-option mimo-studio-model-option-compact ${
        m.id === modelId ? "mimo-studio-model-option-active" : ""
      }`}
      onClick={() => onSelect(m.id)}
    >
      <div className="min-w-0 flex-1 text-left">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{m.name}</span>
          {m.badge ? <span className="mimo-studio-badge-new">{m.badge}</span> : null}
        </div>
      </div>
      {m.id === modelId ? <Check size={15} className="shrink-0 opacity-70" /> : null}
    </button>
  );

  return (
    <div
      className={
        embedded
          ? "mimo-studio-model-menu-embedded mimo-studio-model-menu-flyout"
          : "mimo-studio-model-menu mimo-studio-model-menu-flyout"
      }
      onMouseLeave={scheduleClose}
    >
      {groups.map((group) => {
        const isActive = hoverBrand === group.brand;
        return (
          <div
            key={group.brand}
            className={`mimo-studio-model-group-row ${isActive ? "mimo-studio-model-group-row-active" : ""}`}
            onMouseEnter={() => {
              cancelClose();
              setHoverBrand(group.brand);
            }}
          >
            <div className="mimo-studio-model-group-toggle">
              <span className="flex min-w-0 flex-1 items-center gap-1.5 text-left">
                <FlyoutChevron size={14} className="shrink-0 opacity-40" />
                <span className="truncate font-medium">{getStudioModelBrandLabel(group.brand, locale)}</span>
                <span className="text-xs text-mimo-muted">({group.models.length})</span>
              </span>
            </div>

            {isActive ? (
              <div
                className={flyoutClass}
                onMouseEnter={cancelClose}
                onMouseLeave={scheduleClose}
              >
                <p className="mimo-studio-model-flyout-title">
                  {getStudioModelBrandLabel(group.brand, locale)}
                </p>
                <div className="mimo-studio-model-flyout-list">{group.models.map(renderModel)}</div>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
