import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

const PAGE_SIZE = 4;

type NewsPagerProps = {
  total: number;
  children: (items: { start: number; end: number }) => ReactNode;
  className?: string;
};

/** 动态列表分页：每页 4 条，左右切换 */
export function NewsPager({ total, children, className = "" }: NewsPagerProps) {
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const [page, setPage] = useState(0);
  const safePage = Math.min(page, pageCount - 1);
  const start = safePage * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, total);

  const canPrev = safePage > 0;
  const canNext = safePage < pageCount - 1;

  const nav = useMemo(
    () => ({
      prev: () => setPage((p) => Math.max(0, p - 1)),
      next: () => setPage((p) => Math.min(pageCount - 1, p + 1)),
    }),
    [pageCount]
  );

  if (total <= PAGE_SIZE) {
    return <div className={className}>{children({ start: 0, end: total })}</div>;
  }

  return (
    <div className={className}>
      {children({ start, end })}
      <div className="mimo-news-pager-controls">
        <button
          type="button"
          className="mimo-carousel-btn-bottom"
          onClick={nav.prev}
          disabled={!canPrev}
          aria-label="上一组"
        >
          <ChevronLeft size={18} />
        </button>
        <span className="text-xs text-mimo-muted">
          {safePage + 1} / {pageCount}
        </span>
        <button
          type="button"
          className="mimo-carousel-btn-bottom"
          onClick={nav.next}
          disabled={!canNext}
          aria-label="下一组"
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

export const NEWS_HOME_LIMIT = PAGE_SIZE;
