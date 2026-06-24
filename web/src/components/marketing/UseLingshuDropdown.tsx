import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, ExternalLink } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";

export function UseLingshuDropdown() {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const MENU = [
    {
      title: t.menu.openPlatform,
      items: [
        { label: t.menu.docs, to: "/product/api", external: false },
        { label: t.menu.console, to: "/console/account", external: true },
      ],
    },
    {
      title: t.menu.products,
      items: [
        { label: t.menu.studio, to: "/studio", external: true },
        { label: t.menu.claw, to: "/claw", external: true },
        { label: t.menu.code, to: "/code", external: true },
      ],
    },
    {
      title: t.menu.pricing,
      items: [
        { label: t.menu.apiPricing, to: "/models", external: false },
        { label: t.menu.tokenPlan, to: "/console/points", external: true },
      ],
    },
  ] as const;

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const scheduleClose = () => {
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  };

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  return (
    <div
      ref={rootRef}
      className="relative"
      onMouseEnter={() => {
        cancelClose();
        setOpen(true);
      }}
      onMouseLeave={scheduleClose}
    >
      <button
        type="button"
        className={`mimo-btn-cta mimo-btn-sm ${open ? "mimo-btn-cta-open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {t.nav.useLingshu}
        <ChevronDown size={14} className={`ml-1 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          className="mimo-use-dropdown-bridge"
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
        >
          <div className="mimo-use-dropdown">
            {MENU.map((section, si) => (
              <div key={section.title}>
                {si > 0 && <div className="mimo-use-dropdown-divider" />}
                <p className="mimo-use-dropdown-heading">{section.title}</p>
                <ul>
                  {section.items.map((item) => (
                    <li key={item.label}>
                      <Link
                        to={item.to}
                        className="mimo-use-dropdown-item"
                        onClick={() => setOpen(false)}
                      >
                        <span>{item.label}</span>
                        {item.external && <ExternalLink size={14} className="opacity-45" />}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
