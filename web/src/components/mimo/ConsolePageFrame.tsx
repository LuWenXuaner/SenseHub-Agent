import type { ReactNode } from "react";

export function ConsolePageFrame({
  title,
  subtitle,
  headNote,
  children,
  actions,
  centered,
}: {
  title: string;
  subtitle?: string;
  headNote?: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  centered?: boolean;
}) {
  return (
    <div className={`mimo-console-page ${centered ? "mimo-console-page-centered" : ""}`}>
      <div className={`mimo-console-page-head ${centered ? "text-center" : ""}`}>
        <div className={centered ? "mx-auto" : ""}>
          <h1 className="mimo-console-page-title">{title}</h1>
          {headNote}
          {subtitle && <p className="mimo-console-page-sub">{subtitle}</p>}
        </div>
        {!centered && actions}
      </div>
      {centered && actions && <div className="mb-6 flex justify-center">{actions}</div>}
      <div className={`mimo-console-page-body ${centered ? "mimo-console-page-body-centered" : ""}`}>
        {children}
      </div>
    </div>
  );
}
