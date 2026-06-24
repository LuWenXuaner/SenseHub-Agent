import type { ReactNode } from "react";

/** 系统页外壳：无二级侧栏，内容区一屏内展示（不滚动页面） */
export function SystemPageLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col gap-2 overflow-hidden">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-0.5">
        <h1 className="text-lg font-bold tracking-tight">{title}</h1>
        {description && <p className="text-xs text-text-secondary">{description}</p>}
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
      {footer && <div className="shrink-0 text-xs">{footer}</div>}
    </div>
  );
}

export function SystemCard({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card flex min-h-0 flex-col gap-2 overflow-hidden p-3 ${className}`}>
      {title && <h2 className="shrink-0 text-xs font-semibold uppercase tracking-wide text-text-secondary">{title}</h2>}
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </section>
  );
}

export function CompactRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] gap-2 border-b border-border/50 py-1 text-xs last:border-0">
      <span className="text-text-secondary">{label}</span>
      <span className="truncate font-mono text-text-primary" title={typeof value === "string" ? value : undefined}>
        {value}
      </span>
    </div>
  );
}

export function StatusLine({ ok, children }: { ok?: boolean; children: ReactNode }) {
  return (
    <p className={`text-xs ${ok ? "text-success" : "text-danger"}`}>{children}</p>
  );
}
