import { useEffect, useRef, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { ChevronDown } from "lucide-react";

export type NavDropdownItem = {
  label: string;
  to: string;
  description?: string;
};

type MarketingNavDropdownProps = {
  label: string;
  to: string;
  items: NavDropdownItem[];
};

export function MarketingNavDropdown({ label, to, items }: MarketingNavDropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const scheduleClose = () => {
    closeTimer.current = setTimeout(() => setOpen(false), 140);
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
      <NavLink
        to={to}
        className={({ isActive }) =>
          `mimo-nav-link mimo-nav-dropdown-trigger inline-flex items-center gap-0.5 ${
            isActive || open ? "mimo-nav-link-active" : ""
          } ${open ? "mimo-nav-dropdown-open" : ""}`
        }
        onClick={(e) => {
          if (open) {
            e.preventDefault();
            setOpen(false);
          }
        }}
      >
        {label}
        <ChevronDown
          size={14}
          className={`mimo-nav-dropdown-chevron transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </NavLink>

      {open && (
        <div
          className="mimo-nav-dropdown-bridge"
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
        >
          <div className="mimo-nav-dropdown-panel">
            <ul>
              {items.map((item) => (
                <li key={`${item.to}-${item.label}`}>
                  <Link
                    to={item.to}
                    className="mimo-nav-dropdown-item"
                    onClick={() => setOpen(false)}
                  >
                    <span className="font-medium">{item.label}</span>
                    {item.description ? (
                      <span className="mt-0.5 block text-xs text-mimo-muted">{item.description}</span>
                    ) : null}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
